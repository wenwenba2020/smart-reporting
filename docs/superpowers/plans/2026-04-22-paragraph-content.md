# 文案段落结构化（points → PointItem） Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `SlideItem.points` 从 `list[str]` 升级为 `list[{heading, body}]`，让文案师为每个要点挂一段 120-250 字的具体讲解，前端能看到"小标题 + 段落"的层次，老数据懒升级无缝兼容。

**Architecture:** Pydantic `PointItem` 新模型 + `field_validator` 读侧兼容 `list[str]`；OUTLINE.md 的 points 小节复用 YAML 子文档（`yaml.safe_load` 同时吃 `- str` 和 `- {heading, body}` 两种形态）；copywriter prompt 按 layout 分类产出 body；designer prompt 拼 heading+body；前端边界 `normalizePoint` 统一形态，text-layouts 与 Modal 编辑面板双字段渲染。

**Tech Stack:** Python 3.12 · Pydantic v2 · PyYAML · FastAPI · React 19 · TypeScript · Tailwind v4 · Zustand

**关联 Spec:** `docs/superpowers/specs/2026-04-22-paragraph-content-design.md`

---

## Ground Rules

- 每个后端 task 严格 TDD：先失败测试 → 跑测试确认失败 → 最小实现 → 跑测试确认通过 → commit
- 前端无 Jest，用 `npm run build` 的 TypeScript 类型检查 + 任务末手动冒烟
- 路径一律绝对路径，Python 命令用 `.venv/bin/python` / `.venv/bin/pytest`
- 当前分支：`feat/paragraph-content`（已切好）
- commit message 风格：`feat(scope): 中文描述` / `fix(scope): 描述`

---

## File Structure

### 修改
- `backend/models/outline.py` — 新增 `PointItem`；`SlideItem.points` 类型改；加 `field_validator`；`_parse_slide_block` 改用 YAML 子文档解析；`serialize_outline` 新格式写出
- `backend/agents/copywriter.py` — prompt 改输出 list[dict]；按 layout 规则；赋值改为 list[PointItem]（或 dict，靠 validator 吃）
- `backend/agents/designer.py` — OUTLINE 片段拼 heading+body
- `backend/api/routes/generate.py` — `SlideContentPatch.points` 类型改为 `list[PointItem] | None`
- `backend/tests/test_outline.py` — 新增 points 兼容性测试（或新建 test_point_item.py）
- `backend/tests/test_content_gate.py` — 更新 `test_update_slide_content_in_review_stage` 使用新 schema
- `frontend/src/types/events.ts` — 加 `PointItem`，`SlideItem.points: PointItem[]`
- `frontend/src/hooks/useSSE.ts` — `normalizePoint` helper + 在 `loadInitialSlides` 应用
- `frontend/src/components/SlideWaterfall/text-layouts/CoverText.tsx` — 读 `points[0]?.heading`
- `frontend/src/components/SlideWaterfall/text-layouts/ContentText.tsx` — **重点**：heading + body 两层渲染
- `frontend/src/components/SlideWaterfall/text-layouts/ComparisonText.tsx` — 读 `p.heading`
- `frontend/src/components/SlideWaterfall/text-layouts/ChartText.tsx` — 读 `p.heading`
- `frontend/src/components/SlideModal/index.tsx` — `contentDraft.points: PointItem[]`；`ContentEditorPanel` 每个 point 变成 heading input + body textarea 卡片
- `docs/dev-log.md` — Phase 3 W11 条目 ✅

### 新建
- 无（测试扩充现有文件即可）

---

# Task 1: Backend · PointItem 模型 + OUTLINE 解析/序列化

**Files:**
- Modify: `/Users/wenwenba2020/cc_workspace/ppt_agent/backend/models/outline.py`
- Test: `/Users/wenwenba2020/cc_workspace/ppt_agent/backend/tests/test_outline.py` (append)

这是全局最关键的一步：改 schema 必须保证老 OUTLINE.md 能正常读写。

- [ ] **Step 1: Write failing tests**

Append to `backend/tests/test_outline.py` (or create if missing):

