"""W2-3: 字体管理器 — 子集化 + PPTX 嵌入（zipfile 操作）"""
# TTF only, NOT OTF
import shutil
import tempfile
import zipfile
from pathlib import Path

from fontTools import subset as ft_subset  # 大写 T
from fontTools.ttLib import TTFont

from backend.config import settings

FONTS_DIR = Path(settings.FONTS_DIR)

# 模板 ID → 需要的字体文件列表
TEMPLATE_FONTS: dict[str, list[str]] = {
    "business-blue": [
        "AlibabaPuHuiTi/AlibabaPuHuiTi-Regular.ttf",
        "AlibabaPuHuiTi/AlibabaPuHuiTi-Bold.ttf",
        "AlibabaPuHuiTi/AlibabaPuHuiTi-Light.ttf",
        "Inter/Inter-Regular.ttf",
        "Inter/Inter-Bold.ttf",
    ],
    "tech-dark": [
        "HarmonyOSSans/HarmonyOSSans-Regular.ttf",
        "HarmonyOSSans/HarmonyOSSans-Bold.ttf",
        "HarmonyOSSans/HarmonyOSSans-Light.ttf",
    ],
}


def get_fonts_for_template(template_id: str) -> list[Path]:
    """Return full paths of font files needed for a template."""
    font_names = TEMPLATE_FONTS.get(template_id, TEMPLATE_FONTS["business-blue"])
    return [FONTS_DIR / name for name in font_names]


def create_font_subset(
    font_path: Path,
    text_content: str,
    output_path: Path,
) -> Path:
    """Subset a TTF font to only include glyphs used in text_content."""
    if not verify_ttf(font_path):
        raise ValueError(f"Font is not TTF format (OTF/CFF rejected): {font_path}")

    options = ft_subset.Options()
    options.layout_features = ["*"]
    options.name_IDs = [1, 2, 3, 4, 6]

    font = ft_subset.load_font(str(font_path), options)
    subsetter = ft_subset.Subsetter(options)
    subsetter.populate(text=text_content)
    subsetter.subset(font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    ft_subset.save_font(font, str(output_path), options)
    return output_path


def embed_fonts_in_pptx(pptx_path: str, font_files: list[Path]) -> str:
    """
    Embed TTF fonts into PPTX by manipulating the ZIP structure.
    python-pptx does not support font embedding.

    Updates: [Content_Types].xml + ppt/_rels/presentation.xml.rels
    Returns path to the new PPTX with embedded fonts.
    """
    # Validate all fonts are TTF before starting
    for font_file in font_files:
        if not font_file.exists():
            raise FileNotFoundError(f"Font file not found: {font_file}")
        if not verify_ttf(font_file):
            raise ValueError(f"Font is not TTF format (OTF/CFF rejected): {font_file}")

    pptx_path_obj = Path(pptx_path)
    work_path = str(pptx_path_obj.with_name(pptx_path_obj.stem + "_embedded.pptx"))

    # Unpack to temp dir, modify, repack
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # Extract original PPTX
        with zipfile.ZipFile(pptx_path, "r") as zin:
            zin.extractall(tmp)

        # Add font files to ppt/fonts/
        fonts_dir = tmp / "ppt" / "fonts"
        fonts_dir.mkdir(parents=True, exist_ok=True)

        # 1. Update [Content_Types].xml
        content_types_path = tmp / "[Content_Types].xml"
        ct_xml = content_types_path.read_text(encoding="utf-8")

        # 2. Update ppt/_rels/presentation.xml.rels
        rels_path = tmp / "ppt" / "_rels" / "presentation.xml.rels"
        rels_xml = rels_path.read_text(encoding="utf-8") if rels_path.exists() else ""

        # Find max existing rId to avoid collision
        import re
        existing_ids = re.findall(r'Id="rId(\d+)"', rels_xml)
        next_rid = max((int(x) for x in existing_ids), default=0) + 100

        for i, font_file in enumerate(font_files):
            shutil.copy2(font_file, fonts_dir / font_file.name)

            # Content_Types override
            override = (
                f'<Override PartName="/ppt/fonts/{font_file.name}" '
                f'ContentType="application/x-fontdata"/>'
            )
            if override not in ct_xml:
                ct_xml = ct_xml.replace("</Types>", f"  {override}\n</Types>")

            # Relationship entry
            rid = f"rId{next_rid + i}"
            rel_type = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/font"
            rel_entry = (
                f'<Relationship Id="{rid}" '
                f'Type="{rel_type}" '
                f'Target="fonts/{font_file.name}"/>'
            )
            if font_file.name not in rels_xml:
                rels_xml = rels_xml.replace("</Relationships>", f"  {rel_entry}\n</Relationships>")

        content_types_path.write_text(ct_xml, encoding="utf-8")
        if rels_path.exists():
            rels_path.write_text(rels_xml, encoding="utf-8")

        # Repack as PPTX
        with zipfile.ZipFile(work_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for file in tmp.rglob("*"):
                if file.is_file():
                    arcname = str(file.relative_to(tmp))
                    zout.write(file, arcname)

    return work_path


def verify_ttf(font_path: Path) -> bool:
    """Verify a font file is TTF format (not OTF/CFF)."""
    try:
        font = TTFont(str(font_path))
        return "glyf" in font
    except Exception:
        return False
