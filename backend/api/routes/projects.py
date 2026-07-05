from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_current_user
from backend.models.database import get_db
from backend.models.project import Project

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str
    template_id: str | None = None


class ProjectOut(BaseModel):
    id: str
    name: str
    status: str
    template_id: str | None
    total_slides: int
    stage: str

    model_config = {"from_attributes": True}


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreate,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = Project(name=body.name, template_id=body.template_id, user_id=user)
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.get("", response_model=list[ProjectOut])
async def list_projects(
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).where(Project.user_id == user))
    return result.scalars().all()


class ApplyDesignTemplateRequest(BaseModel):
    template_id: str


# Static route — must be declared BEFORE /{project_id} or FastAPI treats
# "design-templates" as a project_id and returns 404.
@router.get("/design-templates")
async def list_design_templates(
    user: str = Depends(get_current_user),
):
    """List available DESIGN.md templates (built-in + user extracted)."""
    from backend.design_templates import list_templates, list_user_templates
    builtin = list_templates()
    for t in builtin:
        t["source"] = "builtin"
    user_templates = list_user_templates(user)
    for t in user_templates:
        t["source"] = "user"
    return {"templates": builtin + user_templates}


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: str,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project or project.user_id != user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.get("/{project_id}/design")
async def get_project_design(
    project_id: str,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return current DESIGN.md content (if set) + the applied template id (if any)."""
    from backend.storage.file_manager import ProjectStorage

    project = await db.get(Project, project_id)
    if not project or project.user_id != user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    design_path = ProjectStorage.get().get_project_path(project_id) / "DESIGN.md"
    content = design_path.read_text(encoding="utf-8") if design_path.exists() else None
    # Try to infer template id from first-line heading
    template_id = None
    if content:
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("# ") and "·" in line:
                # Parse the subtitle slug: e.g. "# 商务蓝 · Business Navy" → "business-navy"
                try:
                    subtitle = line.split("·", 1)[1].strip()
                    template_id = subtitle.lower().replace(" ", "-")
                except Exception:
                    pass
                break
    return {
        "project_id": project_id,
        "has_custom_design": content is not None,
        "template_id": template_id,
        "content": content,
    }


@router.post("/{project_id}/design/apply-to-all")
async def apply_design_to_all(
    project_id: str,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Re-run designer for every non-locked slide with the current DESIGN.md.

    User flow: switch design template → test on single slide → if satisfied,
    trigger this endpoint to apply to every slide.

    Returns immediately with a task_id; the actual work runs async in Celery.
    """
    from backend.tasks.revise import run_restyle_all

    project = await db.get(Project, project_id)
    if not project or project.user_id != user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    task = run_restyle_all.delay(project_id)
    return {"task_id": task.id, "status": "queued"}


@router.post("/{project_id}/design-template")
async def apply_design_template(
    project_id: str,
    body: ApplyDesignTemplateRequest,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Copy a built-in template into projects/{id}/DESIGN.md.

    Takes effect on subsequent designer runs (full generation or single-slide revise).
    To re-render all slides with the new style, trigger a new generation.
    """
    from backend.design_templates import get_template, get_user_template
    from backend.storage.file_manager import ProjectStorage

    project = await db.get(Project, project_id)
    if not project or project.user_id != user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if body.template_id.startswith("user/"):
        md = get_user_template(user, body.template_id)
        if md is None:
            raise HTTPException(status_code=404, detail=f"Template '{body.template_id}' not found")
    else:
        md = get_template(body.template_id)
        if md is None:
            raise HTTPException(status_code=404, detail=f"Template '{body.template_id}' not found")

    storage = ProjectStorage.get()
    storage.create_project_dir(project_id)
    design_path = storage.get_project_path(project_id) / "DESIGN.md"
    design_path.write_text(md, encoding="utf-8")

    return {
        "project_id": project_id,
        "template_id": body.template_id,
        "bytes_written": len(md.encode("utf-8")),
    }


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import shutil
    from backend.storage.file_manager import ProjectStorage

    project = await db.get(Project, project_id)
    if not project or project.user_id != user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Delete DB record
    await db.delete(project)
    await db.commit()

    # Delete project directory (OUTLINE, SVG, history, exports, ...)
    try:
        project_dir = ProjectStorage.get().get_project_path(project_id)
        if project_dir.exists():
            shutil.rmtree(project_dir, ignore_errors=True)
    except Exception:
        pass  # best-effort disk cleanup
