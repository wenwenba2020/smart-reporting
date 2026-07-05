"""生成触发 + 三阶段规划交互 + SSE 事件推送"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_current_user, decode_token
from backend.agents.events import subscribe_events, publish_slide_content_changed
from backend.models.database import get_db
from backend.models.outline import PointItem
from backend.models.project import Project
from backend.tasks.generate import (
    run_ppt_generation, run_copywriter_only, run_designer_and_beyond,
    run_diagnosis_scan, run_diagnosis_dispatch,
)
from sqlalchemy import update

router = APIRouter(prefix="/projects", tags=["generate"])


class MessageRequest(BaseModel):
    message: str
    stage: int | None = None
    step: int | None = None  # Stage 1 question step (0-4)
    positioning: str | None = None
    positioning_answers: dict | None = None  # {"audience": "...", "scenario": "...", ...}
    outline_skeleton: list | None = None
    url_context: str | None = None


class ReviseSlideRequest(BaseModel):
    instruction: str


class SlideContentPatch(BaseModel):
    title: str | None = None
    subtitle: str | None = None
    points: list[PointItem] | None = None
    notes_speaker: str | None = None

    @field_validator("points", mode="before")
    @classmethod
    def _coerce_points(cls, v):
        """接受 list[str] / list[dict] / list[PointItem]，都转成 list[PointItem]。"""
        if v is None:
            return None
        if not isinstance(v, list):
            return v
        return [
            {"heading": x, "body": None} if isinstance(x, str) else x
            for x in v
        ]


async def _verify_ownership(project_id: str, user: str, db: AsyncSession) -> Project:
    project = await db.get(Project, project_id)
    if not project or project.user_id != user:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/{project_id}/generate")
async def trigger_generation(
    project_id: str,
    body: MessageRequest,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger copywriter-only pass. User must then confirm content before designer runs."""
    await _verify_ownership(project_id, user, db)
    task = run_copywriter_only.delay(project_id, body.message)
    return {"task_id": task.id, "status": "queued"}


