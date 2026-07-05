# PPT 智能助手 · 完整开发计划 v2.0

> **Claude Code 使用说明**：本文档是总纲，开始具体任务前请优先阅读 `docs/` 目录下对应的专项文档。
> 任务清单在 `docs/todo.md`，从那里开始。

---

## 第一章：产品定位与核心约束

### 产品定位

基于多智能体架构的企业 PPT 生成 Web 应用。用户通过自然语言描述需求、上传参考文档，系统自动生成可编辑的原生 PPTX 文件，并支持单页级别的精确修改。

**部署形态**：Web 应用（本地开发 → 腾讯云服务器）

### 四条核心原则

1. **输出必须是原生可编辑的 PPTX**：用户在 PowerPoint/WPS 里可以直接点击编辑任何元素。
2. **单页编辑真正灵活**：AI 指令、Fabric.js 可视化拖拽、属性面板三条路都要通。
3. **规划师不全量介入**：单页精确修改时规划师只做路由判断，不重新生成大纲。
4. **所有字体必须 TTF**：OTF 格式无法嵌入 PPTX，这是 Office 的硬性限制。

---

## 第二章：技术栈选型（已定，不可更改）

### 后端

| 组件 | 选型 | 理由 |
|------|------|------|
| 语言 | Python 3.12 | 与 ppt-master、python-pptx、fonttools 生态一致 |
| Web 框架 | FastAPI | 异步支持好，SSE 流式输出，自动 OpenAPI 文档 |
| 智能体编排 | LangGraph 0.2.28 | 状态机 + 人工确认节点 + 断点续传 |
| PPT 生成内核 | ppt-master（fork） | SVG→DrawingML 原生可编辑 |
| PPTX 操作 | python-pptx 1.0.2 | 增量回写单页，字体嵌入操作 |
| 字体子集化 | fontTools（import 名大写 T） | 按实际用字裁剪 TTF |
| 图表渲染 | pyecharts → SVG | 生成可缩放 SVG 图表 |
| 文档解析 | PyMuPDF（import 名 fitz）+ Crawl4AI | PDF + 网页解析 |
| 任务队列 | Celery + Redis | 长时任务异步执行 |
| 数据库 | SQLAlchemy + aiosqlite（SQLite→PostgreSQL） | 项目元数据 |
| 文件存储 | 本地文件系统 → 腾讯 COS | 项目工作区 |

### 前端

| 组件 | 选型 | 理由 |
|------|------|------|
| 框架 | React 18 + TypeScript + Vite | 生态成熟 |
| UI 组件 | shadcn/ui (Nova preset) + Tailwind v4 | 已配置就绪 |
| 画布编辑 | Fabric.js 6.x | SVG 解析/对象化最成熟，中文无 bug |
| 状态管理 | Zustand | 轻量 |
| 实时通信 | SSE | 智能体状态流式推送 |
| HTTP | Axios + React Query | 请求管理 + 缓存 |

### 智能体 LLM 绑定

统一通过 OpenRouter（OpenAI-compatible）调用，一个 API Key 覆盖所有模型。

| 智能体 | 模型 | OpenRouter Model ID | 输入$/M | 输出$/M |
|--------|------|---------------------|---------|---------|
| 规划师 | Gemini 3.1 Pro | `google/gemini-3.1-pro-preview` | $2.00 | $12.00 |
| 文案师 | DeepSeek V3.2 | `deepseek/deepseek-v3.2` | $0.26 | $0.38 |
| 设计师 | Claude Sonnet 4.6 | `anthropic/claude-sonnet-4.6` | $3.00 | $15.00 |
| 效果师 | Qwen3.5 Flash | `qwen/qwen3.5-flash-02-23` | $0.065 | $0.26 |
| 编辑师 | —（调脚本，不用 LLM） | — | — | — |

OpenRouter API Base：`https://openrouter.ai/api/v1`

成本估算：20 页 PPT 全量生成 ≈ $1.16/次（设计师占 98%）。
超时 60 秒，重试 2 次。

---

## 第三章：项目目录结构