```python
def test_point_item_model_basic():
    from backend.models.outline import PointItem
    p = PointItem(heading="标题", body="段落内容")
    assert p.heading == "标题"
    assert p.body == "段落内容"

    p2 = PointItem(heading="仅标题")
    assert p2.body is None


def test_slide_item_accepts_list_of_strings_for_backward_compat():
    """老 OUTLINE.md 里 points 是 list[str]，Pydantic validator 应自动转。"""
    from backend.models.outline import SlideItem
    s = SlideItem(
        slide_id="01", layout="title-content", title="T",
        points=["要点一", "要点二"],
    )
    assert len(s.points) == 2
    assert s.points[0].heading == "要点一"
    assert s.points[0].body is None
    assert s.points[1].heading == "要点二"


def test_slide_item_accepts_list_of_dicts():
    from backend.models.outline import SlideItem
    s = SlideItem(
        slide_id="01", layout="title-content", title="T",
        points=[
            {"heading": "A", "body": "body A"},
            {"heading": "B"},
        ],
    )
    assert s.points[0].body == "body A"
    assert s.points[1].body is None


def test_slide_item_mixed_str_and_dict_in_points():
    from backend.models.outline import SlideItem
    s = SlideItem(
        slide_id="01", layout="title-content", title="T",
        points=["纯字符串", {"heading": "混合", "body": "段落"}],
    )
    assert s.points[0].heading == "纯字符串"
    assert s.points[0].body is None
    assert s.points[1].heading == "混合"
    assert s.points[1].body == "段落"


def test_outline_parse_serialize_roundtrip_new_format():
    """解析 + 序列化 point 带 body 的新格式"""
    import tempfile
    from pathlib import Path
    from backend.models.outline import (
        OutlineDoc, OutlineMeta, SlideItem, PointItem,
        save_outline, load_outline,
    )

    outline = OutlineDoc(
        meta=OutlineMeta(title="T", total_slides=1, created_at="x", updated_at="x"),
        slides=[SlideItem(
            slide_id="01", layout="title-content", title="Test",
            points=[
                PointItem(heading="第一要点", body="第一段具体讲解 100 字..."),
                PointItem(heading="第二要点"),  # body=None
            ],
        )],
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "OUTLINE.md"
        save_outline(outline, path)
        loaded = load_outline(path)

    assert loaded.slides[0].points[0].heading == "第一要点"
    assert loaded.slides[0].points[0].body == "第一段具体讲解 100 字..."
    assert loaded.slides[0].points[1].heading == "第二要点"
    assert loaded.slides[0].points[1].body is None


def test_outline_parse_old_string_list_points():
    """老 OUTLINE.md 里 points 是 `  - 文字` 纯列表，应解析为 heading=文字 的 PointItem"""
    content = """---
title: Old Project
format: ppt169
total_slides: 1
status: draft
created_at: '2026-01-01'
updated_at: '2026-01-01'
planner_version: '1.0'
design_ref: ./DESIGN.md
---

## Slides

### [01] 老项目页
layout: title-content
status: todo
points:
  - 要点一
  - 要点二
"""
    from backend.models.outline import parse_outline
    outline = parse_outline(content)
    s = outline.slides[0]
    assert len(s.points) == 2
    assert s.points[0].heading == "要点一"
    assert s.points[0].body is None
    assert s.points[1].heading == "要点二"
```

- [ ] **Step 2: Run tests, expect FAIL**

```bash
cd /Users/wenwenba2020/cc_workspace/ppt_agent
.venv/bin/pytest backend/tests/test_outline.py -v -k "point_item or list_of_strings or list_of_dicts or mixed_str or roundtrip_new_format or old_string_list" 2>&1 | tail -30
```

Expected: FAILS (ImportError: PointItem not in backend.models.outline)

- [ ] **Step 3: Add `PointItem` + `field_validator`**

Edit `backend/models/outline.py`:

Update import block (top of file) — add `field_validator`:

```python
from pydantic import BaseModel, Field, field_validator
```

Add `PointItem` class before `SlideItem` (e.g., right after `MediaConfig`):

```python
class PointItem(BaseModel):
    heading: str
    body: str | None = None
```

Modify `SlideItem.points`:

```python
    points: list[PointItem] = Field(default_factory=list)

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
            else:
                result.append(x)  # already PointItem
        return result
```

- [ ] **Step 4: Rewrite parse / serialize to use YAML block for points**

In `_parse_slide_block`, replace the `elif stripped.startswith("- ") and not in_chart:` branch with block-YAML parsing for the `points:` section. The new logic:

Find the current implementation around lines 105-191. Replace the whole function with:

```python
def _parse_slide_block(slide_id: str, title: str, lines: list[str]) -> SlideItem:
    """Parse a single slide block from OUTLINE.md lines into a SlideItem.

    points 小节用 YAML 块解析，兼容 `- str` 与 `- {heading, body}` 两种形态。
    """
    fields: dict[str, Any] = {"slide_id": slide_id, "title": title}
    points_block: list[str] = []
    in_points = False
    in_chart = False
    in_media = False
    chart_lines: list[str] = []
    media_dict: dict[str, str] = {}

    for line in lines:
        # detect exit from points block: any non-indented, non-empty line
        if in_points:
            if line.strip() == "" or line.startswith("  ") or line.startswith("\t"):
                points_block.append(line)
                continue
            else:
                in_points = False  # fall through to handle this line

        stripped = line.strip()
        if not stripped:
            continue

        if ":" in stripped and not stripped.startswith("-"):
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip()

            if key == "points":
                in_points = True
                in_chart = False
                in_media = False
                points_block = []
                continue

            if key == "chart":
                in_chart = True
                in_media = False
                chart_lines = []
                continue
            if in_chart and key in ("type", "data_ref", "data", "caption"):
                chart_lines.append(stripped)
                continue

            if key == "media":
                in_chart = False
                if val == "~":
                    fields["media"] = None
                    in_media = False
                elif val:
                    fields["media"] = MediaConfig(background=val)
                    in_media = False
                else:
                    in_media = True
                    media_dict = {}
                continue
            if in_media and key in ("background", "image"):
                media_dict[key] = val
                continue

            if in_chart:
                in_chart = False
            if in_media:
                if media_dict:
                    fields["media"] = MediaConfig(**media_dict)
                in_media = False

            if key == "layout":
                fields["layout"] = val
            elif key == "status":
                fields["status"] = val
            elif key == "subtitle":
                fields["subtitle"] = val if val != "~" else None
            elif key == "visual_intent":
                fields["visual_intent"] = val if val != "~" else None
            elif key == "notes_speaker":
                fields["notes_speaker"] = val.strip('"').strip("'")
            elif key == "locked":
                fields["locked"] = val.lower() == "true"

        elif in_chart and stripped.startswith("-"):
            chart_lines.append(stripped)

    if in_media and media_dict:
        fields["media"] = MediaConfig(**media_dict)

    if points_block:
        # Dedent 2 spaces so yaml.safe_load can parse the list
        dedented = "\n".join(
            line[2:] if line.startswith("  ") else line
            for line in points_block
        )
        try:
            parsed = yaml.safe_load(dedented)
            if isinstance(parsed, list):
                fields["points"] = parsed  # validator handles str/dict
        except Exception:
            pass

    if chart_lines:
        chart_yaml = "\n".join(chart_lines)
        try:
            chart_data = yaml.safe_load(chart_yaml)
            if isinstance(chart_data, dict):
                fields["chart"] = ChartConfig(**chart_data)
        except Exception:
            pass

    return SlideItem(**fields)
```

