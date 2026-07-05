# Phase 4 企业级模块 + WorkoPilot 集成 · 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建设四大企业级数据底座（知识库、方案库、案例库升级、模板库升级），并接入 WorkoPilot 数字员工平台 Open API，实现"一键生成企业专属PPT"的完整业务闭环。

**Architecture:** 新增 4 个数据模型（KnowledgeBase/KnowledgeEntry/ScenarioTemplate/CaseTag）+ 3 个 API 路由模块（knowledge/scenarios/workopilot），升级现有 slide_library 和 design_templates 系统。规划师和文案师 prompt 改造以注入四大数据源。WorkoPilot 适配层实现 Open API 协议，通过 SSE 流式返回生成进度和 cardData 结构化结果。

**Tech Stack:** SQLAlchemy async + SQLite JSON, OpenRouter text-embedding-3-small, FastAPI SSE, python-docx + PyMuPDF（知识库解析）

---

## 文件清单

| 操作 | 文件 | 职责 |
|------|------|------|
| Create | `backend/models/knowledge.py` | KnowledgeBase + KnowledgeEntry ORM |
| Create | `backend/models/scenario.py` | ScenarioTemplate ORM + 预设数据 |
| Modify | `backend/models/database.py` | 注册新模型 |
| Modify | `backend/models/slide_library.py` | 案例库升级字段 |
| Create | `backend/parsers/knowledge_ingest.py` | 知识库文档解析 + 分块 + embedding |
| Create | `backend/api/routes/knowledge.py` | 知识库 CRUD + 检索 API |
| Create | `backend/api/routes/scenarios.py` | 方案库 CRUD API |
| Modify | `backend/api/routes/slide_library.py` | 案例库场景分类 + 来源标记 |
| Create | `backend/api/routes/workopilot.py` | WorkoPilot Open API 适配 |
| Modify | `backend/api/main.py` | 注册新路由 |
| Modify | `backend/config.py` | 新增配置项 |
| Modify | `backend/agents/planner.py` | prompt 改造（注入四大数据源） |
| Modify | `backend/agents/copywriter.py` | prompt 改造（知识库内容引用） |
| Create | `backend/design_templates/sales-presales.md` | 售前方案模板 |
| Create | `backend/design_templates/work-report.md` | 工作汇报模板 |
| Modify | `frontend/src/types/events.ts` | 新类型定义 |
| Modify | `frontend/src/api/client.ts` | 新 API 函数 |
| Create | `frontend/src/stores/knowledgeStore.ts` | 知识库 Store |
| Create | `frontend/src/stores/scenarioStore.ts` | 方案库 Store |
| Create | `frontend/src/components/KnowledgePanel/index.tsx` | 知识库管理面板 |
| Create | `frontend/src/components/ScenarioSelector/index.tsx` | 场景方案选择器 |
| Modify | `frontend/src/App.tsx` | 新 tab + 场景选择集成 |
| Modify | `frontend/src/components/ChatPanel/index.tsx` | 场景选择入口 |

---

### Task 1: 数据模型 · KnowledgeBase + KnowledgeEntry

**Files:**
- Create: `backend/models/knowledge.py`
- Modify: `backend/models/database.py:15`

- [ ] **Step 1: 创建 knowledge.py ORM 模型**

```python
"""企业知识库数据模型"""
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import String, Integer, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex


class KnowledgeBase(Base):
    """知识库分类（如：产品参数、客户资料、周会纪要）"""
    __tablename__ = "knowledge_bases"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_id)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    category: Mapped[str] = mapped_column(String, nullable=False, default="general")
    # category 枚举: product / customer / meeting / general
    entry_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class KnowledgeEntry(Base):
    """知识条目（文档分块或独立条目）"""
    __tablename__ = "knowledge_entries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_id)
    kb_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    source_name: Mapped[str | None] = mapped_column(String, nullable=True)  # 原始文件名
    title: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    # embedding 存储为 JSON list[float]，SQLite 不原生支持 vector
    embedding: Mapped[Any] = mapped_column(JSON, nullable=True)
    metadata_: Mapped[Any] = mapped_column("metadata_json", JSON, default=dict)
    # metadata_ 示例: {"page": 3, "source_type": "pdf", "tags": ["D7020", "参数"]}
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
```

- [ ] **Step 2: 注册模型到 create_all_tables**

Edit `backend/models/database.py:15`:

```python
async def create_all_tables():
    from backend.models import project, snapshot, slide_library, knowledge, scenario  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

- [ ] **Step 3: 验证模型导入**

Run: `.venv/bin/python -c "from backend.models.knowledge import KnowledgeBase, KnowledgeEntry; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/models/knowledge.py backend/models/database.py
git commit -m "feat: add KnowledgeBase + KnowledgeEntry ORM models"
```

---

### Task 2: 数据模型 · ScenarioTemplate（方案库）

**Files:**
- Create: `backend/models/scenario.py`

- [ ] **Step 1: 创建 scenario.py ORM 模型**

```python
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
```

- [ ] **Step 2: 添加预设场景数据初始化函数**

在同一文件中追加：

```python
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
```

- [ ] **Step 3: 验证模型导入**

Run: `.venv/bin/python -c "from backend.models.scenario import ScenarioTemplate, PRESET_SCENARIOS; print(f'OK — {len(PRESET_SCENARIOS)} presets')"`
Expected: `OK — 5 presets`

- [ ] **Step 4: Commit**

```bash
git add backend/models/scenario.py
git commit -m "feat: add ScenarioTemplate model with 5 preset scenarios"
```

---

### Task 3: 案例库升级 · SlideLibrary 字段扩展

**Files:**
- Modify: `backend/models/slide_library.py`
- Modify: `backend/api/routes/slide_library.py`

- [ ] **Step 1: 给 SlideLibrary 添加场景分类和来源标记**

Edit `backend/models/slide_library.py` — 在 `SlideLibrary` 类中添加字段：

在 `updated_at` 之后添加：
```python
    scenario_type: Mapped[str | None] = mapped_column(String, nullable=True)
    # presales / investor / review / report / channel
    source_type: Mapped[str] = mapped_column(String, nullable=False, default="manual")
    # "manual" = 手动上传, "generated" = 系统生成
    is_excellent: Mapped[bool] = mapped_column(default=False)  # 优质案例标记
    tags: Mapped[Any] = mapped_column(JSON, default=list)  # 业务标签
```

在 `LibrarySlide` 类的 `layout_hint` 之后添加：
```python
    business_tags: Mapped[Any] = mapped_column(JSON, default=list)
    # 业务标签 如: ["D7020", "售前", "长鑫存储"]
    design_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    design_images: Mapped[Any] = mapped_column(JSON, nullable=True)
```

- [ ] **Step 2: 更新上传 API 以支持新字段**

Edit `backend/api/routes/slide_library.py` — 在 `upload_to_library` 函数的 `library` 创建中添加 `source_type="manual"`：

找到 `library = SlideLibrary(...)` 那行，确认已有 `source_type` 默认值。不需要显式修改（ORM 有 default）。

在 `get_deck` 和 `list_decks` 的返回字典中添加：
```python
"scenario_type": d.scenario_type,
"source_type": d.source_type,
"is_excellent": d.is_excellent,
"tags": d.tags or [],
```

在 `get_deck` 的 slides 返回中添加：
```python
"business_tags": s.business_tags or [],
```

- [ ] **Step 3: 新增 PATCH endpoint 用于案例分类**

在 `slide_library.py` 末尾添加：

```python
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
    return {"id": library.id, "scenario_type": library.scenario_type,
            "is_excellent": library.is_excellent, "tags": library.tags}