@router.post("/{project_id}/slides/{slide_id}/revise")
async def revise_slide(
    project_id: str,
    slide_id: str,
    body: ReviseSlideRequest,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revise a single slide based on user instruction.
    Re-runs designer for the slide and editor for full pptx.
    """
    from pathlib import Path
    from backend.config import settings
    from backend.models.outline import load_outline
    from backend.tasks.revise import run_slide_revision

    await _verify_ownership(project_id, user, db)

    instruction = (body.instruction or "").strip()
    if not instruction:
        raise HTTPException(status_code=400, detail="指令不能为空")

    outline_path = Path(settings.LOCAL_STORAGE_PATH) / project_id / "OUTLINE.md"
    if not outline_path.exists():
        raise HTTPException(status_code=404, detail="Outline 未生成，无法修改单页")

    outline = load_outline(str(outline_path))
    slide = next((s for s in outline.slides if s.slide_id == slide_id), None)
    if not slide:
        raise HTTPException(status_code=404, detail=f"Slide {slide_id} 不存在")
    if slide.locked:
        raise HTTPException(status_code=409, detail=f"Slide {slide_id} 已锁定")

    task = run_slide_revision.delay(project_id, slide_id, instruction)
    return {"task_id": task.id, "status": "queued", "slide_id": slide_id}


@router.put("/{project_id}/slides/{slide_id}/content")
async def update_slide_content(
    project_id: str,
    slide_id: str,
    body: SlideContentPatch,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Patch OUTLINE text fields for a slide. Only allowed in awaiting_content_review stage.
    Does NOT re-run designer/editor — intended for the content-review gate UI.
    """
    from pathlib import Path
    from backend.config import settings
    from backend.models.outline import load_outline, save_outline

    project = await _verify_ownership(project_id, user, db)
    if project.stage != "awaiting_content_review":
        raise HTTPException(
            status_code=409,
            detail=f"内容编辑仅在审核态可用（当前 stage={project.stage}）",
        )

    outline_path = Path(settings.LOCAL_STORAGE_PATH) / project_id / "OUTLINE.md"
    if not outline_path.exists():
        raise HTTPException(status_code=404, detail="Outline 未生成")

    outline = load_outline(str(outline_path))
    slide = next((s for s in outline.slides if s.slide_id == slide_id), None)
    if not slide:
        raise HTTPException(status_code=404, detail=f"Slide {slide_id} 不存在")
    if slide.locked:
        raise HTTPException(status_code=409, detail=f"Slide {slide_id} 已锁定")

    # Patch only provided fields
    if body.title is not None:
        slide.title = body.title
    if body.subtitle is not None:
        slide.subtitle = body.subtitle
    if body.points is not None:
        slide.points = body.points
    if body.notes_speaker is not None:
        slide.notes_speaker = body.notes_speaker

    save_outline(outline, str(outline_path))
    publish_slide_content_changed(project_id, slide_id)

    return {"status": "updated", "slide_id": slide_id}


@router.get("/{project_id}/slides/{slide_id}/history")
async def list_slide_history(
    project_id: str,
    slide_id: str,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List available undo snapshots for a slide (most recent first, up to 3)."""
    from pathlib import Path
    from backend.config import settings

    await _verify_ownership(project_id, user, db)

    history_dir = Path(settings.LOCAL_STORAGE_PATH) / project_id / "history" / f"slide_{slide_id}"
    if not history_dir.exists():
        return {"slide_id": slide_id, "history": []}

    entries = []
    for svg_file in sorted(history_dir.glob("*.svg"), reverse=True):
        entries.append({
            "timestamp": svg_file.stem,
            "has_meta": svg_file.with_suffix(".meta.json").exists(),
        })
    return {"slide_id": slide_id, "history": entries}


class TextEditItem(BaseModel):
    index: int
    new_text: str


class EditSlideTextsRequest(BaseModel):
    edits: list[TextEditItem]


@router.get("/{project_id}/slides/{slide_id}/texts")
async def get_slide_texts(
    project_id: str,
    slide_id: str,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List editable text nodes of a slide's SVG (for manual text editing UI)."""
    from pathlib import Path
    from backend.config import settings
    from backend.agents.text_editor import extract_texts

    await _verify_ownership(project_id, user, db)

    svg_path = Path(settings.LOCAL_STORAGE_PATH) / project_id / "svg_output" / f"slide_{slide_id}.svg"
    if not svg_path.exists():
        raise HTTPException(status_code=404, detail=f"Slide {slide_id} 的 SVG 尚未生成")

    svg = svg_path.read_text(encoding="utf-8")
    return {"slide_id": slide_id, "texts": extract_texts(svg)}


@router.post("/{project_id}/slides/{slide_id}/edit-texts")
async def edit_slide_texts(
    project_id: str,
    slide_id: str,
    body: EditSlideTextsRequest,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Apply manual text edits in-place (no LLM), then async re-pack PPTX."""
    from pathlib import Path
    from backend.config import settings
    from backend.tasks.revise import run_slide_text_edit

    await _verify_ownership(project_id, user, db)

    if not body.edits:
        raise HTTPException(status_code=400, detail="没有要保存的修改")

    svg_path = Path(settings.LOCAL_STORAGE_PATH) / project_id / "svg_output" / f"slide_{slide_id}.svg"
    if not svg_path.exists():
        raise HTTPException(status_code=404, detail=f"Slide {slide_id} 的 SVG 尚未生成")

    payload = [{"index": e.index, "new_text": e.new_text} for e in body.edits]
    task = run_slide_text_edit.delay(project_id, slide_id, payload)
    return {"task_id": task.id, "status": "queued", "slide_id": slide_id, "count": len(payload)}


@router.post("/{project_id}/slides/{slide_id}/revert")
async def revert_slide(
    project_id: str,
    slide_id: str,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Undo last revision: restore the most recent history snapshot + re-pack PPTX."""
    from pathlib import Path
    from backend.config import settings
    from backend.tasks.revise import run_slide_revert

    await _verify_ownership(project_id, user, db)

    history_dir = Path(settings.LOCAL_STORAGE_PATH) / project_id / "history" / f"slide_{slide_id}"
    if not history_dir.exists() or not any(history_dir.glob("*.svg")):
        raise HTTPException(status_code=404, detail=f"Slide {slide_id} 没有可撤销的历史版本")

    task = run_slide_revert.delay(project_id, slide_id)
    return {"task_id": task.id, "status": "queued", "slide_id": slide_id}


@router.post("/{project_id}/plan")
async def plan_interact(
    project_id: str,
    body: MessageRequest,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Three-stage interactive planning. Returns planner response for each stage."""
    await _verify_ownership(project_id, user, db)

    from backend.agents.planner import (
        get_positioning_question, _fetch_urls_in_message,
        run_stage2_outline, run_stage3_details, refine_outline,
        load_project_sources,
    )

    stage = body.stage or 1
    url_context = body.url_context or ""

    # 读取已保存的源材料（URL 抓取结果 + 上传文档解析结果）
    source_context = load_project_sources(project_id)
    if source_context:
        if url_context:
            url_context += "\n\n---\n\n"
        url_context += source_context[:8000]

    # Stage 1: Step-by-step positioning questions
    if stage == 1:
        step = body.step if body.step is not None else 0
        if step == 0 and not url_context:
            url_context = _fetch_urls_in_message(body.message)
        q = get_positioning_question(step, body.message, url_context)
        if q.get("done"):
            return {"stage": 1, "done": True, "url_context": url_context}
        return {
            "stage": 1,
            "url_context": url_context[:5000],
            **q,
        }

    # Stage 2: Outline skeleton
    elif stage == 2:
        try:
            result = run_stage2_outline(
                positioning=body.positioning or "",
                user_message=body.message,
                context=url_context,
            )
            return {
                "stage": 2,
                "slides": result.get("slides", []),
                "response": f"已生成 {len(result.get('slides', []))} 页大纲骨架",
            }
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.exception("Stage 2 outline generation failed: %s", e)
            raise HTTPException(status_code=500, detail=f"大纲生成失败：{str(e)}")

    # Stage 3: Detail enrichment
    elif stage == 3:
        try:
            result = run_stage3_details(
                outline_skeleton=body.outline_skeleton or [],
                user_message=body.message,
                context=url_context,
            )
            return {
                "stage": 3,
                "slides": result.get("slides", []),
                "response": f"已完善 {len(result.get('slides', []))} 页内容详情",
            }
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.exception("Stage 3 detail enrichment failed: %s", e)
            raise HTTPException(status_code=500, detail=f"内容详情生成失败：{str(e)}")

    return {"error": "Invalid stage"}


@router.post("/{project_id}/plan/refine")
async def plan_refine(
    project_id: str,
    body: MessageRequest,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Refine outline via natural language conversation."""
    await _verify_ownership(project_id, user, db)

    from backend.agents.planner import refine_outline, load_project_sources

    current_slides = body.outline_skeleton or []
    url_context = body.url_context or ""
    source_context = load_project_sources(project_id)
    if source_context:
        if url_context:
            url_context += "\n\n---\n\n"
        url_context += source_context[:8000]

    result = refine_outline(current_slides, body.message, url_context)

    return {
        "slides": result.get("slides", []),
        "message": result.get("message", ""),
        "unchanged": result.get("unchanged", False),
    }


@router.post("/{project_id}/confirm")
async def confirm_and_generate(
    project_id: str,
    body: MessageRequest,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Finalize outline and trigger full generation pipeline."""
    await _verify_ownership(project_id, user, db)

    from pathlib import Path
    from datetime import datetime, timezone
    from backend.config import settings
    from backend.models.outline import OutlineDoc, OutlineMeta, SlideItem, save_outline
    from backend.storage.file_manager import ProjectStorage

    slides_data = body.outline_skeleton or []
    if not slides_data:
        raise HTTPException(status_code=400, detail="No outline to confirm")

    # Persist outline to OUTLINE.md
    storage = ProjectStorage.get()
    storage.create_project_dir(project_id)
    outline_path = str(storage.get_project_path(project_id) / "OUTLINE.md")

    now = datetime.now(timezone.utc).isoformat()
    slides = []
    for s in slides_data:
        if not isinstance(s, dict):
            continue
        # Validate required fields
        slide_id = s.get("slide_id")
        if not slide_id:
            continue
        slides.append(SlideItem(
            slide_id=str(slide_id),
            layout=s.get("layout", "title-content"),
            title=s.get("title", ""),
            subtitle=s.get("subtitle"),
            points=s.get("points", []),
            visual_intent=s.get("visual_intent"),
            status="todo",
        ))

    # Defensive: ensure we have at least one slide
    if not slides:
        raise HTTPException(
            status_code=400,
            detail=f"无效的大纲数据：收到 {len(slides_data)} 条，但无有效幻灯片"
        )

    outline = OutlineDoc(
        meta=OutlineMeta(
            title=slides[0].title if slides else "Untitled",
            total_slides=len(slides),
            status="confirmed",
            created_at=now,
            updated_at=now,
        ),
        slides=slides,
    )
    save_outline(outline, outline_path)

    # Sync total_slides to database
    await db.execute(
        update(Project)
        .where(Project.id == project_id)
        .values(total_slides=len(slides))
    )
    await db.commit()

    # Verify the file was written correctly
    from backend.models.outline import load_outline
    try:
        saved = load_outline(outline_path)
        if len(saved.slides) != len(slides):
            raise RuntimeError(f"文件验证失败：期望 {len(slides)} 页，实际保存 {len(saved.slides)} 页")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"大纲保存失败：{e}")

    # Trigger full pipeline: copywriter → designer → effects → editor
    task = run_ppt_generation.delay(project_id, "confirmed_outline")
    return {"task_id": task.id, "status": "generating", "slides_count": len(slides)}


@router.get("/{project_id}/outline")
async def get_outline(
    project_id: str,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from pathlib import Path
    from backend.config import settings
    await _verify_ownership(project_id, user, db)

    outline_path = Path(settings.LOCAL_STORAGE_PATH) / project_id / "OUTLINE.md"
    if not outline_path.exists():
        raise HTTPException(status_code=404, detail="Outline not yet generated")

    from backend.models.outline import load_outline
    outline = load_outline(str(outline_path))
    return {"meta": outline.meta.model_dump(), "slides": [s.model_dump() for s in outline.slides]}


@router.get("/{project_id}/stream")
async def stream_events(
    project_id: str,
    token: str = Query(default=""),
    db: AsyncSession = Depends(get_db),
):
    if not token:
        raise HTTPException(status_code=401, detail="Token required")
    user = decode_token(token)
    await _verify_ownership(project_id, user, db)
    return StreamingResponse(
        subscribe_events(project_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.post("/{project_id}/content/confirm")
async def confirm_content(
    project_id: str,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """User confirmed the copywriter output. Transition stage atomically and kick designer."""
    await _verify_ownership(project_id, user, db)

    result = await db.execute(
        update(Project)
        .where(Project.id == project_id, Project.stage == "awaiting_content_review")
        .values(stage="designing")
    )
    await db.commit()

    if result.rowcount == 0:
        raise HTTPException(
            status_code=409,
            detail="项目不在 awaiting_content_review 状态",
        )

    task = run_designer_and_beyond.delay(project_id)
    return {"task_id": task.id, "status": "queued"}


# ---------- Diagnosis endpoints ----------


class DiagnoseRequest(BaseModel):
    message: str


class DiagnoseApplyRequest(BaseModel):
    diagnosis_report: dict


@router.post("/{project_id}/diagnose")
async def trigger_diagnosis(
    project_id: str,
    body: DiagnoseRequest,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger diagnosis scan on the current outline.

    Accepts vague user feedback (e.g. "content is thin", "design feels off")
    and runs planner diagnosis to produce a structured issues report.
    Returns a Celery task_id; subscribe to SSE for real-time report delivery.
    """
    from pathlib import Path
    from backend.config import settings

    project = await _verify_ownership(project_id, user, db)

    outline_path = Path(settings.LOCAL_STORAGE_PATH) / project_id / "OUTLINE.md"
    if not outline_path.exists():
        raise HTTPException(status_code=404, detail="Outline 尚未生成，无法诊断")

    if project.stage in ("idle",):
        raise HTTPException(
            status_code=409,
            detail=f"当前阶段 ({project.stage}) 不支持诊断",
        )

    task = run_diagnosis_scan.delay(project_id, body.message)
    return {"task_id": task.id, "status": "scanning"}


@router.post("/{project_id}/diagnose/apply")
async def apply_diagnosis_fixes(
    project_id: str,
    body: DiagnoseApplyRequest,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Apply confirmed diagnosis fixes.

    Accepts the diagnosis_report (possibly filtered by user) and dispatches
    parallel content fixes + sequential design fixes. Subscribe to SSE for
    per-slide progress events (diagnosis_fix_progress / diagnosis_complete).
    """
    await _verify_ownership(project_id, user, db)

    report = body.diagnosis_report
    if not report or not report.get("issues"):
        raise HTTPException(status_code=400, detail="diagnosis_report 不能为空")

    task = run_diagnosis_dispatch.delay(project_id, report)
    return {"task_id": task.id, "status": "dispatching", "issues_count": len(report["issues"])}
