"""Data source upload and management API."""
import json
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.config import settings
from backend.core.datasource.base import registry
from backend.core.datasource import file_upload  # noqa: F401  trigger @register_adapter
from backend.core.datasource import enterprise_ppt  # noqa: F401  trigger @register_adapter
from backend.core.models import SourceDocument

router = APIRouter(prefix="/datasources", tags=["datasources"])

_source_store: dict[str, SourceDocument] = {}

UPLOAD_DIR = Path(settings.local_storage_path)


@router.post("/upload")
async def upload_source(
    file: UploadFile = File(...),
    metadata: str = Form(default="{}"),
):
    """Upload a file, auto-detect its type, parse to SourceDocument, and store it."""
    if not file.filename:
        raise HTTPException(400, "Filename is required")

    # Parse optional metadata JSON
    try:
        meta_dict = json.loads(metadata)
    except json.JSONDecodeError:
        raise HTTPException(400, "metadata must be valid JSON")

    # Save file to disk
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_path = UPLOAD_DIR / f"{uuid.uuid4().hex}_{file.filename}"
    content = await file.read()
    file_path.write_bytes(content)

    # Find a matching adapter
    adapter = registry.find_by_filename(file.filename)
    if adapter is None:
        file_path.unlink(missing_ok=True)
        raise HTTPException(400, f"No adapter found for file type: {file.filename}")

    # Parse
    try:
        doc = await adapter.parse(str(file_path), file.filename, metadata=meta_dict)
    except Exception as e:
        file_path.unlink(missing_ok=True)
        raise HTTPException(500, f"Parse error: {e}")

    # Store
    _source_store[doc.id] = doc

    preview = doc.content[:500] if doc.content else ""
    return {
        "source_id": doc.id,
        "title": doc.title,
        "source_type": doc.source_type,
        "preview": preview,
        "metadata": doc.metadata,
    }


@router.get("")
async def list_sources():
    """List all uploaded sources (summary only)."""
    return {
        "data": [
            {
                "id": doc.id,
                "title": doc.title,
                "source_type": doc.source_type,
                "metadata": doc.metadata,
            }
            for doc in _source_store.values()
        ]
    }


@router.get("/{source_id}")
async def get_source(source_id: str):
    """Get full source document by ID."""
    doc = _source_store.get(source_id)
    if doc is None:
        raise HTTPException(404, f"Source not found: {source_id}")
    return {
        "id": doc.id,
        "title": doc.title,
        "content": doc.content,
        "source_type": doc.source_type,
        "metadata": doc.metadata,
        "relevance_score": doc.relevance_score,
    }


@router.delete("/{source_id}")
async def delete_source(source_id: str):
    """Remove a source from the store."""
    if source_id not in _source_store:
        raise HTTPException(404, f"Source not found: {source_id}")
    del _source_store[source_id]
    return {"deleted": source_id}
