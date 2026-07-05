# 智能报告应用 · 设计规格书

> 版本: v1.0  
> 日期: 2026-07-05  
> 状态: 设计完成，待用户确认

---

## 1. 项目概述

### 1.1 项目定位

在喔壳(WorkoPilot)平台内构建一个嵌入式的企业智能报告应用，支持多数据源接入、智能意图识别、丰富模板匹配、结构化内容确认编辑、多格式报告导出。

### 1.2 喔壳集成形态 — 混合形态

- **数字员工**："智能报告助手"，对话式交互入口，通过 iframe 技能卡片展示报告编辑工作台，面向终端用户
- **AI 服务**：核心报告能力封装为喔壳 AI 服务（API），供 CRM/ERP 等外部系统调用
- 两层共享同一套自建报告引擎（FastAPI 后端）

### 1.3 核心决策记录

| 决策项 | 结论 |
|--------|------|
| 代码基础 | **从头构建**，PPtX 生成集成方案后续由用户指定 |
| 数据源优先级 | **三阶段**：Phase1 文件+聊天+企业PPT库 → Phase2 MCP+API → Phase3 DB+RAG |
| 模板策略 | **精选模板(8-12种) + 元模板(5-6种)**，兼顾质量和扩展性 |
| 内容确认 | **混合式**：大纲树(拖拽)+ Markdown预览(内联编辑)+ Chat指令(自然语言) |
| PPTX 生成 | **模板驱动默认**（企业PPT库模板），设计引擎仅用户显式指定的兜底方案 |
| 企业 PPT 库 | **双重角色**：内容资产（Slide级复用）+ 样式模板（Deck级基准） |

---

## 2. 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      喔壳平台层                              │
│                                                              │
│  ┌──────────────────────┐    ┌───────────────────────────┐  │
│  │ 数字员工              │    │ AI 服务（Open API）        │  │
│  │ "智能报告助手"        │    │ 供CRM/ERP等系统直接调用    │  │
│  │ MCP/附件提取/计费     │    │                           │  │
│  └──────────┬───────────┘    └─────────────┬─────────────┘  │
│             │ showCard                     │                 │
│             ▼                              │                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Iframe 技能卡片 — 智能报告工作台               │   │
│  │  大纲导航(树形) + Markdown预览(实时) + Chat指令面板   │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │ HTTP/SSE                           │
├─────────────────────────┼───────────────────────────────────┤
│                         ▼                                    │
│                自建后端 — FastAPI                              │
│                                                              │
│  ┌──────────┐  ┌──────────────┐  ┌─────────────────────┐   │
│  │ 数据源层  │  │  智能填报引擎  │  │   报告输出引擎       │   │
│  │          │  │              │  │                     │   │
│  │ 文档上传 │→│ 意图识别     │→│ Word (python-docx)  │   │
│  │ 聊天记录 │  │ 模板匹配     │  │ PDF (WeasyPrint)    │   │
│  │ 企业PPT库│  │ 内容提取     │  │ HTML脑图(Markmap)   │   │
│  │ MCP/API  │  │ 结构化填充   │  │ PPTX(后续指定)      │   │
│  └──────────┘  └──────────────┘  └─────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │       报告模板库（元模板 5-6 + 精选模板 8-12）         │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 核心数据流

### 3.1 完整流程

```
客户输入 → 数据源上传 → 附件提取/解析 → SourceDocument[]
  → 意图识别(LLM) → ReportIntent
  → 模板匹配 → ReportTemplate (精选匹配优先，元模板派生兜底)
  → 智能填报(LLM并行) → StructuredReport
  → [企业PPT库Slide匹配] → Slide引用标记
  → iframe卡片三区确认编辑 → ConfirmedReport
  → 多格式导出 → Word/PDF/HTML脑图/PPTX
```

### 3.2 企业 PPT 库的双重角色在流程中的体现

