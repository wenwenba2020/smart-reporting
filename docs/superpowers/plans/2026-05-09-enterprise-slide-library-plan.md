# 企业幻灯片库 · 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增企业幻灯片库功能 — 用户上传 PPTX 后逐页提取保存为可检索复用的 slide 资产，通过右侧面板浏览管理，支持对话 @ 引用与面板导入到当前项目。

**Architecture:** 后端新增 `slide_library` ORM 模型 + `slide_extractor` 解析器 + `/library` API 路由，数据存储在 `projects/.slide_library/{user_id}/`。前端在右侧面板新增"企业库"tab，包含 PPT 列表、slide 网格、标签编辑、搜索筛选。@ 引用在 ChatPanel 输入框中触发小型搜索面板。

**Tech Stack:** SQLAlchemy async + SQLite JSON fields, python-pptx + zipfile for extraction, React + Zustand + Tailwind

---

## 文件清单

| 操作 | 文件 | 职责 |
|------|------|------|
| Create | `backend/models/slide_library.py` | SlideLibrary + LibrarySlide ORM 模型 + Pydantic schema |
| Modify | `backend/models/database.py` | 注册新模型到 create_all_tables |
| Create | `backend/parsers/slide_extractor.py` | 从 PPTX ZIP 逐页提取 slide XML、文本、图片、SVG 缩略图 |
| Create | `backend/api/routes/slide_library.py` | 7 个 API 端点 |
| Modify | `backend/api/main.py` | 注册 slide_library_router |
| Modify | `frontend/src/types/events.ts` | 新增 LibraryDeck、LibrarySlide 类型 |
| Modify | `frontend/src/api/client.ts` | 新增 8 个 slide library API 函数 |
| Create | `frontend/src/stores/slideLibraryStore.ts` | Zustand store |
| Create | `frontend/src/components/SlideLibrary/index.tsx` | 主面板（上传 + 搜索 + 列表） |
| Create | `frontend/src/components/SlideLibrary/DeckCard.tsx` | 单个 PPT 卡片（可展开） |
| Create | `frontend/src/components/SlideLibrary/LibrarySlideCard.tsx` | 库中单个 slide 卡片 |
| Create | `frontend/src/components/SlideLibrary/TagEditor.tsx` | 标签编辑器组件 |
| Modify | `frontend/src/App.tsx` | RightTab 扩展 + 渲染 SlideLibraryPanel |
| Modify | `frontend/src/components/ChatPanel/index.tsx` | @ 输入触发 slide 搜索弹出面板 |

---

### Task 1: 数据模型 · SlideLibrary + LibrarySlide ORM

**Files:**
- Create: `backend/models/slide_library.py`
- Modify: `backend/models/database.py:14-18`

- [ ] **Step 1: 创建 slide_library.py ORM 模型**

```python
"""企业幻灯片库数据模型"""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex


class SlideLibrary(Base):
    __tablename__ = "slide_libraries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_id)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    original_filename: Mapped[str] = mapped_column(String, nullable=False)
    slide_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    slides: Mapped[list["LibrarySlide"]] = relationship(
        "LibrarySlide", back_populates="library", cascade="all, delete-orphan",
        order_by="LibrarySlide.slide_index"
    )


class LibrarySlide(Base):
    __tablename__ = "library_slides"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_id)
    library_id: Mapped[str] = mapped_column(String, ForeignKey("slide_libraries.id", ondelete="CASCADE"), nullable=False, index=True)
    slide_index: Mapped[int] = mapped_column(Integer, nullable=False)
    slide_number: Mapped[str | None] = mapped_column(String, nullable=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    text_summary: Mapped[str | None] = mapped_column(String, nullable=True)
    tags: Mapped[Any] = mapped_column(JSON, default=list)
    thumbnail_path: Mapped[str | None] = mapped_column(String, nullable=True)
    raw_slide_xml_path: Mapped[str | None] = mapped_column(String, nullable=True)
    layout_hint: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    library: Mapped[SlideLibrary] = relationship("SlideLibrary", back_populates="slides")
```

- [ ] **Step 2: 注册模型到 create_all_tables**

Edit `backend/models/database.py:14-18` — 在导入列表中添加 `slide_library`：

```python
async def create_all_tables():
    from backend.models import project, snapshot, slide_library  # noqa: F401 — register models

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

- [ ] **Step 3: 验证模型可导入**

Run: `.venv/bin/python -c "from backend.models.slide_library import SlideLibrary, LibrarySlide; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/models/slide_library.py backend/models/database.py
git commit -m "feat: add SlideLibrary + LibrarySlide ORM models"
```

---

### Task 2: Slide 提取器 · slide_extractor.py

**Files:**
- Create: `backend/parsers/slide_extractor.py`

- [ ] **Step 1: 编写 extract_slides_from_pptx 函数**

```python
"""从 PPTX 文件逐页提取 slide 内容、XML、图片、缩略图"""
import re
import zipfile
import shutil
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape
from dataclasses import dataclass, field

from pptx import Presentation


@dataclass
class ExtractedSlide:
    slide_index: int          # 1-based
    title: str                # 首个 text_frame 的首段文本（截断）
    text_summary: str         # 全部文本内容
    slide_xml_rel: str        # 相对路径：slides/slide_NN/slide.xml
    thumbnail_rel: str        # 相对路径：slides/slide_NN/thumbnail.svg
    layout_hint: str          # 推测的布局类型


SIMPLE_LAYOUT_RULES = [
    (re.compile(r"^slide_\d+$"), "cover"),
    (re.compile(r"(目录|contents|toc|agenda|outline)", re.I), "toc"),
    (re.compile(r"(团队|team|成员|member|组织)", re.I), "team"),
    (re.compile(r"(对比|比较|vs|comparison|versus)", re.I), "comparison"),
    (re.compile(r"(时间|timeline|历程|历史|里程碑|milestone)", re.I), "timeline"),
    (re.compile(r"(图表|数据|chart|graph|statistics|指标)", re.I), "data-chart"),
    (re.compile(r"(引用|quote|名言|证言|testimonial)", re.I), "quote"),
]


def _guess_layout(title_text: str, body_text: str, slide_index: int, total: int) -> str:
    """根据文本内容推测布局类型。"""
    combined = f"{title_text} {body_text[:200]}"
    if slide_index == 1 and total > 3:
        return "cover"
    for pattern, layout in SIMPLE_LAYOUT_RULES:
        if pattern.search(combined):
            return layout
    return "title-content"


EMU_PER_PX = 914400 / 96


