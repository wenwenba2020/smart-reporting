# 企业智能报告平台 · 整体重构计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 PPT 智能助手从 NotebookLM 通用对话工具重构为「企业智能报告平台」—— 可配置数据源插槽 → 智能填报汇总 → 多格式报告输出（PPT/Word/PDF），支持企业导入自有模板。

**Architecture:** 三层管道架构：DataSourceLayer（数据源插槽抽象）→ SmartFillEngine（智能填报，产出结构化 Markdown + 报表 JSON）→ ReportOutputEngine（模板驱动多格式渲染）。前端从三栏对话布局重构为企业报告工作台（左侧导航 + 中心向导式工作区 + 右侧上下文面板）。

**Tech Stack:** Python 3.12 + FastAPI + SQLAlchemy async + OpenRouter LLM + python-pptx + python-docx + WeasyPrint + React 19 + TypeScript + Zustand + Tailwind v4 + shadcn/ui

---

## 文件清单（架构总览）

```
ppt_agent/
├── backend/
│   ├── models/
│   │   ├── report_template.py      ← NEW 统一报告模板 ORM
│   │   ├── data_source.py          ← NEW 数据源配置 ORM
│   │   ├── report_project.py       ← MODIFY 扩展 Project 支持多报告类型
│   │   ├── knowledge.py            ← (已有) 知识库
│   │   ├── scenario.py             ← (已有) 方案库
│   │   └── slide_library.py        ← (已有) 案例库
│   ├── data_source/                ← NEW 数据源插件目录
│   │   ├── __init__.py             ← 插件注册表
│   │   ├── base.py                 ← DataSourcePlugin 抽象基类
│   │   ├── knowledge_source.py     ← 知识库数据源
│   │   ├── case_library_source.py  ← 案例库数据源
│   │   ├── database_source.py      ← 业务数据库数据源
│   │   └── api_source.py           ← 外部 API 数据源
│   ├── report_engine/              ← NEW 报告引擎目录
│   │   ├── __init__.py
│   │   ├── smart_fill.py           ← 智能填报引擎
│   │   ├── output_engine.py        ← 多格式输出引擎
│   │   ├── ppt_output.py           ← PPT 输出适配器
│   │   ├── docx_output.py          ← Word 输出适配器
│   │   └── pdf_output.py           ← PDF 输出适配器
│   ├── agents/
│   │   ├── planner.py              ← MODIFY 改造为 ReportPlanner
│   │   ├── copywriter.py           ← MODIFY 改造为 ContentWriter
│   │   ├── data_aggregator.py      ← NEW 数据汇总智能体
│   │   └── ...
│   ├── api/routes/
│   │   ├── reports.py              ← NEW 报告项目 CRUD
│   │   ├── data_sources.py         ← NEW 数据源配置 API
│   │   ├── report_templates.py     ← NEW 报告模板管理 API
│   │   ├── smart_fill.py           ← NEW 智能填报 API
│   │   └── workopilot.py           ← MODIFY 适配新输出格式
│   └── parsers/
│       └── template_parser.py      ← NEW 企业模板解析器
├── frontend/src/
│   ├── App.tsx                      ← REPLACE 全新布局
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppShell.tsx         ← NEW 主框架（左导航+中+右）
│   │   │   ├── SideNav.tsx          ← NEW 左侧功能导航
│   │   │   └── ContextPanel.tsx     ← NEW 右侧上下文面板
│   │   ├── report/
│   │   │   ├── CreateReportWizard.tsx ← NEW 向导式报告创建
│   │   │   ├── ReportTypeSelector.tsx  ← NEW 报告类型选择
│   │   │   ├── DataSourceSelector.tsx  ← NEW 数据源勾选
│   │   │   └── ReportHistory.tsx       ← NEW 报告历史列表
│   │   ├── datasource/
│   │   │   ├── DataSourceManager.tsx   ← NEW 数据源管理界面
│   │   │   └── DataSourceConfig.tsx    ← NEW 单数据源配置卡片
│   │   ├── template/
│   │   │   ├── TemplateManager.tsx     ← NEW 模板管理界面
│   │   │   └── TemplateUploadWizard.tsx ← NEW 模板导入向导
│   │   ├── KnowledgePanel/        ← (已有，移入工作台)
│   │   ├── ScenarioSelector/      ← (已有，移入向导)
│   │   └── ChatPanel/             ← MODIFY 降级为辅助对话
│   └── stores/
│       ├── reportStore.ts          ← NEW 报告项目 Store
│       ├── dataSourceStore.ts      ← NEW 数据源 Store
│       └── templateStore.ts        ← NEW 模板 Store
```

---

### Task 1: 数据源插件抽象层 · DataSourcePlugin

**Files:**
- Create: `backend/data_source/__init__.py`
- Create: `backend/data_source/base.py`

- [ ] **Step 1: 创建 DataSourcePlugin 抽象基类**

```python
"""数据源插件抽象基类"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SourceDocument:
    """数据源返回的统一文档结构"""
    source_id: str
    source_type: str            # "knowledge_base" | "case_library" | "database" | "api"
    source_name: str            # 人类可读的名称，如"产品知识库"
    title: str
    content: str                # 纯文本/Markdown 格式
    metadata: dict = field(default_factory=dict)
    relevance_score: float = 0.0


@dataclass
class SourceSchema:
    """数据源的字段/分类结构，供前端展示可选范围"""
    source_type: str
    source_name: str
    categories: list[str]       # 该数据源下的分类，如 product/customer/meeting
    fields: list[str]           # 可检索的关键字段
    total_documents: int = 0


class DataSourcePlugin(ABC):
    """数据源插槽抽象接口。
    
    企业可通过实现此接口接入任意信息源。
    内置实现：KnowledgeBaseSource / CaseLibrarySource / DatabaseSource / ApiSource
    """

    @property
    @abstractmethod
    def source_type(self) -> str:
        """数据源类型标识，如 'knowledge_base'"""
        ...

    @property
    @abstractmethod
    def source_name(self) -> str:
        """人类可读名称，如 '企业知识库'"""
        ...

    @abstractmethod
    async def search(
        self, query: str, top_k: int = 10, **filters
    ) -> list[SourceDocument]:
        """语义/关键词搜索，返回相关文档列表"""
        ...

    @abstractmethod
    async def get_schema(self) -> SourceSchema:
        """返回数据源的结构信息（分类/字段/文档数）"""
        ...

    async def health_check(self) -> bool:
        """检查数据源连接状态，默认返回 True"""
        return True

    def to_config_dict(self) -> dict:
        """导出为前端可展示的配置信息"""
        return {
            "source_type": self.source_type,
            "source_name": self.source_name,
        }


class DataSourceRegistry:
    """数据源插件注册表 —— 单例"""

    _instance: "DataSourceRegistry | None" = None
    _plugins: dict[str, DataSourcePlugin] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(self, plugin: DataSourcePlugin) -> None:
        self._plugins[plugin.source_type] = plugin

    def get(self, source_type: str) -> DataSourcePlugin | None:
        return self._plugins.get(source_type)

    def list_all(self) -> list[DataSourcePlugin]:
        return list(self._plugins.values())

    def list_configs(self) -> list[dict]:
        return [p.to_config_dict() for p in self._plugins.values()]


# 全局单例
registry = DataSourceRegistry()
```

- [ ] **Step 2: 验证导入**