In `serialize_outline`, replace the existing points block:

```python
        if s.points:
            lines.append("points:")
            for p in s.points:
                lines.append(f"  - heading: {p.heading}")
                if p.body:
                    # Multi-line body: preserve as YAML block scalar
                    if "\n" in p.body:
                        lines.append(f"    body: |")
                        for body_line in p.body.splitlines():
                            lines.append(f"      {body_line}")
                    else:
                        # Simple inline; guard colons/quotes by using quoted form
                        escaped = p.body.replace('"', '\\"')
                        lines.append(f'    body: "{escaped}"')
```

Leave the rest of `serialize_outline` untouched.

Also update `get_summary` (around line 84): `"points_count": len(s.points)` still works (list length).

- [ ] **Step 5: Run tests, expect PASS**

```bash
.venv/bin/pytest backend/tests/test_outline.py -v 2>&1 | tail -30
```

Expected: all new tests pass; no regression in pre-existing tests.

Also run full suite:

```bash
.venv/bin/pytest backend/tests/ -v 2>&1 | tail -15
```

Baseline before this task: 70 passed + 1 pre-existing failure. After: acceptable if new tests pass + no new failures beyond pre-existing.

- [ ] **Step 6: Commit**

```bash
cd /Users/wenwenba2020/cc_workspace/ppt_agent
git add backend/models/outline.py backend/tests/test_outline.py
git commit -m "feat(backend): PointItem 模型 + OUTLINE 新格式 parse/serialize（兼容 list[str] 老数据）"
```

---

# Task 2: Backend · Copywriter prompt 升级

**Files:**
- Modify: `/Users/wenwenba2020/cc_workspace/ppt_agent/backend/agents/copywriter.py`
- Test: `/Users/wenwenba2020/cc_workspace/ppt_agent/backend/tests/test_agents.py` (append new test or adjust existing `test_run_copywriter`)

- [ ] **Step 1: Write failing test**

Append to `backend/tests/test_agents.py`:

```python
@patch("backend.agents.copywriter.chat")
def test_run_copywriter_accepts_structured_points(mock_chat, tmp_path):
    """文案师返回 list[{heading, body}]，写入后 OUTLINE.md 保留结构。"""
    from backend.agents.copywriter import run_copywriter
    from backend.models.outline import OutlineDoc, OutlineMeta, SlideItem, save_outline, load_outline

    mock_chat.return_value = (
        '{"title": "市场规模", '
        '"points": ['
        '{"heading": "2024 突破 500 亿", "body": "据 Gartner 数据，2024 年全球 AI 芯片..."}, '
        '{"heading": "中国占比提升", "body": "中国市场在 2024 年..."}'
        '], '
        '"notes_speaker": "重点强调增长趋势"}'
    )

    outline = OutlineDoc(
        meta=OutlineMeta(title="T", total_slides=1, created_at="x", updated_at="x"),
        slides=[SlideItem(slide_id="01", layout="title-content", title="Old")],
    )
    path = tmp_path / "OUTLINE.md"
    save_outline(outline, path)

    result = run_copywriter("proj-x", str(path))
    assert "01" in result["completed_slides"]

    reloaded = load_outline(path)
    s = reloaded.slides[0]
    assert s.title == "市场规模"
    assert len(s.points) == 2
    assert s.points[0].heading == "2024 突破 500 亿"
    assert s.points[0].body.startswith("据 Gartner")
    assert s.points[1].body.startswith("中国市场在")


@patch("backend.agents.copywriter.chat")
def test_run_copywriter_still_accepts_legacy_string_points(mock_chat, tmp_path):
    """LLM 返回老格式 list[str]（向下兼容），validator 仍能升级为 PointItem。"""
    from backend.agents.copywriter import run_copywriter
    from backend.models.outline import OutlineDoc, OutlineMeta, SlideItem, save_outline, load_outline

    mock_chat.return_value = (
        '{"title": "测试", "points": ["纯字符串要点"], "notes_speaker": "N"}'
    )
    outline = OutlineDoc(
        meta=OutlineMeta(title="T", total_slides=1, created_at="x", updated_at="x"),
        slides=[SlideItem(slide_id="01", layout="title-content", title="Old")],
    )
    path = tmp_path / "OUTLINE.md"
    save_outline(outline, path)

    run_copywriter("proj-x", str(path))
    reloaded = load_outline(path)
    assert reloaded.slides[0].points[0].heading == "纯字符串要点"
    assert reloaded.slides[0].points[0].body is None
```

- [ ] **Step 2: Run tests, expect FAIL**

