# 文案段落升级（points → PointItem 结构化）设计

> 日期：2026-04-22
> 关联：改善 #2 · 文案师生成的二级小标题下具体段落内容缺失/单薄
> 分支：`feat/paragraph-content`

---

## 1. 目标与非目标

### 目标
- `SlideItem.points` 从 `list[str]` 升级为 `list[{heading, body}]`：每个要点都可挂一段 100-300 字的具体讲解
- 文案师（copywriter）对 content / comparison / chart 页自动产出带 body 的 points
- 右栏瀑布流 ContentText 可视化出"小标题 + 段落"的层次
- Modal 审核态内容编辑面板支持编辑 heading + body
- 老 OUTLINE.md（纯 str 列表）无感兼容，用"懒升级"策略

### 非目标（YAGNI）
- Stage 3 规划师改动（points 在规划态仍只是 heading 占位）
- Designer SVG 布局对段落的特殊视觉处理（让现有 prompt 自然吸收）
- editor / ppt-master 脚本改动
- 一次性数据迁移脚本（懒升级即可）
- 为封面页 / 章节页产生段落（这些版式不需要）

---

## 2. 核心决策（brainstorming 结论）

| # | 选项 | 决定 |
|---|------|------|
| Q · schema 形态 | 扁平 `body_paragraph` / 结构化 `sections[]` / 混合 `points: [{heading, body}]` | **C** · 混合，向下兼容性最好且贴合用户语义 |
| 迁移策略 | 一次性脚本 vs 懒升级 | **懒升级**（读侧 validator，写侧统一新格式） |
| 封面/章节页 body | 强制 vs 可选 | **可选**（body=null 时视觉不变） |

---

## 3. 数据模型

### 3.1 Pydantic 模型（`backend/models/outline.py`）

```python
class PointItem(BaseModel):
    heading: str
    body: str | None = None


class SlideItem(BaseModel):
    ...
    points: list[PointItem] = []

    @field_validator("points", mode="before")
    @classmethod
    def _coerce_points(cls, v):
        """兼容老 OUTLINE.md：list[str] → list[PointItem(heading=s, body=None)]"""
        if not isinstance(v, list):
            return []
        result = []
        for x in v:
            if isinstance(x, str):
                result.append({"heading": x, "body": None})
            elif isinstance(x, dict):
                result.append(x)
            # PointItem instance passes through via pydantic default
            else:
                result.append(x)
        return result
```

### 3.2 OUTLINE.md 表示

```yaml
slides:
  - slide_id: '03'
    layout: content
    title: '市场规模与增长'
    points:
      - heading: '2024 全球 AI 芯片市场突破 500 亿美元'
        body: '据 Gartner...（150 字段落）'
      - heading: '中国占比稳步上升'
        body: null    # 暂无段落
```

### 3.3 Pydantic v2 序列化

默认输出 YAML 时 `body: None` 会序列化为 `body: null`。保持不变，读回时 Pydantic 自然接受。

---

## 4. 后端 Copywriter & Designer

### 4.1 Copywriter prompt（`backend/agents/copywriter.py`）

现有要求输出：
```json
{"title": "...", "points": ["str", "str"], "notes_speaker": "..."}
```

改为：
```json
{
  "title": "...",
  "points": [
    {"heading": "短标题 (≤20 字)", "body": "120-250 字段落"},
    {"heading": "...", "body": "..."}
  ],
  "notes_speaker": "..."
}
```

**规则（注入到 system prompt）**：
- 对 `layout` ∈ {cover, section, chapter}：`body` 全部 null，保持简短
- 对 `layout` ∈ {content, title-content, comparison, chart}：**每个 point 的 body 必写**，120-250 字
- body 内容围绕 heading 展开论据 / 数据 / 案例 / 方法论；无依据则写分析框架而非虚构数字
- 不生成 "以上/以下/综上" 式连接语

**向下兼容**：若某次 LLM 返回缺 body 字段，Pydantic `_coerce_points` 会把 dict 原样传入，`body` 默认 None（验证器不抛错）。

### 4.2 Designer prompt（`backend/agents/designer.py`）

当前向设计师注入的 OUTLINE 片段里 `points` 是 bullet 文本列表。改为拼接 `heading + body`（body 非空时）：

```
- 2024 全球 AI 芯片市场突破 500 亿美元
  据 Gartner 与 IDC 数据，2024 年全球 AI 芯片市场规模同比增长 45%...（150 字）
- 中国占比稳步上升
  （无段落）
```

这样设计师生成 SVG 时可以用**两级字号**视觉化（大字 heading + 小字 body）。若某 point 的 body 为 null，仍按旧版单 bullet 渲染。

### 4.3 审核态路由

`PUT /projects/{id}/slides/{sid}/content` 的 `SlideContentPatch` 字段升级：

```python
class SlideContentPatch(BaseModel):
    title: str | None = None
    subtitle: str | None = None
    points: list[PointItem] | None = None
    notes_speaker: str | None = None
```

路由里原 `slide.points = body.points` 依然生效，Pydantic 负责类型转换。