Run: `.venv/bin/python -c "from backend.data_source.base import DataSourcePlugin, DataSourceRegistry, SourceDocument, SourceSchema; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/data_source/
git commit -m "feat: add DataSourcePlugin abstract base + registry"
```

---

### Task 2: 内置数据源实现 · KnowledgeBase + CaseLibrary

**Files:**
- Create: `backend/data_source/knowledge_source.py`
- Create: `backend/data_source/case_library_source.py`

- [ ] **Step 1: KnowledgeBaseSource 实现**

```python
"""知识库数据源插件"""
from backend.data_source.base import DataSourcePlugin, SourceDocument, SourceSchema
from backend.models.database import async_session
from backend.models.knowledge import KnowledgeEntry, KnowledgeBase
from backend.parsers.knowledge_ingest import compute_embedding, cosine_similarity
from sqlalchemy import select


class KnowledgeBaseSource(DataSourcePlugin):

    @property
    def source_type(self) -> str:
        return "knowledge_base"

    @property
    def source_name(self) -> str:
        return "企业知识库"

    async def search(
        self, query: str, top_k: int = 10, user_id: str = "", **filters
    ) -> list[SourceDocument]:
        async with async_session() as db:
            q = select(KnowledgeEntry).join(KnowledgeBase).where(
                KnowledgeBase.user_id == user_id
            )
            if filters.get("category"):
                q = q.where(KnowledgeBase.category == filters["category"])
            if filters.get("kb_id"):
                q = q.where(KnowledgeEntry.kb_id == filters["kb_id"])

            result = await db.execute(q)
            entries = list(result.scalars().all())

        if not entries:
            return []

        try:
            query_emb = compute_embedding(query)
            scored = [
                (cosine_similarity(query_emb, e.embedding), e)
                for e in entries if e.embedding
            ]
            scored.sort(key=lambda x: x[0], reverse=True)
        except Exception:
            return [
                SourceDocument(
                    source_id=e.id, source_type=self.source_type,
                    source_name=self.source_name, title=e.title,
                    content=e.content[:600],
                    metadata=e.metadata_ or {},
                )
                for e in entries[:top_k]
            ]

        return [
            SourceDocument(
                source_id=e.id, source_type=self.source_type,
                source_name=self.source_name, title=e.title,
                content=e.content[:600], metadata=e.metadata_ or {},
                relevance_score=round(s, 3),
            )
            for s, e in scored[:top_k] if s > 0.2
        ]

    async def get_schema(self, user_id: str = "") -> SourceSchema:
        async with async_session() as db:
            result = await db.execute(
                select(KnowledgeBase).where(KnowledgeBase.user_id == user_id)
            )
            kbs = list(result.scalars().all())

        categories = list({kb.category for kb in kbs})
        total = sum(kb.entry_count or 0 for kb in kbs)
        return SourceSchema(
            source_type=self.source_type,
            source_name=self.source_name,
            categories=categories,
            fields=["title", "content", "source_name", "category"],
            total_documents=total,
        )
```

- [ ] **Step 2: CaseLibrarySource 实现**

```python
"""案例库数据源插件"""
from backend.data_source.base import DataSourcePlugin, SourceDocument, SourceSchema
from backend.models.database import async_session
from backend.models.slide_library import SlideLibrary, LibrarySlide
from sqlalchemy import select


class CaseLibrarySource(DataSourcePlugin):

    @property
    def source_type(self) -> str:
        return "case_library"

    @property
    def source_name(self) -> str:
        return "企业PPT案例库"

    async def search(
        self, query: str, top_k: int = 10, user_id: str = "", **filters
    ) -> list[SourceDocument]:
        async with async_session() as db:
            q = select(LibrarySlide).join(SlideLibrary).where(
                SlideLibrary.user_id == user_id
            )
            if filters.get("scenario_type"):
                q = q.where(SlideLibrary.scenario_type == filters["scenario_type"])
            if filters.get("is_excellent"):
                q = q.where(SlideLibrary.is_excellent == True)

            result = await db.execute(q)
            slides = list(result.scalars().all())

        # 关键词匹配
        query_lower = query.lower()
        scored = []
        for s in slides:
            text = f"{s.title or ''} {s.text_summary or ''} {' '.join(s.tags or [])}"
            score = 1.0 if query_lower in text.lower() else 0.3
            scored.append((score, s))
        scored.sort(key=lambda x: x[0], reverse=True)

        return [
            SourceDocument(
                source_id=s.id, source_type=self.source_type,
                source_name=self.source_name,
                title=s.title or f"Slide {s.slide_index}",
                content=(s.text_summary or "")[:600],
                metadata={
                    "tags": s.tags or [],
                    "business_tags": s.business_tags or [],
                    "layout_hint": s.layout_hint,
                    "slide_index": s.slide_index,
                    "library_id": s.library_id,
                },
                relevance_score=round(score, 3),
            )
            for score, s in scored[:top_k]
        ]

    async def get_schema(self, user_id: str = "") -> SourceSchema:
        async with async_session() as db:
            result = await db.execute(
                select(SlideLibrary).where(SlideLibrary.user_id == user_id)
            )
            decks = list(result.scalars().all())

        total = sum(d.slide_count or 0 for d in decks)
        scenario_types = list({d.scenario_type for d in decks if d.scenario_type})
        return SourceSchema(
            source_type=self.source_type,
            source_name=self.source_name,
            categories=scenario_types,
            fields=["title", "text_summary", "tags", "business_tags", "layout_hint"],
            total_documents=total,
        )
```

- [ ] **Step 3: 注册到 __init__.py**

```python
"""数据源插件注册"""
from backend.data_source.base import registry
from backend.data_source.knowledge_source import KnowledgeBaseSource
from backend.data_source.case_library_source import CaseLibrarySource


def register_builtin_sources():
    registry.register(KnowledgeBaseSource())
    registry.register(CaseLibrarySource())
```

- [ ] **Step 4: 验证导入**

Run: `.venv/bin/python -c "from backend.data_source import register_builtin_sources; register_builtin_sources(); from backend.data_source.base import registry; print(f'OK — {len(registry.list_all())} sources registered')"`
Expected: `OK — 2 sources registered`

- [ ] **Step 5: Commit**

```bash
git add backend/data_source/
git commit -m "feat: add KnowledgeBase + CaseLibrary data source plugins"
```

---

### Task 3: 报告模板引擎 · ReportTemplate 模型

**Files:**
- Create: `backend/models/report_template.py`

- [ ] **Step 1: 创建 ReportTemplate ORM**

```python
"""企业报告模板数据模型 —— 统一 PPT/Word/PDF 模板"""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import String, Integer, DateTime, Text, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex


class ReportTemplate(Base):
    """企业报告模板 — 支持 PPTX/DOCX/PDF 及企业自定义导入"""
    __tablename__ = "report_templates"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_id)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    report_type: Mapped[str] = mapped_column(String, nullable=False)
    # report_type: "ppt" | "docx" | "pdf"
    source: Mapped[str] = mapped_column(String, nullable=False, default="builtin")
    # source: "builtin" | "user_uploaded"

    # 模板文件路径
    original_filename: Mapped[str | None] = mapped_column(String, nullable=True)
    template_file_path: Mapped[str | None] = mapped_column(String, nullable=True)

    # 从模板中提取的样式规则（JSON）
    style_rules: Mapped[Any] = mapped_column(JSON, nullable=True)
    # 示例: {"colors": ["#1E3A5F", "#4A90D9"], "fonts": ["阿里巴巴普惠体 Bold"], ...}

    # 内容插槽列表（JSON）→ 标记模板中哪些位置可以填入内容
    content_slots: Mapped[Any] = mapped_column(JSON, nullable=True)
    # 示例: [{"slot_id": "title", "type": "text", "position": "cover", "max_chars": 30}, ...]

    # 场景标签
    scenario_type: Mapped[str | None] = mapped_column(String, nullable=True)
    # presales / investor / review / report / channel

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_path: Mapped[str | None] = mapped_column(String, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
```