```bash
.venv/bin/pytest backend/tests/test_agents.py::test_run_copywriter_accepts_structured_points backend/tests/test_agents.py::test_run_copywriter_still_accepts_legacy_string_points -v
```

Expected: FAIL because copywriter currently slices points as `p[:30]` (treats each as str).

- [ ] **Step 3: Update copywriter**

Edit `backend/agents/copywriter.py`:

Replace `COPYWRITER_SYSTEM`:

```python
COPYWRITER_SYSTEM = """你是 PPT 文案师。根据页面布局和主题，为幻灯片生成精炼的中文文案。

严格遵守：
- title: 不超过 15 个字
- points: 返回一个列表，每项是 {"heading": 短标题（≤30 字）, "body": 段落讲解}
  - layout 为 cover / title-only / toc 时：body 填 null，heading 简短
  - layout 为 title-content / two-col / three-col / comparison / data-chart / timeline / team 时：body **必填**，120-250 字，围绕 heading 展开数据 / 论据 / 案例 / 方法论
  - 不编造数据；无依据时写分析框架或背景
  - 最多 5 条
- notes_speaker: 演讲者备注，50-100 字
- 不做排版决策，不提及字体或颜色

返回 JSON：
{
  "title": "...",
  "subtitle": "...",
  "points": [
    {"heading": "...", "body": "..."},
    {"heading": "...", "body": null}
  ],
  "notes_speaker": "..."
}"""
```

Change the points assignment (around line 90-91):

```python
            if "points" in content:
                raw_points = content["points"][:5]
                coerced = []
                for p in raw_points:
                    if isinstance(p, str):
                        coerced.append({"heading": p[:30], "body": None})
                    elif isinstance(p, dict):
                        coerced.append({
                            "heading": str(p.get("heading", ""))[:30],
                            "body": p.get("body") if p.get("body") else None,
                        })
                slide.points = coerced  # SlideItem validator converts to PointItem
```

- [ ] **Step 4: Run tests, expect PASS**

```bash
.venv/bin/pytest backend/tests/test_agents.py -v 2>&1 | tail -20
```

Expected: both new tests pass; `test_run_copywriter` (if pre-existing) may need update if it asserts `points[0] == str`. Check and adjust that assertion too if present.

Also run full suite:

```bash
.venv/bin/pytest backend/tests/ -v 2>&1 | tail -15
```

- [ ] **Step 5: Commit**

```bash
git add backend/agents/copywriter.py backend/tests/test_agents.py
git commit -m "feat(backend): copywriter prompt 输出 {heading, body} 结构化 points"
```

---

# Task 3: Backend · Designer prompt 拼 heading + body

**Files:**
- Modify: `/Users/wenwenba2020/cc_workspace/ppt_agent/backend/agents/designer.py`

- [ ] **Step 1: Locate the OUTLINE snippet builder**

The function around line 140 builds `parts` with `points:` joined. Current:

```python
    if slide.points:
        parts.append(f"points:\n" + "\n".join(f"  - {p}" for p in slide.points))
```

This iterates `slide.points` as if each item is a str; after Task 1 they're `PointItem` objects, so this would produce `"  - heading='X' body='Y'"` (ugly). Must update.

- [ ] **Step 2: Replace the block with heading + body aware rendering**

Replace the `if slide.points:` branch with:

```python
    if slide.points:
        points_lines = ["points:"]
        for p in slide.points:
            points_lines.append(f"  - {p.heading}")
            if p.body:
                for body_line in p.body.splitlines():
                    points_lines.append(f"    {body_line}")
        parts.append("\n".join(points_lines))
```

This produces (for the designer prompt):

```
points:
  - 2024 突破 500 亿
    据 Gartner 数据，2024 年全球 AI 芯片...
  - 中国占比提升
    中国市场在 2024 年...
```

- [ ] **Step 3: Run existing designer tests to ensure no regression**

```bash
cd /Users/wenwenba2020/cc_workspace/ppt_agent
.venv/bin/pytest backend/tests/test_designer.py -v 2>&1 | tail -15
```

If any test constructs `SlideItem(points=["str"])` and examines the prompt text, it should still pass (validator turns strings into PointItem(heading=s, body=None), so the branch produces `  - str` with no body lines — same as old behavior).

Also full suite:

```bash
.venv/bin/pytest backend/tests/ -v 2>&1 | tail -10
```

- [ ] **Step 4: Commit**

```bash
git add backend/agents/designer.py
git commit -m "feat(backend): designer prompt 读 PointItem 拼 heading + body 两级文本"
```

---

# Task 4: Backend · SlideContentPatch 升级 + 审核态测试

**Files:**
- Modify: `/Users/wenwenba2020/cc_workspace/ppt_agent/backend/api/routes/generate.py`
- Modify: `/Users/wenwenba2020/cc_workspace/ppt_agent/backend/tests/test_content_gate.py`

- [ ] **Step 1: Update failing tests first**

Find the existing `test_update_slide_content_in_review_stage` in `backend/tests/test_content_gate.py`. Replace the body call:

```python
    body = SlideContentPatch(title="New Title", points=["new a", "new b", "new c"])
```

with:

```python
    body = SlideContentPatch(
        title="New Title",
        points=[
            {"heading": "new a", "body": "具体段落 A"},
            {"heading": "new b"},  # no body
            {"heading": "new c", "body": None},
        ],
    )
```

