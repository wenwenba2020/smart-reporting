"""PPT 方案库数据模型 · 场景化叙事框架"""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import String, Integer, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex


class ScenarioTemplate(Base):
    """场景方案模板 — 定义某类场景的 PPT 叙事框架"""
    __tablename__ = "scenario_templates"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_id)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)  # 如"设备售前方案"
    scenario_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    # scenario_type: presales / investor / review / report / channel
    description: Mapped[str] = mapped_column(String, nullable=False)
    icon: Mapped[str | None] = mapped_column(String, nullable=True)  # emoji 或 icon 标识

    # 核心叙事结构（JSON）
    # [{"role": "痛点分析", "layout": "title-content", "prompt_hint": "描述客户当前面临的业务挑战..."}]
    slide_framework: Mapped[Any] = mapped_column(JSON, default=list)

    # 数据源提示规则 (给 AI 的指引文本)
    # "从知识库[product]分类提取设备参数，从[meeting]分类提取客户需求..."
    data_source_hints: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 话术模板（开场白、过渡句、结尾语等）
    talk_track_templates: Mapped[Any] = mapped_column(JSON, nullable=True)

    is_preset: Mapped[bool] = mapped_column(default=False)  # 是否为系统预设
    is_active: Mapped[bool] = mapped_column(default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


PRESET_SCENARIOS: list[dict] = [
    {
        "scenario_type": "presales",
        "name": "产品售前方案",
        "description": "面向客户的产品/方案宣讲，核心逻辑：痛点→方案→案例→价值",
        "icon": "🎯",
        "slide_framework": [
            {"seq": 1, "role": "封面", "layout": "cover", "prompt_hint": "标题：[产品名称]售前方案，副标题：公司名称·部门"},
            {"seq": 2, "role": "目录", "layout": "toc", "prompt_hint": "四大板块：行业洞察、解决方案、客户案例、合作价值"},
            {"seq": 3, "role": "行业痛点", "layout": "title-content", "prompt_hint": "描述客户行业当前面临的 3-5 个核心业务挑战，每点用数据支撑"},
            {"seq": 4, "role": "解决方案概述", "layout": "title-content", "prompt_hint": "我们的产品/方案如何系统性解决上述痛点，突出技术优势和差异化"},
            {"seq": 5, "role": "产品核心能力", "layout": "three-col", "prompt_hint": "3 个核心功能/模块，每栏配图标+简要说明+关键参数"},
            {"seq": 6, "role": "技术架构", "layout": "data-chart", "prompt_hint": "系统架构图或技术栈示意（用文字描述代替图表，由设计师渲染）"},
            {"seq": 7, "role": "客户案例 1", "layout": "two-col", "prompt_hint": "客户名称、背景、实施效果，左栏文字右栏数据指标"},
            {"seq": 8, "role": "客户案例 2", "layout": "two-col", "prompt_hint": "同上结构，展示不同行业的案例形成对比"},
            {"seq": 9, "role": "实施计划", "layout": "timeline", "prompt_hint": "4-6 个阶段的项目实施时间线，每阶段标注交付物"},
            {"seq": 10, "role": "合作价值与下一步", "layout": "title-content", "prompt_hint": "总结合作收益，明确下一步行动（POC/商务洽谈/合同签署）"},
        ],
        "data_source_hints": (
            "1. 从知识库[product]分类提取产品参数、功能介绍、技术指标\n"
            "2. 从知识库[customer]分类提取目标客户的行业背景、业务需求\n"
            "3. 从案例库匹配同行业/同类型售前案例，复用内容框架\n"
            "4. 从知识库[meeting]分类提取相关客户会议纪要中的关注点"
        ),
        "talk_track_templates": {
            "opening": "各位领导好，我是[公司]的[角色]，今天向各位汇报[产品]针对贵司业务场景的解决方案。",
            "transition": "接下来我们看一个和贵司情况非常相似的客户案例——",
            "closing": "总结一下，我们的方案能为贵司带来[价值1]、[价值2]和[价值3]。期待与贵司进一步深入交流。"
        },
        "sort_order": 1,
    },
    {
        "scenario_type": "investor",
        "name": "投资人推介",
        "description": "面向投资机构的融资路演，核心逻辑：市场→产品→模式→团队→财务",
        "icon": "💰",
        "slide_framework": [
            {"seq": 1, "role": "封面", "layout": "cover", "prompt_hint": "公司名称+Slogan，简洁有力"},
            {"seq": 2, "role": "市场机会", "layout": "data-chart", "prompt_hint": "市场规模、增速、趋势数据，视觉冲击力强"},
            {"seq": 3, "role": "核心产品", "layout": "title-content", "prompt_hint": "产品定位、差异化优势、技术壁垒"},
            {"seq": 4, "role": "商业模式", "layout": "data-chart", "prompt_hint": "收入模型、客单价、复购率、单位经济模型"},
            {"seq": 5, "role": "竞争格局", "layout": "comparison", "prompt_hint": "与竞品的对比矩阵，突出我们的领先维度"},
            {"seq": 6, "role": "团队介绍", "layout": "team", "prompt_hint": "核心团队背景、行业经验、过往成就"},
            {"seq": 7, "role": "财务预测", "layout": "data-chart", "prompt_hint": "未来 3 年收入/利润预测，关键假设说明"},
            {"seq": 8, "role": "融资需求与用途", "layout": "title-content", "prompt_hint": "本轮融资金额、估值、资金用途分配"},
        ],
        "data_source_hints": (
            "1. 从知识库提取公司核心产品数据和市场数据\n"
            "2. 从知识库[meeting]提取过往投资人交流中的反馈\n"
            "3. 尽量使用最新财务数据和市场报告"
        ),
        "talk_track_templates": {
            "opening": "感谢各位投资人的时间。我是[公司]的[角色]，今天用 20 分钟向各位展示我们的增长故事。",
            "closing": "我们正处于[行业]爆发的前夜，团队、产品、市场三重就绪。期待与各位携手。"
        },
        "sort_order": 2,
    },
    {
        "scenario_type": "review",
        "name": "项目复盘",
        "description": "项目结项复盘汇报，核心逻辑：目标→成果→问题→经验→下一步",
        "icon": "📊",
        "slide_framework": [
            {"seq": 1, "role": "封面", "layout": "cover", "prompt_hint": "项目名称+复盘日期"},
            {"seq": 2, "role": "项目概述", "layout": "title-content", "prompt_hint": "项目目标、范围、时间线、关键干系人"},
            {"seq": 3, "role": "成果总览", "layout": "data-chart", "prompt_hint": "核心 KPI 达成情况，用仪表盘/进度条展示"},
            {"seq": 4, "role": "亮点与成功经验", "layout": "title-content", "prompt_hint": "3-5 个关键成功因素，每点附具体案例"},
            {"seq": 5, "role": "问题与根因分析", "layout": "title-content", "prompt_hint": "遇到的主要问题、影响程度、根本原因"},
            {"seq": 6, "role": "经验教训", "layout": "two-col", "prompt_hint": "左栏：做对了什么（继续坚持）；右栏：哪里可以改进（行动项）"},
            {"seq": 7, "role": "后续规划", "layout": "timeline", "prompt_hint": "遗留事项和后续迭代计划"},
        ],
        "data_source_hints": (
            "1. 从知识库[meeting]提取项目周会纪要中的关键决策和问题\n"
            "2. 从历史案例中匹配同类项目复盘，复用分析框架"
        ),
        "talk_track_templates": {
            "opening": "大家好，今天我们对[项目名称]进行系统性复盘，总结经验、沉淀方法。",
            "closing": "复盘不是追责，是让我们下次做得更好。以上经验将更新到团队知识库中。"
        },
        "sort_order": 3,
    },
    {
        "scenario_type": "report",
        "name": "工作汇报",
        "description": "周期性工作汇报，核心逻辑：成果→问题→规划→资源需求",
        "icon": "📝",
        "slide_framework": [
            {"seq": 1, "role": "封面", "layout": "cover", "prompt_hint": "汇报周期+部门/团队名称"},
            {"seq": 2, "role": "核心成果概览", "layout": "data-chart", "prompt_hint": "3-5 个核心指标或成果的数字卡片"},
            {"seq": 3, "role": "重点工作详述", "layout": "title-content", "prompt_hint": "按优先级排列的重点工作，每项含背景、进展、成果"},
            {"seq": 4, "role": "问题与风险", "layout": "title-content", "prompt_hint": "当前面临的挑战、风险等级、建议应对方案"},
            {"seq": 5, "role": "下阶段规划", "layout": "timeline", "prompt_hint": "下个周期的重点工作计划和时间节点"},
            {"seq": 6, "role": "资源需求", "layout": "title-content", "prompt_hint": "需要支持的人力、预算或其他资源"},
        ],
        "data_source_hints": (
            "1. 从知识库[meeting]提取历史周会纪要和待办事项\n"
            "2. 从知识库提取相关项目的最新进展数据"
        ),
        "talk_track_templates": {
            "opening": "各位好，下面汇报[部门/团队][周期]的工作进展和下阶段规划。",
            "closing": "以上是本周期的工作汇报，请各位提出宝贵意见。"
        },
        "sort_order": 4,
    },
    {
        "scenario_type": "channel",
        "name": "渠道合作方案",
        "description": "面向渠道合作伙伴的合作推介，核心逻辑：市场→产品→政策→支持→收益",
        "icon": "🤝",
        "slide_framework": [
            {"seq": 1, "role": "封面", "layout": "cover", "prompt_hint": "合作主题+双方品牌"},
            {"seq": 2, "role": "市场机会", "layout": "data-chart", "prompt_hint": "合作领域的市场规模和增长趋势"},
            {"seq": 3, "role": "产品/方案介绍", "layout": "title-content", "prompt_hint": "合作产品的核心卖点和差异化优势"},
            {"seq": 4, "role": "合作政策", "layout": "comparison", "prompt_hint": "不同合作等级的政策对比（折扣/返点/账期等）"},
            {"seq": 5, "role": "支持体系", "layout": "three-col", "prompt_hint": "技术支持/培训支持/市场支持三大板块"},
            {"seq": 6, "role": "收益测算", "layout": "data-chart", "prompt_hint": "合作伙伴预期收益模型和 ROI 分析"},
            {"seq": 7, "role": "成功案例", "layout": "two-col", "prompt_hint": "现有合作伙伴的合作成果和数据"},
            {"seq": 8, "role": "下一步行动", "layout": "title-content", "prompt_hint": "签约流程、培训安排、启动时间表"},
        ],
        "data_source_hints": (
            "1. 从知识库[product]提取产品价格体系和渠道政策\n"
            "2. 从案例库匹配渠道合作成功案例"
        ),
        "talk_track_templates": {
            "opening": "很高兴有机会与贵司探讨合作可能。下面我详细介绍一下我们的合作方案。",
            "closing": "我们相信这次合作能为双方带来显著增长。期待尽快推动落地。"
        },
        "sort_order": 5,
    },
]


async def seed_preset_scenarios(db, user_id: str = "admin"):
    """初始化预设场景方案（幂等，已存在则跳过）"""
    from sqlalchemy import select

    for preset in PRESET_SCENARIOS:
        result = await db.execute(
            select(ScenarioTemplate).where(
                ScenarioTemplate.user_id == user_id,
                ScenarioTemplate.scenario_type == preset["scenario_type"],
                ScenarioTemplate.is_preset == True,
            )
        )
        if result.scalar_one_or_none() is None:
            db.add(ScenarioTemplate(
                user_id=user_id,
                name=preset["name"],
                scenario_type=preset["scenario_type"],
                description=preset["description"],
                icon=preset["icon"],
                slide_framework=preset["slide_framework"],
                data_source_hints=preset["data_source_hints"],
                talk_track_templates=preset["talk_track_templates"],
                is_preset=True,
                sort_order=preset["sort_order"],
            ))
    await db.commit()
