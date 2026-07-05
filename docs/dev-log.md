# PPT 智能助手 · 开发记录

> 最后更新：2026-04-29
> 当前阶段：Phase 3 · 内容/设计分离 MVP 落地

---

## 当前状态总览

**部署地址**：http://111.193.111.167:12000/ （本机公网映射 12000→3001）
**API 网关**：OpenRouter (https://openrouter.ai/api/v1)
**项目路径**：`/home/wenwenba2020/cc_workspace/ppt_agent`

**端到端流程已跑通**：用户输入需求 → 网页调研 → 三阶段规划 → 多智能体协作生成 → SVG 预览 → PPTX 下载

---

## 进度一览

| 阶段 | 范围 | 状态 | 测试 |
|------|------|------|------|
| P0 | 准备工作（字体、依赖、.env） | ✅ 完成 | — |
| Phase 1 W1 | 基础设施（FastAPI + DB + JWT + Celery） | ✅ 完成 | 22 → 审查后 22 |
| Phase 1 W2 | PPT 生成内核（解析 + 字体 + 图表 + 转换） | ✅ 完成 | 38 → 审查后 39 |
| Phase 1 W3 | 智能体编排（LangGraph + 规划师 + 文案师 + SSE） | ✅ 完成 | 51 → 审查后 56 |
| Phase 2 W4-5 | 前端 MVP（三栏布局 + SSE + 画布） | ✅ 完成 | — |
| Phase 3 W6-7 | 完整功能（设计师/编辑师/效果师/下载） | ✅ 完成 | 58+1 pre-existing |
| Phase 3 W8 | NotebookLM 重构（布局 + 瀑布 + 单页 Modal + 单页修改 + 图片占位） | ✅ 完成 | — |
| Phase 3 W9 | 内容/设计分离 MVP-1 · DESIGN.md 模板库 + 切换 + 批量应用 | ✅ 完成 | — |
| Phase 3 W10 | 内容/设计分离 MVP-2 · 文案审核闸门 + text-layouts + stage 状态机 | ✅ 完成 | 70 passed |
| Phase 3 W11 | 文案段落结构化 · PointItem（heading + body）+ 向下兼容 | ✅ 完成 | 77 passed |
| Phase 3 W12 | URL 调研功能 · Exa + Tavily 双 provider · 浅/深度抓取 | ✅ 完成 | 77 passed |
| Phase 3 PM | 项目管理模板 · 文件清单 + 进度报告 + 风险/阻塞格式 + 下一步计划模板 | ✅ 完成 | — |
| Phase 4 | 三层架构（content.json + design.md + layouts/） · ImageAgent · 批量化 API | 📐 规划中 | — |

**累计测试**：58 passed + 1 pre-existing failure（test_run_global_mode · 与当前功能无关）
**累计提交**：~60 个 commit
**累计审查**：5 轮双模型审查（Claude + Codex）

---

## 技术栈（已实现）

### 后端 (Python 3.12)
| 层 | 技术 |
|----|------|
| Web 框架 | FastAPI + uvicorn |
| 智能体编排 | LangGraph + SqliteSaver |
| LLM 网关 | OpenRouter (OpenAI-compatible) |
| 任务队列 | Celery + Redis |
| 数据库 | SQLAlchemy + aiosqlite |
| PPT 操作 | python-pptx, fontTools, pyecharts |
| 文档解析 | PyMuPDF, python-docx |
| 网页调研 | Tavily Python SDK |

### 前端 (TypeScript + React 19)
| 层 | 技术 |
|----|------|
| 框架 | Vite + React 19 |
| UI | shadcn/ui (Nova preset) + Tailwind v4 |
| 状态 | Zustand |
| 实时通信 | EventSource (SSE) |
| 布局 | react-resizable-panels (可拖动三栏) |
| HTTP | axios (JWT 拦截器 + 401 自动跳登录) |

### 智能体 LLM 绑定
| 智能体 | 模型 (OpenRouter) | 价格 |
|--------|------------------|------|
| 规划师 | z-ai/glm-5.1 | $0.95/M |
| 文案师 | deepseek/deepseek-v3.2 | $0.26/M |
| 设计师 | z-ai/glm-5.1 | $0.95/M |
| 效果师 | qwen/qwen3.5-9b | $0.05/M |
| 编辑师 | —（调 ppt-master 脚本） | — |

---

## 已实现功能详单

### 认证 & 项目
- [x] 单账号 JWT 登录（admin / ADMIN_PASSWORD）
- [x] 401 自动跳登录 + token 失效清理
- [x] 项目 CRUD（创建/列表/切换）

### 内容输入
- [x] 自然语言需求输入
- [x] URL 自动调研（Tavily 搜索 + 内容提取）
- [x] 源文档上传（PDF/DOCX/TXT/MD）
- [x] 参考 PPTX 上传 + 风格信息提取（图片/字体/配色）

### 三阶段交互式规划
- [x] Stage 1: 逐题确认 PPT 定位（受众/场景/目标/风格/页数）
  - 每题提供 4 个可点击选项（首选标"推荐"）
  - 支持手动输入自定义答案
  - 基于调研内容生成智能选项
- [x] Stage 2: 生成大纲骨架（标题 + 副标题 + 布局类型）
- [x] Stage 3: 完善每页详情（points、visual_intent、chart）
- [x] 自然语言修改大纲（"加一页团队介绍"、"删掉第3页"）
- [x] 每阶段可"重新开始"回初始状态

### 多智能体协作
- [x] 文案师 → 设计师 → 效果师 → 编辑师 顺序流水线
- [x] 智能体间交接消息（🔄 文案师 → 设计师：已完成 8 页文案）
- [x] 思考过程展示（灰色斜体，轮播提示）
- [x] 动态工作状态（跳动圆点 + 渐变进度条 + 时间线连接器）
- [x] SVG 生成失败自动重试 3 次（递增 temperature）

### 输出 & 预览
- [x] SVG 逐页生成（viewBox 0 0 960 540，顺序执行保证风格一致）
- [x] PPTX 转换（ppt-master native DrawingML）
- [x] 字体嵌入（zipfile 操作 + Content_Types + .rels）
- [x] SVG 预览（inline 渲染，支持中文 @font-face）
- [x] PPTX 下载（token query param 支持直链）
- [x] **图片占位 SVG**（W8 · 设计师 prompt 改造）
  - 需要配图的位置输出虚线圆角占位框 + 🖼️ 图标 + 中文描述 + 英文 prompt
  - 用户导出 PPTX 后在 PowerPoint 中替换为真实图片
  - 规划师 Stage 3 的 visual_intent 已要求输出"[需要配图] 类型 / 主体 / Prompt"

### 单页修改（W8 新增）
- [x] **POST /projects/{id}/slides/{slide_id}/revise**
  - 追加用户指令到 slide.visual_intent
  - 调 `generate_single_slide` 带 previous_svg 保持风格一致
  - 写入新 SVG 覆盖旧文件，重跑 editor 刷新 PPTX
- [x] Modal AI 对话栏实时调用 · 输入禁用 + loading 状态
- [x] slide.status 切 generating 时 SVG 区显示蒙层
- [x] 完成后 cache-bust（`?t=timestamp`）自动刷新 SVG

### URL 调研功能（W12 新增）
- [x] **POST /projects/{id}/research** 路由，body `{urls, deep, provider}`
- [x] **双 provider**（用户在 Modal radio 切换，无跨 provider 降级）：
  - `provider='exa'`（默认）：`exa.get_contents(url, text=True, livecrawl='always')`，deep=True 时带 `subpages=10`
  - `provider='tavily'`：`client.extract(url)`；deep=True 走 `crawl` → 失败降级 `map+extract`
- [x] **抓取结果存为 sources/url_<ts>_<idx>.md**（规划师/文案师走既有路径自动读取）
- [x] **UploadSourceModal**：启用 URL input + provider radio + 深度抓取 checkbox + 抓取按钮 + 结果卡片（成功绿 / 失败红）
- [x] **异步化**：`asyncio.to_thread` + `asyncio.wait_for` 包 Tavily/Exa 同步 SDK，150s(深度)/60s(浅) 硬超时，不阻塞事件循环
- [x] **单次限制**：普通 10 个 URL / 深度模式 3 个 URL
- [x] **Exa statuses 透传**：`get_contents` 返回空时把 Exa 自己的 `ContentStatus` 诊断（如 `status='error'`）写入用户可见错误消息

**W12 踩坑清单**：
- `uvicorn --reload` 默认监视整个工作目录包括 `.venv/`：`pip install` 新包会触发无限 reload 循环。已加 `--reload-exclude '.venv/*' 'projects/*' '__pycache__/*'`
- Tavily crawl 对未索引站返回 `400 Invalid Start URL`（W12 中途的 fallback 策略：crawl → map+extract）
- Tavily SDK 是**同步**的，直接在 FastAPI async 路由里调用会阻塞事件循环；必须 `asyncio.to_thread` 包装
- Exa/Tavily 基于境外机房，**抓不到**国内需要中国 IP 的站（`workopilot.com`/`danduola.com` 实测 server curl 本身就无法建立 TCP/SSL，域名本地不通）
- URL 无协议前缀时 Tavily 直接 400，已加 `_normalize_url` 补 `https://`
- 深度抓取 5 分钟无响应 → 根因是 Tavily `crawl extract_depth=advanced` 太慢，改为 `basic`（提速 2-3x）+ SDK 自身 90s 超时

### 文案段落结构化（W11 新增）
- [x] **PointItem 模型**（`SlideItem.points: list[PointItem]`，每项带 `heading` + 可选 `body`）
- [x] **懒升级 · 向下兼容**：Pydantic `field_validator` 读 `list[str]` 自动转 PointItem；首次 save 自动升级 OUTLINE.md 格式
- [x] **OUTLINE.md 新格式**：points 改用 YAML 块（`- heading: ... / body: ...`）；PyYAML 解析兼容旧 `- str` 列表
- [x] **Copywriter prompt 分层**：cover/section/toc body 留空；content/comparison/chart/two-col 等必写 120-250 字 body
- [x] **Designer prompt 拼 heading+body 两级文本**：body 为 null 时输出等同旧版
- [x] **SlideContentPatch.points 升级为 list[PointItem]**，审核态保存走新 schema，validator 兼容 list[str]
- [x] **前端 normalizePoint 边界**：`utils/normalizePoint.ts` 统一复用，在 useSSE/loadInitialSlides + ChatPanel 规范化
- [x] **ContentText 两级可视化**：顶行加粗 heading + 下行小字 body 缩略（line-clamp-2）
- [x] **Modal 编辑面板升级**：每项一个卡片（heading 单行 input + body 多行 textarea + 删除按钮）
- [x] **Pydantic v2 注意点**：`field_validator` 不在属性赋值时触发，copywriter 改为直接构造 `PointItem` 对象以确保类型

### 内容/设计分离 MVP-2（W10 新增）
- [x] **项目状态机 `project.stage`**（7 态：idle / planning / copywriting / awaiting_content_review / designing / completed / failed）
- [x] **Celery task 拆分**：`run_copywriter_only`（文案闸门前）+ `run_designer_and_beyond`（闸门后）
- [x] **文案审核闸门**：copywriter 完成 pipeline 暂停 → 右栏显示带排版的文字内容 → 用户确认后才跑 designer
- [x] **3 个新 SSE 事件**：`content_ready` / `stage_change` / `slide_content_changed`
- [x] **`POST /projects/{id}/content/confirm`**（SQL 原子 UPDATE 防双击）
- [x] **`/slides/{sid}/revise` 按 stage 分支**：审核态只改 OUTLINE，设计态仍重跑 SVG
- [x] **5 个审核态文字版式组件**（cover / section / content / comparison / chart）+ 顶部审核条
- [x] **Modal 审核态内容编辑面板**：大图 TextLayout 预览 + 右侧结构化编辑（title / subtitle / points / notes_speaker）
- [x] **`PUT /projects/{id}/slides/{sid}/content`**：结构化内容编辑路由（不跑 designer，审核态专用）
- [x] **老项目迁移**：启动 `ALTER TABLE ADD COLUMN IF NOT EXISTS stage` + 按 svg_output/ 回填 stage（幂等）

### 内容/设计分离 MVP-1（W9 新增）
- [x] **DESIGN.md 模板库**（`backend/design_templates/*.md`）
  - business-navy（商务蓝） / warm-academic（暖色学术） / vibrant-tech（活力科技）
  - 9-section 结构（借鉴 VoltAgent/awesome-design-md，PPT 特化）：
    Visual Theme · Color Palette · Typography · Layout Principles ·
    Depth & Elevation · Do's & Don'ts · Agent Prompt Guide
  - 每份 ~2KB，设计师 system prompt 直接消费
- [x] **GET /projects/design-templates**（清单 + 色板预览）
  - regex 解析 `- **Role** `#HEX`` 提取色板数组
  - 注意路由声明必须在 `/{project_id}` 之前（FastAPI 按定义顺序匹配）
- [x] **POST /projects/{id}/design-template** 切换应用模板
  - 复制模板文件到 `projects/{id}/DESIGN.md`
  - 下次 designer 执行（整份生成 / 单页 revise）自动读取新规范
- [x] **POST /projects/{id}/design/apply-to-all** 批量应用到全部页面
  - 新 Celery task `run_restyle_all`：备份全部 done slide → 重跑 designer（读最新 DESIGN.md）→ 重跑 editor
  - 保留文字内容（title/points/备注），只换视觉
  - 每页备份到 history/ 可通过"撤销"回退
- [x] 前端 StylePanel 重写
  - 从 API 拉真实模板清单 + 色板预览（不再硬编码）
  - 已应用模板有"已应用"标识 + 蓝色大按钮"应用到全部 N 页"
  - confirm 对话框明确告知（文字不变 / 只换视觉 / 可撤销 / 预计耗时）

### SVG → PPTX 兼容性修复（W9）
- [x] **新增 svg_flatten.py**
  - `flatten_fills()`: `url(#gradient)` → 首个 stop 纯色（ppt-master 不支持 url 填充）
  - `escape_text_content()`: 把 `<text>/<tspan>` 里裸 `&` 转成 `&amp;`（不误伤已转义实体）
  - `sanitize_for_pptx()` = 两者组合，editor 打包前统一清理
- [x] editor.py pipeline 调整为：**finalize_svgs → sanitize → convert**
  - finalize_svgs 会 rmtree+copytree 重建 svg_final，sanitize 必须在它**之后**
  - **删除原 fallback** `source="output"`：只会掩盖真实错误（svg_output/ 含 url(#) 永远转不了）
- [x] 双轨 SVG：`svg_output/`（原版含渐变，浏览器预览好看）/ `svg_final/`（压平版，供 PPTX 转换）

### UI & 交互 (NotebookLM 模式 · W8 重构)
- [x] **三栏布局 · 左栏可收缩**（展开 18% / 收缩 4% ≈ 60px）
  - 收缩时智能体显示为 40×40 icon 方块 + 状态点徽章
  - 使用 react-resizable-panels 原生 collapsible + ImperativePanelHandle
  - autoSaveId 记忆用户自定义宽度
- [x] **中栏 = 主对话区**（永远显示 ChatPanel，不再切换 Canvas）
- [x] **右栏 SlideWaterfall 瀑布**（替代 SlideList）
  - 三态视觉：todo（虚线框）/ generating（蓝色脉动）/ done（SVG 缩略图 + 绿勾）
  - **增量可见**：SSE `slide_status_change: done` 瞬间自动渲染缩略图，不等全部完成
  - sticky 顶栏：全部完成时显示"下载 PPTX"按钮，生成中显示进度条 N/M
  - 缩略图通过 `<img src="/project-files/.../slide_XX.svg">` 加载（静态挂载无鉴权）
- [x] **单页 Modal**（点击缩略图弹出）
  - 缩放工具栏：- / 适应 / 100% / + (0.25x–5x)
  - 左主区：inline SVG 渲染，适应模式 16:9 contain / 自由模式像素缩放
  - 右 320px AI 对话栏：独立上下文，发送调 `/slides/{id}/revise`
  - 底部：演讲者备注折叠面板
  - ESC / 遮罩 / ✕ 关闭
- [x] **演讲者备注 UI**（已随 Modal 整合）
  - 后端 `GET /outline` 已有 notes_speaker 字段
  - SSE `agent_complete: copywriter` 和 `generation_complete` 自动拉 outline 合并备注
- [x] **老项目打开自动填充 slides**（useSSE 初始化时拉 outline）

---

## 待开发清单

### 🔴 阶段 B（当前优先 · 接着做）
- [x] **B-1 · 设计师部分失败自动重试**（W8 完成）
  - 两遍策略：第一轮带 previous_svg，失败页第二轮不带 previous_svg 重试
  - 仍失败标 status='failed'，SSE 通知用户
  - 前端：红色虚线框 + 橙色"下载 PPTX（N 页缺失）"按钮
  - failed 页 Modal 显示失败提示，引导用 AI 栏手动修改
- [ ] **B-2 · 激活 LangGraph 诊断并行派发**
  - 基于 A-4 的单页修改能力，把诊断模式做成 LangGraph 并行节点
  - 诊断 → 分发到失败页 → 并行 revise → 汇总结果

### 🟡 阶段 A 剩余（视需求而定）
- [ ] **A-2.3 / A-2.4 · 消息卡片组件 + ChatPanel 迁移**
  - schema 已就位（types/messages.ts 定义了 12 种 kind）
  - 纯重构：把 currentQuestion / OutlineView / AgentActivityFeed 接入消息流
  - archived-subchat 归档（Modal 关闭时把 AI 对话存进主对话流）
  - 当前 ChatPanel 仍用旧逻辑，只渲染 text 卡片

### 🟢 Phase 4 · 架构升级（规划中，2-3 周）
- [x] **MVP-1 · DESIGN.md 模板库**（W9 完成，方式 A 落地）
  - 3 个预设模板 + API 切换 + 批量应用到全部页面
  - DESIGN.md 纯文本散文 → 设计师 LLM system prompt 消费
  - 切模板 0 代码 · 同内容套不同风格验证通过
- [x] **MVP-2 · 内容/设计 pipeline 分离**（W10 完成）
  - 文案师完成后 pipeline 暂停 → 右栏展示内容审核视图
  - 用户编辑 blocks（emphasis 语义级别 + 换行） → 确认后才跑设计师
  - 积累 content.json schema 样本为 Phase 4 本体做准备
- [ ] **MVP-3 · content.json 结构化内容**
  - 取代现有 SlideItem 的松散字段
  - blocks[{role, emphasis, text}] + image_intent
  - emphasis 映射到 DESIGN.md Typography section
- [ ] **Phase 4 本体 · 三层架构**（等 MVP-2/3 积累 20-30 份样本后启动）
  - 方式 B：layouts/*.svg.tmpl 模板引擎（确定性渲染，无 LLM 调用）
  - design-tokens parser（DESIGN.md → JSON）
  - 设计师从"画 SVG"转为"选 layout_id + 填内容"
- [ ] **独立 ImageAgent**（融入三层架构）
  - 读 content.json 的 image_intent → 输出 image_spec（不生成真实图）
  - 可选：匹配用户素材库 / 集成 Unsplash API
- [ ] **批量化 API**（Phase 4 商业化入口）
  - 一份 design + 多份 content → 批量出多套 PPT
  - 对接 CRM / 企业场景

### ⚠️ 长期 Backlog
- [ ] 版本快照 + 回退 UI
- [ ] Fabric.js 手动编辑（Phase 4 三层架构落地后再做，避开 SVG 烘焙坑）
- [ ] Crawl4AI 替代简单 HTML 抓取
- [ ] 中文字体渲染一致性测试
- [ ] 规划师左栏状态延迟（前端更新，不走 SSE）
- [ ] SVG 文件字体路径硬编码

---

## 关键设计决策与踩过的坑

### 已记录的坑（`docs/known-pitfalls.md`）
1. 思源黑体 OTF 无法嵌入 PPTX → 全项目只用 TTF
2. SVG 生成不能并发 → 顺序执行保证跨页风格一致
3. python-pptx 不支持字体嵌入 → 手动操作 ZIP 结构
4. Fabric.js 中文字体未预加载 → FontFace API 预加载
5. 规划师诊断模式上下文膨胀 → 只读 OUTLINE.md 摘要
6. OUTLINE.md 多智能体并发写 → fcntl 文件锁 + 原子替换
7. SSE 在 Nginx 代理后被缓冲 → X-Accel-Buffering: no
8. Celery 与 LangGraph 职责边界 → Celery 异步外壳，LangGraph 内部编排
9. PPTX 增量回写后页序乱 → 不删 slide 对象，清空内容后原位更新
10. 图表 SVG 嵌入后不可编辑 → 用 python-pptx add_chart() 生成 DrawingML

### 开发中新发现的坑
- **Qwen3 thinking mode**：默认开启 thinking，content 为空，需要 `extra_body={"enable_thinking": False}`
- **EventSource 不支持 headers**：SSE/下载端点需要 `?token=` query param 认证
- **Fabric.js v6 API 变化**：Image 创建方式不同，改用 inline SVG 渲染更简单
- **SqliteSaver 初始化**：新版 `from_conn_string()` 返回 context manager，需直接传 `sqlite3.Connection`
- **Celery task 注册**：autodiscover 不稳定，需要显式 import 保证注册
- **路由器端口映射**：本机通过路由器 NAT 暴露，公网 IP 12000 → 本机 3001
- **W8 · 静态文件浏览器缓存**：单页修改后 img 读旧版，SVG URL 需加 `?t=Date.now()` 破缓存
- **W8 · react-resizable-panels collapsible**：`defaultSize` 只在 mount 时读，动态收缩要用 `collapsible + collapsedSize + ImperativePanelHandle.collapse()`，不能靠改 state 重渲染
- **W8 · Celery solo pool 不 hot reload**：改 task 代码后必须重启 worker，否则新 task 不生效
- **W9 · FastAPI 路由顺序**：静态路径段（如 `/design-templates`）必须在动态段（`/{project_id}`）**之前**声明，否则 FastAPI 按定义顺序把 "design-templates" 当 project_id 传入，返回 404
- **W9 · ppt-master svg_to_pptx 不支持 gradient/pattern 填充**：`fill="url(#id)"` 会抛 "Can't handle color: url(#...)"。修复：把 gradient 首个 stop 色替换 url 引用（svg_flatten.py）
- **W9 · ppt-master finalize_svg 会 rmtree svg_final 再从 svg_output 复制**：任何 SVG 后处理（包括 sanitize）必须在 finalize_svgs **之后**执行，否则会被覆盖
- **W9 · LLM 生成 SVG 偶尔含未转义 `&`**：如 "Partnership & Future" → native XML 解析失败。修复：editor 打包前扫描 text/tspan body 做 XML 转义
- **W9 · editor fallback 会掩盖真错**：`try: source="final" except: source="output"` 的设计有毒——任何 final 失败都降级到含 url 的原版，使真实错误（1 页 XML 问题）被替换成误导性错误（"Can't handle url"）。已删除 fallback

### 多智能体架构反思
当前实现的"多智能体"本质上是：
- ✅ **成本优化**：不同任务用不同价格的模型
- ✅ **prompt 专注**：每个智能体关注单一职责，输出质量更稳定
- ✅ **可观测性**：用户看到明确的"文案师完成→设计师工作中"进度
- ⚠️ 但不是真正的"智能协作"，更像精心分工的 pipeline
- ⚠️ LangGraph 状态机大部分未使用（确认后直接跑顺序流水线）

**未来真正需要多智能体能力的场景**：
- 诊断模式：规划师分析问题 → 分发给不同智能体修改不同页 → 并行执行 → 汇总结果（B-2 要做）
- 迭代修改：单页修改只唤醒相关智能体（**A-4 已落地**：`/slides/{id}/revise` → 只跑 designer + editor）
- 智能体自主协商（设计师发现页面内容太多 → 主动建议文案师精简）

### W8 · 架构共识与 Phase 4 规划

**2026-04-17 与用户对齐的产品/架构方向**：

1. **交互模式 = NotebookLM 风格**
   - 左栏智能体（可收缩）/ 中栏对话（永远在）/ 右栏 slides 瀑布
   - 对话是主线，PPT 是 artifact，单页修改用 Modal 独立上下文
   - "对话连续性" 优先：规划 → 生成 → 单页修改全部在一条 timeline

2. **Phase 4 架构核心 · 内容/设计/布局三层分离**
   - 类似 HTML + CSS：content.md（Markdown 内容）/ design.md（色板/字体/间距/布局槽位）/ layouts/（SVG 模板含占位符）
   - 收益：**上下文成本骤降 10x**（规划师可读全部 PPT 做诊断）、**修改效率 10x**（换色板零 LLM 调用）、**母版天然支持**、**批量化 API 入口**
   - 代价：2-3 周重构，需要从现有 50+ SVG 样本反向归纳 design.md schema
   - 时机：Phase 3 跑稳、有足够样本后启动

3. **图片职能聚焦**
   - **不做**：生图（慢、贵、风格漂移）
   - **做**：占位框 + 英文 suggested_prompt（**A-5 已落地 prompt 版**，Phase 4 独立 ImageAgent）
   - 用户拿 prompt 自己去 Midjourney/DALL-E 生图，在 PowerPoint 中替换
   - 项目聚焦边界：结构化内容 + 风格化排版 + 单页修改，精修交给 PowerPoint

4. **手动编辑的取舍**
   - Modal 已预留"轻量手动"空间（双击文字、点击替换图片 —— 未实现）
   - 不做 Fabric.js 复杂编辑，不与 PowerPoint 抢蛋糕
   - 真正复杂的编辑导出 PPTX 在本地精修

---

## 开发环境启动

```bash
# 1. Redis (Docker)
docker start ppt-redis || docker run -d --name ppt-redis -p 6379:6379 redis:alpine

# 2. 后端 (0.0.0.0 为公网访问)
cd /Users/wenwenba2020/cc_workspace/ppt_agent
.venv/bin/uvicorn backend.api.main:app --host 0.0.0.0 --port 8000

# 3. Celery worker (solo pool，避免并发问题)
.venv/bin/celery -A backend.tasks worker --loglevel=info --pool=solo

# 4. 前端 (公网访问)
cd frontend
npx vite --host 0.0.0.0 --port 3001
```

### 关键配置

**`.env`**（核心配置项）：
```
OPENROUTER_API_KEY=sk-or-v1-...
LLM_API_PROVIDER=openrouter
LLM_PLANNER_MODEL=z-ai/glm-5.1
LLM_DESIGNER_MODEL=z-ai/glm-5.1
LLM_COPYWRITER_MODEL=deepseek/deepseek-v3.2
LLM_EFFECTS_MODEL=qwen/qwen3.5-9b
TAVILY_API_KEY=tvly-dev-...
ADMIN_PASSWORD=admin123
JWT_SECRET=...
```

**`.mcp.json`**（Claude Code MCP 集成）：
- Tavily MCP (搜索/网页抓取)
- Exa MCP (AI 搜索)

---

## 测试

```bash
.venv/bin/pytest backend/tests/ -q
# 58 passed, 1 pre-existing failure (test_run_global_mode)
# 59 passed
```

**关键测试文件**：
- `test_api.py`: FastAPI 路由 + JWT 认证 (6)
- `test_outline.py`: OUTLINE.md 解析/序列化/文件锁 (10)
- `test_storage.py`: 文件存储抽象 + 路径遍历防护 (6)
- `test_parsers.py`: PDF/DOCX/PPTX 解析 (6)
- `test_pipeline.py`: 字体管理 + 图表渲染 (12)
- `test_agents.py`: LangGraph + 规划师 + 文案师 + JSON 提取 (16)
- `test_designer.py`: 设计师顺序生成 + locked 跳过 (3)

---

*本文档随开发进度更新。历史进度参见 `docs/todo.md`，关键坑点参见 `docs/known-pitfalls.md`。*