And update the assertion block:

```python
    # OUTLINE actually changed
    outline2 = load_outline(tmp_path / pid / "OUTLINE.md")
    s = outline2.slides[0]
    assert s.title == "New Title"
    assert len(s.points) == 3
    assert s.points[0].heading == "new a"
    assert s.points[0].body == "具体段落 A"
    assert s.points[1].heading == "new b"
    assert s.points[1].body is None
```

- [ ] **Step 2: Run test, expect FAIL**

```bash
.venv/bin/pytest backend/tests/test_content_gate.py::test_update_slide_content_in_review_stage -v
```

Expected: FAIL — `SlideContentPatch.points` is typed `list[str] | None`, rejects dicts.

- [ ] **Step 3: Update `SlideContentPatch` in `backend/api/routes/generate.py`**

Add import at top (merge with existing outline import if present):

```python
from backend.models.outline import PointItem
```

Change:

```python
class SlideContentPatch(BaseModel):
    title: str | None = None
    subtitle: str | None = None
    points: list[str] | None = None
    notes_speaker: str | None = None
```

to:

```python
class SlideContentPatch(BaseModel):
    title: str | None = None
    subtitle: str | None = None
    points: list[PointItem] | None = None
    notes_speaker: str | None = None
```

**Important:** Pydantic will handle `list[dict]` / `list[str]` to `list[PointItem]` via its own coercion rules but `list[str]` → `list[PointItem]` doesn't auto-coerce because PointItem is a BaseModel (expects dict). If frontend sends strings by mistake, Pydantic will 422. That's acceptable (frontend will be upgraded in Task 6 to send dicts). To still accept strings from old clients, add a validator:

```python
from pydantic import field_validator

class SlideContentPatch(BaseModel):
    title: str | None = None
    subtitle: str | None = None
    points: list[PointItem] | None = None
    notes_speaker: str | None = None

    @field_validator("points", mode="before")
    @classmethod
    def _coerce_points(cls, v):
        if v is None:
            return None
        if not isinstance(v, list):
            return v
        return [
            {"heading": x, "body": None} if isinstance(x, str) else x
            for x in v
        ]
```

Note: `pydantic` and `BaseModel` already imported at top of `generate.py` (pre-existing).

- [ ] **Step 4: Update route body to persist PointItem cleanly**

The existing route (the `update_slide_content` function) currently does:

```python
    if body.points is not None:
        slide.points = body.points
```

After the type change, `body.points` is `list[PointItem]`. Since `SlideItem.points` validator also accepts that, this stays correct — no route-body change needed.

But verify: open the function and read it. If it does any `str`-specific operation on points, adjust.

- [ ] **Step 5: Run tests, expect PASS**

```bash
.venv/bin/pytest backend/tests/test_content_gate.py -v 2>&1 | tail -20
```

Expected: 11/11 pass (all pre-existing + updated test).

Full suite:

```bash
.venv/bin/pytest backend/tests/ -v 2>&1 | tail -15
```

- [ ] **Step 6: Commit**

```bash
git add backend/api/routes/generate.py backend/tests/test_content_gate.py
git commit -m "feat(backend): SlideContentPatch.points 升级为 list[PointItem]（兼容 list[str]）"
```

---

# Task 5: Frontend · types + normalizePoint 边界

**Files:**
- Modify: `/Users/wenwenba2020/cc_workspace/ppt_agent/frontend/src/types/events.ts`
- Modify: `/Users/wenwenba2020/cc_workspace/ppt_agent/frontend/src/hooks/useSSE.ts`
- Modify: `/Users/wenwenba2020/cc_workspace/ppt_agent/frontend/src/api/client.ts`

- [ ] **Step 1: Extend types**

Edit `frontend/src/types/events.ts`. Add `PointItem` interface and update `SlideItem.points`:

```typescript
export interface PointItem {
  heading: string
  body?: string | null
}

export interface SlideItem {
  slide_id: string
  title: string
  layout: string
  status: SlideStatus
  points: PointItem[]   // was: string[]
  locked: boolean
  notes_speaker?: string
}
```

- [ ] **Step 2: Update SlideContentPatch in api client**

Edit `frontend/src/api/client.ts`. Find `SlideContentPatch` (added in Task 10.5b of MVP-2). Update:

```typescript
export interface SlideContentPatch {
  title?: string
  subtitle?: string
  points?: import('@/types/events').PointItem[]  // was: string[]
  notes_speaker?: string
}
```

Or preferably import at top:

```typescript
import type { PointItem } from '@/types/events'
```

and then:

```typescript
export interface SlideContentPatch {
  title?: string
  subtitle?: string
  points?: PointItem[]
  notes_speaker?: string
}
```

- [ ] **Step 3: Add normalizePoint helper + apply in useSSE**

Edit `frontend/src/hooks/useSSE.ts`. Add near the top helpers (above `loadInitialSlides`):

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

Merge `PointItem` into the existing type import:

```typescript
import type { PointItem, SlideItem, SlideStatus } from '@/types/events'
```

In `loadInitialSlides`, update the mapping:

```typescript
    const slides: SlideItem[] = (data.slides || []).map((s: Record<string, unknown>) => ({
      slide_id: String(s.slide_id ?? ''),
      title: String(s.title ?? ''),
      layout: String(s.layout ?? ''),
      status: VALID_STATUS.includes(s.status as SlideStatus) ? (s.status as SlideStatus) : 'todo',
      points: Array.isArray(s.points) ? (s.points as unknown[]).map(normalizePoint) : [],
      locked: Boolean(s.locked),
      notes_speaker: typeof s.notes_speaker === 'string' ? s.notes_speaker : '',
    }))
```

