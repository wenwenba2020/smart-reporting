"""Data source upload and management API."""
import json
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.config import settings
from backend.core.datasource.base import registry
from backend.core.datasource import file_upload  # noqa: F401  trigger @register_adapter
from backend.core.datasource import chat_export  # noqa: F401  trigger @register_adapter
from backend.core.datasource import enterprise_ppt  # noqa: F401  trigger @register_adapter
from backend.core.datasource import api_source  # noqa: F401  trigger @register_adapter
from backend.core.datasource import mcp_source  # noqa: F401  trigger @register_adapter
from backend.core.datasource import database_source  # noqa: F401  trigger @register_adapter
from backend.core.datasource import rag_source  # noqa: F401  trigger @register_adapter
from backend.core.models import SourceDocument, RestApiSourceConfig, McpSourceConfig, DatabaseSourceConfig

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
        "code": 200,
        "msg": "ok",
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


@router.get("/source-types")
async def list_source_types():
    """List all registered data source types."""
    return {"data": registry.list_types()}


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


@router.post("/fetch")
async def fetch_from_source(req: dict):
    """Fetch data from a non-file data source (REST API or MCP)."""
    source_type = req.get("source_type", "")
    if not source_type:
        raise HTTPException(400, "source_type is required")

    adapter = registry.get(source_type)
    if adapter is None:
        raise HTTPException(400, f"Unknown source type: {source_type}")

    raw_config = req.get("config", {})
    if source_type == "rest_api":
        config = RestApiSourceConfig(
            url=raw_config.get("url", ""),
            method=raw_config.get("method", "GET"),
            headers=raw_config.get("headers", {}),
            auth_type=raw_config.get("auth_type", "none"),
            auth_token=raw_config.get("auth_token", ""),
            auth_username=raw_config.get("auth_username", ""),
            auth_password=raw_config.get("auth_password", ""),
            jsonpath_expr=raw_config.get("jsonpath_expr", "$"),
            title_field=raw_config.get("title_field", ""),
        )
    elif source_type == "mcp":
        config = McpSourceConfig(
            robot_id=raw_config.get("robot_id", 0),
            user_id=raw_config.get("user_id", ""),
            tool_prompt=raw_config.get("tool_prompt", ""),
            session_id=raw_config.get("session_id", ""),
        )
    elif source_type == "database":
        config = DatabaseSourceConfig(
            connection_string=raw_config.get("connection_string", ""),
            query=raw_config.get("query", ""),
            db_type=raw_config.get("db_type", "sqlite"),
        )
    else:
        raise HTTPException(400, f"Fetch not supported for source type: {source_type}")

    if not hasattr(adapter, "fetch"):
        raise HTTPException(400, f"Adapter {source_type} does not support fetch()")

    try:
        doc = await adapter.fetch(config)
    except Exception as e:
        raise HTTPException(500, f"Fetch error: {e}")

    _source_store[doc.id] = doc
    preview = doc.content[:500] if doc.content else ""
    return {
        "source_id": doc.id,
        "title": doc.title,
        "source_type": doc.source_type,
        "preview": preview,
        "metadata": doc.metadata,
    }


@router.post("/rag/ingest")
async def rag_ingest(req: dict):
    """Ingest existing source documents into the RAG knowledge base.

    Request: {"source_ids": ["src_001", "src_002"]}
    """
    source_ids = req.get("source_ids", [])
    if not source_ids:
        raise HTTPException(400, "source_ids is required")

    from backend.core.datasource.rag_source import rag_kb
    result = await rag_kb.ingest(source_ids, _source_store)
    return {"data": result}


@router.post("/rag/search")
async def rag_search(req: dict):
    """Semantic search the RAG knowledge base.

    Request: {"query": "华南区Q3销售情况", "top_k": 5}
    Returns a SourceDocument with concatenated relevant chunks.
    """
    query = req.get("query", "")
    if not query:
        raise HTTPException(400, "query is required")

    top_k = req.get("top_k", 5)
    from backend.core.datasource.rag_source import rag_kb
    doc = await rag_kb.search(query, top_k, _source_store)
    _source_store[doc.id] = doc
    return {
        "source_id": doc.id,
        "title": doc.title,
        "source_type": doc.source_type,
        "preview": doc.content[:500],
        "metadata": doc.metadata,
    }
