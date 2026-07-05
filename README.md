# 智能报告平台 (Smart Reporting Studio)

企业级智能报告生成平台 — 可配置数据源插槽 → 智能填报汇总 → 多格式报告输出（PPT/Word/PDF）。

## 核心能力

- **数据源插槽**：可配置对接企业知识库、案例库、业务数据库、外部 API
- **智能填报**：多源检索 + LLM 汇总 → 结构化 Markdown 文档 + 报表 JSON
- **多格式输出**：PPT 演示文稿 / Word 文档报告 / PDF 正式报告
- **场景方案库**：5 个预设场景框架（售前/投资人/复盘/汇报/渠道合作）
- **企业模板导入**：上传自有 PPTX/DOCX 模板 → 自动提取样式 + 内容插槽
- **WorkoPilot 集成**：作为数字员工接入企业 AI 平台

## 快速开始

```bash
# 1. 安装依赖
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cd frontend && npm install && cd ..

# 2. 配置
cp .env.example .env
# 编辑 .env 填入 API Keys

# 3. 启动
docker run -d --name redis -p 6379:6379 redis:alpine
.venv/bin/uvicorn backend.api.main:app --reload --port 8000 &
cd frontend && npm run dev &
.venv/bin/celery -A backend.tasks worker --loglevel=info --pool=solo &
```

## 项目架构

```
smart_reporting/
├── backend/
│   ├── data_source/       # 数据源插件层（DataSourcePlugin 抽象）
│   ├── report_engine/     # 智能填报 + 多格式输出引擎
│   ├── models/            # 数据模型（含 knowledge/scenario/report_template）
│   ├── agents/            # AI 智能体（规划师/文案师/设计师…）
│   ├── api/routes/        # API 端点（含 reports/smart_fill/data_sources…）
│   ├── parsers/           # 文档/模板解析器
│   └── pipeline/          # SVG/PPTX 处理流水线
├── frontend/              # React 企业报告工作台
│   └── src/
│       ├── components/layout/    # AppShell + SideNav
│       ├── components/report/    # CreateReportWizard（4步向导）
│       ├── components/KnowledgePanel/
│       ├── components/ScenarioSelector/
│       └── stores/               # Zustand 状态管理
└── docs/                  # 开发文档 + 计划
```

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | FastAPI + LangGraph + Celery + Redis + SQLAlchemy |
| LLM | OpenRouter (多模型网关) |
| PPT | python-pptx + fontTools + pyecharts |
| Word | python-docx |
| PDF | WeasyPrint |
| 前端 | React 19 + TypeScript + Vite + Tailwind v4 + shadcn/ui |
| 部署 | WorkoPilot 数字员工平台 |

## 基于

本项目从 [PPT 智能助手](https://github.com/wenwenba2020/ppt_agent) 重构升级而来，保留了其 PPT 生成内核，新增了企业数据源管理层和多格式输出能力。