- [ ] **Step 4: Type-check**

```bash
cd /Users/wenwenba2020/cc_workspace/ppt_agent/frontend
npm run build
```

Expected: this will FAIL in SlideModal / text-layouts until Task 6 and Task 7 land (they still treat points as string[]). That's expected — we commit this task's minimal slice, then immediately dispatch the next task that consumes it.

**If the build fails due to the upstream consumers, that's OK for this task** — acknowledge in the commit message. Proceed to Step 5.

- [ ] **Step 5: Commit**

```bash
cd /Users/wenwenba2020/cc_workspace/ppt_agent
git add frontend/src/types/events.ts frontend/src/hooks/useSSE.ts frontend/src/api/client.ts
git commit -m "feat(frontend): PointItem 类型 + normalizePoint 规范化边界（SlideModal/text-layouts 需 Task 6-7 同步）"
```

---

# Task 6: Frontend · 5 个 text-layouts 适配 PointItem

**Files:**
- Modify: `/Users/wenwenba2020/cc_workspace/ppt_agent/frontend/src/components/SlideWaterfall/text-layouts/CoverText.tsx`
- Modify: `/Users/wenwenba2020/cc_workspace/ppt_agent/frontend/src/components/SlideWaterfall/text-layouts/ContentText.tsx`
- Modify: `/Users/wenwenba2020/cc_workspace/ppt_agent/frontend/src/components/SlideWaterfall/text-layouts/ComparisonText.tsx`
- Modify: `/Users/wenwenba2020/cc_workspace/ppt_agent/frontend/src/components/SlideWaterfall/text-layouts/ChartText.tsx`

（SectionText 不用 points，跳过）

- [ ] **Step 1: CoverText**

Edit `CoverText.tsx`:

```tsx
import type { SlideItem } from '@/types/events'

export function CoverText({ slide }: { slide: SlideItem }) {
  const subtitle = slide.points[0]?.heading || ''
  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center text-center px-4 bg-gradient-to-br from-blue-50 to-white">
      <h2 className="text-[13px] font-bold text-slate-800 leading-tight mb-1 line-clamp-2">
        {slide.title || '未命名封面'}
      </h2>
      {subtitle && (
        <p className="text-[9px] text-slate-500 line-clamp-1">{subtitle}</p>
      )}
    </div>
  )
}
```

- [ ] **Step 2: ContentText (重点 · 两级视觉)**

Edit `ContentText.tsx`:

```tsx
import type { SlideItem } from '@/types/events'

export function ContentText({ slide }: { slide: SlideItem }) {
  const shown = slide.points.slice(0, 5)
  const rest = slide.points.length - shown.length
  return (
    <div className="absolute inset-0 flex flex-col px-3 py-2 bg-white">
      <h3 className="text-[10px] font-semibold text-slate-800 mb-1 line-clamp-1 border-b border-slate-200 pb-1">
        {slide.title || '内容页'}
      </h3>
      <ul className="flex-1 min-h-0 space-y-1 overflow-hidden">
        {shown.map((p, i) => (
          <li key={i} className="leading-tight">
            <div className="flex gap-1 text-[8px] text-slate-800 font-medium">
              <span className="text-slate-400 shrink-0">•</span>
              <span className="line-clamp-1">{p.heading}</span>
            </div>
            {p.body && (
              <p className="text-[7px] text-slate-500 line-clamp-2 pl-2 mt-0.5">
                {p.body}
              </p>
            )}
          </li>
        ))}
        {rest > 0 && (
          <li className="text-slate-400 italic text-[7px]">… 还有 {rest} 条</li>
        )}
      </ul>
    </div>
  )
}
```

- [ ] **Step 3: ComparisonText**

Edit `ComparisonText.tsx`:

```tsx
import type { SlideItem } from '@/types/events'

export function ComparisonText({ slide }: { slide: SlideItem }) {
  const half = Math.ceil(slide.points.length / 2)
  const left = slide.points.slice(0, half)
  const right = slide.points.slice(half)
  return (
    <div className="absolute inset-0 flex flex-col px-2 py-2 bg-white">
      <h3 className="text-[10px] font-semibold text-slate-800 mb-1 line-clamp-1 text-center">
        {slide.title || '对比'}
      </h3>
      <div className="flex-1 min-h-0 grid grid-cols-2 gap-1 text-[7px]">
        <div className="bg-blue-50 rounded p-1 overflow-hidden">
          {left.map((p, i) => (
            <p key={i} className="text-slate-700 leading-tight line-clamp-1">• {p.heading}</p>
          ))}
        </div>
        <div className="bg-orange-50 rounded p-1 overflow-hidden">
          {right.map((p, i) => (
            <p key={i} className="text-slate-700 leading-tight line-clamp-1">• {p.heading}</p>
          ))}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: ChartText**

Edit `ChartText.tsx`:

```tsx
import type { SlideItem } from '@/types/events'