| 环节 | 作用 |
|------|------|
| 数据源层 | PPT 上传后自动解析为 SlideAsset 索引 + 模板风格指纹 |
| 智能填报 | 模板中 `source=enterprise_ppt` 的 section 自动检索匹配，复用 Slide |
| 内容确认 | 用户可浏览企业PPT库手动选择 Slide，可指定/上传 PPT 模板 |
| PPTX 导出 | 模板驱动生成：Section 按来源分"复用 Slide"和"模板布局+新建内容"两条路径，设计引擎仅用户显式"不使用模板"时启用 |

---

## 4. 统一领域模型

### 4.1 SourceDocument

```python
@dataclass
class SourceDocument:
    source_id: str
    source_type: str          # "file_upload" | "chat_export" | "enterprise_ppt" | "mcp" | "api" | "database" | "knowledge_base"
    title: str
    content: str              # Markdown
    metadata: dict            # {author, date, department, tags, ...}
    tables: list[list[list]]
    entities: list[dict]      # NER [{name, type, value}, ...]
```

### 4.2 ReportTemplate

```python
@dataclass
class ReportTemplate:
    template_id: str
    name: str
    category: str             # "指标类" | "进度类" | "分析类" | "总结类" | "评估类"
    parent_meta: str | None   # 派生来源元模板ID
    description: str
    sections: list[SectionDef]
    suggested_charts: list[str]
    system_prompt: str

@dataclass
class SectionDef:
    key: str
    title: str
    required: bool
    description: str
    source: str               # "generated" | "enterprise_ppt"
    match_keywords: list[str] # source=enterprise_ppt 时的匹配关键词
    max_matches: int
    fallback: str             # "generated" | None
    subsections: list[SectionDef]
    suggested_length: str     # "short" | "medium" | "long"
```

### 4.3 StructuredReport

```python
@dataclass
class StructuredReport:
    report_id: str
    template_id: str
    title: str
    generated_at: datetime
    meta: ReportMeta
    sections: list[ReportSection]
    data_sources: list[str]
    key_metrics: dict

@dataclass
class ReportSection:
    key: str
    title: str
    content: str              # Markdown
    confidence: float         # 0-1
    source_refs: list[str]
    slide_refs: list[SlideRef]  # 企业PPT库引用
    children: list[ReportSection]
    status: str               # "draft" | "confirmed" | "modified"

@dataclass
class SlideRef:
    slide_id: str
    deck_id: str
    deck_name: str
    slide_index: int
    match_score: float
    accepted: bool
```

### 4.4 企业 PPT 库

```python
@dataclass
class ContentDeck:
    deck_id: str
    filename: str
    category: str
    slides: list[SlideAsset]

@dataclass
class SlideAsset:
    slide_id: str
    deck_id: str
    slide_index: int
    title: str
    content_summary: str
    section_type: str         # "cover" | "toc" | "content" | "chart" | "ending"
    topic_tags: list[str]
    has_chart: bool
    has_table: bool
    thumbnail_path: str

@dataclass
class TemplateDeck:
    deck_id: str
    filename: str
    name: str
    is_default: bool
    style_profile: StyleProfile
    slide_layouts: list[LayoutInfo]

@dataclass
class StyleProfile:
    color_scheme: list[str]
    font_family: str
    title_font_size: str
    body_font_size: str
    has_logo_on_each_page: bool
    logo_position: str
    background_style: str
```

---

## 5. 模块详细设计

### 5.1 数据源适配器层

**Phase 1 适配器：**

| 适配器 | 输入 | 处理 |
|--------|------|------|
| 文件上传 | .docx/.pdf/.xlsx/.txt/.png | PyMuPDF/python-docx 提取 → Markdown；图片走 Vision-Language；Excel 保留表格 |
| 聊天记录 | 微信/企业微信/钉钉导出 | 正则解析时间戳→结构化JSON→按主题分段Markdown |
| 企业PPT库 | .pptx 上传 | python-pptx解析→LLM逐页摘要+标签→SlideAsset索引+StyleProfile提取 |

**Phase 2/3 适配器：** MCP接入、REST API、数据库直连、RAG知识库（详见后述）