### 4.4 其它消费方审计

- `editor.py` / `effects.py`：不读 points 文本字段，无需改
- `run_slide_revision`（审核态分支）：已走 OUTLINE load/save，靠 Pydantic validator 兼容
- `ensure_stage_column` 等迁移：无关

---

## 5. 前端

### 5.1 类型（`frontend/src/types/events.ts`）

```typescript
export interface PointItem {
  heading: string
  body?: string | null
}

export interface SlideItem {
  ...
  points: PointItem[]  // 从 string[] 升级
  ...
}
```

### 5.2 规范化边界（`frontend/src/hooks/useSSE.ts`）

`loadInitialSlides` 里对 points 做统一规范化：

```typescript
function normalizePoint(p: unknown): PointItem {
  if (typeof p === 'string') return { heading: p, body: null }
  if (p && typeof p === 'object') {
    const o = p as { heading?: unknown; body?: unknown }
    return {
      heading: typeof o.heading === 'string' ? o.heading : '',
      body: typeof o.body === 'string' ? o.body : null,
    }
  }
  return { heading: '', body: null }
}
```

应用于 `(data.slides || []).map(...)` 里读 `s.points` 的位置。

### 5.3 5 个 text-layouts 渲染

| 版式 | 变更 |
|---|---|
| CoverText | `points[0]?.heading` 作副标题 |
| SectionText | 不变（本来不用 points） |
| ContentText | **重点**：每项显示 `• heading`（加粗）+ 若 body 存在，下一行 text-[7px] line-clamp-2 显示 body |
| ComparisonText | 显示 `• heading`，body 省略 |
| ChartText | 显示 `• heading`，body 省略 |

### 5.4 Modal 内容编辑（`SlideModal` → `ContentEditorPanel`）

每个 point 从"单行 textarea"升级为：

```
┌──────────────────────────────────┐
│ [heading 单行 input               ]│
│ [body 多行 textarea（rows=3）    ] │
│                               [×] │
└──────────────────────────────────┘
```

保存时把 `draft.points` 传给 `updateSlideContent`，schema 已对齐。

### 5.5 草稿状态结构更新

`contentDraft` 的 points 从 `string[]` 改为 `PointItem[]`。`addPoint` 追加 `{heading:'', body:null}`，`updatePoint` 分两个 handler：`updatePointHeading(i, v)` / `updatePointBody(i, v)`。

---

## 6. 数据兼容策略（懒升级）

| 场景 | 行为 |
|---|---|
| 老 OUTLINE.md（list[str]）load | validator 转 list[PointItem]，body=null |
| 老项目打开不改动 | 文件保持 list[str]，前端规范化后显示 heading 列表（body=null） |
| 老项目任一次 save（revise / content edit / copywriter 重跑）| 自动写成 list[PointItem] 新格式 |
| 新项目 | copywriter 直接产出 list[PointItem] |

**无需一次性迁移脚本。**

---

## 7. 异常与边界

| 场景 | 行为 |
|---|---|
| LLM 返回缺 body 字段 | validator 接受 dict，body 默认 None |
| LLM 返回 `body: "null"`（字符串 null） | 视作有效非空字符串（不做特判，让 LLM prompt 负责） |
| heading 超长 | 前端 line-clamp-1 截断显示，数据库完整保存 |
| points 为空数组 | 所有 text-layouts 已 handle empty case |

**回归风险**：
- Copywriter 输出 token ↑ ~5×（每页从 ~300 到 ~1500），单次生成成本从 $0.01 量级升到 $0.05 量级，可接受
- Designer prompt 输入 token ↑（OUTLINE 截取加长），若超 designer 模型 context，需要在 `run_designer` 里对超长 body 做 truncation（暂不做，先观察）

---

## 8. 实施切片

### 切片 A · 后端 schema + prompt（~0.5 天）
- `outline.py` 新增 PointItem + validator
- copywriter prompt 改 list[dict] 输出，分 layout 规则
- designer prompt 拼 heading + body
- `SlideContentPatch.points` 类型升级
- 单测：validator 兼容 str / dict，copywriter mock 新 schema 仍被接受

### 切片 B · 前端规范化 + 渲染（~0.5 天）
- `types/events.ts` 升级
- `useSSE.ts` normalizePoint
- 5 个 text-layouts 更新（重点 ContentText heading+body）
- SlideModal.ContentEditorPanel 双字段卡片
- `npm run build` 验证

### 切片 C · 收尾 + E2E 冒烟（~0.25 天）
- E2E：新项目 → 规划 → 文案 → 审核 → body 可见 + 可编辑 → 保存 → 确认 → 设计 → 下载
- 老项目打开：纯 heading 显示 OK
- dev-log.md：Phase 3 W11 条目 ✅

**总 ~1.25 天**

---

## 9. 文档更新

- `docs/dev-log.md`：Phase 3 W11 标 ✅，增"文案段落结构化（PointItem）"一节
- `docs/agents-spec.md`：若有"points 字段"说明则同步（待检查）
- `docs/data-formats.md`：更新 OUTLINE.md schema 示例
