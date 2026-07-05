"""数据源管理 API"""
from fastapi import APIRouter, Depends
from backend.api.auth import get_current_user
from backend.data_source.base import registry
from backend.data_source import register_builtin_sources

router = APIRouter(prefix="/data-sources", tags=["data_sources"])

register_builtin_sources()


@router.get("")
async def list_data_sources():
    return registry.list_configs()


@router.get("/{source_type}/schema")
async def get_source_schema(
    source_type: str,
    user: str = Depends(get_current_user),
):
    plugin = registry.get(source_type)
    if not plugin:
        return {"error": f"Unknown source type: {source_type}"}
    schema = await plugin.get_schema(user_id=user)
    return {
        "source_type": schema.source_type, "source_name": schema.source_name,
        "categories": schema.categories, "fields": schema.fields,
        "total_documents": schema.total_documents,
    }
