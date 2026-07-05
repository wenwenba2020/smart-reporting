# 开发任务清单

> 开始任何任务前先读 `CLAUDE.md`。完成一项打一个 ✅。

---

## 📋 项目管理模板（docs/pm/）

> 用于标准化项目进度报告、风险记录和下一步计划。

- [x] **PM-1 · 项目管理文件清单**：`docs/pm/README.md`
- [x] **PM-2 · 进度报告模板**：`docs/pm/progress-report-template.md`（含进度摘要 + 风险/阻塞格式 + 下一步计划）
- [x] **PM-3 · 状态摘要模板**：`docs/pm/status-summary-template.md`（简洁版，日常快速更新）

---

## 🔴 准备工作（开始写代码前必须完成）

### P0-1：检查并安装 ppt-master scripts 依赖
```bash
cd /Users/wenwenba2020/cc_workspace/ppt_agent
.venv/bin/python backend/skills/ppt-master/scripts/svg_to_pptx.py --help
```
如果报 ImportError，记录缺失的包并安装到 `.venv`。

- [x] 运行上述命令，记录所有 ImportError
- [x] 安装缺失依赖到 `.venv`（svglib + reportlab）
- [x] 验证 `svg_to_pptx.py` 可以正常调用

### P0-2：下载字体文件
需要下载阿里巴巴普惠体 TTF 版本到 `fonts/AlibabaPuHuiTi/`。

官方下载地址：https://alibaba.alicdn.com/font/AlibabaPuHuiTi3.zip
或通过包管理下载。

**严格要求**：
- 必须是 `.ttf` 格式，不接受 `.otf`
- 验证命令：`file fonts/AlibabaPuHuiTi/*.ttf` 必须显示 `TrueType font data`

需要的字重（最少需要这三个）：
- [x] `AlibabaPuHuiTi-Regular.ttf`
- [x] `AlibabaPuHuiTi-Bold.ttf`
- [x] `AlibabaPuHuiTi-Light.ttf`

完整 9 字重（有条件尽量都下）：
- [x] Thin / Light / Regular / Medium / Semibold / Bold / Extrabold / Heavy / Black（全部下载，来源 hongzhi725/AlibabaPuHuiTi GitHub）

### P0-3：下载 Inter 英文字体（TTF）
- [x] Inter-Regular.ttf → `fonts/Inter/`
- [x] Inter-Medium.ttf → `fonts/Inter/`
- [x] Inter-Bold.ttf → `fonts/Inter/`
下载地址：https://github.com/rsms/inter/releases

### P0-4：创建 dev-setup.sh
- [x] 创建 `dev-setup.sh`（见下方模板）— 已存在
- [ ] 测试脚本可以正常启动 Redis + 后端

### P0-5：配置 .env 文件
- [ ] 填写 `ANTHROPIC_API_KEY`
- [ ] 填写 `SILICONFLOW_API_KEY`（用于文案师 DeepSeek + 效果师 Qwen）
- [ ] 生成 `JWT_SECRET`：`python3 -c "import secrets; print(secrets.token_hex(32))"`
- [ ] 设置 `ADMIN_PASSWORD`

---

## Phase 1 · Week 1：基础设施

### W1-1：FastAPI 应用骨架
参考文档：无（按下方规格直接写）

- [x] 创建 `backend/api/main.py`（含 lifespan 事件、CORS、路由注册）
- [x] 创建 `backend/api/routes/auth.py`（JWT 登录/刷新）
- [x] 创建 `backend/api/routes/projects.py`（项目 CRUD）
- [x] 创建 `backend/api/routes/health.py`（健康检查端点 GET /health）
- [x] 验收：`curl http://localhost:8000/health` 返回 200

### W1-2：数据库初始化
参考文档：`PPT_ASSISTANT_DEVELOPMENT_PLAN.md` 第十章

- [x] 创建 `backend/models/database.py`（SQLAlchemy engine + session）
- [x] 创建 `backend/models/project.py`（projects 表 ORM 模型）
- [x] 创建 `backend/models/snapshot.py`（project_snapshots 表 ORM 模型）
- [x] 实现 `create_all_tables()` 在 lifespan 启动时调用
- [x] 验收：启动后检查 `ppt_agent.db` 文件存在，表结构正确

### W1-3：OUTLINE.md Pydantic 模型
参考文档：`docs/data-formats.md`

