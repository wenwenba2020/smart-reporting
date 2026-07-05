"""企业幻灯片库 API 端点"""
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.llm_client import get_client
from backend.api.auth import get_current_user
from backend.config import settings
from backend.models.database import get_db
from backend.models.outline import load_outline
from backend.models.project import Project
from backend.models.slide_library import SlideLibrary, LibrarySlide
from backend.parsers.design_extractor import generate_design_md, save_user_template
from backend.pipeline.slide_cloner import clone_slide_to_project
from backend.parsers.slide_extractor import extract_slides_from_pptx
from backend.storage.file_manager import ProjectStorage

router = APIRouter(prefix="/library", tags=["library"])

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
LIBRARY_BASE = Path(settings.LOCAL_STORAGE_PATH) / ".slide_library"


class SlideNumberUpdate(BaseModel):
    slide_number: str | None = None
    tags: list[str] | None = None


class ImportRequest(BaseModel):
    slide_ids: list[str]
    clone_design: bool = False


class ExtractDesignRequest(BaseModel):
    name: str | None = None


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

    library = SlideLibrary(
        user_id=user,
        name=Path(file.filename or "untitled").stem,
        original_filename=file.filename or "untitled.pptx",
    )
    db.add(library)
    await db.flush()

    lib_dir = _lib_dir(user, library.id)
    lib_dir.mkdir(parents=True, exist_ok=True)
    original_path = lib_dir / "original.pptx"
    original_path.write_bytes(content)

    slides_dir = lib_dir / "slides"
    extracted = extract_slides_from_pptx(str(original_path), str(slides_dir))

    library.slide_count = len(extracted)
    for e in extracted:
        lib_slide = LibrarySlide(
            library_id=library.id,
            slide_index=e.slide_index,
            title=e.title,
            text_summary=e.text_summary,
            tags=e.tags,
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
            "scenario_type": d.scenario_type,
            "source_type": d.source_type,
            "is_excellent": d.is_excellent,
            "tags": d.tags or [],
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
        select(SlideLibrary)
        .options(selectinload(SlideLibrary.slides))
        .where(
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
        "scenario_type": library.scenario_type,
        "source_type": library.source_type,
        "is_excellent": library.is_excellent,
        "tags": library.tags or [],
        "created_at": library.created_at.isoformat(),
        "slides": [
            {
                "id": s.id,
                "slide_index": s.slide_index,
                "slide_number": s.slide_number,
                "title": s.title,
                "text_summary": s.text_summary,
                "tags": s.tags or [],
                "business_tags": s.business_tags or [],
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

    result = await db.execute(
        select(LibrarySlide).join(SlideLibrary).where(
            LibrarySlide.id.in_(body.slide_ids),
            SlideLibrary.user_id == user,
        )
    )
    lib_slides = list(result.scalars().all())
    if len(lib_slides) != len(body.slide_ids):
        raise HTTPException(status_code=404, detail="Some slides not found")

    from backend.models.outline import save_outline, SlideItem, OutlineDoc, OutlineMeta

    storage = ProjectStorage.get()
    outline_path = storage.get_project_path(project_id) / "OUTLINE.md"

    if outline_path.exists():
        outline = load_outline(str(outline_path))
    else:
        now = datetime.now(timezone.utc).isoformat()
        outline = OutlineDoc(
            meta=OutlineMeta(
                title=project.name,
                total_slides=0,
                created_at=now,
                updated_at=now,
            ),
            slides=[],
        )

    max_id = max((int(s.slide_id) for s in outline.slides), default=0)
    imported: list[str] = []
    for lib_slide in lib_slides:
        max_id += 1
        new_id = f"{max_id:02d}"
        tag_hint = f"参考标签: {', '.join(lib_slide.tags)}" if lib_slide.tags else ""
        design_ref = None
        design_images = None
        if body.clone_design and lib_slide.raw_slide_xml_path:
            src_xml = _lib_dir(user, lib_slide.library_id) / lib_slide.raw_slide_xml_path
            src_dir = _lib_dir(user, lib_slide.library_id) / "slides" / f"slide_{lib_slide.slide_index:02d}"
            cloned = clone_slide_to_project(
                str(src_xml),
                str(src_dir),
                str(storage.get_project_path(project_id)),
                new_id,
            )
            design_ref = cloned.design_ref
            design_images = cloned.design_images
        outline.slides.append(SlideItem(
            slide_id=new_id,
            layout=lib_slide.layout_hint or "title-content",
            title=lib_slide.title or f"Slide {new_id}",
            visual_intent=tag_hint if tag_hint else None,
            notes_speaker=lib_slide.text_summary or "",
            design_ref=design_ref,
            design_images=design_images,
        ))
        imported.append(new_id)

    outline.meta.total_slides = len(outline.slides)
    save_outline(outline, str(outline_path))

    project.total_slides = len(outline.slides)
    await db.commit()

    return {
        "imported_slide_ids": imported,
        "total_slides": len(outline.slides),
    }


def _embed(text: str) -> list[float]:
    """Convert text to embedding vector via OpenRouter."""
    client = get_client()
    text = text[:8000]
    resp = client.embeddings.create(
        model="openai/text-embedding-3-small",
        input=[text],
        timeout=30,
    )
    return resp.data[0].embedding


def _cosine(a: list[float], b: list[float]) -> float:
    a_np = np.array(a)
    b_np = np.array(b)
    return float(np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np) + 1e-10))


@router.get("/recommend/{project_id}")
async def recommend_slides(
    project_id: str,
    limit: int = 10,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Recommend library slides based on project context via embedding similarity."""
    project = await db.get(Project, project_id)
    if not project or project.user_id != user:
        raise HTTPException(status_code=404, detail="Project not found")

    storage = ProjectStorage.get()
    outline_path = storage.get_project_path(project_id) / "OUTLINE.md"
    project_summary = project.name or ""
    if outline_path.exists():
        try:
            outline = load_outline(str(outline_path))
            titles = [s.title for s in outline.slides if s.title]
            if titles:
                project_summary = f"{project.name}: {', '.join(titles[:10])}"
        except Exception:
            pass

    result = await db.execute(
        select(LibrarySlide).join(SlideLibrary).where(
            SlideLibrary.user_id == user
        )
    )
    all_slides = list(result.scalars().all())
    if not all_slides:
        return {"project_id": project_id, "recommendations": []}

    try:
        proj_embed = _embed(project_summary)
        scored: list[tuple[float, dict]] = []
        for s in all_slides:
            slide_text = f"{s.title or ''} {s.text_summary or ''}"[:2000]
            slide_embed = _embed(slide_text)
            score = _cosine(proj_embed, slide_embed)
            scored.append((score, {
                "id": s.id,
                "library_id": s.library_id,
                "slide_index": s.slide_index,
                "slide_number": s.slide_number,
                "title": s.title,
                "text_summary": (s.text_summary or "")[:200],
                "tags": s.tags or [],
                "thumbnail_url": f"/project-files/.slide_library/{user}/decks/{s.library_id}/slides/slide_{s.slide_index:02d}/thumbnail.svg",
                "layout_hint": s.layout_hint,
                "score": round(score, 3),
            }))

        scored.sort(key=lambda x: x[0], reverse=True)
        recommendations = [item for _, item in scored[:limit] if item["score"] > 0.3]
        return {"project_id": project_id, "recommendations": recommendations}

    except Exception as e:
        return {
            "project_id": project_id,
            "recommendations": [],
            "error": str(e),
        }


@router.post("/decks/{library_id}/extract-design")
async def extract_design(
    library_id: str,
    body: ExtractDesignRequest = ExtractDesignRequest(),
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """从 PPTX 提取设计规范，保存为用户模板。"""
    result = await db.execute(
        select(SlideLibrary).where(
            SlideLibrary.id == library_id,
            SlideLibrary.user_id == user,
        )
    )
    library = result.scalar_one_or_none()
    if not library:
        raise HTTPException(status_code=404, detail="Deck not found")

    pptx_path = _lib_dir(user, library_id) / "original.pptx"
    if not pptx_path.exists():
        raise HTTPException(status_code=404, detail="Original PPTX file not found")

    try:
        slug, content = generate_design_md(str(pptx_path), body.name)
        filepath = save_user_template(user, slug, content)
        return {
            "slug": slug,
            "name": body.name or library.name,
            "path": str(filepath),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Design extraction failed: {str(e)}")


@router.delete("/templates/{slug}")
async def delete_user_template(
    slug: str,
    user: str = Depends(get_current_user),
):
    """删除用户提取的设计模板。"""
    templates_dir = LIBRARY_BASE / user / "templates"
    filepath = templates_dir / f"{slug}.md"
    if not filepath.is_file():
        raise HTTPException(status_code=404, detail="Template not found")
    filepath.unlink()
    return {"deleted": slug}


class DeckTagUpdate(BaseModel):
    scenario_type: str | None = None
    is_excellent: bool | None = None
    tags: list[str] | None = None


@router.patch("/decks/{library_id}/classify")
async def classify_deck(
    library_id: str,
    body: DeckTagUpdate,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新案例的场景分类/优质标记/业务标签。"""
    result = await db.execute(
        select(SlideLibrary).where(
            SlideLibrary.id == library_id,
            SlideLibrary.user_id == user,
        )
    )
    library = result.scalar_one_or_none()
    if not library:
        raise HTTPException(status_code=404, detail="Deck not found")

    if body.scenario_type is not None:
        library.scenario_type = body.scenario_type
    if body.is_excellent is not None:
        library.is_excellent = body.is_excellent
    if body.tags is not None:
        library.tags = body.tags
    await db.commit()
    return {
        "id": library.id,
        "scenario_type": library.scenario_type,
        "is_excellent": library.is_excellent,
        "tags": library.tags,
    }