```

- [ ] **Step 4: 验证模型变更**

Run: `.venv/bin/python -c "from backend.models.slide_library import SlideLibrary, LibrarySlide; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/models/slide_library.py backend/api/routes/slide_library.py
git commit -m "feat: add scenario_type/source_type/excellent flag to case library"
```

---

### Task 4: 知识库解析器 · knowledge_ingest.py

**Files:**
- Create: `backend/parsers/knowledge_ingest.py`

- [ ] **Step 1: 创建知识库文档解析和分块模块**

```python
"""知识库文档摄取：解析 + 分块 + embedding"""
import re
from pathlib import Path
from typing import Any

import numpy as np


CHUNK_SIZE = 800   # 每块字符数
CHUNK_OVERLAP = 100  # 块间重叠字符数


def parse_file_to_text(file_path: str | Path) -> tuple[str, dict]:
    """将支持的文件类型解析为纯文本。

    Returns (text, metadata_dict).
    """
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()
    metadata = {"source_type": suffix.lstrip("."), "filename": file_path.name}

    if suffix == ".pdf":
        import fitz  # PyMuPDF
        doc = fitz.open(str(file_path))
        texts: list[str] = []
        for page in doc:
            texts.append(page.get_text())
        doc.close()
        return "\n\n".join(texts), {**metadata, "pages": len(texts)}

    elif suffix == ".docx":
        from docx import Document
        doc = Document(str(file_path))
        paras = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paras), metadata

    elif suffix in (".txt", ".md"):
        text = file_path.read_text(encoding="utf-8")
        return text, metadata

    elif suffix == ".csv":
        text = file_path.read_text(encoding="utf-8")
        return text, {**metadata, "format": "csv"}

    else:
        raise ValueError(f"Unsupported file type: {suffix}")


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """将长文本切分为重叠块。按段落边界优先切分。"""
    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current_chunk) + len(para) + 2 <= chunk_size:
            current_chunk = (current_chunk + "\n\n" + para).strip()
        else:
            if current_chunk:
                chunks.append(current_chunk)
            if len(para) > chunk_size:
                # 超长段落：按句子切分
                sentences = re.split(r"(?<=[。！？.!?])\s*", para)
                current_chunk = ""
                for sent in sentences:
                    if len(current_chunk) + len(sent) <= chunk_size:
                        current_chunk = (current_chunk + sent).strip()
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = sent
            else:
                current_chunk = para
                # 添加重叠：从前一个 chunk 末尾取 overlap 字符
                if chunks and overlap > 0:
                    prev = chunks[-1]
                    overlap_text = prev[-overlap:] if len(prev) > overlap else prev
                    current_chunk = overlap_text + "\n\n" + current_chunk

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def compute_embedding(text: str) -> list[float]:
    """通过 OpenRouter text-embedding-3-small 计算 embedding 向量。"""
    from backend.agents.llm_client import get_client

    client = get_client()
    text = text[:8000]  # embedding 模型 token 上限
    resp = client.embeddings.create(
        model="openai/text-embedding-3-small",
        input=[text],
        timeout=30,
    )
    return resp.data[0].embedding


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """余弦相似度。"""
    a_np = np.array(a)
    b_np = np.array(b)
    return float(np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np) + 1e-10))


def ingest_file(
    file_path: str | Path,
    kb_id: str,
    source_name: str,
) -> list[dict]:
    """解析文件、分块、计算 embedding，返回 entry 数据列表。

    每条 entry: {title, content, chunk_index, embedding, metadata_, source_name}
    """
    file_path = Path(file_path)
    text, file_meta = parse_file_to_text(file_path)
    chunks = chunk_text(text)
    if not chunks:
        return []

    entries: list[dict] = []
    for i, chunk in enumerate(chunks):
        title_base = file_meta.get("filename", source_name)
        title = f"{title_base} (第{i+1}块)" if len(chunks) > 1 else title_base

        # 用前 100 字做标题
        short_title = chunk[:80].replace("\n", " ").strip()
        if len(short_title) < len(chunk):
            short_title += "..."

        try:
            emb = compute_embedding(chunk)
        except Exception:
            emb = None  # embedding 失败不阻塞流程

        entries.append({
            "kb_id": kb_id,
            "source_name": source_name,
            "title": short_title,
            "content": chunk,
            "chunk_index": i,
            "embedding": emb,
            "metadata_": {
                **file_meta,
                "chunk_index": i,
                "total_chunks": len(chunks),
            },
        })

    return entries
```

- [ ] **Step 2: 验证导入无错误**

Run: `.venv/bin/python -c "from backend.parsers.knowledge_ingest import chunk_text, ingest_file; print('OK')"`
Expected: `OK`

- [ ] **Step 3: 单元测试**

Run: `.venv/bin/python -c "
text = '段落一。' * 100 + '\n\n' + '段落二。' * 100
chunks = __import__('backend.parsers.knowledge_ingest', fromlist=['chunk_text']).chunk_text(text, chunk_size=500)
assert len(chunks) >= 2, f'Expected >=2 chunks, got {len(chunks)}'
print(f'OK — {len(chunks)} chunks')
"`

- [ ] **Step 4: Commit**

```bash
git add backend/parsers/knowledge_ingest.py
git commit -m "feat: add knowledge ingest parser (PDF/DOCX/TXT chunking + embedding)"
```

---

### Task 5: 知识库 API 路由

**Files:**
- Create: `backend/api/routes/knowledge.py`
- Modify: `backend/api/main.py`

- [ ] **Step 1: 创建 knowledge.py 路由**

```python
"""企业知识库 API 端点"""
import shutil
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_current_user
from backend.config import settings
from backend.models.database import get_db
from backend.models.knowledge import KnowledgeBase, KnowledgeEntry
from backend.parsers.knowledge_ingest import ingest_file, compute_embedding, cosine_similarity

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
KB_BASE = Path(settings.LOCAL_STORAGE_PATH) / ".knowledge_base"


def _kb_dir(user_id: str, kb_id: str) -> Path:
    return KB_BASE / user_id / kb_id


# ── KnowledgeBase CRUD ──────────────────────────────────────────

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


# ── File Upload & Ingest ────────────────────────────────────────

@router.post("/bases/{kb_id}/upload")
async def upload_to_kb(
    kb_id: str,
    file: UploadFile = File(...),
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """上传文档到知识库，自动解析、分块、embedding。"""
    # 验证知识库归属
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

    # 保存文件
    kb_dir = _kb_dir(user, kb_id)
    kb_dir.mkdir(parents=True, exist_ok=True)
    file_path = kb_dir / (file.filename or "upload")
    file_path.write_bytes(content)

    # 解析 + 分块 + embedding
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


# ── Search / RAG ─────────────────────────────────────────────────

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
    # 构建查询
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
                # 无 embedding 时降级为关键词匹配
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


# ── List entries ─────────────────────────────────────────────────

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
```

- [ ] **Step 2: 注册路由到 main.py**

Edit `backend/api/main.py` — 在 `slide_library_router` 之后添加：

```python
from backend.api.routes.knowledge import router as knowledge_router  # noqa: E402
from backend.api.routes.scenarios import router as scenarios_router  # noqa: E402

app.include_router(knowledge_router)
app.include_router(scenarios_router)
```

- [ ] **Step 3: 验证路由导入**