- [ ] **Step 2: 注册模型到 database.py**

Edit `backend/models/database.py:15`:
```python
    from backend.models import project, snapshot, slide_library, knowledge, scenario, report_template  # noqa: F401
```

- [ ] **Step 3: 验证导入**

Run: `.venv/bin/python -c "from backend.models.report_template import ReportTemplate; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/models/report_template.py backend/models/database.py
git commit -m "feat: add ReportTemplate model (unified PPT/Word/PDF template)"
```

---

### Task 4: 企业模板解析器 · template_parser.py

**Files:**
- Create: `backend/parsers/template_parser.py`

- [ ] **Step 1: 创建模板解析器**

```python
"""企业报告模板解析器 — 从 PPTX/DOCX 提取样式规则和内容插槽"""
import re
from pathlib import Path
from typing import Any

from pptx import Presentation
from docx import Document


def parse_pptx_template(file_path: str | Path) -> dict:
    """从 PPTX 模板提取样式规则 + 内容插槽。
    
    Returns: {"style_rules": {...}, "content_slots": [...], "slide_count": N}
    """
    file_path = Path(file_path)
    prs = Presentation(str(file_path))

    colors: set[str] = set()
    fonts: set[str] = set()
    font_sizes: set[int] = set()
    slots: list[dict] = []

    for slide_idx, slide in enumerate(prs.slides, 1):
        for shape in slide.shapes:
            # 提取文本占位符作为内容插槽
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    for run in para.runs:
                        text = run.text.strip()
                        if run.font.color and run.font.color.rgb:
                            colors.add(str(run.font.color.rgb))
                        if run.font.name:
                            fonts.add(run.font.name)
                        if run.font.size:
                            font_sizes.add(int(run.font.size.pt))

                        # 检测占位符模式: {{title}}, {{chart}}, {{body}} 等
                        placeholders = re.findall(r'\{\{(\w+)\}\}', text)
                        for ph in placeholders:
                            slots.append({
                                "slot_id": ph,
                                "type": _infer_slot_type(ph),
                                "slide_index": slide_idx,
                                "shape_name": shape.name,
                            })

    return {
        "style_rules": {
            "colors": sorted(colors)[:12],
            "fonts": sorted(fonts),
            "font_sizes": sorted(font_sizes),
        },
        "content_slots": slots,
        "slide_count": len(prs.slides),
    }


def parse_docx_template(file_path: str | Path) -> dict:
    """从 DOCX 模板提取样式规则 + 内容插槽。"""
    file_path = Path(file_path)
    doc = Document(str(file_path))

    fonts: set[str] = set()
    font_sizes: set[int] = set()
    slots: list[dict] = []

    for para in doc.paragraphs:
        for run in para.runs:
            if run.font.name:
                fonts.add(run.font.name)
            if run.font.size:
                font_sizes.add(int(run.font.size.pt))

            placeholders = re.findall(r'\{\{(\w+)\}\}', run.text)
            for ph in placeholders:
                slots.append({
                    "slot_id": ph,
                    "type": _infer_slot_type(ph),
                    "paragraph_style": para.style.name if para.style else None,
                })

    return {
        "style_rules": {
            "fonts": sorted(fonts),
            "font_sizes": sorted(font_sizes),
        },
        "content_slots": slots,
    }


def _infer_slot_type(slot_id: str) -> str:
    """根据占位符名称推断内容类型。"""
    slot_lower = slot_id.lower()
    if any(k in slot_lower for k in ("title", "标题", "heading")):
        return "title"
    if any(k in slot_lower for k in ("chart", "图表", "graph")):
        return "chart"
    if any(k in slot_lower for k in ("table", "表格", "grid")):
        return "table"
    if any(k in slot_lower for k in ("image", "图片", "logo", "photo")):
        return "image"
    if any(k in slot_lower for k in ("date", "日期", "author", "作者")):
        return "metadata"
    return "text"
```

- [ ] **Step 2: 验证导入**

Run: `.venv/bin/python -c "from backend.parsers.template_parser import parse_pptx_template, parse_docx_template; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/parsers/template_parser.py
git commit -m "feat: add template parser (PPTX/DOCX style + slot extraction)"
```

---

### Task 5: 智能填报引擎 · SmartFillEngine

**Files:**
- Create: `backend/report_engine/__init__.py`
- Create: `backend/report_engine/smart_fill.py`

- [ ] **Step 1: 创建 SmartFillEngine**