- [x] 创建 `backend/models/outline.py`
- [x] 实现 `SlideItem`、`OutlineDoc`、`DesignDoc` Pydantic 模型
- [x] 实现 `load_outline(path)` 和 `save_outline(outline, path)` 函数
- [x] 实现文件级写入锁（fcntl，防多智能体并发写入冲突）
- [x] 单元测试：解析示例 OUTLINE.md，验证所有字段正确

### W1-4：文件存储抽象层
- [x] 创建 `backend/storage/file_manager.py`
- [x] 实现 `ProjectStorage` 类（本地文件系统）
- [x] 方法：`create_project_dir`、`save_file`、`read_file`、`list_files`、`get_project_path`
- [x] 确保接口设计允许未来替换为腾讯 COS（保留 abstract base）

### W1-5：JWT 认证中间件
- [x] 实现 `backend/api/auth.py`（token 生成/验证）
- [x] 实现 `get_current_user` FastAPI dependency
- [x] 单账号模式：用户名/密码从 `.env` 读取，验证通过返回 JWT
- [x] 验收：`POST /auth/login` 返回 token，`GET /projects` 无 token 返回 401

### W1-6：Redis + Celery 配置
- [x] 创建 `backend/tasks/__init__.py`（Celery app 初始化）
- [x] 创建 `backend/tasks/generate.py`（PPT 生成任务骨架，暂时只 print）
- [x] 验收：Celery app 导入成功，任务 `ppt_agent.generate` 已注册

---

## Phase 1 · Week 2：PPT 生成内核

### W2-1：文档解析器
参考文档：`docs/ppt-pipeline.md`

- [x] 创建 `backend/parsers/doc_parser.py`
- [x] 实现 PDF → Markdown（PyMuPDF）
- [x] 实现 DOCX → Markdown（python-docx）
- [x] 实现 URL → Markdown（httpx + HTML stripping，MVP 阶段；Crawl4AI 待后续）
- [x] 实现长文档分块策略（超过 50 页 PDF 的处理）
- [x] 验收：test_pdf_to_markdown 通过

### W2-2：参考 PPT 解析（图片提取）
- [x] 创建 `backend/parsers/ppt_parser.py`
- [x] 实现从 PPTX 提取所有图片，保存到 `assets/extracted/`
- [x] 实现提取 PPTX 的配色方案和字体信息
- [x] 输出 JSON 描述文件（analyze_reference_pptx → reference_analysis.json）

### W2-3：字体管理器
参考文档：`docs/font-management.md`

- [x] 创建 `backend/pipeline/font_manager.py`
- [x] 实现 `create_font_subset(font_path, text_content, output_path)`
- [x] 实现 `embed_fonts_in_pptx(pptx_path, font_files)` ← 解压+修改+重打包
- [x] 实现 `get_fonts_for_template(template_id)` 返回该模板需要的字体列表
- [x] 验收：test_embed_fonts_in_pptx 验证嵌入 PPTX 含字体文件

### W2-4：图表渲染器
- [x] 创建 `backend/pipeline/chart_renderer.py`
- [x] 实现 bar/bar-grouped/line/pie/scatter + radar/funnel 七种图表类型
- [x] 输出 SVG 格式（不是 PNG）
- [x] 配色支持自定义 colors 参数（从 DESIGN.md 传入）
- [x] 验收：test_render_bar/pie/line_chart 全部通过

### W2-5：SVG → PPTX 转换器
参考文档：`docs/ppt-pipeline.md`，`backend/skills/ppt-master/scripts/svg_to_pptx.py`

- [x] 创建 `backend/pipeline/svg_to_pptx.py`（封装 ppt-master 的转换脚本）
- [x] 实现全量转换（convert_all_to_pptx）
- [x] 实现增量更新（update_single_slide）⚠️ 不删除 slide 对象
- [x] 实现双输出（native.pptx + reference_svg.pptx via ppt-master 默认行为）
- [x] 实现完整流水线（run_full_pipeline: finalize→convert→embed）

### W2-6：端到端流水线测试
- [x] 写测试 `backend/tests/test_parsers.py` + `backend/tests/test_pipeline.py`
- [x] 38 个测试全部通过（含 Week 1 的 22 个）

---

## Phase 1 · Week 3：智能体编排

### W3-1：LangGraph 状态机
参考文档：`docs/agents-spec.md`，`PPT_ASSISTANT_DEVELOPMENT_PLAN.md` 第五章

- [x] 创建 `backend/graph/state.py`（PPTState TypedDict 定义）
- [x] 创建 `backend/graph/workflow.py`（图结构 + 条件边）
- [x] 配置 SqliteSaver checkpointer（断点续传）
- [x] 实现三种工作模式的路由逻辑（route_by_mode + route_after_confirm）