**设计要点：**
- 适配器注册机制 `DataSourceRegistry`，装饰器注册
- 喔壳附件提取（合同/发票/简历等结构化文档）为前置，自建适配器处理非结构化文本
- 多源合并按 `metadata.date` 排序，`metadata.department` 分组

### 5.2 报告模板库

**两层体系：**

**元模板（5-6种）：** 指标类 / 进度类 / 分析类 / 总结类 / 评估类

**精选模板（Phase1 6种 → Phase2 12种）：**
- 员工KPI报告 / 部门绩效报告
- 销售日报 / 业务周报 / 运营月报
- 项目进度报告 / 销售业绩报告 / 客户分析报告
- 市场调研报告 / 财务简报 / 会议纪要 / 产品行业解决方案

**模板推荐流程：**
```
用户输入 → LLM意图识别(提取:领域/类型/周期/范围) → 关键词+语义匹配 → 
候选模板列表(精选优先→元模板派生兜底) → 用户选择 → 按需微调Section
```

### 5.3 智能填报引擎

**四步流水线：**

1. **多源汇总**：LLM 跨文档去重、关联、时间线整理
2. **逐节并行填充**：每个 SectionDef 独立 LLM 调用（无依赖章节并行），提示词包含模板定义+数据源+章节要求
3. **全局一致性校验**：单次 LLM 扫描全文，检查数字/日期/术语一致性
4. **企业PPT库匹配**：`source=enterprise_ppt` 的 Section 检索 SlideAsset，threshold≥0.85 推荐复用

**关键规则：**
- 数据必须来自数据源，不得编造；数据不足时标注 `[数据不足]`
- 每节标记 `confidence` 和 `source_refs`，低置信度段落前端高亮
- Slide 匹配失败时按 `fallback` 策略处理（LLM生成或跳过）

### 5.4 内容确认与编辑（Iframe 技能卡片）

**三栏布局：**
- **左侧**：大纲树 — 展开/折叠、拖拽排序、右键操作
- **中间**：Markdown 预览 — 实时渲染、内联编辑、低置信度高亮
- **右侧**：Chat 指令面板 — 自然语言修改、历史指令记录

**三区联动机制：**
| 操作 | 大纲树 | Markdown预览 | Chat |
|------|--------|-------------|------|
| 点击大纲节点 | 高亮 | 滚动到对应位置 | — |
| 拖拽大纲节点 | 重排序 | 内容同步重排 | 追加确认消息 |
| 点击预览段落 | 对应节点高亮 | 可编辑浮层 | — |
| Chat 自然语言指令 | 执行后更新 | 执行后更新 | 显示指令和结果 |
| 低置信度段落 | 节点标记⚠ | 段落黄色高亮 | 自动提示建议 |

**Chat 指令类型：** add_section / delete_section / move_section / rewrite / expand / summarize / add_data / fix_style

**交互规则：**
- 选中即上下文：选中段落自动带入 Chat 上下文
- 撤销栈：所有修改入栈，Cmd+Z 全局撤销
- 差异高亮：Chat 指令执行后修改内容短暂高亮 3 秒
- 确认门：显式点击"确认报告"后进入导出阶段，不可再编辑

**模板/PPT库选择入口：**
- 大纲底部 `[+ 添加章节]` 和 `[🏢 从企业PPT库引用Slide]`
- 顶部 `[选择PPT模板▼]` 下拉，含推荐/默认/自定义上传
- 企业PPT库浏览器：Deck列表→Slide网格→选中→确认

### 5.5 报告输出引擎

| 格式 | 技术 | 逻辑 |
|------|------|------|
| Word | python-docx | Markdown→段落/表格/列表/TOC，默认样式（微软雅黑），后续支持自定义Word模板 |
| PDF | WeasyPrint | Markdown→Jinja2 HTML模板→CSS打印样式→PDF |
| HTML脑图 | Markmap(D3.js) | StructuredReport→Markdown大纲树→可交互脑图，节点展开/折叠/缩放 |
| PPTX | 后续指定 | 模板驱动默认（企业PPT库模板+Slide复用），设计引擎兜底 |