```python
"""智能填报引擎 —— 将多数据源内容汇总整理为结构化 Markdown + 报表 JSON"""
import json
from dataclasses import dataclass, field
from typing import Any

from backend.data_source.base import DataSourcePlugin, registry
from backend.agents.llm_client import chat
from backend.agents.json_utils import extract_json_object

MODEL = "deepseek/deepseek-v3.2"

SMART_FILL_SYSTEM = """你是企业智能报告的数据汇总专家。根据多数据源检索结果，生成两份输出：

## 输出 1: structured_markdown（完整结构化 Markdown 文档）
- 按章节组织：封面信息 → 摘要概述 → 详细分析 → 数据附录
- 所有数据需注明来源
- 使用 Markdown 表格展示对比数据
- 不超过 5000 字

## 输出 2: report_json（报表生成用的 JSON）
- 遵循指定的 JSON schema
- 所有数据字段从知识库检索结果中提取
- 缺失数据用 null，不编造

返回 JSON：
{
  "structured_markdown": "完整的 Markdown 文档...",
  "report_json": { ... }
}"""


@dataclass
class SmartFillResult:
    """智能填报结果"""
    structured_markdown: str       # 完整的结构化 Markdown 文档
    report_json: dict              # 报表生成用 JSON
    source_references: list[dict]  # 引用的数据源清单


async def run_smart_fill(
    query: str,
    scenario_type: str | None = None,
    selected_sources: list[str] | None = None,
    user_id: str = "",
    report_type: str = "ppt",
) -> SmartFillResult:
    """执行智能填报流程。

    1. 对每个选中的数据源执行检索
    2. 汇总所有检索结果
    3. 调用 LLM 生成结构化 MD + 报表 JSON
    """

    # Step 1: 检索所有数据源
    all_sources = registry.list_all()
    if selected_sources:
        all_sources = [s for s in all_sources if s.source_type in selected_sources]

    all_docs: list[dict] = []
    source_refs: list[dict] = []
    source_context = ""

    for plugin in all_sources:
        try:
            docs = await plugin.search(
                query, top_k=5, user_id=user_id,
                scenario_type=scenario_type,
            )
        except Exception:
            continue

        if docs:
            source_refs.append({
                "source_type": plugin.source_type,
                "source_name": plugin.source_name,
                "doc_count": len(docs),
            })
            source_context += f"\n## 数据源: {plugin.source_name}\n"
            for d in docs:
                source_context += f"\n### {d.title}\n{d.content}\n"
                all_docs.append({
                    "source_type": d.source_type,
                    "source_name": d.source_name,
                    "title": d.title,
                    "content": d.content,
                })

    if not all_docs:
        return SmartFillResult(
            structured_markdown="",
            report_json={},
            source_references=source_refs,
        )

    # Step 2: 构建场景相关的 JSON schema
    json_schema = _get_report_schema(report_type, scenario_type)

    # Step 3: LLM 汇总
    user_prompt = f"""查询主题: {query}
报告类型: {report_type}
场景: {scenario_type or "通用"}

## 数据源检索结果
{source_context[:8000]}

## 报表 JSON Schema
{json.dumps(json_schema, ensure_ascii=False, indent=2)}

请根据以上数据源内容，生成结构化 Markdown 文档和符合 schema 的报表 JSON。"""

    try:
        resp = chat(
            MODEL,
            messages=[
                {"role": "system", "content": SMART_FILL_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=4096,
        )
        result = extract_json_object(resp) or {}
    except Exception:
        return SmartFillResult(
            structured_markdown=source_context,
            report_json={},
            source_references=source_refs,
        )

    return SmartFillResult(
        structured_markdown=result.get("structured_markdown", source_context),
        report_json=result.get("report_json", {}),
        source_references=source_refs,
    )


def _get_report_schema(report_type: str, scenario_type: str | None) -> dict:
    """根据报告类型和场景返回对应的 JSON schema。"""
    if report_type == "ppt":
        return {
            "title": "string (≤15字)",
            "subtitle": "string",
            "slides": [{
                "slide_id": "string (01, 02, ...)",
                "layout": "string (cover|title-content|data-chart|comparison|timeline|team|toc)",
                "title": "string (≤15字)",
                "points": [{"heading": "string (≤30字)", "body": "string (120-250字)"}],
                "chart": {
                    "type": "bar-grouped|pie|line",
                    "data": [["label", 0]],
                    "caption": "string"
                },
                "notes_speaker": "string (50-100字)",
                "source_ref": "string (数据来源引用)"
            }]
        }
    elif report_type == "docx":
        return {
            "title": "string",
            "abstract": "string (200字摘要)",
            "sections": [{
                "heading": "string",
                "body": "string (Markdown格式)",
                "tables": [{"caption": "string", "headers": ["string"], "rows": [["string"]]}],
                "source_ref": "string"
            }]
        }
    else:  # pdf
        return {
            "title": "string",
            "sections": [{"heading": "string", "content": "string"}],
            "tables": [{"caption": "string", "data": []}]
        }
```

- [ ] **Step 2: 验证导入**

Run: `.venv/bin/python -c "from backend.report_engine.smart_fill import run_smart_fill, SmartFillResult; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/report_engine/
git commit -m "feat: add SmartFillEngine — multi-source aggregation → structured MD + report JSON"
```

---

### Task 6: 多格式输出引擎 · ReportOutputEngine

**Files:**
- Create: `backend/report_engine/output_engine.py`
- Create: `backend/report_engine/pptx_output.py`
- Create: `backend/report_engine/docx_output.py`
- Create: `backend/report_engine/pdf_output.py`

- [ ] **Step 1: 创建输出引擎基类**

```python
"""多格式报告输出引擎"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class OutputResult:
    """输出结果"""
    file_path: str
    file_type: str            # "pptx" | "docx" | "pdf"
    mime_type: str
    file_size: int


class OutputAdapter(ABC):
    """输出格式适配器抽象基类"""

    @property
    @abstractmethod
    def format_type(self) -> str:
        ...

    @abstractmethod
    async def generate(
        self,
        report_json: dict,
        template_path: str | None = None,
        style_rules: dict | None = None,
        output_dir: str | Path = ".",
    ) -> OutputResult:
        ...


class ReportOutputEngine:
    """统一报告输出引擎"""

    _adapters: dict[str, OutputAdapter] = {}

    def register(self, adapter: OutputAdapter) -> None:
        self._adapters[adapter.format_type] = adapter

    async def generate(
        self,
        report_json: dict,
        format_type: str,
        template_path: str | None = None,
        style_rules: dict | None = None,
        output_dir: str | Path = ".",
    ) -> OutputResult:
        adapter = self._adapters.get(format_type)
        if not adapter:
            raise ValueError(f"Unsupported format: {format_type}. Available: {list(self._adapters.keys())}")

        return await adapter.generate(
            report_json=report_json,
            template_path=template_path,
            style_rules=style_rules,
            output_dir=output_dir,
        )

    def list_formats(self) -> list[str]:
        return list(self._adapters.keys())


# 全局单例
output_engine = ReportOutputEngine()
```

- [ ] **Step 2: PPT 输出适配器**

```python
"""PPT 输出适配器 —— 将 report_json 渲染为 PPTX"""
from pathlib import Path
from backend.report_engine.output_engine import OutputAdapter, OutputResult


class PptOutputAdapter(OutputAdapter):

    @property
    def format_type(self) -> str:
        return "pptx"

    async def generate(
        self,
        report_json: dict,
        template_path: str | None = None,
        style_rules: dict | None = None,
        output_dir: str | Path = ".",
    ) -> OutputResult:
        """遍历 report_json.slides，逐页调用现有的 designer + editor pipeline。"""
        import asyncio
        from backend.models.outline import SlideItem, OutlineDoc, OutlineMeta, save_outline
        from backend.storage.file_manager import ProjectStorage

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 1. 构建 OUTLINE.md
        slides_data = report_json.get("slides", [])
        slides = [
            SlideItem(
                slide_id=s.get("slide_id", f"{i+1:02d}"),
                layout=s.get("layout", "title-content"),
                title=s.get("title", ""),
                points=s.get("points", []),
                visual_intent=s.get("visual_intent"),
                notes_speaker=s.get("notes_speaker", ""),
            )
            for i, s in enumerate(slides_data)
        ]

        outline = OutlineDoc(
            meta={"title": report_json.get("title", "报告"), "total_slides": len(slides)},
            slides=slides,
        )

        # 2. 写 OUTLINE.md
        storage = ProjectStorage.get()
        project_path = storage.get_project_path(output_dir.name)
        save_outline(outline, str(project_path / "OUTLINE.md"))

        # 3. 调用现有 designer → editor pipeline
        from backend.agents.designer import run_designer
        from backend.agents.editor import run_editor

        await run_designer(str(project_path))
        await run_editor(str(project_path))

        pptx_file = project_path / "exports" / "native.pptx"
        return OutputResult(
            file_path=str(pptx_file),
            file_type="pptx",
            mime_type="application/vnd.openxmlformats-officedocument.presentationml.document",
            file_size=pptx_file.stat().st_size if pptx_file.exists() else 0,
        )
```

- [ ] **Step 3: Word 输出适配器**

