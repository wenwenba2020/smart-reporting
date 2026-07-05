"""智能填报 API"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from backend.api.auth import get_current_user
from backend.report_engine.smart_fill import run_smart_fill

router = APIRouter(prefix="/smart-fill", tags=["smart_fill"])


class SmartFillRequest(BaseModel):
    query: str
    scenario_type: str | None = None
    selected_sources: list[str] | None = None
    report_type: str = "ppt"


@router.post("")
async def smart_fill(
    body: SmartFillRequest,
    user: str = Depends(get_current_user),
):
    result = await run_smart_fill(
        query=body.query,
        scenario_type=body.scenario_type,
        selected_sources=body.selected_sources,
        user_id=user,
        report_type=body.report_type,
    )

    if not result.structured_markdown:
        raise HTTPException(400, "未能从数据源中检索到相关内容")

    return {
        "structured_markdown": result.structured_markdown,
        "report_json": result.report_json,
        "source_references": result.source_references,
    }
