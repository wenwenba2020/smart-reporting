# MVP-2 · 内容/设计 pipeline 分离 · 文案审核闸门

> 日期：2026-04-21
> 关联：`docs/dev-log.md` Phase 4 · MVP-2
> 范围：后端 pipeline 拆分 + 前端文字排版审核视图 + 用户确认闸门

---

## 1. 目标与非目标

### 目标
- 文案师完成后 pipeline **暂停**，不自动进入设计师
- 右栏瀑布流每页显示**带排版格式的文字内容**（按 layout 类型分支渲染）
- 用户**确认**后才跑设计师/效果师/编辑师
- 用户可在审核态下打开 Modal 文字编辑 tab 修改文案，修改不触发 SVG 生成

### 非目标（明确 YAGNI）
- content.json blocks schema（留给 MVP-3）
- 文案级整体重写 / 回退规划师（留给 Phase 4 之后）
- 富文本 / emphasis 选择器 / 拖拽排序
- 设计态的审核闸门（本次只在 copywriter 后设一道闸）
- 逐页勾选确认（默认全通过，单独打回走 Modal 编辑）

---

## 2. 核心决策（brainstorming 结论）

| # | 选项 | 决定 |
|---|------|------|
| Q1 | 审核态交互定位 | **C** · 卡片只读 + Modal 编辑入口 + 顶部「确认进入设计」按钮 |
| Q2 | 后端暂停机制 | **B** · 拆两个 Celery task（不改 LangGraph checkpointing） |
| Q3 | 文字排版保真度 | **B** · 按 layout 分支（cover/section/content/comparison/chart），数据源沿用 OUTLINE.md |
| Q4 | 确认粒度 | **C** · 默认全通过 + 可单独打开 Modal 修改 |
| Q5 | 回退规划师出口 | **A** · 不给，想重来只能删项目新建（Modal 编辑可覆盖大多数精修诉求） |

---

## 3. 项目状态机

在 `project` 表加 `stage` 字段（字符串，默认 `'idle'`）：

| stage | 含义 | 进入时机 |
|---|---|---|
| `idle` | 未开始 / 规划中 | 建项目 |
| `planning` | 三阶段规划中 | 开始规划 |
| `copywriting` | 文案师生成中 | task-1 启动 |
| `awaiting_content_review` | **文案完毕、等待用户确认** | task-1 结束 |
| `designing` | 设计师/效果师/编辑师运行中 | task-2 启动 |
| `completed` | 下载就绪 | editor 完成 |
| `failed` | 任一环节彻底失败 | 异常处理 |

**约束**：
- `stage = awaiting_content_review` 时，后端拒绝 designer 相关调用（返回 409）
- 老项目迁移：启动时扫描，有完整 `svg_output/` → `completed`；仅 OUTLINE → `awaiting_content_review`；都没 → `idle`。幂等（基于 `stage = 'idle'` 判定）。
- SQLite：直接 `ALTER TABLE ADD COLUMN IF NOT EXISTS`（项目已有简易迁移模式）

---

## 4. 后端 Pipeline 拆分

### 4.1 Celery task

```
旧：run_full_generation(project_id)
    → graph.invoke(researcher → planner → copywriter → designer → effects → editor)

新：
  run_copywriter_only(project_id)
    前置：stage ∈ {idle, planning}
    → copywriter 节点
    → 写 OUTLINE.md
    → stage = 'awaiting_content_review'
    → SSE push 'content_ready'

  run_designer_and_beyond(project_id)
    前置：stage = 'awaiting_content_review'
    → stage = 'designing'（原子 UPDATE）
    → graph.invoke(designer → effects → editor)
    → stage = 'completed'
```

### 4.2 API

| 路由 | 作用 |
|---|---|
| `POST /projects/{id}/content/confirm` | 用户点确认，原子检查 stage，触发 task-2 |
| `GET /projects/{id}/outline` | 审核视图数据源，**不改** |
| `POST /projects/{id}/slides/{sid}/revise` | 按 stage 分支：审核态只回写 OUTLINE.md，designing/completed 时仍改 SVG |

**`/content/confirm` 原子性**：
```sql
UPDATE projects SET stage='designing'
WHERE id=? AND stage='awaiting_content_review'
```
rowcount=0 → 409 Conflict（双击保护）

### 4.3 SSE 新事件

| event | payload | 触发 |
|---|---|---|
| `content_ready` | `{}` | copywriter 全部完成（前端收到后调 `/outline` 刷新） |
| `stage_change` | `{stage}` | 每次 stage 流转 |
| `slide_content_changed` | `{slide_id}` | 审核态下单页文案被 revise 修改 |

规划师阶段已有的 SSE 事件不改。

---

## 5. 前端审核视图

### 5.1 状态

