"""OUTLINE.md / DESIGN.md Pydantic 模型 + 文件读写（含文件锁）"""
import fcntl
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator


# ---------- Chart / Media ----------

class ChartConfig(BaseModel):
    type: str
    data_ref: str = "inline"
    data: list[Any] | None = None
    caption: str | None = None


class MediaConfig(BaseModel):
    background: str | None = None
    image: str | None = None


class PointItem(BaseModel):
    heading: str
    body: str | None = None


# ---------- Enums ----------

SlideStatus = Literal["todo", "generating", "done", "locked", "failed"]

LayoutType = Literal[
    "cover", "title-only", "title-content", "two-col", "three-col",
    "data-chart", "full-image", "quote", "timeline", "comparison",
    "team", "toc", "blank",
]


# ---------- Slide ----------

class SlideItem(BaseModel):
    slide_id: str
    layout: LayoutType
    status: SlideStatus = "todo"
    title: str
    subtitle: str | None = None
    points: list[PointItem] = Field(default_factory=list)
    chart: ChartConfig | None = None
    visual_intent: str | None = None
    notes_speaker: str = ""
    media: MediaConfig | None = None
    locked: bool = False
    design_ref: str | None = None       # library slide XML path (relative to project dir)
    design_images: str | None = None    # library slide images dir (relative to project dir)

    @field_validator("points", mode="before")
    @classmethod
    def _coerce_points(cls, v):
        """兼容老 OUTLINE.md：list[str] → list[PointItem(heading=s, body=None)]"""
        if not isinstance(v, list):
            return []
        result = []
        for x in v:
            if isinstance(x, str):
                result.append({"heading": x, "body": None})
            elif isinstance(x, dict):
                result.append(x)
            else:
                result.append(x)  # already PointItem passes through
        return result


# ---------- Outline ----------

class OutlineMeta(BaseModel):
    title: str
    format: str = "ppt169"
    total_slides: int
    status: str = "draft"
    created_at: str
    updated_at: str
    planner_version: str = "1.0"
    design_ref: str = "./DESIGN.md"


class OutlineDoc(BaseModel):
    meta: OutlineMeta
    slides: list[SlideItem]

    def get_slide(self, slide_id: str) -> SlideItem | None:
        for s in self.slides:
            if s.slide_id == slide_id:
                return s
        return None

    def get_summary(self) -> list[dict]:
        """规划师诊断模式用，只返回结构摘要，不含 SVG"""
        return [{
            "slide_id": s.slide_id,
            "title": s.title,
            "layout": s.layout,
            "status": s.status,
            "points_count": len(s.points),
            "has_chart": s.chart is not None,
            "has_media": s.media is not None,
            "locked": s.locked,
        } for s in self.slides]


# ---------- Design ----------

class DesignDoc(BaseModel):
    template_name: str
    template_id: str
    version: str = "1.0"
    body: str  # raw markdown body after frontmatter


# ---------- Parse / Serialize ----------

_SLIDE_HEADER_RE = re.compile(r"^### \[(\d+)\] (.+)$")


def _parse_slide_block(slide_id: str, title: str, lines: list[str]) -> SlideItem:
    """Parse a single slide block from OUTLINE.md lines into a SlideItem.

    points 小节用 YAML 块解析，兼容 `- str` 与 `- {heading, body}` 两种形态。
    """
    fields: dict[str, Any] = {"slide_id": slide_id, "title": title}
    points_block: list[str] = []
    in_points = False
    in_chart = False
    in_media = False
    chart_lines: list[str] = []
    media_dict: dict[str, str] = {}

    for line in lines:
        # detect continuation/exit of points block
        if in_points:
            if line.strip() == "" or line.startswith("  ") or line.startswith("\t"):
                points_block.append(line)
                continue
            else:
                in_points = False  # fall through to handle this line normally

        stripped = line.strip()
        if not stripped:
            continue

        if ":" in stripped and not stripped.startswith("-"):
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip()

            if key == "points":
                in_points = True
                in_chart = False
                in_media = False
                points_block = []
                continue

            if key == "chart":
                in_chart = True
                in_media = False
                chart_lines = []
                continue
            if in_chart and key in ("type", "data_ref", "data", "caption"):
                chart_lines.append(stripped)
                continue

            if key == "media":
                in_chart = False
                if val == "~":
                    fields["media"] = None
                    in_media = False
                elif val:
                    fields["media"] = MediaConfig(background=val)
                    in_media = False
                else:
                    in_media = True
                    media_dict = {}
                continue
            if in_media and key in ("background", "image"):
                media_dict[key] = val
                continue

            if in_chart:
                in_chart = False
            if in_media:
                if media_dict:
                    fields["media"] = MediaConfig(**media_dict)
                in_media = False

            if key == "layout":
                fields["layout"] = val
            elif key == "status":
                fields["status"] = val
            elif key == "subtitle":
                fields["subtitle"] = val if val != "~" else None
            elif key == "visual_intent":
                fields["visual_intent"] = val if val != "~" else None
            elif key == "notes_speaker":
                fields["notes_speaker"] = val.strip('"').strip("'")
            elif key == "locked":
                fields["locked"] = val.lower() == "true"
            elif key == "design_ref":
                fields["design_ref"] = val if val != "~" else None
            elif key == "design_images":
                fields["design_images"] = val if val != "~" else None

        elif in_chart and stripped.startswith("-"):
            chart_lines.append(stripped)

    if in_media and media_dict:
        fields["media"] = MediaConfig(**media_dict)

    if points_block:
        # Dedent 2 spaces so yaml.safe_load can parse the list
        dedented = "\n".join(
            line[2:] if line.startswith("  ") else line
            for line in points_block
        )
        try:
            parsed = yaml.safe_load(dedented)
            if isinstance(parsed, list):
                fields["points"] = parsed  # validator handles str/dict
        except Exception:
            pass

    if chart_lines:
        chart_yaml = "\n".join(chart_lines)
        try:
            chart_data = yaml.safe_load(chart_yaml)
            if isinstance(chart_data, dict):
                fields["chart"] = ChartConfig(**chart_data)
        except Exception:
            pass

    return SlideItem(**fields)


