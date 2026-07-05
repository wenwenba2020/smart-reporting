"""W2-5: SVG → PPTX 转换器 — 封装 ppt-master 脚本 + 增量更新"""
import subprocess
import sys
from pathlib import Path

from pptx import Presentation

from backend.config import settings


def _run_ppt_master_script(script_name: str, *args: str) -> tuple[int, str, str]:
    """Run a ppt-master script using the current Python interpreter."""
    script = str(Path(settings.PPT_MASTER_SKILL_DIR) / "scripts" / script_name)

    result = subprocess.run(
        [sys.executable, script, *args],
        capture_output=True,
        text=True,
        cwd=str(Path(settings.PPT_MASTER_SKILL_DIR).parent.parent.parent),
    )
    return result.returncode, result.stdout, result.stderr


def finalize_svgs(project_path: str) -> None:
    """Run SVG post-processing (path optimization, font check)."""
    code, stdout, stderr = _run_ppt_master_script("finalize_svg.py", project_path)
    if code != 0:
        raise RuntimeError(f"finalize_svg.py failed: {stderr}")


def convert_all_to_pptx(
    project_path: str,
    source: str = "final",
    output: str | None = None,
) -> str:
    """
    Full conversion: all SVG pages → one PPTX.
    Returns path to native.pptx.

    Note: ppt-master may return non-zero exit code when some slides fail
    but still produce a valid PPTX with the successful ones. We check
    for the output file rather than relying solely on exit code.
    """
    exports_dir = Path(project_path) / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)

    if output is None:
        output = str(exports_dir / "native.pptx")

    args = [project_path, "-s", source, "-o", output]
    code, stdout, stderr = _run_ppt_master_script("svg_to_pptx.py", *args)

    output_path = Path(output)
    if code != 0 and not output_path.exists():
        raise RuntimeError(f"svg_to_pptx.py failed (no output): {stderr or stdout}")

    if not output_path.exists():
        raise RuntimeError(f"svg_to_pptx.py produced no output file")

    return output


def convert_native_only(project_path: str, source: str = "final") -> str:
    """Generate only the native DrawingML version (no SVG reference)."""
    exports_dir = Path(project_path) / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    output = str(exports_dir / "native.pptx")

    args = [project_path, "-s", source, "--only", "native", "-o", output]
    code, stdout, stderr = _run_ppt_master_script("svg_to_pptx.py", *args)
    if code != 0:
        raise RuntimeError(f"svg_to_pptx.py failed: {stderr}")

    return output


def update_single_slide(pptx_path: str, slide_index: int, new_svg_path: str) -> None:
    """
    Incremental update: replace a single slide's content in an existing PPTX.
    WARNING: Does NOT delete the slide object — clears content and rebuilds in-place.

    TODO: Week 3 — integrate with ppt-master's native DrawingML converter.
    Currently raises NotImplementedError until the editor agent is implemented.
    """
    raise NotImplementedError(
        "Single-slide incremental update requires ppt-master's DrawingML converter. "
        "Will be implemented in Week 3 with the editor agent."
    )


def run_full_pipeline(project_path: str) -> str:
    """
    Complete generation pipeline as described in ppt-pipeline.md:
    1. finalize_svg.py (SVG post-processing)
    2. svg_to_pptx.py (SVG → DrawingML)
    3. embed_fonts_in_pptx (font embedding)
    Returns path to the final embedded PPTX.
    """
    from backend.pipeline.font_manager import embed_fonts_in_pptx, get_fonts_for_template

    # Step 1: SVG post-processing
    finalize_svgs(project_path)

    # Step 2: SVG → PPTX conversion (generates both native and reference)
    native_path = convert_all_to_pptx(project_path, source="final")

    # Step 3: Embed fonts
    # Read template_id from project (default to business-blue for now)
    fonts = get_fonts_for_template("business-blue")
    existing_fonts = [f for f in fonts if f.exists()]
    if existing_fonts:
        embedded_path = embed_fonts_in_pptx(native_path, existing_fonts)
        return embedded_path

    return native_path
