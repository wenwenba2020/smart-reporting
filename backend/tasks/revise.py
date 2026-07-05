"""单页修改 / 回退 Celery 任务 — 只重跑设计师（这一页）+ 编辑师（全部）

流程：
1. 加载 OUTLINE
2. 备份当前 SVG + slide 元数据到 history/（保留最近 3 版本）
3. 追加用户指令到目标 slide 的 visual_intent
4. 读取现有 SVG 作为 previous_svg（保持风格一致）
5. 调 generate_single_slide 重新生成这一页
6. 保存 SVG（覆盖旧文件）
7. 保存 OUTLINE
8. 重跑编辑师生成新 PPTX
9. SSE 事件贯穿全程

回退：
- run_slide_revert 恢复最近一次历史版本 + 删除该历史文件（实现逐步撤销）
"""
import json
import shutil
from datetime import datetime
from pathlib import Path

from backend.agents.events import (
    publish_agent_start, publish_agent_complete, publish_error,
    publish_event, publish_slide_status,
)
from backend.config import settings
from backend.tasks import celery_app

MAX_HISTORY = 3


def _outline_path(project_id: str) -> str:
    return str(Path(settings.LOCAL_STORAGE_PATH) / project_id / "OUTLINE.md")


def _safe(fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except Exception:
        pass


def _history_dir(project_id: str, slide_id: str) -> Path:
    return Path(settings.LOCAL_STORAGE_PATH) / project_id / "history" / f"slide_{slide_id}"


def _backup_slide(project_id: str, slide_id: str, svg_path: Path, slide) -> None:
    """Save SVG + slide metadata snapshot. Keep only last MAX_HISTORY versions."""
    history_dir = _history_dir(project_id, slide_id)
    history_dir.mkdir(parents=True, exist_ok=True)

    if not svg_path.exists():
        return

    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    try:
        shutil.copy2(svg_path, history_dir / f"{ts}.svg")
        (history_dir / f"{ts}.meta.json").write_text(
            json.dumps(slide.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        return

    # Prune old versions (keep only the newest MAX_HISTORY)
    all_svgs = sorted(history_dir.glob("*.svg"), reverse=True)
    for old in all_svgs[MAX_HISTORY:]:
        old.unlink(missing_ok=True)
        old.with_suffix(".meta.json").unlink(missing_ok=True)


@celery_app.task(bind=True, name="ppt_agent.revise_slide")
def run_slide_revision(self, project_id: str, slide_id: str, instruction: str):
    """Revise a single slide: re-run designer for that slide, re-run editor for full pptx."""
    from backend.agents.designer import DEFAULT_DESIGN, generate_single_slide
    from backend.models.outline import load_outline, save_outline
    from backend.storage.file_manager import ProjectStorage

    outline_path = _outline_path(project_id)

    try:
        # Stage-aware branching: in review stage, only update OUTLINE text fields.
        # Designer/editor are NOT invoked so the user can iterate on copy without
        # paying for SVG regeneration until the review gate is passed.
        from backend.tasks.generate import get_project_stage_sync
        from backend.agents.events import publish_slide_content_changed

        stage = get_project_stage_sync(project_id)
        if stage == "awaiting_content_review":
            from backend.models.outline import load_outline, save_outline
            outline = load_outline(outline_path)
            slide = next((s for s in outline.slides if s.slide_id == slide_id), None)
            if not slide:
                _safe(publish_error, project_id, "copywriter",
                      f"审核态单页修改：找不到 slide {slide_id}", False)
                return {"status": "not_found", "slide_id": slide_id}
            existing_intent = (slide.visual_intent or "").strip()
            revision_tag = f"[审核态修改] {instruction.strip()}"
            slide.visual_intent = (
                f"{existing_intent}\n{revision_tag}" if existing_intent else revision_tag
            )
            # No copywriter single-page rewrite API yet — patch notes_speaker so
            # the instruction surfaces on the card; users do precise edits via the
            # Modal 文字编辑 tab (W8) which uses a different endpoint.
            slide.notes_speaker = (slide.notes_speaker or "") + f"\n[修改意图] {instruction}"
            save_outline(outline, outline_path)
            _safe(publish_slide_content_changed, project_id, slide_id)
            return {"status": "content_updated", "slide_id": slide_id}

        outline = load_outline(outline_path)
        slide = next((s for s in outline.slides if s.slide_id == slide_id), None)
        if not slide:
            _safe(publish_error, project_id, "designer",
                  f"单页修改：找不到 slide {slide_id}", False)
            return {"status": "not_found", "slide_id": slide_id}

        if slide.locked:
            _safe(publish_error, project_id, "designer",
                  f"单页修改：slide {slide_id} 已锁定，无法修改", False)
            return {"status": "locked", "slide_id": slide_id}

        # Announce
        _safe(publish_event, project_id, {
            "type": "agent_thinking",
            "agent": "designer",
            "thought": f"接收单页修改指令 · slide {slide_id}：{instruction[:80]}",
        })
        _safe(publish_agent_start, project_id, "designer",
              f"重新设计 slide {slide_id}...")
        _safe(publish_slide_status, project_id, slide_id, "generating")

        # Load current SVG (full, un-truncated) as the modification base
        storage = ProjectStorage.get()
        svg_dir = storage.get_project_path(project_id) / "svg_output"
        svg_path = svg_dir / f"slide_{slide_id}.svg"
        current_svg = svg_path.read_text(encoding="utf-8") if svg_path.exists() else None

        # Backup current state BEFORE mutating slide or SVG (for undo)
        _backup_slide(project_id, slide_id, svg_path, slide)

        # Merge instruction into visual_intent so designer sees it
        existing_intent = (slide.visual_intent or "").strip()
        revision_tag = f"[用户修改指令] {instruction.strip()}"
        slide.visual_intent = (
            f"{existing_intent}\n{revision_tag}" if existing_intent else revision_tag
        )

        # Load DESIGN.md or default
        design_path = Path(settings.LOCAL_STORAGE_PATH) / project_id / "DESIGN.md"
        design_md = (
            design_path.read_text(encoding="utf-8") if design_path.is_file()
            else DEFAULT_DESIGN
        )

        # Regenerate SVG for this slide · pass current_svg so designer
        # preserves everything that's not touched by the latest instruction
        new_svg = generate_single_slide(slide, design_md, current_svg=current_svg)

        svg_dir.mkdir(parents=True, exist_ok=True)
        svg_path.write_text(new_svg, encoding="utf-8")

        slide.status = "done"
        save_outline(outline, outline_path)

        _safe(publish_slide_status, project_id, slide_id, "done")
        _safe(publish_agent_complete, project_id, "designer")

        # Re-run editor to refresh PPTX
        _safe(publish_agent_start, project_id, "editor",
              "重新打包 PPTX...")
        from backend.agents.editor import run_editor
        editor_result = run_editor(project_id, outline_path)
        _safe(publish_agent_complete, project_id, "editor",
              editor_result.get("export_path", ""))

        _safe(publish_event, project_id, {
            "type": "slide_revised",
            "slide_id": slide_id,
        })

        return {
            "status": "completed",
            "slide_id": slide_id,
            "export_path": editor_result.get("export_path", ""),
        }

    except Exception as exc:
        _safe(publish_error, project_id, "designer",
              f"单页修改失败 · slide {slide_id}：{exc}", True)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=10)
        raise


@celery_app.task(bind=True, name="ppt_agent.restyle_all")
def run_restyle_all(self, project_id: str):
    """Re-run designer for every non-locked slide with the current DESIGN.md.

    Use case: user switched design template and wants to apply the new style
    to every slide (not just the one they tested on).

    Behavior:
    - Keeps OUTLINE content (title/points/visual_intent) unchanged
    - For each done slide: backup SVG (enables undo) → reset status='todo'
    - Run designer (it reads projects/{id}/DESIGN.md which was just swapped)
    - Run editor to re-pack PPTX
    """
    from backend.agents.designer import run_designer
    from backend.agents.editor import run_editor
    from backend.models.outline import load_outline, save_outline
    from backend.storage.file_manager import ProjectStorage

    outline_path = _outline_path(project_id)
    storage = ProjectStorage.get()
    project_dir = storage.get_project_path(project_id)
    svg_dir = project_dir / "svg_output"
    design_path = project_dir / "DESIGN.md"

    try:
        outline = load_outline(outline_path)
        to_redo = [s for s in outline.slides if s.status == "done" and not s.locked]
        if not to_redo:
            _safe(publish_error, project_id, "designer",
                  "没有可重生成的页面（所有页面都已锁定或未生成）", False)
            return {"status": "nothing_to_do", "count": 0}

        _safe(publish_event, project_id, {
            "type": "agent_thinking",
            "agent": "designer",
            "thought": f"应用新设计风格，重新生成全部 {len(to_redo)} 页...",
        })

        # Phase 1: backup + reset status to 'todo' so designer picks them up
        for slide in to_redo:
            svg_path = svg_dir / f"slide_{slide.slide_id}.svg"
            _backup_slide(project_id, slide.slide_id, svg_path, slide)
            slide.status = "todo"
            _safe(publish_slide_status, project_id, slide.slide_id, "todo")
        save_outline(outline, outline_path)

        # Phase 2: run designer (reads DESIGN.md fresh)
        _safe(publish_agent_start, project_id, "designer",
              f"按新风格重绘 {len(to_redo)} 页 SVG...")
        run_designer(project_id, outline_path, str(design_path) if design_path.exists() else "")
        _safe(publish_agent_complete, project_id, "designer")

        # Phase 3: repack PPTX
        _safe(publish_agent_start, project_id, "editor", "重新打包 PPTX...")
        editor_result = run_editor(project_id, outline_path)
        _safe(publish_agent_complete, project_id, "editor",
              editor_result.get("export_path", ""))

        _safe(publish_event, project_id, {
            "type": "restyle_all_complete",
            "count": len(to_redo),
        })
        return {"status": "completed", "count": len(to_redo)}

    except Exception as exc:
        _safe(publish_error, project_id, "designer",
              f"批量应用风格失败：{exc}", True)
        raise


@celery_app.task(bind=True, name="ppt_agent.edit_slide_texts")
def run_slide_text_edit(self, project_id: str, slide_id: str, edits: list[dict]):
    """Apply manual text edits to a slide's SVG (no LLM), then repack PPTX.
    edits: [{"index": int, "new_text": str}]
    """
    from backend.agents.text_editor import apply_text_edits
    from backend.models.outline import load_outline
    from backend.storage.file_manager import ProjectStorage

    outline_path = _outline_path(project_id)
    storage = ProjectStorage.get()
    svg_path = storage.get_project_path(project_id) / "svg_output" / f"slide_{slide_id}.svg"

    try:
        if not svg_path.exists():
            _safe(publish_error, project_id, "editor",
                  f"手动编辑失败：slide {slide_id} 的 SVG 不存在", False)
            return {"status": "svg_missing", "slide_id": slide_id}

        outline = load_outline(outline_path)
        slide = next((s for s in outline.slides if s.slide_id == slide_id), None)

        _safe(publish_slide_status, project_id, slide_id, "generating")
        _safe(publish_agent_start, project_id, "editor",
              f"应用手动文字编辑到 slide {slide_id}...")

        # Backup (so undo works)
        if slide is not None:
            _backup_slide(project_id, slide_id, svg_path, slide)

        # Apply edits
        current = svg_path.read_text(encoding="utf-8")
        updated = apply_text_edits(current, edits)
        svg_path.write_text(updated, encoding="utf-8")

        _safe(publish_slide_status, project_id, slide_id, "done")

        # Repack PPTX
        from backend.agents.editor import run_editor
        editor_result = run_editor(project_id, outline_path)
        _safe(publish_agent_complete, project_id, "editor",
              editor_result.get("export_path", ""))
        _safe(publish_event, project_id, {
            "type": "slide_text_edited",
            "slide_id": slide_id,
            "count": len(edits),
        })

        return {"status": "completed", "slide_id": slide_id, "edits": len(edits)}

    except Exception as exc:
        _safe(publish_error, project_id, "editor",
              f"手动编辑失败 · slide {slide_id}：{exc}", True)
        raise


@celery_app.task(bind=True, name="ppt_agent.revert_slide")
def run_slide_revert(self, project_id: str, slide_id: str):
    """Restore the most recent history snapshot of a slide.
    After restore, re-run editor so the downloadable PPTX matches.
    The restored history file is deleted so consecutive reverts walk back further.
    """
    from backend.models.outline import SlideItem, load_outline, save_outline
    from backend.storage.file_manager import ProjectStorage

    outline_path = _outline_path(project_id)
    storage = ProjectStorage.get()
    project_dir = storage.get_project_path(project_id)
    svg_path = project_dir / "svg_output" / f"slide_{slide_id}.svg"
    history_dir = _history_dir(project_id, slide_id)

    try:
        svg_files = sorted(history_dir.glob("*.svg"), reverse=True) if history_dir.exists() else []
        if not svg_files:
            _safe(publish_error, project_id, "designer",
                  f"撤销失败 · slide {slide_id} 没有历史版本", False)
            return {"status": "no_history", "slide_id": slide_id}

        latest_svg = svg_files[0]
        latest_meta = latest_svg.with_suffix(".meta.json")

        _safe(publish_slide_status, project_id, slide_id, "generating")
        _safe(publish_agent_start, project_id, "designer",
              f"撤销 slide {slide_id} 到上一版本...")

        # Restore SVG (overwrite current)
        svg_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(latest_svg, svg_path)

        # Restore slide metadata (title, visual_intent, points 等)
        outline = load_outline(outline_path)
        if latest_meta.exists():
            try:
                meta_data = json.loads(latest_meta.read_text(encoding="utf-8"))
                for i, s in enumerate(outline.slides):
                    if s.slide_id == slide_id:
                        restored = SlideItem(**meta_data)
                        restored.status = "done"  # always mark done after revert
                        outline.slides[i] = restored
                        break
                save_outline(outline, outline_path)
            except Exception:
                pass  # meta restore is best-effort

        # Consume this history version so another revert walks further back
        latest_svg.unlink(missing_ok=True)
        latest_meta.unlink(missing_ok=True)

        _safe(publish_slide_status, project_id, slide_id, "done")
        _safe(publish_agent_complete, project_id, "designer")

        # Re-pack PPTX to match
        _safe(publish_agent_start, project_id, "editor", "重新打包 PPTX...")
        from backend.agents.editor import run_editor
        editor_result = run_editor(project_id, outline_path)
        _safe(publish_agent_complete, project_id, "editor",
              editor_result.get("export_path", ""))

        _safe(publish_event, project_id, {
            "type": "slide_reverted",
            "slide_id": slide_id,
        })

        return {"status": "completed", "slide_id": slide_id}

    except Exception as exc:
        _safe(publish_error, project_id, "designer",
              f"撤销失败 · slide {slide_id}：{exc}", True)
        raise