- `projectStore` 加 `stage: ProjectStage` 字段
- `useSSE` 监听 `stage_change` / `content_ready` / `slide_content_changed`
- 初次打开项目时 `GET /projects/{id}` 带回 stage

### 5.2 SlideCard 渲染分支

```
status === 'done'                    → SVG 缩略图（现状）
stage === 'awaiting_content_review'  → 文字版式卡片（新，按 layout 分支）
status === 'generating'              → 蓝色脉动（现状）
status === 'failed'                  → 红色虚线框（现状）
status === 'todo'                    → 灰色页码（现状）
```

### 5.3 文字版式子组件

新增 `frontend/src/components/SlideWaterfall/text-layouts/`，5 个组件，尺寸 16:9，Tailwind 等比字号：

| 组件 | 适用 layout | 渲染 |
|---|---|---|
| `CoverText` | cover / title | 大标题居中 + 副标题灰字 + 作者行 |
| `SectionText` | section / chapter | 左侧超大章节号 + 右侧大标题 |
| `ContentText` | content / bullets（默认） | 顶部标题 + • bullets 列表（≤5，溢出省略） |
| `ComparisonText` | comparison / vs | 标题 + 左右两列（points 前后折半） |
| `ChartText` | chart | 标题 + `📊 [chart 类型]` 占位条 + bullets |

未知 layout 回落到 `ContentText`。

### 5.4 顶部审核条

`stage === 'awaiting_content_review'` 时替换 SlideWaterfall 顶部的"下载 PPTX"按钮：

```
📝 文案审核中 · 点击任一页可编辑
[ ✅ 确认文案，进入设计阶段 (N 页) ]
```

点击 → `POST /content/confirm` → 乐观切 stage=designing → 等 SSE 驱动后续。

### 5.5 修改路径

用户点卡片 → Modal 打开「文字编辑 tab」（W8 已有）→ 改标题/要点/备注 → 保存调 `POST /slides/{sid}/revise`（审核态语义：只回写 OUTLINE.md）→ 后端 SSE `slide_content_changed` → 卡片重渲染。

---

## 6. 异常与边界

| 场景 | 行为 |
|---|---|
| task-1 copywriter 失败 | stage → `failed`，前端红色提示 + 「重跑文案」按钮 |
| task-2 designer 部分页失败 | 沿用 W8 现状，失败页标 `failed`，不回退 stage |
| 审核期关闭浏览器再回来 | `GET /projects/{id}` 返回 stage，前端进入审核视图 |
| 绕过前端双调 `/content/confirm` | 第二次 409 |
| revise 在错误 stage 被调 | `designing`/`completed` 改 SVG；`awaiting_content_review` 只改 OUTLINE；其它 409 |

**并发**：`/content/confirm` 靠 SQL 原子 UPDATE 保护，避免双 task-2。

**回归风险**：
- 前端 ChatPanel SSE 监听要改：`content_ready` 后不再期待 designer 事件直到用户点确认
- `test_run_global_mode` 与旧全流程相关，需调整或替换

---

## 7. 实施切片

### 切片 A · 后端闸门（~0.5 天）
- DB 加 `stage` 字段 + 启动迁移 + 老项目回填
- 拆 `run_copywriter_only` / `run_designer_and_beyond`
- 新增 `POST /content/confirm`（原子 UPDATE）
- `slides/{sid}/revise` 加 stage 分支
- SSE 新增 3 个事件
- 单测：stage 机、confirm 幂等、revise 分支、老项目迁移

### 切片 B · 前端审核视图（~1 天）
- store 加 `stage`；useSSE 监听新事件
- 5 个 text-layouts 组件
- SlideCard 审核态分支
- 顶部审核条 + 确认按钮 → `/content/confirm`
- Modal 文字编辑 tab 保存走审核态分支
- `content_ready` 到达拉 `/outline` 合并

### 切片 C · 回归收尾（~0.5 天）
- E2E 冒烟：需求 → 规划 → 文案 → 审核 → 改一页 → 确认 → 设计 → 下载
- 调整/替换 `test_run_global_mode`
- 更新 `docs/dev-log.md` MVP-2 标 ✅，同步 `docs/todo.md`

**总计 ~2 天**

---

## 8. 测试要点

- **后端**：`stage` 状态机在各 API 下的转换正确；confirm 双击只触发一次 task；revise 在 3 种 stage 下行为分叉正确；老项目迁移幂等
- **前端**：审核态 5 种 layout 渲染快照；顶部按钮点击后乐观切态；SSE `slide_content_changed` 触发单卡重渲染；Modal 保存流正确
- **E2E**：完整冒烟流（含一次"改一页文案"）

---

## 9. 文档更新

- `docs/dev-log.md`：MVP-2 条目标 ✅，新增"Phase 3 W10 · 内容审核闸门"一节
- `docs/todo.md`：移除 MVP-2 条目
- `docs/agents-spec.md`：如 copywriter 行为有细节变动则追加（预计无）
