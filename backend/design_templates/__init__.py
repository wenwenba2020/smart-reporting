"""DESIGN.md 预设模板库

每个 .md 文件首行 H1 标题作为显示名，`# 名称 · English-Slug` 格式
slug 是模板 id（文件名去 .md 后缀）。
"""
import re
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent

# Match lines like: "- **Primary** `#1E3A5F` — 品牌..."
COLOR_LINE_RE = re.compile(
    r"^-\s*\*\*(?P<role>[A-Za-z][A-Za-z0-9\-]*)\*\*\s*`(?P<hex>#[0-9A-Fa-f]{3,8})`",
    re.MULTILINE,
)


def _parse_h1(md: str) -> tuple[str, str]:
    """Parse '# Chinese · English' from first non-empty line. Returns (display_name, subtitle)."""
    for line in md.splitlines():
        line = line.strip()
        if line.startswith("# "):
            raw = line[2:].strip()
            if " · " in raw:
                name, subtitle = raw.split(" · ", 1)
                return name.strip(), subtitle.strip()
            return raw, ""
    return "未命名", ""


def _extract_colors(md: str) -> list[dict]:
    """Extract ordered {role, hex} list from the Color Palette section."""
    colors = []
    for m in COLOR_LINE_RE.finditer(md):
        colors.append({"role": m.group("role"), "hex": m.group("hex").upper()})
    return colors


def list_templates() -> list[dict]:
    """Return [{id, name, subtitle, preview}] for all .md files in this dir."""
    out = []
    for f in sorted(TEMPLATES_DIR.glob("*.md")):
        try:
            md = f.read_text(encoding="utf-8")
            name, subtitle = _parse_h1(md)
            # Preview: extract first few lines after H1 as description
            lines = md.splitlines()
            desc = ""
            # Look for the first ## Visual Theme section's first paragraph
            for i, line in enumerate(lines):
                if line.strip().startswith("## 1.") or "Visual Theme" in line:
                    for j in range(i + 1, min(i + 4, len(lines))):
                        text = lines[j].strip()
                        if text and not text.startswith("#"):
                            desc = text
                            break
                    break
            out.append({
                "id": f.stem,
                "name": name,
                "subtitle": subtitle,
                "description": desc,
                "colors": _extract_colors(md)[:6],  # up to 6 swatches for preview
            })
        except Exception:
            continue
    return out


def get_template(template_id: str) -> str | None:
    """Return the raw markdown content of a template, or None if not found."""
    f = TEMPLATES_DIR / f"{template_id}.md"
    if not f.is_file():
        return None
    return f.read_text(encoding="utf-8")


def list_user_templates(user_id: str) -> list[dict]:
    """Return user-extracted templates from .slide_library/{user_id}/templates/."""
    from backend.config import settings
    user_dir = Path(settings.LOCAL_STORAGE_PATH) / ".slide_library" / user_id / "templates"
    if not user_dir.is_dir():
        return []

    out = []
    for f in sorted(user_dir.glob("*.md")):
        try:
            md = f.read_text(encoding="utf-8")
            name, subtitle = _parse_h1(md)
            lines = md.splitlines()
            desc = ""
            for i, line in enumerate(lines):
                if line.strip().startswith("## 1.") or "Visual Theme" in line:
                    for j in range(i + 1, min(i + 4, len(lines))):
                        text = lines[j].strip()
                        if text and not text.startswith("#"):
                            desc = text
                            break
                    break
            out.append({
                "id": f"user/{f.stem}",
                "name": name,
                "subtitle": subtitle,
                "description": desc,
                "colors": _extract_colors(md)[:6],
            })
        except Exception:
            continue
    return out


def get_user_template(user_id: str, template_id: str) -> str | None:
    """Return the raw markdown content of a user template, or None."""
    slug = template_id.replace("user/", "", 1)
    from backend.config import settings
    f = Path(settings.LOCAL_STORAGE_PATH) / ".slide_library" / user_id / "templates" / f"{slug}.md"
    if not f.is_file():
        return None
    return f.read_text(encoding="utf-8")
