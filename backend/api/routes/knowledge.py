"""企业知识库 API 端点"""
import shutil
from pathlib import Path

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_current_user
from backend.config import settings
from backend.models.database import get_db
from backend.models.knowledge import KnowledgeBase, KnowledgeEntry
from backend.parsers.knowledge_ingest import ingest_file, compute_embedding, cosine_similarity

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

MAX_FILE_SIZE = 50 * 1024 * 1024
KB_BASE = Path(settings.LOCAL_STORAGE_PATH) / ".knowledge_base"


def _kb_dir(user_id: str, kb_id: str) -> Path:
    return KB_BASE / user_id / kb_id


@router.post("/bases")
async def create_kb(
    body: dict,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建知识库分类。"""
    kb = KnowledgeBase(
        user_id=user,
        name=body.get("name", "未命名"),
        description=body.get("description"),
        category=body.get("category", "general"),
    )
    db.add(kb)
    await db.commit()
    await db.refresh(kb)
    return {"id": kb.id, "name": kb.name, "category": kb.category}


@router.get("/bases")
async def list_kbs(
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """列出所有知识库。"""
    result = await db.execute(
        select(KnowledgeBase)
        .where(KnowledgeBase.user_id == user)
        .order_by(KnowledgeBase.created_at.desc())
    )
    kbs = result.scalars().all()
    return [
        {
            "id": kb.id, "name": kb.name, "description": kb.description,
            "category": kb.category, "entry_count": kb.entry_count,
            "created_at": kb.created_at.isoformat(),
        }
        for kb in kbs
    ]


@router.delete("/bases/{kb_id}")
async def delete_kb(
    kb_id: str,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除知识库及其所有条目。"""
    result = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.user_id == user,
        )
    )
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    kb_dir = _kb_dir(user, kb_id)
    if kb_dir.exists():
        shutil.rmtree(kb_dir)

    await db.delete(kb)
    await db.commit()
    return {"deleted": kb_id}


@router.post("/bases/{kb_id}/upload")
async def upload_to_kb(
    kb_id: str,
    file: UploadFile = File(...),
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """上传文档到知识库，自动解析、分块、embedding。"""
    result = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.user_id == user,
        )
    )
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in (".pdf", ".docx", ".txt", ".md", ".csv"):
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")

    kb_dir = _kb_dir(user, kb_id)
    kb_dir.mkdir(parents=True, exist_ok=True)
    file_path = kb_dir / (file.filename or "upload")
    file_path.write_bytes(content)

    try:
        entries_data = ingest_file(str(file_path), kb_id, file.filename or "upload")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File parsing failed: {str(e)}")

    for entry_data in entries_data:
        db.add(KnowledgeEntry(**entry_data))

    kb.entry_count = (kb.entry_count or 0) + len(entries_data)
    await db.commit()

    return {
        "kb_id": kb_id,
        "filename": file.filename,
        "chunks_created": len(entries_data),
    }


@router.get("/search")
async def search_knowledge(
    q: str,
    kb_id: str | None = None,
    category: str | None = None,
    top_k: int = 5,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """向量+关键词混合检索知识库。"""
    query = select(KnowledgeEntry).join(KnowledgeBase).where(
        KnowledgeBase.user_id == user
    )
    if kb_id:
        query = query.where(KnowledgeEntry.kb_id == kb_id)
    if category:
        query = query.where(KnowledgeBase.category == category)

    result = await db.execute(query)
    all_entries = list(result.scalars().all())
    if not all_entries:
        return {"query": q, "results": []}

    try:
        query_emb = compute_embedding(q)
        scored: list[tuple[float, KnowledgeEntry]] = []
        for entry in all_entries:
            if entry.embedding:
                score = cosine_similarity(query_emb, entry.embedding)
            else:
                score = 0.1 if q.lower() in entry.content.lower() else 0.0
            scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = [
            {
                "id": entry.id,
                "kb_id": entry.kb_id,
                "title": entry.title,
                "content": entry.content[:500],
                "source_name": entry.source_name,
                "score": round(score, 3),
                "metadata": entry.metadata_,
            }
            for score, entry in scored[:top_k]
            if score > 0.2
        ]
        return {"query": q, "results": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/bases/{kb_id}/entries")
async def list_entries(
    kb_id: str,
    offset: int = 0,
    limit: int = 50,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """列出知识库中的条目。"""
    result = await db.execute(
        select(KnowledgeEntry)
        .where(KnowledgeEntry.kb_id == kb_id)
        .order_by(KnowledgeEntry.chunk_index)
        .offset(offset).limit(limit)
    )
    entries = result.scalars().all()
    return [
        {
            "id": e.id,
            "title": e.title,
            "content_preview": e.content[:200],
            "source_name": e.source_name,
            "chunk_index": e.chunk_index,
            "created_at": e.created_at.isoformat(),
        }
        for e in entries
    ]


@router.delete("/entries/{entry_id}")
async def delete_entry(
    entry_id: str,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除单条知识条目。"""
    result = await db.execute(
        select(KnowledgeEntry).join(KnowledgeBase).where(
            KnowledgeEntry.id == entry_id,
            KnowledgeBase.user_id == user,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    await db.delete(entry)
    await db.commit()
    return {"deleted": entry_id}