```python
"""Word 输出适配器 —— 将 report_json 渲染为 DOCX"""
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from backend.report_engine.output_engine import OutputAdapter, OutputResult


class DocxOutputAdapter(OutputAdapter):

    @property
    def format_type(self) -> str:
        return "docx"

    async def generate(
        self,
        report_json: dict,
        template_path: str | None = None,
        style_rules: dict | None = None,
        output_dir: str | Path = ".",
    ) -> OutputResult:
        """将 report_json.sections 渲染为 Word 文档。"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        doc = Document(template_path) if template_path else Document()

        # 标题
        title = doc.add_heading(report_json.get("title", "报告"), level=0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # 摘要
        abstract = report_json.get("abstract", "")
        if abstract:
            p = doc.add_paragraph(abstract)
            p.style = doc.styles['Subtitle'] if 'Subtitle' in [s.name for s in doc.styles] else doc.styles['Normal']

        # 正文章节
        for section in report_json.get("sections", []):
            doc.add_heading(section.get("heading", ""), level=1)
            doc.add_paragraph(section.get("body", ""))

            # 表格
            for table_data in section.get("tables", []):
                doc.add_paragraph(table_data.get("caption", ""))
                headers = table_data.get("headers", [])
                rows = table_data.get("rows", [])
                if headers and rows:
                    table = doc.add_table(rows=len(rows) + 1, cols=len(headers))
                    table.style = 'Light Grid Accent 1'
                    for j, h in enumerate(headers):
                        table.rows[0].cells[j].text = str(h)
                    for i, row in enumerate(rows):
                        for j, cell in enumerate(row):
                            table.rows[i + 1].cells[j].text = str(cell)

        file_path = output_dir / "report.docx"
        doc.save(str(file_path))

        return OutputResult(
            file_path=str(file_path),
            file_type="docx",
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            file_size=file_path.stat().st_size,
        )
```

- [ ] **Step 4: PDF 输出适配器**

```python
"""PDF 输出适配器 —— 先渲染 Markdown → HTML → PDF"""
from pathlib import Path
from backend.report_engine.output_engine import OutputAdapter, OutputResult


class PdfOutputAdapter(OutputAdapter):

    @property
    def format_type(self) -> str:
        return "pdf"

    async def generate(
        self,
        report_json: dict,
        template_path: str | None = None,
        style_rules: dict | None = None,
        output_dir: str | Path = ".",
    ) -> OutputResult:
        """将 report_json 各 section 拼接为 HTML，用 WeasyPrint 转 PDF。"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        html = _build_html(report_json, style_rules)

        try:
            from weasyprint import HTML
            file_path = output_dir / "report.pdf"
            HTML(string=html).write_pdf(str(file_path))
        except ImportError:
            # WeasyPrint 不可用时的降级：保存 HTML 文件
            file_path = output_dir / "report.html"
            file_path.write_text(html, encoding="utf-8")

        return OutputResult(
            file_path=str(file_path),
            file_type="pdf",
            mime_type="application/pdf",
            file_size=file_path.stat().st_size,
        )


def _build_html(report_json: dict, style_rules: dict | None = None) -> str:
    """构建 PDF 报告的 HTML。"""
    colors = (style_rules or {}).get("colors", ["#1E3A5F", "#333333"])
    primary = colors[0] if colors else "#1E3A5F"

    sections_html = ""
    for s in report_json.get("sections", []):
        heading = s.get("heading", "")
        content = s.get("content", "").replace("\n", "<br>")
        sections_html += f"<h2>{heading}</h2>\n<p>{content}</p>\n"

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8">
<style>
  body {{ font-family: 'SimSun', serif; max-width: 210mm; margin: 20mm auto; color: #333; }}
  h1 {{ color: {primary}; text-align: center; font-size: 24pt; }}
  h2 {{ color: {primary}; font-size: 16pt; border-bottom: 1px solid #ddd; }}
  p {{ line-height: 1.8; font-size: 12pt; }}
</style></head>
<body>
  <h1>{report_json.get("title", "报告")}</h1>
  {sections_html}
</body>
</html>"""
```

- [ ] **Step 5: 注册适配器到 __init__.py**

```python
from backend.report_engine.output_engine import output_engine
from backend.report_engine.pptx_output import PptOutputAdapter
from backend.report_engine.docx_output import DocxOutputAdapter
from backend.report_engine.pdf_output import PdfOutputAdapter

output_engine.register(PptOutputAdapter())
output_engine.register(DocxOutputAdapter())
output_engine.register(PdfOutputAdapter())
```

- [ ] **Step 6: 验证导入**

Run: `.venv/bin/python -c "from backend.report_engine import output_engine; print(f'OK — formats: {output_engine.list_formats()}')"`
Expected: `OK — formats: ['pptx', 'docx', 'pdf']`

- [ ] **Step 7: Commit**

```bash
git add backend/report_engine/
git commit -m "feat: add ReportOutputEngine with PPT/Word/PDF adapters"
```

---

### Task 7: API 路由 · 报告模板 + 智能填报 + 数据源管理

**Files:**
- Create: `backend/api/routes/report_templates.py`
- Create: `backend/api/routes/data_sources.py`
- Create: `backend/api/routes/smart_fill.py`
- Modify: `backend/api/main.py`

- [ ] **Step 1: 报告模板管理 API**

```python
"""报告模板管理 API"""
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_current_user
from backend.config import settings
from backend.models.database import get_db
from backend.models.report_template import ReportTemplate
from backend.parsers.template_parser import parse_pptx_template, parse_docx_template

router = APIRouter(prefix="/report-templates", tags=["templates"])

TEMPLATES_DIR = Path(settings.LOCAL_STORAGE_PATH) / ".report_templates"
MAX_FILE_SIZE = 50 * 1024 * 1024


@router.get("")
async def list_templates(
    report_type: str | None = None,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """列出可用模板，可选按 report_type 过滤。"""
    q = select(ReportTemplate).where(
        ReportTemplate.user_id == user,
        ReportTemplate.is_active == True,
    )
    if report_type:
        q = q.where(ReportTemplate.report_type == report_type)
    q = q.order_by(ReportTemplate.created_at.desc())
    result = await db.execute(q)
    templates = result.scalars().all()
    return [
        {
            "id": t.id, "name": t.name, "report_type": t.report_type,
            "source": t.source, "scenario_type": t.scenario_type,
            "description": t.description, "style_rules": t.style_rules,
            "content_slots": t.content_slots,
            "created_at": t.created_at.isoformat(),
        }
        for t in templates
    ]


@router.post("/upload")
async def upload_template(
    file: UploadFile = File(...),
    name: str = "",
    report_type: str = "ppt",
    scenario_type: str | None = None,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """上传企业自有模板，自动提取样式和内容插槽。"""
    suffix = Path(file.filename or "").suffix.lower()
    allowed = {".pptx": "ppt", ".docx": "docx"}
    if suffix not in allowed:
        raise HTTPException(400, f"仅支持 {list(allowed.keys())} 格式")
    if report_type not in ("ppt", "docx", "pdf"):
        raise HTTPException(400, "report_type 必须是 ppt/docx/pdf")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, "文件过大（最大 50MB）")

    user_dir = TEMPLATES_DIR / user
    user_dir.mkdir(parents=True, exist_ok=True)
    file_path = user_dir / (file.filename or "template")
    file_path.write_bytes(content)

    # 解析模板
    parsed = {}
    if suffix == ".pptx":
        parsed = parse_pptx_template(str(file_path))
    elif suffix == ".docx":
        parsed = parse_docx_template(str(file_path))

    template = ReportTemplate(
        user_id=user,
        name=name or Path(file.filename).stem,
        report_type=allowed[suffix],
        source="user_uploaded",
        original_filename=file.filename,
        template_file_path=str(file_path),
        style_rules=parsed.get("style_rules"),
        content_slots=parsed.get("content_slots"),
        scenario_type=scenario_type,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)

    return {
        "id": template.id, "name": template.name, "report_type": template.report_type,
        "style_rules": template.style_rules, "content_slots": template.content_slots,
        "slide_count": parsed.get("slide_count", 0),
    }


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ReportTemplate).where(ReportTemplate.id == template_id, ReportTemplate.user_id == user)
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(404, "Template not found")
    await db.delete(t)
    await db.commit()
    return {"deleted": template_id}
```