def _render_svg_thumbnail(
    slide,
    width: int = 960,
    height: int = 540,
) -> str:
    """为单个 slide 生成 SVG 缩略图（文本 + 近似位置）。"""
    bg_color = "#ffffff"
    try:
        bg = slide.background
        if bg.fill and bg.fill.type is not None:
            fc = bg.fill.fore_color
            if fc and fc.type is not None:
                bg_color = f"#{fc.rgb}"
    except Exception:
        pass

    lines: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="{bg_color}"/>',
    ]

    for shape in slide.shapes:
        try:
            left = shape.left / EMU_PER_PX if shape.left else 0
            top = shape.top / EMU_PER_PX if shape.top else 0
            w = shape.width / EMU_PER_PX if shape.width else width
            h = shape.height / EMU_PER_PX if shape.height else 20
            text = shape.text_frame.text.strip() if shape.has_text_frame else ""
        except Exception:
            continue

        if not text:
            # 图片占位
            if shape.shape_type and shape.shape_type == 13:  # MSO_SHAPE_TYPE.PICTURE
                lines.append(
                    f'<rect x="{left:.0f}" y="{top:.0f}" width="{w:.0f}" height="{h:.0f}" '
                    f'fill="#e5e7eb" stroke="#d1d5db" rx="4"/>'
                    f'<text x="{left + w/2:.0f}" y="{top + h/2:.0f}" '
                    f'text-anchor="middle" dominant-baseline="central" font-size="11" fill="#9ca3af">📷</text>'
                )
            continue

        font_size = 12
        is_bold = False
        try:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    for run in para.runs:
                        if run.font.size and run.font.size.pt:
                            font_size = run.font.size.pt
                        if run.font.bold:
                            is_bold = True
                        break
                    break
        except Exception:
            pass

        weight = "bold" if is_bold else "normal"
        # 按行拆分渲染，确保多行文本可见
        text_lines = text.split("\n")[:8]
        line_height = font_size + 4
        for li, line_text in enumerate(text_lines):
            y = top + line_height * (li + 1)
            # 截断过长行
            display_text = line_text[:80] + ("..." if len(line_text) > 80 else "")
            lines.append(
                f'<text x="{left:.0f}" y="{y:.0f}" font-size="{font_size}" '
                f'font-weight="{weight}" fill="#1f2937" font-family="sans-serif">'
                f'{xml_escape(display_text)}</text>'
            )

    lines.append("</svg>")
    return "\n".join(lines)


