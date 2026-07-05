"""PPT 生成 Celery 任务 — 拆分为"文案"与"设计+后续"两段，中间由用户审核闸门隔开。"""
import logging
from pathlib import Path

from backend.agents.events import (
    publish_agent_start, publish_agent_complete, publish_error, publish_event,
    publish_content_ready, publish_stage_change, publish_slide_status,
    publish_diagnosis_start, publish_diagnosis_report,
    publish_diagnosis_fix_progress, publish_diagnosis_complete,
)
from backend.config import settings
from backend.tasks import celery_app

logger = logging.getLogger(__name__)


def _resolve_outline_path(project_id: str) -> str:
    return str(Path(settings.LOCAL_STORAGE_PATH) / project_id / "OUTLINE.md")


def _publish_safe(fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except Exception:
        pass


def _publish_handoff(project_id: str, from_agent: str, to_agent: str, detail: str):
    _publish_safe(publish_event, project_id, {
        "type": "agent_handoff",
        "from_agent": from_agent,
        "to_agent": to_agent,
        "detail": detail,
    })


# ---------- stage helpers (sync, Celery context) ----------

def set_project_stage_sync(project_id: str, new_stage: str) -> None:
    """同步设置 project.stage（Celery worker 用）。"""
    import asyncio
    from sqlalchemy import update
    from backend.models.database import async_session
    from backend.models.project import Project

    async def _run():
        async with async_session() as db:
            await db.execute(
                update(Project).where(Project.id == project_id).values(stage=new_stage)
            )
            await db.commit()

    asyncio.run(_run())
    _publish_safe(publish_stage_change, project_id, new_stage)


def get_project_stage_sync(project_id: str) -> str:
    import asyncio
    from backend.models.database import async_session
    from backend.models.project import Project

    async def _run():
        async with async_session() as db:
            p = await db.get(Project, project_id)
            return p.stage if p else "idle"

    return asyncio.run(_run())


def cas_stage_sync(project_id: str, from_stage: str, to_stage: str) -> bool:
    """原子 compare-and-swap：仅当当前 stage==from_stage 时切到 to_stage。返回是否成功。"""
    import asyncio
    from sqlalchemy import update
    from backend.models.database import async_session
    from backend.models.project import Project

    async def _run():
        async with async_session() as db:
            result = await db.execute(
                update(Project)
                .where(Project.id == project_id, Project.stage == from_stage)
                .values(stage=to_stage)
            )
            await db.commit()
            return result.rowcount > 0

    ok = asyncio.run(_run())
    if ok:
        _publish_safe(publish_stage_change, project_id, to_stage)
    return ok


# ---------- Task 1: copywriter only ----------

@celery_app.task(bind=True, name="ppt_agent.copywriter_only", max_retries=2, default_retry_delay=30)
def run_copywriter_only(self, project_id: str, user_message: str):
    outline_path = _resolve_outline_path(project_id)
    try:
        set_project_stage_sync(project_id, "copywriting")

        _publish_safe(publish_agent_start, project_id, "copywriter", "正在填充各页文案...")
        _publish_safe(publish_event, project_id, {
            "type": "agent_thinking",
            "agent": "copywriter",
            "thought": "阅读大纲结构，准备为每一页撰写精炼内容...",
        })

        from backend.agents.copywriter import run_copywriter
        copy_result = run_copywriter(project_id, outline_path)
        completed = copy_result.get("completed_slides", [])

        _publish_safe(publish_agent_complete, project_id, "copywriter")
        _publish_handoff(project_id, "copywriter", "user",
                         f"已完成 {len(completed)} 页文案，请在右侧预览中确认")

        set_project_stage_sync(project_id, "awaiting_content_review")
        _publish_safe(publish_content_ready, project_id)

        return {"project_id": project_id, "status": "awaiting_content_review",
                "completed_slides": completed}

    except Exception as exc:
        _publish_safe(publish_error, project_id, "copywriter", str(exc), False)
        set_project_stage_sync(project_id, "failed")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        raise


# ---------- Task 2: designer → effects → editor ----------

@celery_app.task(bind=True, name="ppt_agent.designer_and_beyond", max_retries=2, default_retry_delay=30)
def run_designer_and_beyond(self, project_id: str):
    outline_path = _resolve_outline_path(project_id)

    # Guard: must be in awaiting_content_review OR already designing (idempotent re-entry after CAS by API)
    current = get_project_stage_sync(project_id)
    if current not in ("awaiting_content_review", "designing"):
        _publish_safe(publish_error, project_id, "system",
                      f"无法进入设计阶段：当前 stage={current}", False)
        return {"project_id": project_id, "status": "invalid_stage", "current_stage": current}

    try:
        if current == "awaiting_content_review":
            set_project_stage_sync(project_id, "designing")

        # ---- Designer ----
        _publish_safe(publish_agent_start, project_id, "designer", "开始逐页生成 SVG 排版...")
        _publish_safe(publish_event, project_id, {
            "type": "agent_thinking", "agent": "designer",
            "thought": "读取文案内容和设计规范，按照页面布局类型逐页生成 SVG...",
        })

        from backend.agents.designer import run_designer
        design_path = str(Path(settings.LOCAL_STORAGE_PATH) / project_id / "DESIGN.md")
        design_result = run_designer(project_id, outline_path, design_path)
        designed = design_result.get("completed_slides", [])
        failed = design_result.get("failed_slides", [])

        _publish_safe(publish_agent_complete, project_id, "designer")

        if failed:
            _publish_safe(publish_event, project_id, {
                "type": "agent_thinking", "agent": "designer",
                "thought": f"⚠️ {len(failed)} 页排版失败（{', '.join(failed)}），其余 {len(designed)} 页已完成",
            })

        _publish_handoff(project_id, "designer", "effects",
                         f"{len(designed)} 页 SVG 已生成，检查是否需要注入图表")

        # ---- Effects ----
        _publish_safe(publish_agent_start, project_id, "effects", "检查图表需求...")

        from backend.agents.effects import run_effects
        effects_result = run_effects(project_id, outline_path)
        charts = effects_result.get("charts_generated", [])

        _publish_safe(publish_event, project_id, {
            "type": "agent_thinking", "agent": "effects",
            "thought": f"已生成 {len(charts)} 个数据图表" if charts else "本次无图表需求，跳过",
        })

        _publish_safe(publish_agent_complete, project_id, "effects")
        _publish_handoff(project_id, "effects", "editor",
                         "所有内容就绪，开始转换为 PPTX 文件")

        # ---- Editor ----
        _publish_safe(publish_agent_start, project_id, "editor", "SVG → PPTX 转换中...")
        _publish_safe(publish_event, project_id, {
            "type": "agent_thinking", "agent": "editor",
            "thought": "调用 ppt-master 将 SVG 转换为 DrawingML 原生可编辑格式...",
        })

        from backend.agents.editor import run_editor
        editor_result = run_editor(project_id, outline_path)
        export_path = editor_result.get("export_path", "")

        _publish_safe(publish_agent_complete, project_id, "editor", export_path)

        if editor_result.get("warnings"):
            for w in editor_result["warnings"]:
                _publish_safe(publish_event, project_id, {
                    "type": "agent_thinking", "agent": "editor", "thought": f"⚠️ {w}",
                })

        _publish_safe(publish_event, project_id, {
            "type": "generation_complete",
            "export_url": f"/projects/{project_id}/download",
        })

        set_project_stage_sync(project_id, "completed")
        return {"project_id": project_id, "status": "completed", "export_path": export_path}

    except Exception as exc:
        _publish_safe(publish_error, project_id, "system", str(exc), False)
        set_project_stage_sync(project_id, "failed")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        raise


# ---------- Diagnosis: scan + parallel dispatch ----------


def _build_task_queue(diagnosis_report: dict) -> list[dict]:
    """Parse diagnosis_report issues into a task_queue for dispatch.

    Each issue has: dimension, description, affected_slides, fix_proposal.
    Maps to: [{agent, slide_id, action, params}].
    """
    issues = diagnosis_report.get("issues", [])
    if not isinstance(issues, list):
        return []

    task_queue: list[dict] = []
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        dimension = (issue.get("dimension") or "").lower()
        fix_proposal = issue.get("fix_proposal", "")
        affected = issue.get("affected_slides", [])
        if not isinstance(affected, list):
            continue

        agent = "copywriter" if dimension in ("content", "structure", "copy") else "designer"

        for slide_id in affected:
            task_queue.append({
                "agent": agent,
                "slide_id": str(slide_id),
                "action": "revise",
                "params": {
                    "instruction": fix_proposal,
                    "dimension": dimension,
                    "description": issue.get("description", ""),
                },
            })

    return task_queue


def _snapshot_outline(project_id: str) -> str | None:
    """Save a timestamped copy of OUTLINE.md before diagnosis fixes. Returns snapshot path."""
    import shutil
    from datetime import datetime, timezone
    outline_path = Path(settings.LOCAL_STORAGE_PATH) / project_id / "OUTLINE.md"
    if not outline_path.exists():
        return None
    snap_dir = Path(settings.LOCAL_STORAGE_PATH) / project_id / "snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    snap_path = snap_dir / f"OUTLINE_{ts}.md"
    shutil.copy2(outline_path, snap_path)
    return str(snap_path)


def _fix_slide_content(project_id: str, slide_id: str, instruction: str) -> dict:
    """Re-run copywriter for a single slide. Returns {slide_id, status, error?}."""
    from backend.agents.copywriter import _generate_slide_content
    from backend.models.outline import load_outline, save_outline

    outline_path = str(Path(settings.LOCAL_STORAGE_PATH) / project_id / "OUTLINE.md")
    outline = load_outline(outline_path)
    slide = next((s for s in outline.slides if s.slide_id == slide_id), None)

    if not slide:
        return {"slide_id": slide_id, "status": "not_found", "error": f"Slide {slide_id} 不存在"}
    if slide.locked:
        return {"slide_id": slide_id, "status": "skipped", "error": "Slide locked"}

    content = _generate_slide_content(
        slide_id=slide_id,
        layout=slide.layout,
        visual_intent=(slide.visual_intent or "") + f"\n[诊断修复] {instruction}",
        existing_title=slide.title,
    )

    if content:
        if "title" in content:
            slide.title = content["title"][:15]
        if "subtitle" in content:
            slide.subtitle = content.get("subtitle")
        if "points" in content:
            from backend.models.outline import PointItem
            raw_points = content["points"][:5]
            slide.points = [
                PointItem(
                    heading=str(p.get("heading", ""))[:30] if isinstance(p, dict) else str(p)[:30],
                    body=p.get("body") if isinstance(p, dict) and p.get("body") else None,
                )
                for p in raw_points
            ]
        if "notes_speaker" in content:
            slide.notes_speaker = content["notes_speaker"]

        save_outline(outline, outline_path)
        return {"slide_id": slide_id, "status": "fixed"}

    return {"slide_id": slide_id, "status": "failed", "error": "LLM returned empty response"}


def _fix_slide_design(project_id: str, slide_id: str, instruction: str) -> dict:
    """Re-run designer for a single slide. Sequential only — caller must not call concurrently."""
    from backend.agents.designer import DEFAULT_DESIGN, generate_single_slide
    from backend.models.outline import load_outline, save_outline

    outline_path = str(Path(settings.LOCAL_STORAGE_PATH) / project_id / "OUTLINE.md")
    outline = load_outline(outline_path)
    slide = next((s for s in outline.slides if s.slide_id == slide_id), None)

    if not slide:
        return {"slide_id": slide_id, "status": "not_found", "error": f"Slide {slide_id} 不存在"}
    if slide.locked:
        return {"slide_id": slide_id, "status": "skipped", "error": "Slide locked"}

    svg_path = Path(settings.LOCAL_STORAGE_PATH) / project_id / "svg_output" / f"slide_{slide_id}.svg"
    current_svg = svg_path.read_text(encoding="utf-8") if svg_path.exists() else None

    existing_intent = (slide.visual_intent or "").strip()
    slide.visual_intent = (
        f"{existing_intent}\n[诊断修复] {instruction}" if existing_intent else f"[诊断修复] {instruction}"
    )

    design_path = Path(settings.LOCAL_STORAGE_PATH) / project_id / "DESIGN.md"
    design_md = design_path.read_text(encoding="utf-8") if design_path.is_file() else DEFAULT_DESIGN

    # Snapshot current SVG before overwriting
    if svg_path.exists():
        import shutil
        from datetime import datetime, timezone
        snap_dir = Path(settings.LOCAL_STORAGE_PATH) / project_id / "snapshots"
        snap_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        shutil.copy2(svg_path, snap_dir / f"slide_{slide_id}_{ts}.svg")

    try:
        new_svg = generate_single_slide(slide, design_md, current_svg=current_svg)
        svg_path.parent.mkdir(parents=True, exist_ok=True)
        svg_path.write_text(new_svg, encoding="utf-8")
        slide.status = "done"
        save_outline(outline, outline_path)
        return {"slide_id": slide_id, "status": "fixed"}
    except Exception as e:
        return {"slide_id": slide_id, "status": "failed", "error": str(e)}


@celery_app.task(bind=True, name="ppt_agent.diagnosis_scan", max_retries=1)
def run_diagnosis_scan(self, project_id: str, user_message: str):
    """Run planner diagnosis mode and publish the report via SSE."""
    from backend.agents.planner import run_diagnose_mode

    outline_path = str(Path(settings.LOCAL_STORAGE_PATH) / project_id / "OUTLINE.md")

    try:
        _publish_safe(publish_diagnosis_start, project_id)
        _publish_safe(publish_event, project_id, {
            "type": "agent_thinking",
            "agent": "planner",
            "thought": "正在逐页分析内容质量和设计一致性...",
        })

        report = run_diagnose_mode(user_message, outline_path)

        issues = report.get("issues", [])
        _publish_safe(publish_diagnosis_report, project_id, report)
        _publish_safe(publish_event, project_id, {
            "type": "agent_thinking",
            "agent": "planner",
            "thought": f"诊断完成，发现 {len(issues)} 个问题",
        })

        return {
            "project_id": project_id,
            "status": "completed",
            "issues_count": len(issues),
            "report": report,
        }

    except Exception as exc:
        _publish_safe(publish_error, project_id, "planner", str(exc), False)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        raise


@celery_app.task(bind=True, name="ppt_agent.diagnosis_dispatch", max_retries=1)
def run_diagnosis_dispatch(self, project_id: str, diagnosis_report: dict):
    """Dispatch diagnosis fixes. Content fixes first (sequential, each load-modify-save OUTLINE.md),
    followed by design fixes (sequential due to cross-slide style consistency)."""
    task_queue = _build_task_queue(diagnosis_report)

    if not task_queue:
        _publish_safe(publish_diagnosis_complete, project_id, {"fixed": 0, "errors": []})
        return {"project_id": project_id, "status": "nothing_to_fix"}

    content_tasks = [t for t in task_queue if t["agent"] == "copywriter"]
    design_tasks = [t for t in task_queue if t["agent"] == "designer"]

    _publish_safe(publish_event, project_id, {
        "type": "agent_thinking",
        "agent": "route_handler",
        "thought": f"诊断修复开始：{len(content_tasks)} 项内容修复，{len(design_tasks)} 项设计修复",
    })

    # Snapshot outline before any modifications
    snap_path = _snapshot_outline(project_id)

    results: list[dict] = []

    # Phase 1: Content fixes sequentially (each does load-modify-save on OUTLINE.md)
    if content_tasks:
        _publish_safe(publish_event, project_id, {
            "type": "agent_thinking",
            "agent": "route_handler",
            "thought": f"顺序执行 {len(content_tasks)} 项内容修复...",
        })

        for task in content_tasks:
            slide_id = task["slide_id"]
            instruction = task["params"]["instruction"]
            _publish_safe(publish_diagnosis_fix_progress, project_id, slide_id, "fixing",
                         f"修复文案: {instruction[:60]}")
            try:
                result = _fix_slide_content(project_id, slide_id, instruction)
            except Exception as e:
                result = {"slide_id": slide_id, "status": "failed", "error": str(e)}
            if result.get("status") == "fixed":
                _publish_safe(publish_diagnosis_fix_progress, project_id, slide_id, "done",
                             "文案修复完成")
                _publish_safe(publish_slide_status, project_id, slide_id, "done")
            else:
                _publish_safe(publish_diagnosis_fix_progress, project_id, slide_id, "failed",
                             result.get("error", "未知错误"))
            results.append(result)

    # Phase 2: Design fixes sequentially (designer constraint)
    if design_tasks:
        _publish_safe(publish_event, project_id, {
            "type": "agent_thinking",
            "agent": "route_handler",
            "thought": f"顺序执行 {len(design_tasks)} 项设计修复（遵守 Designer 顺序约束）...",
        })

        for task in design_tasks:
            slide_id = task["slide_id"]
            instruction = task["params"]["instruction"]
            _publish_safe(publish_diagnosis_fix_progress, project_id, slide_id, "fixing",
                         f"修复设计: {instruction[:60]}")
            result = _fix_slide_design(project_id, slide_id, instruction)
            if result.get("status") == "fixed":
                _publish_safe(publish_diagnosis_fix_progress, project_id, slide_id, "done",
                             "设计修复完成")
                _publish_safe(publish_slide_status, project_id, slide_id, "done")
            else:
                _publish_safe(publish_diagnosis_fix_progress, project_id, slide_id, "failed",
                             result.get("error", "未知错误"))
            results.append(result)

    # Phase 3: Repack PPTX if any fixes succeeded
    fixed_count = sum(1 for r in results if r.get("status") == "fixed")
    errors = [r for r in results if r.get("status") not in ("fixed", "skipped")]

    if fixed_count > 0:
        _publish_safe(publish_agent_start, project_id, "editor", "诊断修复后重新打包 PPTX...")
        try:
            from backend.agents.editor import run_editor
            editor_result = run_editor(project_id, str(Path(settings.LOCAL_STORAGE_PATH) / project_id / "OUTLINE.md"))
            _publish_safe(publish_agent_complete, project_id, "editor", editor_result.get("export_path", ""))
        except Exception as e:
            _publish_safe(publish_error, project_id, "editor", str(e), True)

    summary = {
        "fixed": fixed_count,
        "skipped": sum(1 for r in results if r.get("status") == "skipped"),
        "failed": len(errors),
        "errors": [{"slide_id": e["slide_id"], "error": e.get("error", "")} for e in errors],
    }
    _publish_safe(publish_diagnosis_complete, project_id, summary)

    return {"project_id": project_id, "status": "completed", **summary}


# ---------- Backward compat shim (not called by API anymore) ----------

@celery_app.task(bind=True, name="ppt_agent.generate", max_retries=0)
def run_ppt_generation(self, project_id: str, user_message: str):
    """Deprecated — use run_copywriter_only + user confirm + run_designer_and_beyond instead."""
    return run_copywriter_only.run(project_id, user_message)