export function ChartText({ slide }: { slide: SlideItem }) {
  const shown = slide.points.slice(0, 3)
  return (
    <div className="absolute inset-0 flex flex-col px-3 py-2 bg-white">
      <h3 className="text-[10px] font-semibold text-slate-800 mb-1 line-clamp-1 border-b border-slate-200 pb-1">
        {slide.title || '图表页'}
      </h3>
      <div className="bg-slate-100 rounded h-8 flex items-center justify-center text-[9px] text-slate-500 mb-1">
        📊 图表占位
      </div>
      <ul className="flex-1 min-h-0 text-[8px] text-slate-600">
        {shown.map((p, i) => (
          <li key={i} className="line-clamp-1 leading-tight">• {p.heading}</li>
        ))}
      </ul>
    </div>
  )
}
```

- [ ] **Step 5: Build check**

```bash
cd /Users/wenwenba2020/cc_workspace/ppt_agent/frontend
npm run build
```

This will still fail in SlideModal (Task 7 handles it). Proceed.

- [ ] **Step 6: Commit**

```bash
cd /Users/wenwenba2020/cc_workspace/ppt_agent
git add frontend/src/components/SlideWaterfall/text-layouts
git commit -m "feat(frontend): 4 个 text-layouts 读 PointItem · ContentText 显示 heading+body 两级"
```

---

# Task 7: Frontend · SlideModal ContentEditorPanel 升级

**File:**
- Modify: `/Users/wenwenba2020/cc_workspace/ppt_agent/frontend/src/components/SlideModal/index.tsx`

- [ ] **Step 1: Update state type + initializer**

Find the line:

```typescript
  const [contentDraft, setContentDraft] = useState<{ title: string; subtitle: string; points: string[]; notes_speaker: string } | null>(null)
```

Change to:

```typescript
  const [contentDraft, setContentDraft] = useState<{ title: string; subtitle: string; points: PointItem[]; notes_speaker: string } | null>(null)
```

Add `PointItem` import at the top:

```typescript
import type { PointItem } from '@/types/events'
```

- [ ] **Step 2: Update draft initializer effect**

Find the `useEffect` that resets `contentDraft` when `slide` / `isReviewStage` change. The body sets `points: [...(slide.points || [])]`. This already copies the array; since `slide.points` is now `PointItem[]`, just update any downstream assumptions.

If the existing line is:

```typescript
        points: [...(slide.points || [])],
```

Change to (same logic, just type-correct):

```typescript
        points: (slide.points || []).map((p) => ({ heading: p.heading, body: p.body ?? null })),
```

This clones each PointItem (shallow) so edits don't mutate the store's slide object.

- [ ] **Step 3: Update save handler**

Find `handleSaveContent`. Currently the patch build:

```typescript
        points: contentDraft.points.filter((p) => p.trim() !== ''),
```

Change to:

```typescript
        points: contentDraft.points
          .filter((p) => p.heading.trim() !== '' || (p.body && p.body.trim() !== ''))
          .map((p) => ({ heading: p.heading.trim(), body: p.body && p.body.trim() !== '' ? p.body : null })),
```

(If the exact existing code differs, adapt — the semantic is: drop fully empty rows, trim, normalize empty body to null.)

- [ ] **Step 4: Update ContentEditorPanel handlers + render**

Inside `ContentEditorPanel`, replace the `updatePoint(i, v)` handler with two:

```tsx
  const updatePointHeading = (i: number, v: string) => {
    const next = [...draft.points]
    next[i] = { ...next[i], heading: v }
    setDraft({ ...draft, points: next })
  }
  const updatePointBody = (i: number, v: string) => {
    const next = [...draft.points]
    next[i] = { ...next[i], body: v }
    setDraft({ ...draft, points: next })
  }
  const addPoint = () => setDraft({ ...draft, points: [...draft.points, { heading: '', body: null }] })
  const removePoint = (i: number) =>
    setDraft({ ...draft, points: draft.points.filter((_, idx) => idx !== i) })
```

Replace the point render block inside the "要点" section (the `{draft.points.map((p, i) => ...)}` block) with:

```tsx
          {draft.points.map((p, i) => (
            <div key={i} className="rounded border border-slate-200 p-2 space-y-1.5 bg-slate-50/60">
              <div className="flex gap-1 items-start">
                <input
                  value={p.heading}
                  onChange={(e) => updatePointHeading(i, e.target.value)}
                  disabled={saving}
                  placeholder="小标题"
                  className="flex-1 rounded-md border px-2 py-1 text-xs outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
                />
                <button
                  type="button"
                  onClick={() => removePoint(i)}
                  disabled={saving}
                  className="w-6 h-6 flex items-center justify-center rounded-md text-muted-foreground hover:text-red-600 hover:bg-red-50 disabled:opacity-30 shrink-0"
                  title="删除"
                >
                  ×
                </button>
              </div>
              <textarea
                value={p.body ?? ''}
                onChange={(e) => updatePointBody(i, e.target.value)}
                disabled={saving}
                rows={3}
                placeholder="段落正文（可选，120-250 字）"
                className="w-full rounded-md border px-2 py-1 text-xs outline-none focus:ring-2 focus:ring-ring disabled:opacity-50 resize-none"
              />
            </div>
          ))}
