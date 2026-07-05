"""编辑师智能体 — SVG → PPTX 转换 + 字体嵌入（不用 LLM，调脚本）

流水线：
1. flatten_fills: url(#gradient) → 首个 stop 纯色（ppt-master 不认识 gradient）
2. finalize_svg.py（SVG 后处理，可选）
3. svg_to_pptx.py（SVG → DrawingML 原生可编辑）
4. embed_fonts_in_pptx（字体嵌入）
"""
import logging
from pathlib import Path

from backend.agents.events import publish_agent_complete, publish_agent_progress, publish_error
from backend.agents.svg_flatten import sanitize_for_pptx
from backend.pipeline.font_manager import embed_fonts_in_pptx, get_fonts_for_template
from backend.pipeline.svg_to_pptx import convert_all_to_pptx, finalize_svgs

logger = logging.getLogger(__name__)


def _sanitize_svgs_in_place(dir_path: Path) -> int:
    """Sanitize every SVG inside dir_path (in place) for ppt-master compatibility:
    - Flatten url(#gradient) fills to first stop color
    - Escape stray '&' inside <text>/<tspan> bodies (LLMs sometimes forget)

    Must run AFTER finalize_svgs() which rebuilds svg_final/ from svg_output/.
    """
    if not dir_path.exists():
        return 0
    count = 0
    for svg_file in dir_path.glob("*.svg"):
        try:
            original = svg_file.read_text(encoding="utf-8")
            sanitized = sanitize_for_pptx(original)
            if sanitized != original:
                svg_file.write_text(sanitized, encoding="utf-8")
            count += 1
        except Exception as e:
            logger.warning("sanitize failed for %s: %s", svg_file.name, e)
    return count


def run_editor(project_id: str, outline_path: str, template_id: str = "business-blue") -> dict:
    """Run the full SVG → PPTX pipeline. Returns path to final PPTX."""
    from backend.storage.file_manager import ProjectStorage

    storage = ProjectStorage.get()
    project_path = str(storage.get_project_path(project_id))
    project_dir = Path(project_path)
    exports_dir = project_dir / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)

    warnings: list[str] = []

    # Step 1: ppt-master finalize (rebuilds svg_final/ from svg_output/, embeds icons, etc.)
    publish_agent_progress(project_id, "editor", 0.2, "SVG 后处理中...")
    svg_final_dir = project_dir / "svg_final"
    try:
        finalize_svgs(project_path)
    except RuntimeError as e:
        logger.warning("finalize_svg failed: %s; falling back to manual copy", e)
        warnings.append(f"SVG 后处理失败: {e}")
        # Manual copy as fallback (same as finalize_svg.py lines 148-150)
        import shutil as _sh
        if svg_final_dir.exists():
            _sh.rmtree(svg_final_dir)
        _sh.copytree(project_dir / "svg_output", svg_final_dir)

    # Step 1b: sanitize SVGs in svg_final/ (flatten gradient url(#) + escape stray '&').
    # Must run AFTER finalize_svgs which rebuilds svg_final/ from svg_output/.
    publish_agent_progress(project_id, "editor", 0.4, "SVG 兼容性清理...")
    sanitized = _sanitize_svgs_in_place(svg_final_dir)
    logger.info("sanitized %d SVG files in svg_final/", sanitized)

    # Step 2: SVG → PPTX conversion from svg_final/ (already sanitized).
    # NO fallback to source="output" — the raw svg_output/ has url(#...) refs
    # that ppt-master can't handle; falling back just masks the real error.
    publish_agent_progress(project_id, "editor", 0.5, "转换为 PPTX...")
    native_path = convert_all_to_pptx(project_path, source="final")

    # Step 3: Embed fonts
    publish_agent_progress(project_id, "editor", 0.8, "嵌入字体...")
    fonts = get_fonts_for_template(template_id)
    existing_fonts = [f for f in fonts if f.exists()]

    final_path = native_path
    if existing_fonts:
        try:
            final_path = embed_fonts_in_pptx(native_path, existing_fonts)
        except Exception as e:
            logger.error("Font embedding failed: %s", e, exc_info=True)
            warnings.append(f"字体嵌入失败: {e}")
            publish_error(project_id, "editor", f"字体嵌入失败，PPTX 可能在无字体环境显示异常: {e}", recoverable=True)
    else:
        warnings.append("未找到可嵌入的字体文件")

    publish_agent_complete(project_id, "editor", final_path)

    return {
        "export_path": final_path,
        "native_path": native_path,
        "warnings": warnings,
    }