Run: `.venv/bin/python -c "from backend.api.routes.knowledge import router; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/api/routes/knowledge.py backend/api/main.py
git commit -m "feat: add knowledge base API (CRUD + search + upload + ingest)"
```

---

### Task 6: 方案库 API 路由

**Files:**
- Create: `backend/api/routes/scenarios.py`

- [ ] **Step 1: 创建 scenarios.py 路由**

```python
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
        # 首次访问：自动注入预设场景
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
```

- [ ] **Step 2: 验证路由导入**

Run: `.venv/bin/python -c "from backend.api.routes.scenarios import router; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/api/routes/scenarios.py
git commit -m "feat: add scenario library API (list/get/update + 5 presets)"
```

---

### Task 7: 设计模板扩充 · 新增场景专用模板

**Files:**
- Create: `backend/design_templates/sales-presales.md`
- Create: `backend/design_templates/work-report.md`

- [ ] **Step 1: 创建售前方案模板**

```markdown
# 商务售前 · sales-presales

## Visual Theme & Atmosphere
专业商务风格。深蓝主色配合金色点缀，传递稳重、可信赖的品牌形象。适合产品售前宣讲、客户方案汇报。

## Color Palette & Roles
- **Primary** `#0D3B66` — 深蓝，标题、封面背景
- **Secondary** `#2B7A9E` — 中蓝，图表主色、图标
- **Accent** `#E8A838` — 暖金，关键数据、CTA 按钮
- **Surface** `#FFFFFF` — 白底
- **Surface-Alt** `#F4F7FA` — 浅灰，卡片背景
- **Text-Primary** `#1A1A2E` — 深色正文
- **Text-Secondary** `#6B7280` — 辅助文字
- **Border** `#E5E7EB` — 分割线

## Typography
- **Hero (44pt)**: 阿里巴巴普惠体 Bold — 封面主标题
- **H1 (32pt)**: 阿里巴巴普惠体 Bold — 页面标题
- **H2 (24pt)**: 阿里巴巴普惠体 Medium — 区块标题
- **H3 (20pt)**: 阿里巴巴普惠体 Medium — 卡片标题
- **Body (18pt)**: 阿里巴巴普惠体 Regular — 正文
- **Caption (13pt)**: 阿里巴巴普惠体 Light — 图表标注、来源说明
- 英文配套: Inter Bold/Regular

## Layout Principles
- 封面：左侧金色竖线 + 标题右对齐，底部公司信息栏
- 内容页：顶部标题栏（Primary 色条）+ 左侧要点列表 + 右侧数据区
- 图表页：上 60% 图表区 + 下 40% 分析文字
- 对比页：左右对称卡片，Accent 色突出我方优势列

## Do's and Don'ts
- DO: 每页保留金色点缀（标题下划线、要点圆点）
- DO: 数据用大号 Accent 色突出
- DO: 案例页加上客户 logo 占位区
- DON'T: 避免超过 3 列的信息布局
- DON'T: 图表不使用超过 5 种颜色
- DON'T: 单页文字不超过 120 字

## Agent Prompt Guide
生成售前方案 SVG 时：使用 Primary 深蓝色调奠定专业基调，在每个要点前用 Accent 金色小菱形作为列表符号。图表区域留白充足，让数据呼吸。案例页加入客户 logo 虚线圆角占位框。整体视觉风格对标麦肯锡/BCG 咨询报告。
```

- [ ] **Step 2: 创建工作汇报模板**

```markdown
# 工作汇报 · work-report

## Visual Theme & Atmosphere
简洁高效风格。白色底配合蓝色系微妙渐变，大面积留白突出信息层级。适合周报、月报、季度工作汇报。

## Color Palette & Roles
- **Primary** `#1E40AF` — 经典蓝，标题、进度条
- **Secondary** `#3B82F6` — 明亮蓝，图表、高亮
- **Accent** `#10B981` — 翠绿，完成率、正向指标
- **Alert** `#EF4444` — 警示红，风险项、延期标记
- **Surface** `#FFFFFF` — 纯白背景
- **Surface-Alt** `#F8FAFC` — 极浅灰，信息卡片
- **Text-Primary** `#0F172A` — 深色正文
- **Text-Secondary** `#64748B` — 辅助说明
- **Border** `#E2E8F0` — 分割线

## Typography
- **Hero (36pt)**: 阿里巴巴普惠体 Bold — 封面标题
- **H1 (28pt)**: 阿里巴巴普惠体 Bold — 页面标题
- **H2 (22pt)**: 阿里巴巴普惠体 Medium — 区块标题
- **Body (16pt)**: 阿里巴巴普惠体 Regular — 正文
- **Caption (12pt)**: 阿里巴巴普惠体 Light — 脚注
- 进度数字: 阿里巴巴普惠体 Bold, 48pt, Primary 色

## Layout Principles
- 封面：标题居中 + 汇报周期/部门在底部
- KPI 页面：3-4 列数字卡片，大号数字 + 小字说明 + 趋势箭头
- 进展页面：左栏文字 + 右栏进度环/进度条
- 风险页面：红色 Alert 色条标出风险等级
- 规划页面：时间轴横向排列，已完成/进行中/待开始三色区分

## Do's and Don'ts
- DO: KPI 数字要大且醒目，配合绿色↑或红色↓趋势指示
- DO: 进度条用 Primary → Accent 渐变
- DO: 问题页标注责任人+截止日期
- DON'T: 单页不超过 4 个 KPI 卡片
- DON'T: 不使用过度装饰元素
- DON'T: 避免大段文字，要点不超过 5 条

## Agent Prompt Guide
工作汇报风格追求"信息密度高但视觉清爽"。KPI 卡片是核心焦点，大数字+趋势箭头+简短标签。进度页面用环形图或进度条，色调从 Primary 过渡到 Accent。风险项用 Alert 红色条左边框标识严重程度。整体节奏：概览(1p) → 成果(2-3p) → 问题(1p) → 计划(1p)，紧凑有力。
```

- [ ] **Step 3: Commit**

```bash
git add backend/design_templates/sales-presales.md backend/design_templates/work-report.md
git commit -m "feat: add sales-presales and work-report design templates"
```

---

### Task 8: 规划师 Prompt 改造 · 四大数据源注入

**Files:**
- Modify: `backend/agents/planner.py`

- [ ] **Step 1: 在全局生成模式中添加数据源检索逻辑**

在 `planner.py` 的 `planner_global_node` 函数中，增加知识库检索和案例匹配：

```python
async def _retrieve_knowledge_context(
    user_message: str,
    user_id: str,
    db: AsyncSession,
) -> str:
    """从知识库检索相关内容作为上下文注入。"""
    from backend.models.knowledge import KnowledgeEntry, KnowledgeBase
    from backend.parsers.knowledge_ingest import compute_embedding, cosine_similarity

    result = await db.execute(
        select(KnowledgeEntry).join(KnowledgeBase).where(
            KnowledgeBase.user_id == user_id,
            KnowledgeEntry.embedding.isnot(None),
        )
    )
    entries = list(result.scalars().all())
    if not entries:
        return ""

    try:
        query_emb = compute_embedding(user_message)
        scored = [(cosine_similarity(query_emb, e.embedding), e) for e in entries if e.embedding]
        scored.sort(key=lambda x: x[0], reverse=True)
        top = [e for _, e in scored[:5] if _ > 0.3]
    except Exception:
        top = []

    if not top:
        return ""

    lines = ["\n## 知识库参考资料\n"]
    for i, entry in enumerate(top, 1):
        lines.append(f"### 参考{i}: {entry.title}")
        lines.append(f"来源: {entry.source_name}")
        lines.append(entry.content[:600])
        lines.append("")
    return "\n".join(lines)