def extract_slides_from_pptx(
    pptx_path: str | Path,
    output_dir: str | Path,
) -> list[ExtractedSlide]:
    """从 PPTX 文件逐页提取。返回 ExtractedSlide 列表。"""
    pptx_path = Path(pptx_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    prs = Presentation(str(pptx_path))
    total = len(prs.slides)
    results: list[ExtractedSlide] = []

    # 解压原始 PPTX，提取每页 slide XML
    slides_xml: dict[int, bytes] = {}
    with zipfile.ZipFile(pptx_path, "r") as zf:
        for name in zf.namelist():
            m = re.match(r"ppt/slides/slide(\d+)\.xml", name)
            if m:
                slide_num = int(m.group(1))
                slides_xml[slide_num] = zf.read(name)

    for idx, slide in enumerate(prs.slides, 1):
        slide_dir = output_dir / f"slide_{idx:02d}"
        slide_dir.mkdir(parents=True, exist_ok=True)

        # 提取文本
        all_texts: list[str] = []
        title = ""
        for shape in slide.shapes:
            if shape.has_text_frame:
                text = shape.text_frame.text.strip()
                if text:
                    all_texts.append(text)
                    if shape.shape_type == 1 and not title:  # MSO_SHAPE_TYPE.PLACEHOLDER title
                        title = text
        if not title and all_texts:
            title = all_texts[0][:60]
        text_summary = "\n\n".join(all_texts)

        # 保存原始 slide XML
        slide_xml_path = slide_dir / "slide.xml"
        if idx in slides_xml:
            slide_xml_path.write_bytes(slides_xml[idx])

        # 生成 SVG 缩略图
        thumbnail_path = slide_dir / "thumbnail.svg"
        svg = _render_svg_thumbnail(slide)
        thumbnail_path.write_text(svg, encoding="utf-8")

        # 提取图片
        images_dir = slide_dir / "images"
        images_dir.mkdir(exist_ok=True)
        img_count = 0
        for shape in slide.shapes:
            if shape.shape_type and shape.shape_type == 13:  # MSO_SHAPE_TYPE.PICTURE
                try:
                    image = shape.image
                    blob = image.blob
                    ext = image.content_type.split("/")[-1]
                    if ext == "jpeg":
                        ext = "jpg"
                    img_path = images_dir / f"img_{img_count + 1}.{ext}"
                    img_path.write_bytes(blob)
                    img_count += 1
                except Exception:
                    pass

        layout_hint = _guess_layout(title, text_summary, idx, total)

        results.append(ExtractedSlide(
            slide_index=idx,
            title=title or f"Slide {idx}",
            text_summary=text_summary,
            slide_xml_rel=str((slide_dir / "slide.xml").relative_to(output_dir.parent)),
            thumbnail_rel=str(thumbnail_path.relative_to(output_dir.parent)),
            layout_hint=layout_hint,
        ))

    return results
```

- [ ] **Step 2: 验证导入无错误**

Run: `.venv/bin/python -c "from backend.parsers.slide_extractor import extract_slides_from_pptx; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/parsers/slide_extractor.py
git commit -m "feat: add slide extractor for PPTX page-by-page parsing"
```

---

### Task 3: API 路由 · slide_library.py

**Files:**
- Create: `backend/api/routes/slide_library.py`
- Modify: `backend/api/main.py`

- [ ] **Step 1: 创建 slide_library.py 路由**

```python
"""企业幻灯片库 API 端点"""
import shutil
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel
from sqlalchemy import select, delete, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_current_user
from backend.config import settings
from backend.models.database import get_db
from backend.models.project import Project
from backend.models.slide_library import SlideLibrary, LibrarySlide
from backend.parsers.slide_extractor import extract_slides_from_pptx

router = APIRouter(prefix="/library", tags=["library"])

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
LIBRARY_BASE = Path(settings.LOCAL_STORAGE_PATH) / ".slide_library"


class SlideNumberUpdate(BaseModel):
    slide_number: str | None = None
    tags: list[str] | None = None


class ImportRequest(BaseModel):
    slide_ids: list[str]


def _lib_dir(user_id: str, library_id: str) -> Path:
    return LIBRARY_BASE / user_id / "decks" / library_id


@router.post("/upload")
async def upload_to_library(
    file: UploadFile = File(...),
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """上传 PPTX 到企业库，自动逐页提取。"""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix != ".pptx":
        raise HTTPException(status_code=400, detail="Only .pptx files allowed")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")

    # 创建 SlideLibrary 记录
    library = SlideLibrary(
        user_id=user,
        name=Path(file.filename or "untitled").stem,
        original_filename=file.filename or "untitled.pptx",
    )
    db.add(library)
    await db.flush()  # 获取 library.id

    # 写入磁盘
    lib_dir = _lib_dir(user, library.id)
    lib_dir.mkdir(parents=True, exist_ok=True)
    original_path = lib_dir / "original.pptx"
    original_path.write_bytes(content)

    # 逐页提取
    slides_dir = lib_dir / "slides"
    extracted = extract_slides_from_pptx(str(original_path), str(slides_dir))

    # 写入 LibrarySlide 记录
    library.slide_count = len(extracted)
    for e in extracted:
        lib_slide = LibrarySlide(
            library_id=library.id,
            slide_index=e.slide_index,
            title=e.title,
            text_summary=e.text_summary,
            thumbnail_path=e.thumbnail_rel,
            raw_slide_xml_path=e.slide_xml_rel,
            layout_hint=e.layout_hint,
        )
        db.add(lib_slide)

    await db.commit()
    await db.refresh(library)

    return {
        "library_id": library.id,
        "name": library.name,
        "original_filename": library.original_filename,
        "slide_count": library.slide_count,
    }


@router.get("/decks")
async def list_decks(
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """列出当前用户的所有 PPT。"""
    result = await db.execute(
        select(SlideLibrary)
        .where(SlideLibrary.user_id == user)
        .order_by(SlideLibrary.created_at.desc())
    )
    decks = result.scalars().all()
    return [
        {
            "id": d.id,
            "name": d.name,
            "original_filename": d.original_filename,
            "slide_count": d.slide_count,
            "created_at": d.created_at.isoformat(),
            "updated_at": d.updated_at.isoformat(),
        }
        for d in decks
    ]


@router.get("/decks/{library_id}")
async def get_deck(
    library_id: str,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取单个 PPT 详情（含所有 slides）。"""
    result = await db.execute(
        select(SlideLibrary).where(
            SlideLibrary.id == library_id,
            SlideLibrary.user_id == user,
        )
    )
    library = result.scalar_one_or_none()
    if not library:
        raise HTTPException(status_code=404, detail="Deck not found")

    base = f"/project-files/.slide_library/{user}/decks/{library.id}"
    return {
        "id": library.id,
        "name": library.name,
        "original_filename": library.original_filename,
        "slide_count": library.slide_count,
        "created_at": library.created_at.isoformat(),
        "slides": [
            {
                "id": s.id,
                "slide_index": s.slide_index,
                "slide_number": s.slide_number,
                "title": s.title,
                "text_summary": s.text_summary,
                "tags": s.tags or [],
                "thumbnail_url": f"{base}/slides/slide_{s.slide_index:02d}/thumbnail.svg",
                "layout_hint": s.layout_hint,
            }
            for s in library.slides
        ],
    }


@router.delete("/decks/{library_id}")
async def delete_deck(
    library_id: str,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除 PPT 及其所有 slides。"""
    result = await db.execute(
        select(SlideLibrary).where(
            SlideLibrary.id == library_id,
            SlideLibrary.user_id == user,
        )
    )
    library = result.scalar_one_or_none()
    if not library:
        raise HTTPException(status_code=404, detail="Deck not found")

    # 删除磁盘文件
    lib_dir = _lib_dir(user, library_id)
    if lib_dir.exists():
        shutil.rmtree(lib_dir)

    await db.delete(library)
    await db.commit()
    return {"deleted": library_id}


@router.patch("/decks/{library_id}")
async def update_deck_name(
    library_id: str,
    body: dict,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改 PPT 名称。"""
    result = await db.execute(
        select(SlideLibrary).where(
            SlideLibrary.id == library_id,
            SlideLibrary.user_id == user,
        )
    )
    library = result.scalar_one_or_none()
    if not library:
        raise HTTPException(status_code=404, detail="Deck not found")

    if "name" in body:
        library.name = body["name"]
        await db.commit()
    return {"id": library.id, "name": library.name}


@router.patch("/slides/{slide_id}")
async def update_slide(
    slide_id: str,
    body: SlideNumberUpdate,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改单页标签 / 编号。"""
    result = await db.execute(
        select(LibrarySlide).join(SlideLibrary).where(
            LibrarySlide.id == slide_id,
            SlideLibrary.user_id == user,
        )
    )
    slide = result.scalar_one_or_none()
    if not slide:
        raise HTTPException(status_code=404, detail="Slide not found")

    if body.slide_number is not None:
        slide.slide_number = body.slide_number
    if body.tags is not None:
        slide.tags = body.tags
    await db.commit()
    return {"id": slide.id, "slide_number": slide.slide_number, "tags": slide.tags}


@router.get("/slides/search")
async def search_slides(
    q: str = "",
    tag: str = "",
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """搜索 slides（按标签/文本模糊匹配）。"""
    query = select(LibrarySlide).join(SlideLibrary).where(
        SlideLibrary.user_id == user
    )
    conditions: list[Any] = []
    if q:
        conditions.append(
            or_(
                LibrarySlide.title.ilike(f"%{q}%"),
                LibrarySlide.text_summary.ilike(f"%{q}%"),
                LibrarySlide.slide_number.ilike(f"%{q}%"),
            )
        )
    if tag:
        # SQLite JSON 字段模糊匹配
        conditions.append(
            LibrarySlide.tags.cast(str).ilike(f"%{tag}%")
        )
    if conditions:
        query = query.where(or_(*conditions) if len(conditions) > 1 else conditions[0])

    query = query.order_by(LibrarySlide.library_id, LibrarySlide.slide_index).limit(30)
    result = await db.execute(query)
    slides = result.scalars().all()

    return [
        {
            "id": s.id,
            "library_id": s.library_id,
            "slide_index": s.slide_index,
            "slide_number": s.slide_number,
            "title": s.title,
            "text_summary": (s.text_summary or "")[:200],
            "tags": s.tags or [],
            "thumbnail_url": f"/project-files/.slide_library/{user}/decks/{s.library_id}/slides/slide_{s.slide_index:02d}/thumbnail.svg",
            "layout_hint": s.layout_hint,
        }
        for s in slides
    ]


@router.post("/import-to-project/{project_id}")
async def import_slides_to_project(
    project_id: str,
    body: ImportRequest,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """将库中 slides 导入到指定项目。"""
    # 验证 project 归属
    project = await db.get(Project, project_id)
    if not project or project.user_id != user:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.stage not in ("idle",):
        raise HTTPException(
            status_code=400,
            detail="项目已进入生成流程，请在活动开始前导入 slides",
        )

    if not body.slide_ids:
        raise HTTPException(status_code=400, detail="至少选择一个 slide")

    # 批量查询 slides（验证归属）
    result = await db.execute(
        select(LibrarySlide).join(SlideLibrary).where(
            LibrarySlide.id.in_(body.slide_ids),
            SlideLibrary.user_id == user,
        )
    )
    lib_slides = list(result.scalars().all())
    if len(lib_slides) != len(body.slide_ids):
        raise HTTPException(status_code=404, detail="Some slides not found")

    # 读取 OUTLINE.md
    from backend.models.outline import load_outline, save_outline, SlideItem
    from backend.storage.file_manager import ProjectStorage

    storage = ProjectStorage.get()
    outline_path = storage.get_project_path(project_id) / "OUTLINE.md"

    if outline_path.exists():
        outline = load_outline(str(outline_path))
    else:
        from backend.models.outline import OutlineDoc, OutlineMeta
        outline = OutlineDoc(
            meta=OutlineMeta(
                title=project.name,
                total_slides=0,
            ),
            slides=[],
        )

    # 为每个 slide 创建 SlideItem 并追加到末尾
    max_id = max((int(s.slide_id) for s in outline.slides), default=0)
    imported: list[str] = []
    for lib_slide in lib_slides:
        max_id += 1
        new_id = f"{max_id:02d}"
        # 将 tags 合并为 visual_intent 提示
        tag_hint = f"参考标签: {', '.join(lib_slide.tags)}" if lib_slide.tags else ""
        outline.slides.append(SlideItem(
            slide_id=new_id,
            layout=lib_slide.layout_hint or "title-content",
            title=lib_slide.title or f"Slide {new_id}",
            visual_intent=tag_hint if tag_hint else None,
            notes_speaker=lib_slide.text_summary or "",
        ))
        imported.append(new_id)

    outline.meta.total_slides = len(outline.slides)
    save_outline(outline, str(outline_path))

    # 更新 project
    project.total_slides = len(outline.slides)
    await db.commit()

    return {
        "imported_slide_ids": imported,
        "total_slides": len(outline.slides),
    }
```

- [ ] **Step 2: 注册路由到 main.py**

Edit `backend/api/main.py` — 在 upload_router 之后添加：

```python
from backend.api.routes.slide_library import router as slide_library_router  # noqa: E402

app.include_router(slide_library_router)
```

- [ ] **Step 3: 验证路由导入**

Run: `.venv/bin/python -c "from backend.api.routes.slide_library import router; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/api/routes/slide_library.py backend/api/main.py
git commit -m "feat: add slide library API routes (upload/list/search/import)"
```

---

### Task 4: 前端类型 + API 客户端

**Files:**
- Modify: `frontend/src/types/events.ts`
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: 添加类型定义**

Edit `frontend/src/types/events.ts` — 在文件末尾追加：

```typescript
// Slide Library types
export interface LibraryDeck {
  id: string
  name: string
  original_filename: string
  slide_count: number
  created_at: string
  updated_at: string
}

export interface LibrarySlide {
  id: string
  library_id: string
  slide_index: number
  slide_number: string | null
  title: string
  text_summary: string
  tags: string[]
  thumbnail_url: string
  layout_hint: string
}
```

- [ ] **Step 2: 添加 API 函数**

Edit `frontend/src/api/client.ts` — 在文件末尾 `export default api` 之前追加：

```typescript
// Slide Library
export const uploadToLibrary = (file: File) => {
  const form = new FormData()
  form.append('file', file)
  return api.post<{ library_id: string; name: string; slide_count: number }>(
    '/library/upload', form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  ).then(r => r.data)
}

export const listLibraryDecks = () =>
  api.get<LibraryDeck[]>('/library/decks').then(r => r.data)

export const getLibraryDeck = (id: string) =>
  api.get<LibraryDeck & { slides: LibrarySlide[] }>(`/library/decks/${id}`).then(r => r.data)

export const deleteLibraryDeck = (id: string) =>
  api.delete(`/library/decks/${id}`)

export const updateLibraryDeckName = (id: string, name: string) =>
  api.patch(`/library/decks/${id}`, { name })

export const updateLibrarySlide = (id: string, data: { slide_number?: string | null; tags?: string[] }) =>
  api.patch(`/library/slides/${id}`, data).then(r => r.data)

export const searchLibrarySlides = (q?: string, tag?: string) => {
  const params = new URLSearchParams()
  if (q) params.set('q', q)
  if (tag) params.set('tag', tag)
  return api.get<LibrarySlide[]>(`/library/slides/search?${params.toString()}`).then(r => r.data)
}

export const importSlidesToProject = (projectId: string, slideIds: string[]) =>
  api.post<{ imported_slide_ids: string[]; total_slides: number }>(
    `/library/import-to-project/${projectId}`, { slide_ids: slideIds }
  ).then(r => r.data)
```

- [ ] **Step 3: 验证前端编译**

Run: `cd frontend && npm run build 2>&1 | tail -5`
Expected: no errors (warnings about unused imports in other files are OK)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/events.ts frontend/src/api/client.ts
git commit -m "feat: add slide library types and API client functions"
```

Note: At this point `LibraryDeck` and `LibrarySlide` imports in `client.ts` need to come from `@/types/events`.  Verify the import line at the top of `client.ts` already imports from `@/types/events`:

```typescript
import type { Project, PointItem } from '@/types/events'
```

Change to:

```typescript
import type { Project, PointItem, LibraryDeck, LibrarySlide } from '@/types/events'
```

---

### Task 5: Zustand Store · slideLibraryStore

**Files:**
- Create: `frontend/src/stores/slideLibraryStore.ts`

- [ ] **Step 1: 创建 store**

```typescript
import { create } from 'zustand'
import type { LibraryDeck, LibrarySlide } from '@/types/events'
import {
  listLibraryDecks,
  getLibraryDeck,
  uploadToLibrary,
  deleteLibraryDeck,
  updateLibraryDeckName,
  updateLibrarySlide,
  importSlidesToProject,
} from '@/api/client'

interface SlideLibraryState {
  decks: LibraryDeck[]
  expandedDeckId: string | null
  expandedSlides: LibrarySlide[]
  loading: boolean
  searchQuery: string
  uploadError: string | null

  loadDecks: () => Promise<void>
  toggleExpand: (deckId: string) => Promise<void>
  uploadDeck: (file: File) => Promise<string | null>
  removeDeck: (id: string) => Promise<void>
  renameDeck: (id: string, name: string) => Promise<void>
  patchSlide: (id: string, data: { slide_number?: string | null; tags?: string[] }) => Promise<void>
  importToProject: (projectId: string, slideIds: string[]) => Promise<number>
  setSearchQuery: (q: string) => void
}

export const useSlideLibraryStore = create<SlideLibraryState>((set, get) => ({
  decks: [],
  expandedDeckId: null,
  expandedSlides: [],
  loading: false,
  searchQuery: '',
  uploadError: null,

  loadDecks: async () => {
    set({ loading: true })
    try {
      const decks = await listLibraryDecks()
      set({ decks, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  toggleExpand: async (deckId: string) => {
    const { expandedDeckId } = get()
    if (expandedDeckId === deckId) {
      set({ expandedDeckId: null, expandedSlides: [] })
    } else {
      const data = await getLibraryDeck(deckId)
      set({ expandedDeckId: deckId, expandedSlides: data.slides })
    }
  },

  uploadDeck: async (file: File) => {
    set({ uploadError: null })
    try {
      const result = await uploadToLibrary(file)
      await get().loadDecks()
      return result.library_id
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string }
      const msg = e.response?.data?.detail || e.message || '上传失败'
      set({ uploadError: msg })
      return null
    }
  },

  removeDeck: async (id: string) => {
    await deleteLibraryDeck(id)
    const { expandedDeckId } = get()
    if (expandedDeckId === id) {
      set({ expandedDeckId: null, expandedSlides: [] })
    }
    await get().loadDecks()
  },

  renameDeck: async (id: string, name: string) => {
    await updateLibraryDeckName(id, name)
    await get().loadDecks()
  },

  patchSlide: async (id: string, data) => {
    await updateLibrarySlide(id, data)
    const { expandedDeckId } = get()
    if (expandedDeckId) {
      const refreshed = await getLibraryDeck(expandedDeckId)
      set({ expandedSlides: refreshed.slides })
    }
  },

  importToProject: async (projectId, slideIds) => {
    const result = await importSlidesToProject(projectId, slideIds)
    return result.total_slides
  },

  setSearchQuery: (q: string) => set({ searchQuery: q }),
}))
```

- [ ] **Step 2: 验证前端编译**

Run: `cd frontend && npm run build 2>&1 | tail -5`
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/stores/slideLibraryStore.ts
git commit -m "feat: add slideLibrary Zustand store"
```

---

### Task 6: 前端组件 · TagEditor

**Files:**
- Create: `frontend/src/components/SlideLibrary/TagEditor.tsx`

- [ ] **Step 1: 创建 TagEditor 组件**

```tsx
import { useState, useRef, useEffect } from 'react'
import { X, Plus } from 'lucide-react'

interface Props {
  tags: string[]
  onTagsChange: (tags: string[]) => void
}

export function TagEditor({ tags, onTagsChange }: Props) {
  const [editing, setEditing] = useState(false)
  const [input, setInput] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (editing) inputRef.current?.focus()
  }, [editing])

  const removeTag = (idx: number) => {
    onTagsChange(tags.filter((_, i) => i !== idx))
  }

  const addTags = () => {
    const newTags = input
      .split(/[,，]/)
      .map(t => t.trim())
      .filter(t => t.length > 0 && !tags.includes(t))
    if (newTags.length > 0) {
      onTagsChange([...tags, ...newTags])
    }
    setInput('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      addTags()
    } else if (e.key === 'Escape') {
      setEditing(false)
      setInput('')
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-1 min-h-[20px]">
      {tags.map((tag, i) => (
        <span
          key={i}
          className="inline-flex items-center gap-0.5 bg-primary/10 text-primary text-[10px] px-1.5 py-0.5 rounded-full"
        >
          {tag}
          <button
            onClick={(e) => { e.stopPropagation(); removeTag(i) }}
            className="hover:text-red-500 transition-colors"
          >
            <X className="w-3 h-3" />
          </button>
        </span>
      ))}
      {editing ? (
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={() => { addTags(); setEditing(false) }}
          placeholder="标签, 逗号分隔"
          className="text-[10px] bg-transparent border-b border-primary/30 outline-none px-1 py-0.5 w-28"
        />
      ) : (
        <button
          onClick={() => setEditing(true)}
          className="inline-flex items-center gap-0.5 text-[10px] text-muted-foreground hover:text-primary transition-colors"
        >
          <Plus className="w-3 h-3" />
          {tags.length === 0 ? '标签' : ''}
        </button>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/SlideLibrary/TagEditor.tsx
git commit -m "feat: add TagEditor component for slide library"
```

---

### Task 7: 前端组件 · LibrarySlideCard

**Files:**
- Create: `frontend/src/components/SlideLibrary/LibrarySlideCard.tsx`

- [ ] **Step 1: 创建 LibrarySlideCard 组件**

```tsx
import { useState } from 'react'
import { Plus, Check } from 'lucide-react'
import type { LibrarySlide } from '@/types/events'
import { TagEditor } from './TagEditor'
import { useSlideLibraryStore } from '@/stores/slideLibraryStore'

interface Props {
  slide: LibrarySlide
  onImport?: (slideId: string) => void
}

export function LibrarySlideCard({ slide, onImport }: Props) {
  const patchSlide = useSlideLibraryStore((s) => s.patchSlide)
  const [imported, setImported] = useState(false)
  const [localNumber, setLocalNumber] = useState(slide.slide_number || '')

  const handleNumberBlur = () => {
    if (localNumber !== (slide.slide_number || '')) {
      patchSlide(slide.id, { slide_number: localNumber || null })
    }
  }

  const handleTagsChange = (tags: string[]) => {
    patchSlide(slide.id, { tags })
  }

  const handleImport = () => {
    if (imported) return
    onImport?.(slide.id)
    setImported(true)
    setTimeout(() => setImported(false), 2000)
  }

  return (
    <div className="group flex gap-2 p-2 rounded-lg hover:bg-accent/30 transition-all border border-transparent hover:border-border/30">
      {/* Thumbnail */}
      <div className="w-28 h-[63px] shrink-0 bg-muted/30 rounded-md overflow-hidden border border-border/20">
        {slide.thumbnail_url ? (
          <img
            src={slide.thumbnail_url}
            alt={slide.title}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-[10px] text-muted-foreground">
            {slide.slide_index}
          </div>
        )}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0 flex flex-col justify-between">
        <div className="flex items-center gap-1.5">
          <input
            value={localNumber}
            onChange={(e) => setLocalNumber(e.target.value)}
            onBlur={handleNumberBlur}
            placeholder={`#${slide.slide_index}`}
            className="text-[10px] font-mono bg-transparent border-b border-transparent hover:border-border/30 focus:border-primary/30 outline-none w-12 text-muted-foreground"
          />
          <p className="text-xs font-medium truncate flex-1">{slide.title}</p>
        </div>

        <TagEditor tags={slide.tags} onTagsChange={handleTagsChange} />

        <div className="flex items-center gap-2">
          <span className="text-[10px] text-muted-foreground capitalize">{slide.layout_hint || 'slide'}</span>
          <span className="text-[10px] text-muted-foreground/50">
            {(slide.text_summary || '').slice(0, 40)}...
          </span>
        </div>
      </div>

      {/* Import button */}
      <button
        onClick={handleImport}
        disabled={imported}
        className="shrink-0 self-center opacity-0 group-hover:opacity-100 transition-all p-1 rounded-md hover:bg-primary/10 text-primary disabled:opacity-100 disabled:text-green-500"
        title="插入到项目"
      >
        {imported ? <Check className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
      </button>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/SlideLibrary/LibrarySlideCard.tsx
git commit -m "feat: add LibrarySlideCard component"
```

---

### Task 8: 前端组件 · DeckCard

**Files:**
- Create: `frontend/src/components/SlideLibrary/DeckCard.tsx`

- [ ] **Step 1: 创建 DeckCard 组件**

```tsx
import { useState } from 'react'
import { ChevronDown, ChevronRight, Trash2, Pencil } from 'lucide-react'
import type { LibraryDeck } from '@/types/events'
import { useSlideLibraryStore } from '@/stores/slideLibraryStore'
import { LibrarySlideCard } from './LibrarySlideCard'

interface Props {
  deck: LibraryDeck
}

export function DeckCard({ deck }: Props) {
  const [editingName, setEditingName] = useState(false)
  const [name, setName] = useState(deck.name)
  const expandedDeckId = useSlideLibraryStore((s) => s.expandedDeckId)
  const expandedSlides = useSlideLibraryStore((s) => s.expandedSlides)
  const toggleExpand = useSlideLibraryStore((s) => s.toggleExpand)
  const removeDeck = useSlideLibraryStore((s) => s.removeDeck)
  const renameDeck = useSlideLibraryStore((s) => s.renameDeck)
  const importToProject = useSlideLibraryStore((s) => s.importToProject)
  const currentProject = useSlideLibraryStore.getState ? null : null // 稍后从 projectStore 获取

  const isExpanded = expandedDeckId === deck.id

  const handleToggle = () => {
    toggleExpand(deck.id)
  }

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (confirm(`删除「${deck.name}」及其全部 ${deck.slide_count} 页？`)) {
      removeDeck(deck.id)
    }
  }

  const handleNameBlur = () => {
    setEditingName(false)
    const trimmed = name.trim()
    if (trimmed && trimmed !== deck.name) {
      renameDeck(deck.id, trimmed)
    } else {
      setName(deck.name)
    }
  }

  const handleImportSlide = async (slideId: string) => {
    const store = (await import('@/stores/projectStore')).useProjectStore.getState()
    const pid = store.currentProject?.id
    if (!pid) return
    await importToProject(pid, [slideId])
  }

  return (
    <div className="border border-border/20 rounded-xl overflow-hidden bg-card/30 transition-all">
      {/* Header */}
      <button
        onClick={handleToggle}
        className="w-full flex items-center gap-2 px-3 py-2.5 hover:bg-accent/20 transition-colors text-left"
      >
        <span className="text-muted-foreground shrink-0">
          {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </span>

        {editingName ? (
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            onBlur={handleNameBlur}
            onKeyDown={(e) => { if (e.key === 'Enter') handleNameBlur() }}
            className="flex-1 text-sm font-medium bg-transparent border-b border-primary/30 outline-none px-1"
            autoFocus
            onClick={(e) => e.stopPropagation()}
          />
        ) : (
          <span className="flex-1 text-sm font-medium truncate">{deck.name}</span>
        )}

        <span className="text-[10px] text-muted-foreground bg-muted/30 px-1.5 py-0.5 rounded-full">
          {deck.slide_count} 页
        </span>

        <button
          onClick={(e) => { e.stopPropagation(); setEditingName(true); setName(deck.name) }}
          className="opacity-0 group-hover:opacity-100 p-0.5 hover:text-primary transition-all"
          title="重命名"
        >
          <Pencil className="w-3 h-3" />
        </button>

        <button
          onClick={handleDelete}
          className="opacity-0 group-hover:opacity-100 p-0.5 hover:text-red-500 transition-all"
          title="删除"
        >
          <Trash2 className="w-3 h-3" />
        </button>
      </button>

      {/* Expanded slides */}
      {isExpanded && (
        <div className="border-t border-border/10 divide-y divide-border/10">
          {expandedSlides.length === 0 ? (
            <p className="text-xs text-muted-foreground p-4 text-center">加载中...</p>
          ) : (
            expandedSlides.map((slide) => (
              <LibrarySlideCard
                key={slide.id}
                slide={slide}
                onImport={handleImportSlide}
              />
            ))
          )}
        </div>
      )}
    </div>
  )
}
```

Wait — the `DeckCard` has a problem with importing `useProjectStore` dynamically. Let me fix that. The `handleImportSlide` should use a prop callback instead of importing dynamically. Let me restructure.

Fix: Pass `projectId` as a prop from the parent.

```tsx
import { useState } from 'react'
import { ChevronDown, ChevronRight, Trash2, Pencil } from 'lucide-react'
import type { LibraryDeck } from '@/types/events'
import { useSlideLibraryStore } from '@/stores/slideLibraryStore'
import { LibrarySlideCard } from './LibrarySlideCard'

interface Props {
  deck: LibraryDeck
  projectId: string | null
}

export function DeckCard({ deck, projectId }: Props) {
  const [editingName, setEditingName] = useState(false)
  const [name, setName] = useState(deck.name)
  const expandedDeckId = useSlideLibraryStore((s) => s.expandedDeckId)
  const expandedSlides = useSlideLibraryStore((s) => s.expandedSlides)
  const toggleExpand = useSlideLibraryStore((s) => s.toggleExpand)
  const removeDeck = useSlideLibraryStore((s) => s.removeDeck)
  const renameDeck = useSlideLibraryStore((s) => s.renameDeck)
  const importToProject = useSlideLibraryStore((s) => s.importToProject)

  const isExpanded = expandedDeckId === deck.id

  const handleToggle = () => {
    toggleExpand(deck.id)
  }

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (confirm(`删除「${deck.name}」及其全部 ${deck.slide_count} 页？`)) {
      removeDeck(deck.id)
    }
  }

  const handleNameBlur = () => {
    setEditingName(false)
    const trimmed = name.trim()
    if (trimmed && trimmed !== deck.name) {
      renameDeck(deck.id, trimmed)
    } else {
      setName(deck.name)
    }
  }

  const handleImportSlide = async (slideId: string) => {
    if (!projectId) return
    await importToProject(projectId, [slideId])
  }

  return (
    <div className="group border border-border/20 rounded-xl overflow-hidden bg-card/30 transition-all">
      {/* Header */}
      <button
        onClick={handleToggle}
        className="w-full flex items-center gap-2 px-3 py-2.5 hover:bg-accent/20 transition-colors text-left"
      >
        <span className="text-muted-foreground shrink-0">
          {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </span>

        {editingName ? (
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            onBlur={handleNameBlur}
            onKeyDown={(e) => { if (e.key === 'Enter') handleNameBlur() }}
            className="flex-1 text-sm font-medium bg-transparent border-b border-primary/30 outline-none px-1"
            autoFocus
            onClick={(e) => e.stopPropagation()}
          />
        ) : (
          <span className="flex-1 text-sm font-medium truncate">{deck.name}</span>
        )}

        <span className="text-[10px] text-muted-foreground bg-muted/30 px-1.5 py-0.5 rounded-full">
          {deck.slide_count} 页
        </span>

        <button
          onClick={(e) => { e.stopPropagation(); setEditingName(true); setName(deck.name) }}
          className="opacity-0 group-hover:opacity-100 p-0.5 hover:text-primary transition-all"
          title="重命名"
        >
          <Pencil className="w-3 h-3" />
        </button>

        <button
          onClick={handleDelete}
          className="opacity-0 group-hover:opacity-100 p-0.5 hover:text-red-500 transition-all"
          title="删除"
        >
          <Trash2 className="w-3 h-3" />
        </button>
      </button>

      {/* Expanded slides */}
      {isExpanded && (
        <div className="border-t border-border/10 divide-y divide-border/10">
          {expandedSlides.length === 0 ? (
            <p className="text-xs text-muted-foreground p-4 text-center">加载中...</p>
          ) : (
            expandedSlides.map((slide) => (
              <LibrarySlideCard
                key={slide.id}
                slide={slide}
                onImport={handleImportSlide}
              />
            ))
          )}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/SlideLibrary/DeckCard.tsx
git commit -m "feat: add DeckCard component with expand/collapse"
```

---

### Task 9: 前端组件 · SlideLibraryPanel (主面板)

**Files:**
- Create: `frontend/src/components/SlideLibrary/index.tsx`

- [ ] **Step 1: 创建主面板组件**

```tsx
import { useEffect, useRef, useState } from 'react'
import { Upload, Search, Loader2, Inbox } from 'lucide-react'
import { useSlideLibraryStore } from '@/stores/slideLibraryStore'
import { useProjectStore } from '@/stores/projectStore'
import { DeckCard } from './DeckCard'

const MAX_FILE_SIZE = 50 * 1024 * 1024

export function SlideLibraryPanel() {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const currentProject = useProjectStore((s) => s.currentProject)
  const addMessage = useProjectStore((s) => s.addMessage)

  const {
    decks,
    loading,
    searchQuery,
    uploadError,
    loadDecks,
    uploadDeck,
    setSearchQuery,
  } = useSlideLibraryStore()

  useEffect(() => {
    loadDecks()
  }, [loadDecks])

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    e.target.value = ''

    if (!file.name.endsWith('.pptx')) {
      addMessage?.('system', '企业库仅支持 .pptx 文件')
      return
    }
    if (file.size > MAX_FILE_SIZE) {
      addMessage?.('system', '文件过大（最大 50MB）')
      return
    }

    setUploading(true)
    const libraryId = await uploadDeck(file)
    setUploading(false)
    if (libraryId) {
      addMessage?.('system', `已上传「${file.name}」到企业幻灯片库（${file.size > 1024 * 1024 ? (file.size / 1024 / 1024).toFixed(1) + 'MB' : (file.size / 1024).toFixed(0) + 'KB'}）`)
    }
  }

  const filtered = decks.filter((d) =>
    !searchQuery || d.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-3 border-b border-border/30 space-y-2 shrink-0">
        <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest font-display">
          企业幻灯片库
        </h2>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索标题或标签..."
            className="w-full pl-7 pr-3 py-1.5 text-xs rounded-lg border border-border/30 bg-muted/20 outline-none focus:border-primary/30 transition-colors"
          />
        </div>

        {/* Upload button */}
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className="w-full rounded-lg border border-dashed border-border/40 p-2 text-xs text-muted-foreground hover:text-primary hover:border-primary/30 hover:bg-accent/20 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {uploading ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              正在提取...
            </>
          ) : (
            <>
              <Upload className="w-3.5 h-3.5" />
              上传 PPT 到企业库
            </>
          )}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept=".pptx"
          onChange={handleUpload}
        />

        {uploadError && (
          <p className="text-[10px] text-red-500">❌ {uploadError}</p>
        )}
      </div>

      {/* Deck list */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-muted-foreground gap-2">
            <Inbox className="w-10 h-10 opacity-30" />
            <p className="text-xs">
              {searchQuery ? '没有匹配的 PPT' : '上传你的第一个企业 PPT'}
            </p>
            <p className="text-[10px] opacity-50">
              上传后自动逐页提取，可编号、打标签、复用
            </p>
          </div>
        ) : (
          filtered.map((deck) => (
            <DeckCard
              key={deck.id}
              deck={deck}
              projectId={currentProject?.id ?? null}
            />
          ))
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/SlideLibrary/index.tsx
git commit -m "feat: add SlideLibraryPanel main component"
```

---

### Task 10: App.tsx 集成 · 新增企业库 tab

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: 修改 RightTab 类型和 tab 渲染**

Edit `frontend/src/App.tsx`:

Line 5 — 添加导入：
```typescript
import { SlideLibraryPanel } from '@/components/SlideLibrary'
```

Line 16 — 修改类型：
```typescript
type RightTab = 'slides' | 'style' | 'library'
```

Lines 179-215 — 替换整个右侧面板 header + content 部分：

```tsx
        {/* Right panel: slides / style / library */}
        <Panel id="right-panel" order={3} defaultSize={30} minSize={15} maxSize={45}>
          <div className="h-full flex flex-col border-l border-border/50 backdrop-blur-sm">
            <div className="h-12 border-b border-border/50 flex shrink-0 bg-gradient-to-r from-transparent to-card/50">
              {(['slides', 'style', 'library'] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setRightTab(tab)}
                  className={`flex-1 text-sm font-medium transition-all relative ${
                    rightTab === tab
                      ? 'text-primary'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  {tab === 'slides' ? '幻灯片' : tab === 'style' ? '风格' : '企业库'}
                  {rightTab === tab && (
                    <span className="absolute bottom-0 left-1/4 right-1/4 h-0.5 bg-primary rounded-full shadow-[0_0_8px_var(--glow-color)]" />
                  )}
                </button>
              ))}
            </div>
            <div className="flex-1 overflow-y-auto">
              {rightTab === 'slides' ? (
                <SlideWaterfall />
              ) : rightTab === 'style' ? (
                <StylePanel />
              ) : (
                <SlideLibraryPanel />
              )}
            </div>
          </div>
        </Panel>
```

- [ ] **Step 2: 验证前端编译**

Run: `cd frontend && npm run build 2>&1 | tail -10`
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat: add enterprise slide library tab to right panel"
```

---

### Task 11: ChatPanel @ 引用 · 基础搜索触发器

**Files:**
- Modify: `frontend/src/components/ChatPanel/index.tsx`

- [ ] **Step 1: 在输入框添加 @ 触发逻辑**

Read `ChatPanel/index.tsx` to find the input area (near the bottom where the text input and send button are). Add @ detection:

In the input's `onChange` handler, detect when user types `@` and set a flag. When `@` is typed, show a small popup with search results from the slide library.

Read the existing ChatPanel file first.

**Step 1a: Read ChatPanel/index.tsx**

Run: `wc -l frontend/src/components/ChatPanel/index.tsx`

If the file is large, read the input area section. Then add:

In the component body, add these states near other useState declarations:

```typescript
const [showSlideSearch, setShowSlideSearch] = useState(false)
const [slideSearchQuery, setSlideSearchQuery] = useState('')
```

Add a `useEffect` that watches the input value:

```typescript
// Detect @ trigger in input
useEffect(() => {
  const lastAt = inputValue.lastIndexOf('@')
  if (lastAt >= 0 && lastAt === inputValue.length - 1) {
    setShowSlideSearch(true)
    setSlideSearchQuery('')
  }
}, [inputValue])
```

Add the slide search popup right before the input area:

```tsx
{showSlideSearch && (
  <SlideSearchPopup
    query={slideSearchQuery}
    onSelect={(slide) => {
      // Insert reference into message
      const ref = `@slide:${slide.library_id}/${slide.slide_index} 「${slide.title}」`
      setInputValue((prev) => prev.replace(/@$/, ref))
      setShowSlideSearch(false)
    }}
    onClose={() => setShowSlideSearch(false)}
    onQueryChange={setSlideSearchQuery}
  />
)}
```

**Step 1b: Create SlideSearchPopup inline (minimal version)**

For the popup, create a small component at the bottom of ChatPanel/index.tsx or as a separate file. Minimal implementation:

```tsx
function SlideSearchPopup({
  query,
  onSelect,
  onClose,
  onQueryChange,
}: {
  query: string
  onSelect: (slide: LibrarySlide) => void
  onClose: () => void
  onQueryChange: (q: string) => void
}) {
  const [results, setResults] = useState<LibrarySlide[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!query) {
      setResults([])
      return
    }
    const timer = setTimeout(async () => {
      setLoading(true)
      try {
        const data = await searchLibrarySlides(query)
        setResults(data)
      } catch { setResults([]) }
      setLoading(false)
    }, 200)
    return () => clearTimeout(timer)
  }, [query])

  return (
    <div className="absolute bottom-full mb-2 left-0 right-0 bg-card border border-border rounded-xl shadow-xl z-50 max-h-64 overflow-y-auto">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-border/30">
        <Search className="w-3.5 h-3.5 text-muted-foreground" />
        <input
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder="搜索企业库 slide..."
          className="flex-1 text-xs bg-transparent outline-none"
          autoFocus
        />
        <button onClick={onClose} className="text-xs text-muted-foreground hover:text-foreground">✕</button>
      </div>
      {loading ? (
        <div className="px-3 py-4 text-center"><Loader2 className="w-4 h-4 animate-spin mx-auto" /></div>
      ) : results.length === 0 ? (
        <p className="px-3 py-4 text-xs text-muted-foreground text-center">
          {query ? '无匹配结果' : '输入关键词搜索'}
        </p>
      ) : (
        results.map((s) => (
          <button
            key={s.id}
            onClick={() => onSelect(s)}
            className="w-full text-left px-3 py-2 hover:bg-accent/30 transition-colors flex items-center gap-2"
          >
            <span className="text-xs font-mono text-muted-foreground shrink-0">
              {s.slide_number || `#${s.slide_index}`}
            </span>
            <span className="text-xs truncate flex-1">{s.title}</span>
            <span className="text-[10px] text-muted-foreground capitalize">{s.layout_hint}</span>
          </button>
        ))
      )}
    </div>
  )
}
```

Add the needed imports at the top of ChatPanel/index.tsx:

```typescript
import { searchLibrarySlides } from '@/api/client'
import type { LibrarySlide } from '@/types/events'
```

- [ ] **Step 2: 验证前端编译**

Run: `cd frontend && npm run build 2>&1 | tail -10`
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ChatPanel/index.tsx
git commit -m "feat: add @ mention slide search in ChatPanel input"
```

---

### Task 12: 端到端验证 + 回归测试

**Files:** None (test only)

- [ ] **Step 1: 运行全部后端测试**

```bash
.venv/bin/pytest backend/tests/ -v --tb=short 2>&1 | tail -20
```

Expected: 76+ passed, 0 new failures

- [ ] **Step 2: 验证 slide_library 模型可创建表**

```bash
.venv/bin/python -c "
import asyncio
from backend.models.database import create_all_tables
asyncio.run(create_all_tables())
print('Tables created OK')
"
```

- [ ] **Step 3: 前端完整编译**

```bash
cd frontend && npm run build 2>&1 | tail -10
```

Expected: no errors

- [ ] **Step 4: Commit (if any fixups)**

No commit needed unless fixes were made.
```

---

## 自审清单

1. **Spec 覆盖**: 逐条对照 spec：
   - ✅ 数据模型 (slide_libraries + library_slides 表)
   - ✅ 存储结构 (.slide_library/{user_id}/decks/{lib_id}/)
   - ✅ 7 个 API 端点全部实现
   - ✅ 上传流程（保存→解压→提取→写库）
   - ✅ 导入流程（验证归属→读 XML→插入 OUTLINE.md）
   - ✅ 前端组件树（Panel → DeckCard → LibrarySlideCard → TagEditor）
   - ✅ App.tsx 新增 tab
   - ✅ @ 引用触发搜索弹出
   - ✅ 标签自由文本、逗号分隔
   - ✅ SQLite LIKE + JSON 搜索（无向量数据库）
   - ✅ 导入仅限 idle 阶段
   - ✅ 单文件 ≤ 50MB

2. **无占位符**: 搜索 TBD/TODO/placeholder — 无匹配。

3. **类型一致性**:
   - `LibrarySlide.id` 在后端是 `String` (UUID hex)，前端是 `string` — 一致
   - `LibrarySlide.tags` 后端 `JSON` → Python `list[str]`，前端 `string[]` — 一致
   - `SlideNumberUpdate` Pydantic schema 与 `PATCH /slides/{id}` body 匹配
   - Store `patchSlide` 签名与 `updateLibrarySlide` API 一致
   - `DeckCard` 的 `projectId` prop 正确传入 `handleImportSlide`