### W3-2：规划师智能体
参考文档：`docs/agents-spec.md` 4.1节

- [x] 创建 `backend/agents/planner.py`
- [x] 实现全局生成模式（需求分析 + 大纲生成）
- [x] 实现路由模式（意图识别 + 智能体路由）
- [x] 实现诊断模式（问题扫描 + 修改提案）
- [x] ⚠️ 诊断模式只读 OUTLINE.md（get_summary），不读 svg_output/

### W3-3：文案师智能体
- [x] 创建 `backend/agents/copywriter.py`
- [x] 接入 OpenRouter（DeepSeek V3.2 via OpenAI-compatible API）
- [x] 实现逐页文案生成（填充 OUTLINE.md 各页字段）
- [x] 实现备注生成（notes_speaker 字段）

### W3-4：SSE 事件推送
参考文档：`PPT_ASSISTANT_DEVELOPMENT_PLAN.md` 第九章

- [x] 创建 `backend/api/routes/generate.py`
- [x] 实现 Redis pub/sub 事件总线（backend/agents/events.py）
- [x] 实现 SSE endpoint（`GET /projects/{id}/stream`）
- [x] 实现智能体状态事件发布（publish_agent_start/progress/complete/error）
- [x] ⚠️ 响应头加 `X-Accel-Buffering: no` 防 Nginx 缓冲

---

## Phase 2 · Week 4-5：前端 MVP

### W4-1：主界面三栏布局
- [x] 实现左侧智能体状态面板（AgentPanel 组件）
- [x] 实现中间对话区（ChatPanel 组件）
- [x] 实现右侧幻灯片缩略图列表（SlideList 组件）
- [x] 实现 SSE 连接管理（useSSE hook）
- [x] 实现 Zustand 项目状态 store
- [x] 实现登录页面（LoginForm 组件）
- [x] 实现 API 客户端（axios + JWT 拦截器）

### W4-2：Fabric.js 画布（单页编辑）
- [x] 实现 Canvas 组件（SVG 加载 + 字体预加载）
- [x] ⚠️ 字体用 FontFace API 预加载完成后才渲染 canvas
- [ ] 实现元素选中 + 属性面板联动（待设计师智能体产出 SVG 后完善）
- [ ] 实现拖拽/缩放/属性修改（同上）
- [ ] 实现修改后序列化回 SVG，调用 API 触发增量更新（同上）

### W4-3：风格/模板面板
- [x] 实现模板选择（3 套预制模板：商务蓝/科技感/极简留白）
- [x] 实现颜色/字体预览

---

## Phase 3 · Week 6-7：完整功能

- [x] 设计师智能体（SVG 排版生成，Claude Sonnet 4.6，顺序生成）
- [x] 编辑师智能体（SVG→PPTX 转换 + 字体嵌入，调脚本）
- [x] PPTX 下载端点（GET /projects/{id}/download）
- [x] 静态文件挂载（/fonts/ 供前端字体预加载）
- [x] 效果师智能体（图表 ChartData 生成 + JSON 保存）
- [x] 大纲确认 UI（OutlineConfirmation 组件 + POST /confirm 恢复流程）
- [x] 文件上传端点（PDF/DOCX/PPTX 上传 + 解析）
- [x] 下载 UI（前端下载按钮 + token query param 支持）
- [ ] 规划师诊断模式前端交互
- [ ] 版本快照 + 回退 UI
- [ ] 演讲者备注生成和编辑
- [ ] 错误处理 + 断点续传测试
- [ ] 中文字体渲染一致性测试
- [ ] 模板库扩充（≥5 套）

---

## dev-setup.sh 模板

在项目根目录创建此文件：

```bash
#!/bin/bash
set -e

PROJECT_DIR="/Users/wenwenba2020/cc_workspace/ppt_agent"
cd "$PROJECT_DIR"

echo "=== 启动 Redis ==="
if ! docker ps | grep -q ppt-redis; then
  docker run -d --name ppt-redis -p 6379:6379 redis:alpine
  echo "Redis 已启动"
else
  echo "Redis 已在运行"
fi

echo "=== 检查虚拟环境 ==="
source .venv/bin/activate
python -c "import fastapi; print('后端依赖 OK')"

echo "=== 环境就绪 ==="
echo "运行后端: .venv/bin/uvicorn backend.api.main:app --reload --port 8000"
echo "运行前端: cd frontend && npm run dev"
echo "运行 Celery: .venv/bin/celery -A backend.tasks worker --loglevel=info"
```