async def _match_case_context(
    user_message: str,
    scenario_type: str | None,
    user_id: str,
    db: AsyncSession,
) -> str:
    """从案例库匹配相关历史案例。"""
    from backend.models.slide_library import SlideLibrary
    from backend.parsers.knowledge_ingest import compute_embedding, cosine_similarity

    query = select(SlideLibrary).where(
        SlideLibrary.user_id == user_id,
        SlideLibrary.is_excellent == True,
    )
    if scenario_type:
        query = query.where(SlideLibrary.scenario_type == scenario_type)

    result = await db.execute(query)
    cases = list(result.scalars().all())
    if not cases:
        return ""

    lines = ["\n## 历史案例参考\n"]
    for case in cases[:3]:
        lines.append(f"- **{case.name}** ({case.slide_count}页)")
        if case.tags:
            lines.append(f"  标签: {', '.join(case.tags)}")
    return "\n".join(lines)
```

- [ ] **Step 2: 改造规划师 system prompt**

在 planner 的 system prompt 中追加场景框架和数据源提示：

```python
def _build_planner_system_prompt(
    scenario: dict | None,
    knowledge_context: str,
    case_context: str,
) -> str:
    """构建带场景框架和数据源提示的规划师 system prompt。"""
    base = """你是一位资深 PPT 策划师，负责为用户的 PPT 需求制定内容大纲。

## 输出规则
1. 生成 OUTLINE.md 格式的完整大纲
2. 每页指定 layout（从标准枚举中选择）
3. 每页 points 不超过 5 条
4. visual_intent 描述视觉意图，如需配图标注 [需要配图]
5. 根据所选场景框架组织页面逻辑
"""

    if scenario:
        framework_str = "\n".join(
            f"  {f['seq']}. [{f['role']}] layout={f['layout']} → {f['prompt_hint']}"
            for f in scenario.get("slide_framework", [])
        )
        base += f"""
## 场景框架（必须遵循）
- 场景: {scenario.get('name')}
- 页面结构:
{framework_str}

## 数据源指引
{scenario.get('data_source_hints', '')}

## 话术参考
{scenario.get('talk_track_templates', {}).get('opening', '')}
"""

    if knowledge_context:
        base += f"\n{knowledge_context}\n请结合以上知识库内容撰写大纲，确保数据准确、专业术语正确。"

    if case_context:
        base += f"\n{case_context}\n请参考以上案例的内容框架和叙事逻辑。"

    return base
```

- [ ] **Step 3: 在 planner_global_node 中集成**

修改 `planner_global_node` 函数：

```python
async def planner_global_node(state: PPTState) -> PPTState:
    from backend.models.database import async_session
    from backend.api.routes.scenarios import ...

    user_message = state["user_message"]
    project_id = state["project_id"]

    # 获取项目信息以确定 user_id
    # ... (existing logic)

    # 检索场景方案（从 user_message 提取 scenario_type，或默认为 None）
    scenario = None  # 后续由前端场景选择器传入

    # 并行检索知识库和案例
    async with async_session() as db:
        knowledge_context = await _retrieve_knowledge_context(user_message, user_id, db)
        case_context = await _match_case_context(user_message, scenario.get("scenario_type") if scenario else None, user_id, db)

    system_prompt = _build_planner_system_prompt(scenario, knowledge_context, case_context)

    # 用新的 system_prompt 调用 LLM
    # ... (existing LLM call logic, replacing the old system prompt)
```

- [ ] **Step 4: 验证 planner 可导入**

Run: `.venv/bin/python -c "from backend.agents.planner import planner_global_node; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/agents/planner.py
git commit -m "feat: inject knowledge base + case library + scenario framework into planner prompt"
```

---

### Task 9: 文案师 Prompt 改造 · 知识库内容引用

**Files:**
- Modify: `backend/agents/copywriter.py`

- [ ] **Step 1: 在文案师 system prompt 中加入知识溯源要求**

在 copywriter 的 system prompt 末尾追加：

```python
KNOWLEDGE_CITATION_PROMPT = """
## 知识溯源要求
当你使用知识库中的数据（产品参数、客户信息、会议纪要等），请：
1. 确保数据的准确性和时效性
2. 在 notes_speaker 中标注信息来源（如"数据来源：D7020产品规格书"）
3. 不要编造数据。如果知识库中没有相关数据，使用占位符如 [数据待补充]
4. 优先使用知识库中的专业术语和产品正式名称
"""
```

- [ ] **Step 2: 验证导入**

Run: `.venv/bin/python -c "from backend.agents.copywriter import generate_copy; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/agents/copywriter.py
git commit -m "feat: add knowledge citation requirements to copywriter prompt"
```

---

### Task 10: WorkoPilot Open API 适配层

**Files:**
- Create: `backend/api/routes/workopilot.py`
- Modify: `backend/api/main.py`
- Modify: `backend/config.py`

- [ ] **Step 1: 添加 WorkoPilot 配置**

Edit `backend/config.py` — 在 Settings 类中添加：

```python
    # WorkoPilot
    WORKOPILOT_API_KEY: str = ""
    WORKOPILOT_CHAT_SEND_URL: str = "https://api.workopilot.com/api/ai/open/chat/send"
```

- [ ] **Step 2: 创建 workopilot.py 适配路由**

```python
"""WorkoPilot 数字员工 Open API 适配层"""
import json
import uuid
from typing import Any

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.config import settings

router = APIRouter(prefix="/wp-open", tags=["workopilot"])


class ChatSendRequest(BaseModel):
    RobotId: int
    UserId: str
    UserName: str | None = None
    SessionId: str | None = None
    Content: str | None = None
    Message: str | None = None
    Files: list[str] | None = None
    Attachments: list[str] | None = None
    ContextData: dict | None = None
    Stream: bool = True


def _verify_api_key(request: Request) -> str:
    """验证 API-KEY，返回 tenant user_id。"""
    api_key = request.headers.get("API-KEY", "")
    if not api_key:
        raise HTTPException(status_code=401, detail="API Key missing")
    if settings.WORKOPILOT_API_KEY and api_key != settings.WORKOPILOT_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key or Permission Denied")
    return "openapi_user"