```

Update the interface if needed:

```typescript
interface ContentEditorPanelProps {
  draft: { title: string; subtitle: string; points: PointItem[]; notes_speaker: string } | null
  setDraft: (d: { title: string; subtitle: string; points: PointItem[]; notes_speaker: string } | null) => void
  onSave: () => void
  saving: boolean
  error: string | null
}
```

- [ ] **Step 5: Type-check (should pass now)**

```bash
cd /Users/wenwenba2020/cc_workspace/ppt_agent/frontend
npm run build
```

Expected: build succeeds, no type errors.

- [ ] **Step 6: Commit**

```bash
cd /Users/wenwenba2020/cc_workspace/ppt_agent
git add frontend/src/components/SlideModal/index.tsx
git commit -m "feat(frontend): Modal 内容编辑面板升级为 PointItem（heading input + body textarea 卡片）"
```

---

# Task 8: E2E 冒烟 + dev-log 收尾

- [ ] **Step 1: Full backend tests**

```bash
cd /Users/wenwenba2020/cc_workspace/ppt_agent
.venv/bin/pytest backend/tests/ -v 2>&1 | tail -20
```

Expected: all new tests from Tasks 1-4 pass; no new failures beyond the pre-existing `test_run_global_mode`.

- [ ] **Step 2: E2E smoke**

Ensure Redis + uvicorn + celery + vite running (refer to `CLAUDE.md` startup section).

Flow:
1. 新建项目 → 输入需求 → 三阶段规划
2. 文案师跑完 → **右栏 ContentText 卡片**应显示"• 小标题" + 下面小字段落
3. 点某张卡 → Modal 打开 → **内容编辑面板**每项是"heading input + body textarea"卡片
4. 改一个 body → 保存 → 卡片文字更新（SSE → loadInitialSlides）
5. 确认进入设计 → 设计师跑完 → SVG 里应看到两级视觉（大字 heading + 小字段落）
6. 下载 PPTX，打开看段落内容确实写进了 slide

Test 老项目：打开之前已完成的项目，右栏显示应保持不变（body=null 时视觉与之前一致）。

If any step fails, classify (backend / frontend / prompt quality) and fix, commit, re-test.

- [ ] **Step 3: Update dev-log**

Edit `docs/dev-log.md`:

Find `Phase 3 W10` row in the progress table. Add below:

```markdown
| Phase 3 W11 | 文案段落结构化 · PointItem（heading + body）+ 向下兼容 | ✅ 完成 | — |
```

Find the "内容/设计分离 MVP-2（W10 新增）" section. After it (before MVP-1 section) add:

```markdown
### 文案段落结构化（W11 新增）
- [x] **PointItem 模型**（`SlideItem.points: list[PointItem]`，每项带 `heading` + 可选 `body`）
- [x] **懒升级 · 向下兼容**：Pydantic `field_validator` 读 `list[str]` 自动转 PointItem；首次 save 自动升级 OUTLINE.md 格式
- [x] **OUTLINE.md 新格式**：points 改用 YAML 块（`- heading: ... / body: ...`）；PyYAML 解析兼容旧 `- str` 列表
- [x] **Copywriter prompt 分层**：cover/section/toc body 留空；content/comparison/chart/two-col 等必写 120-250 字 body
- [x] **Designer prompt 拼 heading+body 两级文本**：body 为 null 时输出等同旧版
- [x] **SlideContentPatch.points 升级为 list[PointItem]**，审核态保存走新 schema
- [x] **前端 normalizePoint 边界**：useSSE.loadInitialSlides 统一形态
- [x] **ContentText 两级可视化**：顶行加粗 heading + 下行小字 body 缩略（line-clamp-2）
- [x] **Modal 编辑面板升级**：每项一个卡片（heading 单行 input + body 多行 textarea）
```

- [ ] **Step 4: Commit dev-log**

```bash
git add docs/dev-log.md
git commit -m "docs: 更新 dev-log 记录 W11 迭代（文案段落结构化）"
```

- [ ] **Step 5: Merge feature branch to main**

```bash
git checkout main
git merge --no-ff feat/paragraph-content -m "merge: 文案段落结构化（PointItem）落地"
git log --oneline -3
```

---

# Self-Review

**Spec coverage:**
- §3 数据模型 → Task 1
- §4.1 Copywriter prompt → Task 2
- §4.2 Designer prompt → Task 3
- §4.3 SlideContentPatch → Task 4
- §5.1-5.2 前端类型 + normalize → Task 5
- §5.3 text-layouts → Task 6
- §5.4-5.5 Modal ContentEditorPanel → Task 7
- §6 懒升级 → Task 1 validator + Task 2 copywriter 写侧
- §7 异常 → 覆盖在 Task 1/2/4 的测试
- §8 切片 + §9 文档 → Tasks 8

**Placeholder scan:** 无 "TBD" / "和 Task N 类似" / 模糊占位。所有 code 块给出完整代码。

**Type consistency:**
- `PointItem` 在后端（Pydantic） / 前端（TS interface）/ API payload 全程一致：`{heading: str, body: str | None}`
- `SlideContentPatch` 字段命名一致（`title / subtitle / points / notes_speaker`）
- `normalizePoint` / `updatePointHeading` / `updatePointBody` / `addPoint` / `removePoint` 命名稳定
- 老测试如 `test_run_copywriter` 若断言 `points[0] == str`，Task 2 Step 4 已提示排查（现在 `points[0]` 是 `PointItem`）

---

# Execution Handoff

计划已保存到 `docs/superpowers/plans/2026-04-22-paragraph-content.md`。

两种执行方式：

1. **Subagent-Driven（推荐）** — 每个 task 派一个 fresh subagent，task 间我做 review
2. **Inline Execution** — 在当前会话连跑，批量 + checkpoint

选哪个？