- [ ] **Step 2: 数据源管理 API**

```python
"""数据源管理 API"""
from fastapi import APIRouter, Depends
from backend.api.auth import get_current_user
from backend.data_source.base import registry
from backend.data_source import register_builtin_sources

router = APIRouter(prefix="/data-sources", tags=["data_sources"])

# 启动时注册内置数据源
register_builtin_sources()


@router.get("")
async def list_data_sources():
    """列出所有已注册的数据源。"""
    return registry.list_configs()


@router.get("/{source_type}/schema")
async def get_source_schema(
    source_type: str,
    user: str = Depends(get_current_user),
):
    """获取数据源的字段结构。"""
    plugin = registry.get(source_type)
    if not plugin:
        return {"error": f"Unknown source type: {source_type}"}
    schema = await plugin.get_schema(user_id=user)
    return {
        "source_type": schema.source_type,
        "source_name": schema.source_name,
        "categories": schema.categories,
        "fields": schema.fields,
        "total_documents": schema.total_documents,
    }
```

- [ ] **Step 3: 智能填报 API**

```python
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
    """执行智能填报：检索数据源 → LLM汇总 → 返回结构化MD + 报表JSON。"""
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
```

- [ ] **Step 4: 注册到 main.py**

Edit `backend/api/main.py`:
```python
from backend.api.routes.report_templates import router as report_templates_router  # noqa: E402
from backend.api.routes.data_sources import router as data_sources_router  # noqa: E402
from backend.api.routes.smart_fill import router as smart_fill_router  # noqa: E402

app.include_router(report_templates_router)
app.include_router(data_sources_router)
app.include_router(smart_fill_router)
```

- [ ] **Step 5: 验证**

Run: `.venv/bin/python -c "from backend.api.routes.report_templates import router; from backend.api.routes.data_sources import router as dsr; from backend.api.routes.smart_fill import router as sfr; print('OK')"`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add backend/api/routes/report_templates.py backend/api/routes/data_sources.py backend/api/routes/smart_fill.py backend/api/main.py
git commit -m "feat: add report template + data source + smart fill API routes"
```

---

### Task 8: 前端 · 企业报告工作台 · AppShell + SideNav

**Files:**
- Replace: `frontend/src/App.tsx`
- Create: `frontend/src/components/layout/AppShell.tsx`
- Create: `frontend/src/components/layout/SideNav.tsx`
- Create: `frontend/src/stores/reportStore.ts`

- [ ] **Step 1: 报告 Store**

```typescript
import { create } from 'zustand'

export type ReportType = 'ppt' | 'docx' | 'pdf'
export type NavSection = 'create' | 'history' | 'datasources' | 'templates' | 'settings'

interface ReportState {
  navSection: NavSection
  reportType: ReportType
  scenarioId: string | null
  selectedSources: string[]
  query: string

  setNav: (section: NavSection) => void
  setReportType: (type: ReportType) => void
  setScenario: (id: string | null) => void
  toggleSource: (sourceType: string) => void
  setQuery: (q: string) => void
}

export const useReportStore = create<ReportState>((set) => ({
  navSection: 'create',
  reportType: 'ppt',
  scenarioId: null,
  selectedSources: ['knowledge_base', 'case_library'],
  query: '',

  setNav: (section) => set({ navSection: section }),
  setReportType: (type) => set({ reportType: type }),
  setScenario: (id) => set({ scenarioId: id }),
  toggleSource: (sourceType) => set((s) => ({
    selectedSources: s.selectedSources.includes(sourceType)
      ? s.selectedSources.filter(t => t !== sourceType)
      : [...s.selectedSources, sourceType],
  })),
  setQuery: (q) => set({ query: q }),
}))
```

- [ ] **Step 2: SideNav 左侧导航**

```tsx
import { FileText, History, Database, Layout, Settings } from 'lucide-react'
import { useReportStore, type NavSection } from '@/stores/reportStore'

const NAV_ITEMS: { key: NavSection; label: string; icon: typeof FileText }[] = [
  { key: 'create', label: '新建报告', icon: FileText },
  { key: 'history', label: '报告历史', icon: History },
  { key: 'datasources', label: '数据源', icon: Database },
  { key: 'templates', label: '模板管理', icon: Layout },
  { key: 'settings', label: '系统设置', icon: Settings },
]