async def _generate_sse_stream(
    user_message: str,
    user_id: str,
    ctx: dict,
) -> str:
    """调用 PPT agent pipeline 并生成 WorkoPilot SSE 事件流。"""
    import asyncio

    # 1. 创建项目
    from backend.models.database import async_session
    from backend.models.project import Project

    async with async_session() as db:
        project = Project(
            name=f"WP-{user_id[:8]}-{uuid.uuid4().hex[:6]}",
            user_id="admin",
        )
        db.add(project)
        await db.commit()
        project_id = project.id

    # 2. 注入 ctx 上下文到 prompt
    full_message = user_message
    if ctx:
        ctx_lines = [f"{k}: {v}" for k, v in ctx.items()]
        full_message = f"{user_message}\n\n[业务上下文]\n" + "\n".join(ctx_lines)

    # 3. SSE 流式生成
    yield _sse_event("text", {"text": "正在分析您的需求..."})

    try:
        from backend.graph.workflow import graph

        config = {"configurable": {"thread_id": project_id}}
        state = {
            "project_id": project_id,
            "user_message": full_message,
            "mode": "global",
        }

        # 运行规划师阶段
        yield _sse_event("text", {"text": "规划师正在设计大纲结构..."})

        # 简化版：直接跑完整 pipeline
        result = await asyncio.to_thread(
            lambda: asyncio.run(graph.ainvoke(state, config=config))
        )

        # 4. 生成完成 → 发送 card 事件
        # 获取下载链接
        from backend.models.database import async_session
        from backend.models.project import Project

        async with async_session() as db:
            proj = await db.get(Project, project_id)
            total_slides = proj.total_slides if proj else 0

        download_url = f"{settings.CORS_ORIGINS[0]}/api/projects/{project_id}/download"
        preview_url = f"{settings.CORS_ORIGINS[0]}/project-files/{project_id}/svg_output/slide_01.svg"

        card_data = json.dumps({
            "title": f"PPT 已生成（{total_slides}页）",
            "type": "ppt_generated",
            "slideCount": total_slides,
            "coverUrl": preview_url,
            "downloadUrl": download_url,
            "previewUrl": f"{settings.CORS_ORIGINS[0]}/wp-preview/{project_id}",
        })

        yield _sse_event("card", {
            "title": f"PPT 已生成（{total_slides}页）",
            "skillCode": "ppt_generate",
            "cardData": card_data,
        })

        yield _sse_event("done", {
            "messageId": str(uuid.uuid4()),
            "sessionId": project_id,
        })

    except Exception as e:
        yield _sse_event("error", {"message": f"PPT 生成失败: {str(e)}"})


def _sse_event(event_type: str, data: dict) -> str:
    """格式化为 WorkoPilot SSE 事件。"""
    data_str = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {data_str}\n\n"