```
ppt_agent/
├── CLAUDE.md                          # Claude Code 入口（每次必读）
├── PPT_ASSISTANT_DEVELOPMENT_PLAN.md  # 本文件（总纲）
├── dev-setup.sh                       # 开发环境启动脚本
├── .env                               # 环境变量（不提交 git）
├── .env.example                       # 环境变量模板
├── .gitignore
├── docs/                              # 专项文档（开始任务前必读对应文档）
│   ├── todo.md                        # ← 任务清单，从这里开始
│   ├── known-pitfalls.md              # 关键坑点（每次必读）
│   ├── data-formats.md                # OUTLINE.md + DESIGN.md 格式
│   ├── agents-spec.md                 # 五智能体详细规格
│   ├── font-management.md             # 字体管理规范
│   └── ppt-pipeline.md                # PPT 生成流水线
├── backend/
│   ├── agents/
│   │   ├── planner.py                 # 规划师（三种模式）
│   │   ├── copywriter.py              # 文案师
│   │   ├── designer.py                # 设计师
│   │   ├── effects.py                 # 效果师
│   │   └── editor.py                 # 编辑师
│   ├── graph/
│   │   ├── state.py                   # PPTState TypedDict
│   │   └── workflow.py                # LangGraph 状态机
│   ├── pipeline/
│   │   ├── svg_generator.py           # SVG 生成封装
│   │   ├── svg_to_pptx.py             # SVG→PPTX 转换封装
│   │   ├── font_manager.py            # 字体子集化 + PPTX 嵌入
│   │   └── chart_renderer.py          # pyecharts SVG 图表
│   ├── parsers/
│   │   ├── doc_parser.py              # PDF/DOCX/URL → Markdown
│   │   └── ppt_parser.py              # 参考 PPTX → 图片/风格提取
│   ├── models/
│   │   ├── database.py                # SQLAlchemy engine
│   │   ├── project.py                 # projects 表
│   │   ├── snapshot.py                # snapshots 表
│   │   └── outline.py                 # OUTLINE.md Pydantic 模型
│   ├── api/
│   │   ├── main.py                    # FastAPI 入口（lifespan）
│   │   ├── auth.py                    # JWT 工具函数
│   │   └── routes/
│   │       ├── auth.py                # 登录/刷新
│   │       ├── projects.py            # 项目 CRUD
│   │       ├── generate.py            # 生成触发 + SSE
│   │       ├── slides.py              # 单页操作
│   │       └── health.py              # 健康检查
│   ├── storage/
│   │   └── file_manager.py            # 文件存储抽象层
│   ├── tasks/
│   │   ├── __init__.py                # Celery app
│   │   └── generate.py                # PPT 生成 Celery task
│   ├── skills/
│   │   └── ppt-master/                # ⚠️ 只读参考，不改结构
│   └── requirements.txt
├── frontend/                          # React 前端（已初始化）
│   ├── src/
│   │   ├── components/
│   │   │   ├── AgentPanel/            # 智能体状态面板
│   │   │   ├── ChatPanel/             # 对话区
│   │   │   ├── Canvas/                # Fabric.js 画布
│   │   │   ├── SlideList/             # 幻灯片缩略图
│   │   │   └── StylePanel/            # 风格/属性面板
│   │   ├── stores/
│   │   │   ├── projectStore.ts
│   │   │   └── agentStore.ts
│   │   ├── hooks/
│   │   │   └── useSSE.ts
│   │   └── api/
│   │       └── client.ts
│   └── public/fonts/                  # TTF 字体（Web 静态文件）
├── fonts/                             # 服务端字体库（不提交 git）
│   ├── AlibabaPuHuiTi/
│   ├── HarmonyOSSans/
│   ├── SourceHanSans-TTF/
│   ├── SourceHanSerif-TTF/
│   ├── Inter/
│   └── subsets/
└── projects/                          # 用户项目工作区（不提交 git）
```

---

## 第四章：数据格式

详见 `docs/data-formats.md`。

核心文件：
- `OUTLINE.md`：项目内容结构和生成状态，所有智能体共享
- `DESIGN.md`：视觉设计规范，设计师初始化时生成

---

## 第五章：五智能体规格

详见 `docs/agents-spec.md`。

---

## 第六章：LangGraph 状态机

详见 `docs/agents-spec.md` 最后一节。

关键点：
- `PPTState` TypedDict 定义在 `backend/graph/state.py`
- Celery task 是外壳，LangGraph 是内部编排，不混用
- `interrupt_before=["human_confirm"]` 实现人工确认节点

---

## 第七章：字体管理

详见 `docs/font-management.md`。

核心规则：只用 TTF，不用 OTF。

---

## 第八章：PPT 生成流水线

详见 `docs/ppt-pipeline.md`。

---

## 第九章：单页编辑

### 三层机制

**AI 语言指令层**：
```
用户:"第3页标题改大，背景换深色"
→ 规划师（路由模式）识别意图
→ 路由给设计师
→ 重新生成 slide_03.svg
→ 编辑师增量回写第3页 PPTX
→ 前端 Canvas 重新渲染
```

**Fabric.js 可视化层**：
```javascript
// 字体预加载（必须先于 canvas 加载）
await preloadFonts(templateId)

// 加载当前页 SVG
fabric.loadSVGFromURL(svgUrl, (objects, options) => {
  const group = fabric.util.groupSVGElements(objects, options)
  canvas.add(group)
  group.toActiveSelection()
  canvas.requestRenderAll()
})

// 变更后序列化并触发增量更新
const modifiedSVG = canvas.toSVG()
await api.updateSlide(projectId, slideId, modifiedSVG)
```

**属性面板手动输入层**：字体大小、颜色、位置、尺寸直接绑定 Fabric 对象属性。

### Fabric.js + SVG 注意事项

