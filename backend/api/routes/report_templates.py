"""报告模板管理 API"""
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_current_user
from backend.config import settings
from backend.models.database import get_db
from backend.models.report_template import ReportTemplate
from backend.parsers.template_parser import parse_pptx_template, parse_docx_template

router = APIRouter(prefix="/report-templates", tags=["templates"])

TEMPLATES_DIR = Path(settings.LOCAL_STORAGE_PATH) / ".report_templates"
MAX_FILE_SIZE = 50 * 1024 * 1024


@router.get("")
async def list_templates(
    report_type: str | None = None,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(ReportTemplate).where(ReportTemplate.user_id == user, ReportTemplate.is_active == True)
    if report_type:
        q = q.where(ReportTemplate.report_type == report_type)
    q = q.order_by(ReportTemplate.created_at.desc())
    result = await db.execute(q)
    templates = result.scalars().all()
    return [
        {
            "id": t.id, "name": t.name, "report_type": t.report_type,
            "source": t.source, "scenario_type": t.scenario_type,
            "description": t.description, "style_rules": t.style_rules,
            "content_slots": t.content_slots, "created_at": t.created_at.isoformat(),
        }
        for t in templates
    ]


@router.post("/upload")
async def upload_template(
    file: UploadFile = File(...),
    name: str = "",
    report_type: str = "ppt",
    scenario_type: str | None = None,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    suffix = Path(file.filename or "").suffix.lower()
    allowed = {".pptx": "ppt", ".docx": "docx"}
    if suffix not in allowed:
        raise HTTPException(400, f"仅支持 {list(allowed.keys())} 格式")
    if report_type not in ("ppt", "docx", "pdf"):
        raise HTTPException(400, "report_type 必须是 ppt/docx/pdf")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, "文件过大（最大 50MB）")

    user_dir = TEMPLATES_DIR / user
    user_dir.mkdir(parents=True, exist_ok=True)
    file_path = user_dir / (file.filename or "template")
    file_path.write_bytes(content)

    parsed = {}
    if suffix == ".pptx":
        parsed = parse_pptx_template(str(file_path))
    elif suffix == ".docx":
        parsed = parse_docx_template(str(file_path))

    template = ReportTemplate(
        user_id=user,
        name=name or Path(file.filename).stem,
        report_type=allowed[suffix],
        source="user_uploaded",
        original_filename=file.filename,
        template_file_path=str(file_path),
        style_rules=parsed.get("style_rules"),
        content_slots=parsed.get("content_slots"),
        scenario_type=scenario_type,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)

    return {
        "id": template.id, "name": template.name, "report_type": template.report_type,
        "style_rules": template.style_rules, "content_slots": template.content_slots,
        "slide_count": parsed.get("slide_count", 0),
    }


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ReportTemplate).where(ReportTemplate.id == template_id, ReportTemplate.user_id == user)
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(404, "Template not found")
    await db.delete(t)
    await db.commit()
    return {"deleted": template_id}
