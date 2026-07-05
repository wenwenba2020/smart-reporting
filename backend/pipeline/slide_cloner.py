"""Clone library slide assets into a project directory for design preservation."""
import shutil
from pathlib import Path
from dataclasses import dataclass


@dataclass
class ClonedSlide:
    slide_id: str
    design_ref: str       # relative path: lib_slides/slide_NN/slide.xml
    design_images: str    # relative path: lib_slides/slide_NN/images/


def clone_slide_to_project(
    library_slide_xml: str,
    library_slide_dir: str,
    project_dir: str | Path,
    slide_id: str,
) -> ClonedSlide:
    """Copy a library slide's XML and images into the project directory.

    Args:
        library_slide_xml: Path to slide.xml in the slide library
        library_slide_dir: Path to the slide directory in the library (contains images/)
        project_dir: Project root directory
        slide_id: Target slide_id (e.g. "03")

    Returns ClonedSlide with relative paths.
    """
    project_dir = Path(project_dir)
    dest_dir = project_dir / "lib_slides" / f"slide_{slide_id}"
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Copy slide.xml
    src_xml = Path(library_slide_xml)
    dest_xml = dest_dir / "slide.xml"
    if src_xml.is_file():
        shutil.copy2(src_xml, dest_xml)

    # Copy images/
    src_images = Path(library_slide_dir) / "images"
    dest_images = dest_dir / "images"
    if src_images.is_dir() and any(src_images.iterdir()):
        if dest_images.exists():
            shutil.rmtree(dest_images)
        shutil.copytree(src_images, dest_images)

    design_ref = f"lib_slides/slide_{slide_id}/slide.xml"
    design_images = f"lib_slides/slide_{slide_id}/images/" if dest_images.is_dir() else ""

    return ClonedSlide(
        slide_id=slide_id,
        design_ref=design_ref,
        design_images=design_images,
    )


def parse_slide_xml_layout(xml_path: str) -> dict:
    """Lightweight parse of slide XML to extract layout hints for the designer agent.

    Returns a dict with:
      - background_color: str
      - text_positions: [{left, top, width, height, font_name, font_size_pt}]
      - has_images: bool
    """
    import xml.etree.ElementTree as ET

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except Exception:
        return {"background_color": None, "text_positions": [], "has_images": False}

    bg_color = None
    text_positions = []
    has_images = False

    # Extract background
    for bg in root.iter("{http://schemas.openxmlformats.org/presentationml/2006/main}bg"):
        for sr in bg.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}srgbClr"):
            bg_color = f"#{sr.get('val', 'FFFFFF')}"

    # Extract shape positions and text
    EMU_PER_PX = 914400 / 96
    for sp in root.iter("{http://schemas.openxmlformats.org/presentationml/2006/main}sp"):
        # Position & size
        xfrm = sp.find(".//{http://schemas.openxmlformats.org/drawingml/2006/main}xfrm")
        if xfrm is not None:
            off = xfrm.find("{http://schemas.openxmlformats.org/drawingml/2006/main}off")
            ext = xfrm.find("{http://schemas.openxmlformats.org/drawingml/2006/main}ext")
            left = int(off.get("x", 0)) / EMU_PER_PX if off is not None else 0
            top = int(off.get("y", 0)) / EMU_PER_PX if off is not None else 0
            width = int(ext.get("cx", 0)) / EMU_PER_PX if ext is not None else 0
            height = int(ext.get("cy", 0)) / EMU_PER_PX if ext is not None else 0
        else:
            left = top = width = height = 0

        # Text
        font_name = None
        font_size = None
        for rpr in sp.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}rPr"):
            latin = rpr.find("{http://schemas.openxmlformats.org/drawingml/2006/main}latin")
            if latin is not None:
                font_name = latin.get("typeface")
            sz = rpr.get("sz")
            if sz:
                font_size = int(sz) / 100  # hundredths of a point

        if font_name or font_size:
            text_positions.append({
                "left": round(left, 1),
                "top": round(top, 1),
                "width": round(width, 1),
                "height": round(height, 1),
                "font_name": font_name,
                "font_size_pt": font_size,
            })

    # Check for images
    for _ in root.iter("{http://schemas.openxmlformats.org/presentationml/2006/main}pic"):
        has_images = True
        break

    return {
        "background_color": bg_color,
        "text_positions": text_positions[:20],  # max 20
        "has_images": has_images,
    }