- SVG viewBox 统一 `0 0 960 540`（PPT 16:9 标准）
- Canvas 宽度按比例缩放显示（如 960px 容器 1:1，480px 容器 0.5x）
- 超过 50 个 SVG 元素时用 `StaticCanvas` 只读预览，点击"编辑"切换 `Canvas`
- `canvas.toSVG()` 坐标保留 2 位小数

---

## 第十章：SSE 实时推送

详见 `docs/agents-spec.md` SSE 事件类型一节。

**关键**：响应头必须加 `X-Accel-Buffering: no`，防止 Nginx 缓冲。

事件总线：Redis pub/sub，Key 格式 `project:{project_id}:events`。

---

## 第十一章：用户认证

### 当前阶段（MVP）

单账号模式：

```python
# backend/api/auth.py
# 用户名/密码从 .env 读取
ADMIN_USERNAME = settings.ADMIN_USERNAME
ADMIN_PASSWORD = settings.ADMIN_PASSWORD

# 登录验证
def verify_credentials(username: str, password: str) -> bool:
    return (
        username == ADMIN_USERNAME and
        password == ADMIN_PASSWORD
    )
```

JWT 有效期 7 天，所有项目 `user_id = "admin"`。

### 数据库 Schema

```sql
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    user_id TEXT NOT NULL DEFAULT 'admin',
    status TEXT NOT NULL DEFAULT 'draft',
    template_id TEXT,
    total_slides INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    outline_path TEXT,
    export_path TEXT,
    snapshot_count INTEGER DEFAULT 0
);

CREATE TABLE project_snapshots (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    version TEXT NOT NULL,
    trigger TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    snapshot_path TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);
```

---

## 第十二章：关键坑点

详见 `docs/known-pitfalls.md`（共 13 条，每次开始任务前必读）。

最高危的三条：
1. 思源黑体 OTF 无法嵌入 PPTX
2. SVG 生成不能并发
3. python-pptx 不支持字体嵌入，必须用 zipfile

---

## 第十三章：分阶段开发路线图

查看 `docs/todo.md` 获取完整带 checkbox 的任务清单。

### 阶段总览

| 阶段 | 时间 | 里程碑 |
|------|------|--------|
| 准备工作 | 开始前 | 字体下载、依赖检查、.env 配置 |
| Phase 1 Week 1 | 第1-2周 | FastAPI 骨架、数据库、认证、Celery |
| Phase 1 Week 2 | 第2-3周 | 文档解析、字体管理、SVG→PPTX 流水线 |
| Phase 1 Week 3 | 第3-4周 | LangGraph 状态机、规划师、文案师、SSE |
| Phase 2 Week 4-5 | 第4-6周 | React 前端、Fabric.js 画布、单页编辑 |
| Phase 3 Week 6-7 | 第6-8周 | 设计师、效果师、诊断模式、模板库 |

---

## 第十四章：测试验收标准

### Phase 1 验收

1. 给定一段 Markdown，能生成含中文、图表的可编辑 PPTX
2. 在无字体的 Windows 10 上打开 PPTX，字体正确显示（嵌入成功）
3. SVG 和 PPTX 字体视觉一致（字号、字重、行距相差 ≤2px）

### Phase 2 验收

1. Canvas 拖动文字框，变更同步回 PPTX
2. 单页 AI 修改响应 < 30 秒
3. 断网重连后 SSE 继续接收
4. 版本回退后前端正确显示历史 SVG

### Phase 3 验收

1. 笼统反馈"视觉冲击力不够"生成合理诊断报告
2. 参考 PPT 图片正确提取并用于新 PPT
3. 20 页 PPT 全量生成 < 5 分钟
4. PPTX 在 WPS 中正确打开（兼容性）

---

## 附录：环境变量模板（.env.example）

```bash
# LLM API Keys
ANTHROPIC_API_KEY=sk-ant-
SILICONFLOW_API_KEY=sk-
WAVESPEED_API_KEY=

# 认证（单账号模式）
ADMIN_USERNAME=admin
ADMIN_PASSWORD=
JWT_SECRET=                          # 用 python3 -c "import secrets; print(secrets.token_hex(32))" 生成
JWT_EXPIRE_DAYS=7

# Redis
REDIS_URL=redis://localhost:6379/0

# 存储
STORAGE_TYPE=local
LOCAL_STORAGE_PATH=./projects

# 字体
FONTS_DIR=./fonts

# ppt-master
PPT_MASTER_SKILL_DIR=./backend/skills/ppt-master

# LLM 超时
LLM_TIMEOUT_SECONDS=60
LLM_MAX_RETRIES=2

# 生产阶段追加
# COS_SECRET_ID=
# COS_SECRET_KEY=
# COS_BUCKET=
# COS_REGION=ap-guangzhou
```

---

*文档版本：v2.0 · 2026-04-15*
*本文档与 docs/ 目录下各专项文档配合使用。*
