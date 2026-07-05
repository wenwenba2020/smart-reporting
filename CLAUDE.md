# 智能报告平台 · Claude Code 工作指引

## 项目基本信息

- **项目路径**：`/home/wenwenba2020/cc_workspace/smart_reporting`
- **Python 虚拟环境**：`.venv/bin/python`（始终用这个，不用系统 python）
- **项目定位**：企业智能报告平台 — 可配置数据源 → 智能填报 → 多格式报告输出（PPT/Word/PDF）
- **技术基座**：基于 ppt_agent（`~/cc_workspace/ppt_agent`）重构升级
- **开发记录**：`docs/dev-log.md`

---

## 核心架构

```
数据源插槽层（DataSourcePlugin）
  ├── 企业知识库（产品/客户/会议…）
  ├── 企业PPT案例库
  ├── 业务数据库（可扩展）
  └── 外部API（可扩展）
        ↓
智能填报引擎（SmartFillEngine）
  → 多源检索 → LLM汇总 → 结构化Markdown + 报表JSON
        ↓
报告输出引擎（ReportOutputEngine）
  ├── PPT适配器（复用 ppt_agent 的 designer/editor 流水线）
  ├── Word适配器（python-docx）
  └── PDF适配器（WeasyPrint）
        ↑
报告模板引擎（ReportTemplate）
  → 企业自有模板导入 → 自动提取样式+内容插槽
```

---

## 关键模块清单

| 模块 | 路径 | 职责 |
|------|------|------|
| 数据源插件 | `backend/data_source/` | DataSourcePlugin 抽象基类 + KnowledgeBase/CaseLibrary 内置实现 |
| 智能填报 | `backend/report_engine/smart_fill.py` | 多源检索 → LLM → MD + JSON |
| 输出引擎 | `backend/report_engine/` | PPT/Word/PDF 三格式适配器 |
| 知识库 | `backend/models/knowledge.py` | KnowledgeBase + KnowledgeEntry ORM |
| 方案库 | `backend/models/scenario.py` | ScenarioTemplate + 5 预设场景框架 |
| 报告模板 | `backend/models/report_template.py` | 统一 PPT/Word/PDF 模板模型 |
| 案例库 | `backend/models/slide_library.py` | 升级版：场景分类 + 来源标记 + 优质标记 |
| API路由 | `backend/api/routes/` | 含 knowledge/scenarios/reports/report_templates/data_sources/smart_fill/workopilot |
| 前端工作台 | `frontend/src/` | 企业报告工作台（SideNav + CreateReportWizard） |

---

## 启动开发环境

```bash
# 1. 创建虚拟环境（首次）
cd /home/wenwenba2020/cc_workspace/smart_reporting
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 OPENROUTER_API_KEY 等

# 3. 启动 Redis（需要 Docker）
docker run -d --name redis -p 6379:6379 redis:alpine

# 4. 启动后端
.venv/bin/uvicorn backend.api.main:app --reload --port 8000

# 5. 启动前端（新终端）
cd frontend && npm install && npm run dev

# 6. 启动 Celery worker（新终端）
.venv/bin/celery -A backend.tasks worker --loglevel=info --pool=solo
```

---

## 五条重要规则（继承自 ppt_agent）

1. **字体必须 TTF**：OTF 无法嵌入 PPTX
2. **SVG 生成必须顺序**：跨页风格一致性依赖连续上下文
3. **规划师不读 SVG 文件**：只读 OUTLINE.md 结构字段
4. **PPTX 单页更新不重建**：清空内容后原位重写
5. **字体嵌入用 zipfile**：python-pptx 不支持字体嵌入

---

## 技术栈速查

| 层 | 技术 |
|----|------|
| 后端框架 | FastAPI + uvicorn |
| 智能体编排 | LangGraph |
| LLM 网关 | OpenRouter |
| PPT 操作 | python-pptx + fontTools + pyecharts |
| Word 操作 | python-docx |
| PDF 操作 | WeasyPrint |
| 文档解析 | PyMuPDF (fitz) |
| 任务队列 | Celery + Redis |
| 数据库 | SQLAlchemy + aiosqlite |
| 前端 | React 19 + TypeScript + Vite + Tailwind v4 + shadcn/ui |
| 状态管理 | Zustand |
| 实时通信 | SSE (Server-Sent Events) |