def parse_outline(content: str) -> OutlineDoc:
    """Parse OUTLINE.md content string into OutlineDoc."""
    # Split frontmatter and body
    parts = content.split("---", 2)
    if len(parts) < 3:
        raise ValueError("Invalid OUTLINE.md: missing frontmatter delimiters")

    meta_raw = yaml.safe_load(parts[1])
    meta = OutlineMeta(**meta_raw)

    body = parts[2]
    slides: list[SlideItem] = []

    # Split into slide blocks
    current_id: str | None = None
    current_title: str = ""
    current_lines: list[str] = []

    for line in body.splitlines():
        match = _SLIDE_HEADER_RE.match(line.strip())
        if match:
            if current_id is not None:
                slides.append(_parse_slide_block(current_id, current_title, current_lines))
            current_id = match.group(1)
            current_title = match.group(2)
            current_lines = []
        elif current_id is not None:
            current_lines.append(line)

    if current_id is not None:
        slides.append(_parse_slide_block(current_id, current_title, current_lines))

    return OutlineDoc(meta=meta, slides=slides)


def serialize_outline(outline: OutlineDoc) -> str:
    """Serialize OutlineDoc back to OUTLINE.md format."""
    meta_dict = outline.meta.model_dump()
    meta_yaml = yaml.dump(meta_dict, default_flow_style=False, allow_unicode=True).strip()
    lines = [f"---\n{meta_yaml}\n---\n", "## Slides\n"]

    for s in outline.slides:
        lines.append(f"### [{s.slide_id}] {s.title}")
        lines.append(f"layout: {s.layout}")
        lines.append(f"status: {s.status}")
        if s.subtitle:
            lines.append(f"subtitle: {s.subtitle}")
        if s.points:
            lines.append("points:")
            for p in s.points:
                # Defensive: handle both PointItem and raw str (transition period)
                if isinstance(p, str):
                    lines.append(f"  - heading: {p}")
                else:
                    lines.append(f"  - heading: {p.heading}")
                    if p.body:
                        if "\n" in p.body:
                            lines.append(f"    body: |")
                            for body_line in p.body.splitlines():
                                lines.append(f"      {body_line}")
                        else:
                            escaped = p.body.replace('"', '\\"')
                            lines.append(f'    body: "{escaped}"')
        if s.chart:
            lines.append("chart:")
            lines.append(f"  type: {s.chart.type}")
            lines.append(f"  data_ref: {s.chart.data_ref}")
            if s.chart.data:
                lines.append("  data:")
                for item in s.chart.data:
                    lines.append(f"    - {item}")
            if s.chart.caption:
                lines.append(f"  caption: {s.chart.caption}")
        if s.visual_intent:
            lines.append(f"visual_intent: {s.visual_intent}")
        if s.media and (s.media.background or s.media.image):
            lines.append("media:")
            if s.media.background:
                lines.append(f"  background: {s.media.background}")
            if s.media.image:
                lines.append(f"  image: {s.media.image}")
        else:
            lines.append("media: ~")
        lines.append(f"notes_speaker: {s.notes_speaker}")
        lines.append(f"locked: {'true' if s.locked else 'false'}")
        if s.design_ref:
            lines.append(f"design_ref: {s.design_ref}")
        if s.design_images:
            lines.append(f"design_images: {s.design_images}")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


# ---------- File I/O with locking ----------

def _lock_path(path: Path) -> Path:
    """Return the lock file path for a given outline file."""
    return path.with_suffix(".lock")


def load_outline(path: str | Path) -> OutlineDoc:
    """Read and parse OUTLINE.md from disk with shared lock."""
    path = Path(path)
    lock = _lock_path(path)
    lock.touch(exist_ok=True)

    with open(lock, "r") as lf:
        fcntl.flock(lf, fcntl.LOCK_SH)
        try:
            content = path.read_text(encoding="utf-8")
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)
    return parse_outline(content)


def save_outline(outline: OutlineDoc, path: str | Path) -> None:
    """Atomic write: lock → write to temp → fsync → rename. No truncation race."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = serialize_outline(outline)
    lock = _lock_path(path)
    lock.touch(exist_ok=True)

    with open(lock, "r") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
            try:
                os.write(fd, content.encode("utf-8"))
                os.fsync(fd)
            finally:
                os.close(fd)
            os.replace(tmp, str(path))
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)