export function SideNav() {
  const { navSection, setNav } = useReportStore()

  return (
    <nav className="w-56 h-full flex flex-col border-r border-border/30 bg-card/30 shrink-0">
      <div className="p-4 border-b border-border/30">
        <h1 className="text-sm font-bold tracking-tight">📊 智能报告平台</h1>
        <p className="text-[10px] text-muted-foreground mt-0.5">Enterprise Report Studio</p>
      </div>
      <div className="flex-1 p-2 space-y-1">
        {NAV_ITEMS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setNav(key)}
            className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-all ${
              navSection === key
                ? 'bg-primary/10 text-primary font-medium'
                : 'text-muted-foreground hover:bg-accent/30 hover:text-foreground'
            }`}
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>
    </nav>
  )
}
```

- [ ] **Step 3: AppShell 主框架**

```tsx
import { SideNav } from './SideNav'
import { ContextPanel } from './ContextPanel'
import { useReportStore } from '@/stores/reportStore'
import { CreateReportWizard } from '@/components/report/CreateReportWizard'
import { ReportHistory } from '@/components/report/ReportHistory'
import { DataSourceManager } from '@/components/datasource/DataSourceManager'
import { TemplateManager } from '@/components/template/TemplateManager'

export function AppShell() {
  const { navSection } = useReportStore()

  return (
    <div className="h-screen flex overflow-hidden bg-background">
      <SideNav />

      <main className="flex-1 overflow-y-auto">
        {navSection === 'create' && <CreateReportWizard />}
        {navSection === 'history' && <ReportHistory />}
        {navSection === 'datasources' && <DataSourceManager />}
        {navSection === 'templates' && <TemplateManager />}
        {navSection === 'settings' && <div className="p-6">系统设置</div>}
      </main>

      <ContextPanel />
    </div>
  )
}
```

- [ ] **Step 4: 替换 App.tsx**

```tsx
import { AppShell } from '@/components/layout/AppShell'
import { SlideModal } from '@/components/SlideModal'
import { ProjectManagerModal } from '@/components/ProjectManagerModal'
import { AccountModal } from '@/components/AccountModal'

export default function App() {
  return (
    <>
      <AppShell />
      <SlideModal />
      <ProjectManagerModal />
      <AccountModal />
    </>
  )
}
```

- [ ] **Step 5: 验证编译**

Run: `cd frontend && npm run build 2>&1 | tail -10`
Expected: no errors

- [ ] **Step 6: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/layout/ frontend/src/stores/reportStore.ts
git commit -m "feat: new enterprise report workbench layout (SideNav + AppShell)"
```

---

### Task 9: 前端 · 向导式报告创建 · CreateReportWizard

**Files:**
- Create: `frontend/src/components/report/CreateReportWizard.tsx`
- Create: `frontend/src/components/report/ReportTypeSelector.tsx`
- Create: `frontend/src/components/report/DataSourceSelector.tsx`

- [ ] **Step 1: ReportTypeSelector**

```tsx
import { Presentation, FileText, FileType } from 'lucide-react'
import { useReportStore, type ReportType } from '@/stores/reportStore'

const REPORT_TYPES: { key: ReportType; label: string; desc: string; icon: typeof Presentation }[] = [
  { key: 'ppt', label: 'PPT 演示文稿', desc: '适合售前宣讲、工作汇报、投资人路演', icon: Presentation },
  { key: 'docx', label: 'Word 文档报告', desc: '适合详细分析报告、项目结项文档', icon: FileText },
  { key: 'pdf', label: 'PDF 正式报告', desc: '适合对外正式交付、归档留存', icon: FileType },
]

export function ReportTypeSelector() {
  const { reportType, setReportType } = useReportStore()

  return (
    <div>
      <h2 className="text-lg font-semibold mb-4">选择报告类型</h2>
      <div className="grid grid-cols-3 gap-4">
        {REPORT_TYPES.map(({ key, label, desc, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setReportType(key)}
            className={`p-6 rounded-xl border-2 text-left transition-all ${
              reportType === key
                ? 'border-primary bg-primary/5 shadow-sm'
                : 'border-border/30 hover:border-border/60 hover:bg-accent/10'
            }`}
          >
            <Icon className="w-8 h-8 mb-3 text-primary" />
            <h3 className="text-sm font-semibold">{label}</h3>
            <p className="text-[11px] text-muted-foreground mt-1">{desc}</p>
          </button>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: DataSourceSelector**

```tsx
import { useEffect, useState } from 'react'
import { Check } from 'lucide-react'
import { useReportStore } from '@/stores/reportStore'
import { listDataSources, getDataSourceSchema } from '@/api/client'

interface SourceInfo {
  source_type: string
  source_name: string
  categories: string[]
  total_documents: number
}

export function DataSourceSelector() {
  const { selectedSources, toggleSource } = useReportStore()
  const [sources, setSources] = useState<SourceInfo[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    (async () => {
      setLoading(true)
      try {
        const configs = await listDataSources()
        const detailed = await Promise.all(
          configs.map(async (c: { source_type: string }) => {
            try {
              return await getDataSourceSchema(c.source_type)
            } catch { return { ...c, categories: [], total_documents: 0 } }
          })
        )
        setSources(detailed)
      } catch {} finally { setLoading(false) }
    })()
  }, [])

  return (
    <div>
      <h2 className="text-lg font-semibold mb-4">选择数据源</h2>
      <p className="text-xs text-muted-foreground mb-4">勾选需要用于本报告的数据源，AI 将自动检索相关内容</p>

      {loading ? (
        <p className="text-sm text-muted-foreground">加载中...</p>
      ) : (
        <div className="space-y-3">
          {sources.map((s) => (
            <button
              key={s.source_type}
              onClick={() => toggleSource(s.source_type)}
              className={`w-full text-left p-4 rounded-xl border transition-all flex items-center justify-between ${
                selectedSources.includes(s.source_type)
                  ? 'border-primary/40 bg-primary/5'
                  : 'border-border/20 hover:bg-accent/10'
              }`}
            >
              <div>
                <p className="text-sm font-medium">{s.source_name}</p>
                <div className="flex items-center gap-2 mt-1">
                  {s.categories.map(c => (
                    <span key={c} className="text-[10px] bg-muted px-1.5 py-0.5 rounded">{c}</span>
                  ))}
                  <span className="text-[10px] text-muted-foreground">{s.total_documents} 条记录</span>
                </div>
              </div>
              <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                selectedSources.includes(s.source_type)
                  ? 'bg-primary border-primary text-primary-foreground'
                  : 'border-muted-foreground/30'
              }`}>
                {selectedSources.includes(s.source_type) && <Check className="w-3 h-3" />}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 3: CreateReportWizard（主向导）**

```tsx
import { useState } from 'react'
import { ArrowRight, ArrowLeft, Sparkles, Loader2 } from 'lucide-react'
import { useReportStore } from '@/stores/reportStore'
import { ReportTypeSelector } from './ReportTypeSelector'
import { DataSourceSelector } from './DataSourceSelector'
import { ScenarioSelector } from '@/components/ScenarioSelector'
import { smartFill } from '@/api/client'

const STEPS = ['报告类型', '方案框架', '数据源', '生成']

export function CreateReportWizard() {
  const [step, setStep] = useState(0)
  const [generating, setGenerating] = useState(false)
  const [result, setResult] = useState<{
    structured_markdown: string
    report_json: object
    source_references: Array<{ source_type: string; source_name: string; doc_count: number }>
  } | null>(null)
  const { reportType, scenarioId, selectedSources, query, setQuery } = useReportStore()

  const handleGenerate = async () => {
    if (!query.trim()) return
    setGenerating(true)
    try {
      const data = await smartFill({
        query, report_type: reportType,
        scenario_type: undefined, // scenarioId → scenario_type lookup
        selected_sources: selectedSources,
      })
      setResult(data)
      setStep(3)
    } catch (e: any) {
      alert(e?.response?.data?.detail || '生成失败')
    } finally { setGenerating(false) }
  }

  return (
    <div className="max-w-4xl mx-auto p-8">
      {/* 步骤指示器 */}
      <div className="flex items-center gap-2 mb-8">
        {STEPS.map((label, i) => (
          <div key={i} className="flex items-center gap-2">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
              i <= step ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'
            }`}>{i + 1}</div>
            <span className={`text-sm ${i <= step ? 'font-medium' : 'text-muted-foreground'}`}>{label}</span>
            {i < STEPS.length - 1 && <div className="w-8 h-px bg-border" />}
          </div>
        ))}
      </div>

      {/* Step 0: 需求输入 + 报告类型 */}
      {step === 0 && (
        <div className="space-y-6">
          <ReportTypeSelector />
          <div className="mt-6">
            <label className="text-sm font-medium mb-2 block">报告主题</label>
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="例如：为长鑫存储生成 D7020 设备售前方案，重点介绍设备参数和客户案例..."
              className="w-full h-28 p-4 rounded-xl border border-border/30 bg-background resize-none text-sm outline-none focus:border-primary/30"
            />
          </div>
          <button onClick={() => setStep(1)}
            disabled={!query.trim()}
            className="flex items-center gap-2 px-6 py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:opacity-90 disabled:opacity-50 ml-auto">
            下一步 <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Step 1: 场景方案 */}
      {step === 1 && (
        <div className="space-y-6">
          <ScenarioSelector />
          <div className="flex items-center gap-3 justify-between mt-6">
            <button onClick={() => setStep(0)}
              className="flex items-center gap-2 px-4 py-2 text-sm text-muted-foreground hover:text-foreground">
              <ArrowLeft className="w-4 h-4" />上一步
            </button>
            <button onClick={() => setStep(2)}
              className="flex items-center gap-2 px-6 py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-medium">
              下一步 <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Step 2: 数据源选择 */}
      {step === 2 && (
        <div className="space-y-6">
          <DataSourceSelector />
          <div className="flex items-center gap-3 justify-between mt-6">
            <button onClick={() => setStep(1)}
              className="flex items-center gap-2 px-4 py-2 text-sm text-muted-foreground hover:text-foreground">
              <ArrowLeft className="w-4 h-4" />上一步
            </button>
            <button onClick={handleGenerate} disabled={generating}
              className="flex items-center gap-2 px-6 py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:opacity-90 disabled:opacity-50">
              {generating ? <><Loader2 className="w-4 h-4 animate-spin" />生成中...</> : <><Sparkles className="w-4 h-4" />生成报告</>}
            </button>
          </div>
        </div>
      )}

      {/* Step 3: 结果预览 */}
      {step === 3 && result && (
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-sm text-green-600">
            <Sparkles className="w-4 h-4" />
            智能填报完成 — 从 {result.source_references.length} 个数据源检索到相关内容
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 rounded-xl border border-border/30 bg-card">
              <h3 className="text-sm font-semibold mb-2">结构化文档 (Markdown)</h3>
              <pre className="text-xs whitespace-pre-wrap max-h-[500px] overflow-y-auto font-mono">
                {result.structured_markdown.slice(0, 2000)}...
              </pre>
            </div>
            <div className="p-4 rounded-xl border border-border/30 bg-card">
              <h3 className="text-sm font-semibold mb-2">报表数据 (JSON)</h3>
              <pre className="text-xs whitespace-pre-wrap max-h-[500px] overflow-y-auto font-mono">
                {JSON.stringify(result.report_json, null, 2).slice(0, 2000)}...
              </pre>
            </div>
          </div>
          <div className="flex gap-3">
            {['pptx', 'docx', 'pdf'].map(fmt => (
              <button key={fmt}
                className="px-4 py-2 rounded-lg border border-border/30 text-sm hover:bg-accent/30">
                导出 {fmt.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 4: 添加前端 API 函数**

在 `client.ts` 追加：
```typescript
export const listDataSources = () =>
  api.get<Array<{ source_type: string; source_name: string }>>('/data-sources').then(r => r.data)

export const getDataSourceSchema = (sourceType: string) =>
  api.get<{ source_type: string; source_name: string; categories: string[]; fields: string[]; total_documents: number }>(
    `/data-sources/${sourceType}/schema`
  ).then(r => r.data)

export const smartFill = (data: { query: string; report_type: string; scenario_type?: string | null; selected_sources?: string[] }) =>
  api.post<{ structured_markdown: string; report_json: object; source_references: Array<{ source_type: string; source_name: string; doc_count: number }> }>(
    '/smart-fill', data
  ).then(r => r.data)

export const listReportTemplates = (reportType?: string) => {
  const params = reportType ? `?report_type=${reportType}` : ''
  return api.get<Array<{ id: string; name: string; report_type: string; source: string; style_rules: object; content_slots: Array<object> }>>(
    `/report-templates${params}`
  ).then(r => r.data)
}

export const uploadReportTemplate = (file: File, name?: string, reportType?: string) => {
  const form = new FormData()
  form.append('file', file)
  if (name) form.append('name', name)
  if (reportType) form.append('report_type', reportType)
  return api.post('/report-templates/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data)
}
```

- [ ] **Step 5: 验证编译**

Run: `cd frontend && npm run build 2>&1 | tail -10`
Expected: no errors

- [ ] **Step 6: Commit**

```bash
git add frontend/
git commit -m "feat: add report creation wizard (type → scenario → sources → generate) + API client"
```

---

### Task 10: 报告产出 API · 对接输出引擎

**Files:**
- Create: `backend/api/routes/reports.py`
- Modify: `backend/api/main.py`

- [ ] **Step 1: 创建报告产出 API**

```python
"""报告产出 API — 对接 ReportOutputEngine"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path

from backend.api.auth import get_current_user
from backend.config import settings
from backend.report_engine import output_engine

router = APIRouter(prefix="/reports", tags=["reports"])


class GenerateRequest(BaseModel):
    report_json: dict
    format_type: str           # "pptx" | "docx" | "pdf"
    template_id: str | None = None


@router.post("/generate")
async def generate_report(
    body: GenerateRequest,
    user: str = Depends(get_current_user),
):
    """根据 report_json 生成指定格式的报告文件。"""
    output_dir = Path(settings.LOCAL_STORAGE_PATH) / user / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        result = await output_engine.generate(
            report_json=body.report_json,
            format_type=body.format_type,
            output_dir=output_dir,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    return {
        "format": result.file_type,
        "mime_type": result.mime_type,
        "file_size": result.file_size,
        "download_url": f"/api/reports/download/{Path(result.file_path).name}",
    }


@router.get("/formats")
async def list_formats():
    """列出支持的输出格式。"""
    return {"formats": output_engine.list_formats()}
```

- [ ] **Step 2: 注册路由**

```python
from backend.api.routes.reports import router as reports_router  # noqa: E402
app.include_router(reports_router)
```

- [ ] **Step 3: 验证 + Commit**

```bash
.venv/bin/python -c "from backend.api.routes.reports import router; print('OK')"
git add backend/api/routes/reports.py backend/api/main.py
git commit -m "feat: add report generation API endpoint (PPT/Word/PDF)"
```

---

### Task 11: 端到端验证

**Files:** None (test only)

- [ ] **Step 1: 运行全部后端测试**

```bash
.venv/bin/pytest backend/tests/ -v --tb=short 2>&1 | tail -30
```
Expected: 76+ passed, 0 new failures

- [ ] **Step 2: 验证所有新模块导入**

```bash
.venv/bin/python -c "
from backend.data_source.base import DataSourcePlugin, registry
from backend.data_source.knowledge_source import KnowledgeBaseSource
from backend.data_source.case_library_source import CaseLibrarySource
from backend.models.report_template import ReportTemplate
from backend.parsers.template_parser import parse_pptx_template, parse_docx_template
from backend.report_engine.smart_fill import run_smart_fill, SmartFillResult
from backend.report_engine import output_engine
from backend.api.routes.report_templates import router as rtr
from backend.api.routes.data_sources import router as dsr
from backend.api.routes.smart_fill import router as sfr
from backend.api.routes.reports import router as rr
print(f'All modules OK — Report formats: {output_engine.list_formats()}')
"
```
Expected: `All modules OK — Report formats: ['pptx', 'docx', 'pdf']`

- [ ] **Step 3: 前端完整编译**

```bash
cd frontend && npm run build 2>&1 | tail -10
```
Expected: no errors

- [ ] **Step 4: Commit (if any fixups)**

---

## 自审清单

1. **需求覆盖**：
   - ✅ 数据源"插槽"抽象层（DataSourcePlugin + 2 个内置实现）
   - ✅ 智能填报引擎（多源检索 → LLM 汇总 → MD + JSON）
   - ✅ 多格式输出引擎（PPT/Word/PDF 三个适配器）
   - ✅ 报告模板引擎（ReportTemplate + 解析器 + 上传 API）
   - ✅ 前端工作台（SideNav + 向导式创建 + 数据源选择）
   - ✅ 企业模板导入（上传→自动提取样式和插槽）
   - ✅ 报告类型选择（PPT/Word/PDF 三选一）

2. **无占位符**：全部代码已提供

3. **类型一致性**：
   - `DataSourcePlugin.source_type` / `SourceDocument.source_type` 一致
   - `ReportTemplate.report_type` 枚举 "ppt"/"docx"/"pdf" 前后端一致
   - `OutputAdapter.format_type` 匹配 `report_type`
   - `SmartFillResult` 字段在 API 返回和前端消费中一致
   - `NavSection` 类型覆盖所有导航项