**统一接口：** `ReportOutputEngine.export(report, format, options, ppt_template_id?) → ExportResult`

### 5.6 喔壳集成层

**集成清单：**

| 步骤 | 喔壳能力 | 用途 |
|------|---------|------|
| 创建数字员工 | `create_digital_employee.py` | "智能报告助手" — MCP/知识库/技能卡片配置 |
| 注册 iframe 卡片 | `register_iframe_card.py` | 报告编辑主卡片 + PPT模板选择器 + 企业PPT库浏览器 |
| 配置附件分类 | `create_attachment_classification.py` | 销售数据/聊天记录/KPI数据提取规则 |
| 封装 AI 服务 | `create_ai_service.py` | 意图识别/报告生成/Slide匹配 供外部调用 |
| 会话管理 | `POST /api/ai/open/chat/session` | 用户报告会话 |
| 消息发送 | `POST /api/ai/open/chat/send` (SSE) | 对话交互 + showCard 触发 |
| 文件提取 | `POST /api/attachment/extract` | 喔壳Vision-Language解析上传文件 |
| 计费集成 | MCP/卡片中触发 | report_generate(5 units) + report_export(2 units) |

**安全：** API-KEY 服务端环境变量，不暴露前端；iframe 卡片生产环境 HTTPS；计费防止成本失控

### 5.7 PPTX 生成决策逻辑

```
PPTX导出请求
  ├─ 客户指定"不使用模板" → 设计引擎生成（兜底路径）
  └─ 默认 → 模板驱动生成
       ├─ 客户指定模板 → 使用指定模板
       ├─ 未指定但有默认模板 → 使用默认模板
       ├─ 系统智能推荐 → 客户确认候选
       └─ 无可用模板 → 提示上传 或 走设计引擎
              │
              ▼
       逐 Section 渲染：
       ├─ source=enterprise_ppt → 复制企业PPT库Slide（可选继承模板字体/颜色）
       └─ source=generated → 模板Layout + python-pptx填充文本/图表
```

---

## 6. API 设计

### 6.1 基础约定

```
Base URL: https://your-domain.com/api/v1
Content-Type: application/json
Auth: Bearer {JWT}
统一响应: { "code": 200, "msg": "success", "data": {...} }
```

### 6.2 路由全景

```
/api/v1/
├── health/                        GET  /
├── datasources/                   POST /upload          GET /  GET|DELETE /{id}  GET /{id}/preview
├── enterprise-ppt/                POST /upload          GET /decks  GET|DELETE|PUT /decks/{id}
│                                  GET /slides/{id}      GET /slides/search      GET /templates
├── reports/                       POST /intent          POST /generate(SSE)
│                                  GET|PUT|DELETE /{id}  PATCH /{id}/section/{key}
│                                  POST /{id}/chat-command(SSE)   POST /{id}/confirm
├── templates/                     GET /                 GET /{id}               GET /recommend
├── export/                        POST /{report_id}/export   GET /tasks/{task_id}
└── ppt-template/                  GET /recommend        POST /select             POST /upload-custom
```

### 6.3 核心接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/reports/intent` | POST | 意图识别+模板推荐，返回 ReportIntent + 候选模板 + PPT模板建议 |
| `/reports/generate` | POST | SSE 流式生成报告，逐节推送 + Slide 匹配结果 |
| `/reports/{id}/chat-command` | POST | SSE 返回章节更新，Chat 自然语言→结构化操作 |
| `/reports/{id}/confirm` | POST | 确认报告，触发计费 |
| `/reports/{id}/export` | POST | 多格式导出，返回 task_id |

---

## 7. 项目结构

