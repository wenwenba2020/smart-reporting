"""PPT 方案库 API 端点"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_current_user
from backend.models.database import get_db
from backend.models.scenario import ScenarioTemplate, seed_preset_scenarios

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


class ScenarioUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    slide_framework: list[dict] | None = None
    data_source_hints: str | None = None
    talk_track_templates: dict | None = None
    is_active: bool | None = None


@router.get("")
async def list_scenarios(
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """列出所有可用的场景方案。"""
    result = await db.execute(
        select(ScenarioTemplate)
        .where(
            ScenarioTemplate.user_id == user,
            ScenarioTemplate.is_active == True,
        )
        .order_by(ScenarioTemplate.sort_order)
    )
    scenarios = result.scalars().all()

    if not scenarios:
        await seed_preset_scenarios(db, user)
        result = await db.execute(
            select(ScenarioTemplate)
            .where(ScenarioTemplate.user_id == user, ScenarioTemplate.is_active == True)
            .order_by(ScenarioTemplate.sort_order)
        )
        scenarios = result.scalars().all()

    return [
        {
            "id": s.id,
            "name": s.name,
            "scenario_type": s.scenario_type,
            "description": s.description,
            "icon": s.icon,
            "slide_count": len(s.slide_framework) if s.slide_framework else 0,
            "is_preset": s.is_preset,
            "sort_order": s.sort_order,
        }
        for s in scenarios
    ]


@router.get("/{scenario_id}")
async def get_scenario(
    scenario_id: str,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取单个场景方案的完整详情（含框架结构）。"""
    result = await db.execute(
        select(ScenarioTemplate).where(
            ScenarioTemplate.id == scenario_id,
            ScenarioTemplate.user_id == user,
        )
    )
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Scenario not found")

    return {
        "id": s.id,
        "name": s.name,
        "scenario_type": s.scenario_type,
        "description": s.description,
        "icon": s.icon,
        "slide_framework": s.slide_framework,
        "data_source_hints": s.data_source_hints,
        "talk_track_templates": s.talk_track_templates,
        "is_preset": s.is_preset,
        "is_active": s.is_active,
    }


@router.put("/{scenario_id}")
async def update_scenario(
    scenario_id: str,
    body: ScenarioUpdate,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新方案库内容。"""
    result = await db.execute(
        select(ScenarioTemplate).where(
            ScenarioTemplate.id == scenario_id,
            ScenarioTemplate.user_id == user,
        )
    )
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Scenario not found")

    if body.name is not None:
        s.name = body.name
    if body.description is not None:
        s.description = body.description
    if body.slide_framework is not None:
        s.slide_framework = body.slide_framework
    if body.data_source_hints is not None:
        s.data_source_hints = body.data_source_hints
    if body.talk_track_templates is not None:
        s.talk_track_templates = body.talk_track_templates
    if body.is_active is not None:
        s.is_active = body.is_active

    await db.commit()
    return {"id": s.id, "name": s.name, "updated": True}


@router.get("/types/list")
async def list_scenario_types():
    """返回所有场景类型枚举。"""
    return {
        "types": [
            {"key": "presales", "label": "产品售前方案", "icon": "🎯"},
            {"key": "investor", "label": "投资人推介", "icon": "💰"},
            {"key": "review", "label": "项目复盘", "icon": "📊"},
            {"key": "report", "label": "工作汇报", "icon": "📝"},
            {"key": "channel", "label": "渠道合作方案", "icon": "🤝"},
        ]
    }