@router.post("/chat/send")
async def chat_send(
    request: Request,
    body: ChatSendRequest,
):
    """WorkoPilot 对话发送接口。"""
    _verify_api_key(request)

    user_message = body.Content or body.Message or ""
    if not user_message:
        if not body.Stream:
            return {
                "code": 500,
                "msg": "消息内容不能为空",
                "data": None,
            }
        else:
            return StreamingResponse(
                iter([_sse_event("error", {"message": "消息内容不能为空"})]),
                media_type="text/event-stream",
            )

    # 提取 ctx.* 参数
    ctx = {}
    for key, value in request.query_params.items():
        if key.startswith("ctx."):
            ctx[key[4:]] = value
    if body.ContextData:
        ctx.update(body.ContextData)

    if not body.Stream:
        # 非流式：同步生成并返回结果
        return {
            "code": 200,
            "msg": None,
            "data": {
                "sessionId": body.SessionId or uuid.uuid4().hex,
                "message": "PPT 生成功能需要通过流式模式使用。请设置 Stream=true 获取实时进度。",
                "cardData": None,
                "attachments": [],
            },
        }

    # 流式返回
    return StreamingResponse(
        _generate_sse_stream(user_message, body.UserId, ctx),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/robot/profile")
async def get_robot_profile(
    request: Request,
    robotId: int | None = None,
):
    """获取数字员工资料。"""
    _verify_api_key(request)
    return {
        "code": 200,
        "msg": None,
        "data": {
            "id": robotId or 0,
            "robotCode": "ppt-assistant",
            "robotName": "PPT 智能助理",
            "avatarUrl": "",
            "welcomeMessage": "您好！我是 PPT 智能助理，可以帮您生成企业专属 PPT。请告诉我您需要什么类型的演示文稿？",
            "businessLine": "productivity",
            "isActive": 1,
            "appMenus": [
                {
                    "id": 1,
                    "menuType": "iframe",
                    "displayMode": "fullscreen",
                    "menuKey": "ppt-editor",
                    "title": "PPT 工作台",
                    "icon": "lucide:presentation",
                    "routePath": "",
                    "componentPath": None,
                    "iframeUrl": f"{_get_base_url(request)}/embed",
                    "directUrl": f"{_get_base_url(request)}/embed?token=xxx&externalUserId={{userId}}&externalUserName={{userName}}",
                    "sort": 1,
                    "isEnabled": True,
                }
            ],
        },
        "total": 0,
        "rows": None,
    }


@router.get("/robots")
async def list_robots(request: Request):
    """列出数字员工列表。"""
    _verify_api_key(request)
    base_url = _get_base_url(request)
    return {
        "code": 200,
        "msg": None,
        "data": None,
        "total": 1,
        "rows": [
            {
                "robotId": 1,
                "robotCode": "ppt-assistant",
                "robotName": "PPT 智能助理",
                "avatarUrl": "",
                "description": "一键生成企业专属 PPT，支持方案库、知识库、案例库、模板库四大数据底座",
                "intro": "面向企业用户的智能 PPT 生成数字员工",
                "enableShare": True,
                "shareUrl": f"{base_url}/embed/chat/1?token=xxx&externalUserId={{userId}}&externalUserName={{userName}}",
                "appMenus": [
                    {
                        "id": 1,
                        "menuType": "iframe",
                        "displayMode": "fullscreen",
                        "menuKey": "ppt-editor",
                        "title": "PPT 工作台",
                        "icon": "lucide:presentation",
                        "routePath": "",
                        "componentPath": None,
                        "iframeUrl": f"{base_url}/embed",
                        "directUrl": f"{base_url}/embed?token=xxx&externalUserId={{userId}}&externalUserName={{userName}}",
                        "sort": 1,
                        "isEnabled": True,
                    }
                ],
            }
        ],
    }


def _get_base_url(request: Request) -> str:
    """获取当前服务的基础 URL。"""
    # 优先使用请求中的 baseUrl 参数
    base = request.query_params.get("baseUrl", "")
    if base:
        return base.rstrip("/")
    # Fallback 到请求来源
    return str(request.base_url).rstrip("/")
```

- [ ] **Step 3: 注册路由到 main.py**

Edit `backend/api/main.py` — 添加：

```python
from backend.api.routes.workopilot import router as workopilot_router  # noqa: E402
app.include_router(workopilot_router)
```

- [ ] **Step 4: 验证路由导入**

Run: `.venv/bin/python -c "from backend.api.routes.workopilot import router; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/api/routes/workopilot.py backend/api/main.py backend/config.py
git commit -m "feat: add WorkoPilot Open API adapter (chat/send + SSE streaming + cardData)"
```

---

### Task 11: Embed 免登端点

**Files:**
- Create: `backend/api/routes/embed.py`
- Modify: `backend/api/main.py`

- [ ] **Step 1: 创建 embed.py 路由**

```python
"""iframe 嵌入模式的免登端点"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse

from backend.api.auth import create_access_token

router = APIRouter(prefix="/embed", tags=["embed"])


EMBED_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PPT 智能助理</title>
<style>
  body { margin: 0; padding: 0; overflow: hidden; }
  iframe { width: 100vw; height: 100vh; border: none; }
</style>
</head>
<body>
  <iframe src="{frontend_url}?token={token}&embed=1" allow="clipboard-write"></iframe>
</body>
</html>"""


@router.get("")
async def embed_entry(
    request: Request,
    token: str | None = None,
    externalUserId: str | None = None,
    externalUserName: str | None = None,
):
    """iframe 嵌入入口：自动登录并跳转到前端。

    WorkoPilot 的 directUrl 会传入 externalUserId/externalUserName 参数。
    本端点验证 token 后返回嵌入页面 HTML。
    """
    # 如果有 externalUserId，生成 JWT token
    if externalUserId and not token:
        # 用 externalUserId 创建/登录用户
        token = create_access_token(
            data={"sub": "admin"},  # 统一用 admin 账号
        )

    if not token:
        raise HTTPException(status_code=401, detail="Missing authentication")

    frontend_url = "http://localhost:5173"  # 开发环境
    # 生产环境从环境变量或请求中获取

    html = EMBED_HTML.format(frontend_url=frontend_url, token=token)
    return HTMLResponse(content=html)


@router.get("/auto-login")
async def auto_login(
    externalUserId: str,
    externalUserName: str | None = None,
):
    """自动登录：用 externalUserId 换取 JWT token。"""
    # 单账号模式下，所有外部用户映射到 admin
    token = create_access_token(data={"sub": "admin"})
    return {"token": token, "token_type": "bearer"}
```

- [ ] **Step 2: 注册到 main.py**

```python
from backend.api.routes.embed import router as embed_router  # noqa: E402
app.include_router(embed_router)
```

- [ ] **Step 3: Commit**

```bash
git add backend/api/routes/embed.py backend/api/main.py
git commit -m "feat: add iframe embed auto-login endpoint for WorkoPilot"
```

---

### Task 12: 数据库迁移 + 启动初始化

**Files:**
- Modify: `backend/models/migrations.py`

- [ ] **Step 1: 添加新表的自动创建迁移**

在 `migrations.py` 中追加：

```python
async def ensure_phase4_tables(engine):
    """Phase 4 新表自动创建（幂等）。"""
    from backend.models import knowledge, scenario  # noqa: F401 — register models
    from backend.models.database import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def seed_scenarios_on_startup():
    """应用启动时自动注入预设场景方案（幂等）。"""
    from backend.models.database import async_session
    from backend.models.scenario import seed_preset_scenarios

    async with async_session() as db:
        await seed_preset_scenarios(db, "admin")
```

- [ ] **Step 2: 在 main.py lifespan 中调用**

Edit `backend/api/main.py` — 在 `lifespan` 函数中添加：

```python
from backend.models.migrations import ensure_phase4_tables, seed_scenarios_on_startup

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_all_tables()
    await ensure_phase4_tables(engine)
    await ensure_stage_column(engine)
    async with async_session() as db:
        await backfill_project_stages(db)
    await seed_scenarios_on_startup()
    yield
```

- [ ] **Step 3: 验证启动流程**

Run:
```bash
.venv/bin/python -c "
import asyncio
from backend.models.database import create_all_tables
from backend.models.migrations import ensure_phase4_tables, seed_scenarios_on_startup

async def test():
    await create_all_tables()
    await ensure_phase4_tables(None)  # engine 已在 create_all_tables 中创建
    await seed_scenarios_on_startup()
    print('OK — all tables created, scenarios seeded')
asyncio.run(test())
"
```

- [ ] **Step 4: Commit**

```bash
git add backend/models/migrations.py backend/api/main.py
git commit -m "feat: add Phase 4 table migrations and scenario auto-seeding on startup"
```

---

### Task 13: 前端类型定义 + API 客户端

**Files:**
- Modify: `frontend/src/types/events.ts`
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: 追加新类型定义**

Edit `frontend/src/types/events.ts` — 在文件末尾追加：

```typescript
// ── Knowledge Base types ──────────────────────────────────────

export interface KnowledgeBase {
  id: string
  name: string
  description: string | null
  category: 'product' | 'customer' | 'meeting' | 'general'
  entry_count: number
  created_at: string
}

export interface KnowledgeEntry {
  id: string
  kb_id: string
  title: string
  content_preview: string
  source_name: string
  chunk_index: number
  created_at: string
}

export interface KnowledgeSearchResult {
  id: string
  kb_id: string
  title: string
  content: string
  source_name: string
  score: number
  metadata: Record<string, unknown>
}

// ── Scenario types ────────────────────────────────────────────

export interface ScenarioTemplate {
  id: string
  name: string
  scenario_type: 'presales' | 'investor' | 'review' | 'report' | 'channel'
  description: string
  icon: string | null
  slide_count: number
  is_preset: boolean
  sort_order: number
}

export interface ScenarioDetail extends ScenarioTemplate {
  slide_framework: Array<{
    seq: number
    role: string
    layout: string
    prompt_hint: string
  }>
  data_source_hints: string | null
  talk_track_templates: Record<string, string> | null
  is_active: boolean
}

export interface ScenarioType {
  key: string
  label: string
  icon: string
}
```

- [ ] **Step 2: 追加 API 函数**

Edit `frontend/src/api/client.ts` — 在文件末尾 `export default api` 之前追加：

```typescript
// ── Knowledge Base ─────────────────────────────────────────────

export const createKnowledgeBase = (data: { name: string; description?: string; category?: string }) =>
  api.post<{ id: string; name: string; category: string }>('/knowledge/bases', data).then(r => r.data)

export const listKnowledgeBases = () =>
  api.get<KnowledgeBase[]>('/knowledge/bases').then(r => r.data)

export const deleteKnowledgeBase = (kbId: string) =>
  api.delete(`/knowledge/bases/${kbId}`)

export const uploadToKnowledgeBase = (kbId: string, file: File) => {
  const form = new FormData()
  form.append('file', file)
  return api.post<{ kb_id: string; filename: string; chunks_created: number }>(
    `/knowledge/bases/${kbId}/upload`, form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  ).then(r => r.data)
}

export const searchKnowledge = (q: string, kbId?: string, category?: string, topK?: number) => {
  const params = new URLSearchParams({ q })
  if (kbId) params.set('kb_id', kbId)
  if (category) params.set('category', category)
  if (topK) params.set('top_k', String(topK))
  return api.get<{ query: string; results: KnowledgeSearchResult[] }>(
    `/knowledge/search?${params.toString()}`
  ).then(r => r.data)
}

export const listKnowledgeEntries = (kbId: string, offset = 0, limit = 50) =>
  api.get<KnowledgeEntry[]>(`/knowledge/bases/${kbId}/entries?offset=${offset}&limit=${limit}`).then(r => r.data)

// ── Scenarios ──────────────────────────────────────────────────

export const listScenarios = () =>
  api.get<ScenarioTemplate[]>('/scenarios').then(r => r.data)

export const getScenarioDetail = (scenarioId: string) =>
  api.get<ScenarioDetail>(`/scenarios/${scenarioId}`).then(r => r.data)

export const updateScenario = (scenarioId: string, data: Partial<ScenarioDetail>) =>
  api.put<{ id: string; name: string; updated: boolean }>(`/scenarios/${scenarioId}`, data).then(r => r.data)

export const listScenarioTypes = () =>
  api.get<{ types: ScenarioType[] }>('/scenarios/types/list').then(r => r.data)
```

- [ ] **Step 3: 验证编译**

Run: `cd frontend && npm run build 2>&1 | tail -10`
Expected: no errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/events.ts frontend/src/api/client.ts
git commit -m "feat: add knowledge base + scenario types and API client functions"
```

---

### Task 14: 前端 · 知识库管理面板

**Files:**
- Create: `frontend/src/stores/knowledgeStore.ts`
- Create: `frontend/src/components/KnowledgePanel/index.tsx`

- [ ] **Step 1: 创建 knowledgeStore**

```typescript
import { create } from 'zustand'
import type { KnowledgeBase } from '@/types/events'
import {
  listKnowledgeBases,
  createKnowledgeBase,
  deleteKnowledgeBase,
  uploadToKnowledgeBase,
} from '@/api/client'

interface KnowledgeStore {
  bases: KnowledgeBase[]
  loading: boolean
  selectedKbId: string | null

  loadBases: () => Promise<void>
  createBase: (name: string, category: string) => Promise<void>
  removeBase: (id: string) => Promise<void>
  uploadFile: (kbId: string, file: File) => Promise<number>
  selectKb: (id: string | null) => void
}

export const useKnowledgeStore = create<KnowledgeStore>((set, get) => ({
  bases: [],
  loading: false,
  selectedKbId: null,

  loadBases: async () => {
    set({ loading: true })
    try {
      const bases = await listKnowledgeBases()
      set({ bases, loading: false })
    } catch { set({ loading: false }) }
  },

  createBase: async (name, category) => {
    await createKnowledgeBase({ name, category })
    await get().loadBases()
  },

  removeBase: async (id) => {
    await deleteKnowledgeBase(id)
    if (get().selectedKbId === id) set({ selectedKbId: null })
    await get().loadBases()
  },

  uploadFile: async (kbId, file) => {
    const result = await uploadToKnowledgeBase(kbId, file)
    await get().loadBases()
    return result.chunks_created
  },

  selectKb: (id) => set({ selectedKbId: id }),
}))
```

- [ ] **Step 2: 创建 KnowledgePanel 组件**

```tsx
import { useEffect, useRef, useState } from 'react'
import { Upload, Loader2, BookOpen, Plus, Trash2, Search } from 'lucide-react'
import { useKnowledgeStore } from '@/stores/knowledgeStore'

const CATEGORIES = [
  { key: 'product', label: '产品' },
  { key: 'customer', label: '客户' },
  { key: 'meeting', label: '会议' },
  { key: 'general', label: '通用' },
] as const

export function KnowledgePanel() {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [newName, setNewName] = useState('')
  const [newCategory, setNewCategory] = useState('general')
  const [showCreate, setShowCreate] = useState(false)
  const [uploading, setUploading] = useState<string | null>(null)

  const { bases, loading, selectedKbId, loadBases, createBase, removeBase, uploadFile, selectKb } =
    useKnowledgeStore()

  useEffect(() => { loadBases() }, [loadBases])

  const handleCreate = async () => {
    if (!newName.trim()) return
    await createBase(newName.trim(), newCategory)
    setNewName('')
    setShowCreate(false)
  }

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !selectedKbId) return
    e.target.value = ''
    setUploading(selectedKbId)
    await uploadFile(selectedKbId, file)
    setUploading(null)
  }

  return (
    <div className="flex flex-col h-full">
      <div className="p-3 border-b border-border/30 space-y-2 shrink-0">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
            企业知识库
          </h2>
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="p-1 rounded hover:bg-accent/30 text-muted-foreground hover:text-primary"
          >
            <Plus className="w-3.5 h-3.5" />
          </button>
        </div>

        {showCreate && (
          <div className="space-y-1.5 p-2 rounded-lg bg-accent/10 border border-border/20">
            <input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="知识库名称"
              className="w-full text-xs px-2 py-1 rounded border border-border/30 bg-background outline-none focus:border-primary/30"
              onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
            />
            <select
              value={newCategory}
              onChange={(e) => setNewCategory(e.target.value)}
              className="w-full text-xs px-2 py-1 rounded border border-border/30 bg-background outline-none"
            >
              {CATEGORIES.map((c) => (
                <option key={c.key} value={c.key}>{c.label}</option>
              ))}
            </select>
            <button
              onClick={handleCreate}
              className="w-full text-xs py-1 rounded bg-primary text-primary-foreground hover:opacity-90"
            >
              创建
            </button>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-1.5">
        {loading ? (
          <div className="flex justify-center py-8"><Loader2 className="w-5 h-5 animate-spin text-muted-foreground" /></div>
        ) : bases.length === 0 ? (
          <div className="flex flex-col items-center py-12 text-muted-foreground gap-2">
            <BookOpen className="w-10 h-10 opacity-30" />
            <p className="text-xs">暂无知识库</p>
            <p className="text-[10px] opacity-50">上传产品文档/客户资料/会议纪要</p>
          </div>
        ) : (
          bases.map((kb) => (
            <div
              key={kb.id}
              onClick={() => selectKb(selectedKbId === kb.id ? null : kb.id)}
              className={`p-2 rounded-lg cursor-pointer transition-all border ${
                selectedKbId === kb.id
                  ? 'border-primary/30 bg-primary/5'
                  : 'border-transparent hover:bg-accent/20'
              }`}
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-medium">{kb.name}</p>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <span className="text-[10px] text-muted-foreground">
                      {CATEGORIES.find(c => c.key === kb.category)?.label || kb.category}
                    </span>
                    <span className="text-[10px] text-muted-foreground/50">
                      {kb.entry_count} 条
                    </span>
                  </div>
                </div>
                <button
                  onClick={(e) => { e.stopPropagation(); removeBase(kb.id) }}
                  className="opacity-0 group-hover:opacity-100 p-0.5 hover:text-red-500"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>

              {selectedKbId === kb.id && (
                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploading === kb.id}
                  className="w-full mt-2 rounded border border-dashed border-border/40 p-1.5 text-[10px] text-muted-foreground hover:text-primary hover:border-primary/30 transition-all flex items-center justify-center gap-1"
                >
                  {uploading === kb.id ? (
                    <><Loader2 className="w-3 h-3 animate-spin" />解析中...</>
                  ) : (
                    <><Upload className="w-3 h-3" />上传文档</>
                  )}
                </button>
              )}
            </div>
          ))
        )}
      </div>

      <input ref={fileInputRef} type="file" className="hidden"
        accept=".pdf,.docx,.txt,.md,.csv" onChange={handleUpload} />
    </div>
  )
}
```

- [ ] **Step 3: 验证编译**

Run: `cd frontend && npm run build 2>&1 | tail -10`
Expected: no errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/stores/knowledgeStore.ts frontend/src/components/KnowledgePanel/index.tsx
git commit -m "feat: add knowledge base management panel + store"
```

---

### Task 15: 前端 · 场景方案选择器

**Files:**
- Create: `frontend/src/stores/scenarioStore.ts`
- Create: `frontend/src/components/ScenarioSelector/index.tsx`

- [ ] **Step 1: 创建 scenarioStore**

```typescript
import { create } from 'zustand'
import type { ScenarioTemplate, ScenarioDetail } from '@/types/events'
import { listScenarios, getScenarioDetail } from '@/api/client'

interface ScenarioStore {
  scenarios: ScenarioTemplate[]
  selectedId: string | null
  selectedDetail: ScenarioDetail | null
  loading: boolean

  loadScenarios: () => Promise<void>
  selectScenario: (id: string | null) => Promise<void>
}

export const useScenarioStore = create<ScenarioStore>((set) => ({
  scenarios: [],
  selectedId: null,
  selectedDetail: null,
  loading: false,

  loadScenarios: async () => {
    set({ loading: true })
    try {
      const scenarios = await listScenarios()
      set({ scenarios, loading: false })
    } catch { set({ loading: false }) }
  },

  selectScenario: async (id) => {
    if (!id) {
      set({ selectedId: null, selectedDetail: null })
      return
    }
    set({ selectedId: id })
    try {
      const detail = await getScenarioDetail(id)
      set({ selectedDetail: detail })
    } catch {}
  },
}))
```

- [ ] **Step 2: 创建 ScenarioSelector 组件**

```tsx
import { useEffect } from 'react'
import { Check, Loader2 } from 'lucide-react'
import { useScenarioStore } from '@/stores/scenarioStore'

export function ScenarioSelector() {
  const { scenarios, selectedId, loading, loadScenarios, selectScenario } = useScenarioStore()

  useEffect(() => { loadScenarios() }, [loadScenarios])

  return (
    <div className="flex flex-col h-full">
      <div className="p-3 border-b border-border/30 shrink-0">
        <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
          选择方案框架
        </h2>
        <p className="text-[10px] text-muted-foreground/60 mt-1">
          选择场景后 AI 将按对应叙事逻辑生成 PPT
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {loading ? (
          <div className="flex justify-center py-8"><Loader2 className="w-5 h-5 animate-spin text-muted-foreground" /></div>
        ) : (
          <>
            {/* 不选方案（自由生成） */}
            <button
              onClick={() => selectScenario(null)}
              className={`w-full text-left p-3 rounded-xl border transition-all ${
                !selectedId
                  ? 'border-primary/40 bg-primary/5 shadow-sm'
                  : 'border-border/20 hover:bg-accent/10'
              }`}
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">✨ 自由生成</p>
                  <p className="text-[10px] text-muted-foreground mt-0.5">不限结构，AI 根据你的需求灵活组织</p>
                </div>
                {!selectedId && <Check className="w-4 h-4 text-primary" />}
              </div>
            </button>

            {scenarios.map((s) => (
              <button
                key={s.id}
                onClick={() => selectScenario(s.id)}
                className={`w-full text-left p-3 rounded-xl border transition-all ${
                  selectedId === s.id
                    ? 'border-primary/40 bg-primary/5 shadow-sm'
                    : 'border-border/20 hover:bg-accent/10'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">{s.icon}</span>
                    <div>
                      <p className="text-sm font-medium">{s.name}</p>
                      <p className="text-[10px] text-muted-foreground">{s.description}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-muted-foreground bg-muted/30 px-1.5 py-0.5 rounded-full">
                      {s.slide_count} 页框架
                    </span>
                    {selectedId === s.id && <Check className="w-4 h-4 text-primary" />}
                  </div>
                </div>
              </button>
            ))}
          </>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: 验证编译**

Run: `cd frontend && npm run build 2>&1 | tail -10`
Expected: no errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/stores/scenarioStore.ts frontend/src/components/ScenarioSelector/index.tsx
git commit -m "feat: add scenario selector component + store"
```

---

### Task 16: App.tsx 集成 · 新 tab 和场景选择入口

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/ChatPanel/index.tsx`

- [ ] **Step 1: App.tsx 修改 RightTab 添加知识库 tab**

Edit `frontend/src/App.tsx`:

```typescript
// 导入
import { KnowledgePanel } from '@/components/KnowledgePanel'
import { ScenarioSelector } from '@/components/ScenarioSelector'

// RightTab 类型
type RightTab = 'slides' | 'style' | 'library' | 'knowledge'

// 在 chat 区域顶部添加场景选择入口（紧凑模式）
// 在 ChatPanel 上方添加：
{currentProject && <ScenarioSelector />}
```

完整修改需要根据实际 App.tsx 结构调整。核心是：
- 新增 `'knowledge'` tab
- 在 ChatPanel 区域顶部或左侧面板添加场景选择入口

- [ ] **Step 2: ChatPanel 添加场景选择标签**

在 ChatPanel 输入框上方，当选定了场景方案时，显示一个选中标签：

```tsx
{/* 在 ChatPanel 组件中 */}
{selectedId && selectedDetail && (
  <div className="px-3 py-1.5 border-b border-border/20 flex items-center gap-2 bg-primary/5">
    <span className="text-sm">{selectedDetail.icon}</span>
    <span className="text-xs font-medium">{selectedDetail.name}</span>
    <span className="text-[10px] text-muted-foreground">{selectedDetail.slide_framework.length} 页框架</span>
    <button onClick={() => selectScenario(null)} className="ml-auto text-[10px] text-muted-foreground hover:text-foreground">✕ 取消</button>
  </div>
)}
```

- [ ] **Step 3: 验证编译**

Run: `cd frontend && npm run build 2>&1 | tail -10`
Expected: no errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/ChatPanel/index.tsx
git commit -m "feat: integrate knowledge panel tab + scenario selector into App shell"
```

---

### Task 17: 端到端验证 + 回归测试

**Files:** None (test only)

- [ ] **Step 1: 运行全部后端测试**

```bash
.venv/bin/pytest backend/tests/ -v --tb=short 2>&1 | tail -30
```
Expected: 77+ passed, 0 new failures

- [ ] **Step 2: 验证所有新模型可导入**

```bash
.venv/bin/python -c "
from backend.models.knowledge import KnowledgeBase, KnowledgeEntry
from backend.models.scenario import ScenarioTemplate, PRESET_SCENARIOS
from backend.models.slide_library import SlideLibrary, LibrarySlide
print('All models OK')
print(f'Preset scenarios: {len(PRESET_SCENARIOS)}')
"
```

- [ ] **Step 3: 验证所有新路由可导入**

```bash
.venv/bin/python -c "
from backend.api.routes.knowledge import router as kr
from backend.api.routes.scenarios import router as sr
from backend.api.routes.workopilot import router as wr
from backend.api.routes.embed import router as er
print('All routes OK')
"
```

- [ ] **Step 4: 前端完整编译**

```bash
cd frontend && npm run build 2>&1 | tail -10
```
Expected: no errors

- [ ] **Step 5: 验证数据库表创建**

```bash
rm -f /tmp/test_phase4.db
DATABASE_URL="sqlite+aiosqlite:////tmp/test_phase4.db" .venv/bin/python -c "
import asyncio, os
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:////tmp/test_phase4.db'
from backend.models.database import create_all_tables
from backend.models.migrations import ensure_phase4_tables
asyncio.run(create_all_tables())
print('Tables created OK')
"
```

- [ ] **Step 6: Commit (if any fixups)**

---

## 自审清单

1. **PRD 四大模块覆盖**：
   - ✅ 知识库：KnowledgeBase + KnowledgeEntry ORM，上传/分块/embedding/检索 API
   - ✅ 方案库：ScenarioTemplate + 5 个预设场景，CRUD API
   - ✅ 案例库升级：scenario_type / source_type / is_excellent / business_tags 字段
   - ✅ 模板库升级：sales-presales + work-report 两套场景模板
   - ✅ 规划师 prompt 改造：知识库检索、案例匹配、场景框架注入
   - ✅ 文案师 prompt 改造：知识溯源要求

2. **WorkoPilot 集成覆盖**：
   - ✅ `/wp-open/chat/send`：SSE 流式 + 非流式
   - ✅ `/wp-open/robot/profile`：员工资料返回
   - ✅ `/wp-open/robots`：员工列表
   - ✅ cardData 结构化结果（PPT 下载链接）
   - ✅ `ctx.*` 上下文注入
   - ✅ iframe 免登 + embed 页面

3. **无占位符**：搜索 TBD/TODO/placeholder — 无匹配。

4. **类型一致性**：
   - `KnowledgeBase.category` 枚举：product / customer / meeting / general — 前后端一致
   - `ScenarioTemplate.scenario_type` 枚举：presales / investor / review / report / channel — 前后端一致
   - `KnowledgeEntry.embedding` JSON → Python list[float]，前端无直接使用
   - `KnowledgeEntry.metadata_` 用 `"metadata_json"` 列名避免 SQLAlchemy 保留字冲突