```
smart_reporting/
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── api/
│   │   ├── deps.py
│   │   └── routes/               # health, datasources, enterprise_ppt, templates, reports, export, ppt_template
│   ├── core/
│   │   ├── models.py
│   │   ├── datasource/           # base + registry + 各适配器 (file_upload, chat_export, enterprise_ppt, ...)
│   │   ├── engine/               # intent, template_matcher, summarizer, filler, validator, slide_matcher
│   │   ├── output/               # base + docx_exporter, pdf_exporter, mindmap_exporter, pptx_exporter
│   │   └── llm/                  # client, prompts
│   ├── storage/                  # database, file_store, ORM models
│   ├── workopilot/               # client, auth, billing, configs
│   └── tests/
├── frontend/
│   └── src/
│       ├── api/client.ts
│       ├── stores/               # reportStore, pptLibraryStore (Zustand)
│       ├── components/
│       │   ├── layout/ReportWorkspace.tsx     # 三栏布局
│       │   ├── outline/OutlineTree.tsx        # 大纲树
│       │   ├── preview/MarkdownPreview.tsx    # Markdown预览
│       │   ├── chat/ChatPanel.tsx             # Chat指令面板
│       │   ├── ppt-library/                   # 企业PPT库浏览器
│       │   ├── ppt-template/PPTTemplateSelector.tsx
│       │   ├── datasource/DataSourceUploader.tsx
│       │   ├── intent/IntentResult.tsx
│       │   ├── export/ExportPanel.tsx
│       │   └── ui/                            # 通用组件
│       ├── hooks/                # useSSE, useReportEditor, useUndo
│       └── utils/postMessage.ts  # 喔壳iframe通信
└── docs/
    └── superpowers/specs/2026-07-05-smart-reporting-design.md
```

---

## 8. MVP 阶段规划

### Phase 1 · 核心可用 (6-8 周)

| # | 模块 | 估时 |
|---|------|------|
| 1.1 | 项目初始化（FastAPI + Vite + DB + LLM客户端） | 3d |
| 1.2 | 报告模板库（5元模板 + 6精选模板 + API） | 3d |
| 1.3 | 数据源 — 文件上传（Word/PDF/Excel/TXT解析） | 4d |
| 1.4 | 数据源 — 聊天记录（微信/企业微信导出解析） | 3d |
| 1.5 | 数据源 — 企业PPT库（上传/解析/Slide索引/模板提取） | 5d |
| 1.6 | 意图识别 + 模板推荐 | 4d |
| 1.7 | 智能填报引擎（汇总+并行填充+校验+Slide匹配） | 6d |
| 1.8 | 内容确认 — iframe卡片（三栏布局+大纲+预览+Chat） | 8d |
| 1.9 | Word 导出（python-docx + TOC + 样式） | 3d |
| 1.10 | PDF 导出（Markdown→HTML→WeasyPrint） | 2d |
| 1.11 | HTML 脑图导出（Markmap集成） | 2d |
| 1.12 | 喔壳集成（数字员工+iframe注册+附件分类+计费） | 5d |
| 1.13 | 测试 + 联调 | 5d |

**Phase 1 可交付：** 上传数据源 → AI生成周报/月报/KPI报告 → 三区确认修改 → 导出Word/PDF/脑图

### Phase 2 · 扩展接入 (3-4 周)

- MCP数据源 + REST API数据源
- 精选模板扩展至12种
- PPT模板选择器 + PPTX生成集成（待用户指定方案）

### Phase 3 · 深度整合 (2-3 周)

- 数据库直连 + RAG知识库
- 喔壳AI服务封装（供外部系统调用）
- Word模板自定义 + 脑图增强

---

## 9. 对外依赖

| 依赖 | 用途 | 配置 |
|------|------|------|
| 喔壳 Open API | 数字员工/会话/附件提取/计费 | API-KEY + agent.workopilot.com |
| LLM (OpenRouter/OpenAI) | 意图识别/内容生成/校验/Slide摘要 | OPENROUTER_API_KEY |
| Redis | Celery 任务队列(导出) | redis://localhost:6379 |
| 数据库(SQLite/PostgreSQL) | 报告/模板/数据源持久化 | SQLAlchemy |

---

## 10. 变更记录

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-07-05 | v1.0 | 初始设计完成 |
