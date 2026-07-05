# 五智能体详细规格

> 写任何智能体代码前必读。

---

## 总体架构

```
用户输入
   ↓
意图路由器（规划师）
   ├── 全局生成模式 → 文案师 → 设计师 → 效果师 → 编辑师
   ├── 路由模式 → 直接路由到对应智能体（不经过完整流水线）
   └── 诊断模式 → 规划师诊断 → ⛔确认 → 对应智能体
```

---

## 规划师（Planner）

**文件**：`backend/agents/planner.py`
**模型**：Gemini 3.1 Pro（`google/gemini-3.1-pro-preview`，via OpenRouter）
**角色**：整个系统的"大脑"，根据情况切换三种工作模式

### 模式一：全局生成模式

**触发条件**：用户首次提交需求，或明确要求"重新生成整个PPT"

**输入**：
- 用户需求（自然语言）
- 源文档的 Markdown 摘要（不是原始文档全文）
- 用户选择的模板 ID

**处理流程**：
1. 分析文档结构和用户意图
2. 生成 OUTLINE.md 的 slides 部分（所有页 status=todo）
3. ⛔ **BLOCKING**：等待用户确认大纲（用户可增删页、调整顺序）
4. 确认后：根据模板 ID 写入 DESIGN.md
5. 向后续智能体分发任务

**输出**：已确认的 OUTLINE.md + DESIGN.md

**关键约束**：
- 大纲中每页 `points` 不超过 5 条
- 每条 points 不超过 30 字
- 不生成 SVG，不做排版决策

### 模式二：路由模式

**触发条件**：用户消息中明确指向某页（"第3页"、"营收分析那页"）

**处理流程**：
1. 解析修改意图
2. 判断归属（只能选其一或并发多个）：
   - 文字内容改动 → 路由给文案师
   - 排版/视觉改动 → 路由给设计师
   - 图表/图片改动 → 路由给效果师
   - 多维度改动 → 并发路由多个智能体
3. **不重新生成大纲**，不消耗全量上下文
4. 只读 OUTLINE.md 对应页字段（不读 SVG 文件）

**输出**：路由指令（目标智能体 + slide_id + 修改参数）

### 模式三：诊断模式

**触发条件**：用户反馈笼统，不包含具体页码
- "内容有点单薄"
- "视觉冲击力不够"
- "感觉不够专业"

**处理流程**：
1. 读取 OUTLINE.md 的结构摘要（调用 `outline.get_summary()`）
2. ⚠️ **绝对不读** `svg_output/` 目录
3. 从三个维度扫描问题：
   - 内容维度：points 是否充实，数据是否具体
   - 视觉维度：layout 选择是否合适，是否有图表
   - 结构维度：页面逻辑是否清晰，节奏是否合理
4. 生成诊断报告：问题描述 + 修改提案 + 影响页列表
5. ⛔ **BLOCKING**：等待用户确认（用户可接受全部/剔除几条）
6. 确认后按页分发任务

**输出**：用户确认后的修改任务列表

---

## 文案师（Copywriter）

**文件**：`backend/agents/copywriter.py`
**模型**：DeepSeek V3.2（`deepseek/deepseek-v3.2`，via OpenRouter）

**职责**：从源文档提炼内容，生成每页文案

**输入**：
- 目标页的 layout + visual_intent
- 源文档中与该页主题相关的段落（切片，不是全文）
- DESIGN.md 的排版规范（字数限制等）

**输出**：填写完整的 OUTLINE.md 单页内容字段：
- `title`（≤15字）
- `subtitle`（可选）
- `points`（每条≤30字，最多5条）
- `notes_speaker`（演讲者备注，可比幻灯片更详细）

**关键约束**：
- 不负责排版，不生成 SVG
- 不修改其他页的字段
- 修改完成后将该页 status 从 todo 改为 todo（保持，等设计师）
- 写入 OUTLINE.md 时必须加文件锁

---

## 设计师（Designer）

**文件**：`backend/agents/designer.py`
**模型**：Claude Sonnet 4.6（`anthropic/claude-sonnet-4.6`，via OpenRouter）

**职责**：根据 OUTLINE.md 单页内容 + DESIGN.md，生成该页的 SVG 排版

**输入**：
- 单页完整字段（title/subtitle/points/chart/visual_intent）
- DESIGN.md 全文
- ppt-master 对应 layout 的模板 SVG（`backend/skills/ppt-master/templates/layouts/`）
- 前一页生成的 SVG（用于保持跨页风格一致）

**输出**：`svg_output/slide_{id}.svg`

**SVG 规范**：
- viewBox 必须是 `0 0 960 540`（PPT 16:9 标准）
- 字体引用必须与 DESIGN.md 完全一致
- 每页 SVG 顶部必须包含 `@font-face` 声明块
- 字体路径格式：`url('/fonts/{FontName}/{FontName}-{Weight}.ttf')`

**最重要的约束**：
```python
# 正确：顺序生成，保持上下文连续
async def generate_all_slides(outline: OutlineDoc):
    previous_svg = None
    for slide in outline.slides:
        if slide.status == "locked":
            continue  # 跳过锁定页
        svg = await generate_single_slide(slide, previous_svg)
        save_svg(svg, slide.slide_id)
        update_outline_status(slide.slide_id, "done")
        previous_svg = svg  # 传递给下一页

# 错误：禁止并发
# await asyncio.gather(*[generate_single_slide(s) for s in slides])
```

**生成完成后**：将该页 status 更新为 `done`

---

## 效果师（Effects）

**文件**：`backend/agents/effects.py`
**模型**：Qwen3.5 Flash（`qwen/qwen3.5-flash-02-23`，via OpenRouter）

**职责**：处理所有图片和图表资产

### 图片来源优先级（严格按此顺序）

1. **参考 PPT 提取**（`user://extract/...`）
   - 由 `backend/parsers/ppt_parser.py` 解析
   - 用户上传参考 PPTX 时自动执行
   
2. **用户直接上传**（`user://uploads/...`）
   - 上传时保存到 `projects/{id}/assets/uploads/`
   
3. **ECharts/pyecharts 数据图表**（`ai://charts/...`）
   - 调用 `backend/pipeline/chart_renderer.py`
   - 输出 SVG 格式（可缩放，不是光栅图）
   - ⚠️ 图表必须用 python-pptx `add_chart()` 插入，不是插入 SVG 图片
   
4. **AI 生成兜底**（`ai://generated/...`）
   - 调用 WaveSpeed Nano / Flux API
   - 异步生成，不阻塞主流程
   - 生成完成后通知前端更新

### 图表生成规范

```python
# 正确：输出用于 python-pptx add_chart() 的数据结构
def generate_chart_data(chart_config: ChartConfig) -> dict:
    return {
        "chart_type": XL_CHART_TYPE.BAR_CLUSTERED,
        "categories": [...],
        "series": [{"name": "...", "values": [...]}]
    }

# 错误：不要输出 SVG 图片再插入
# svg_bytes = render_echart_to_svg(...)  # 这样插入后不可编辑
```

---

## 编辑师（Editor）

**文件**：`backend/agents/editor.py`
**模型**：无（调脚本，不用 LLM）

**职责**：SVG → DrawingML 转换，增量回写 PPTX

### 完整生成流水线（按顺序执行）

```python
async def full_generation(project_path: str):
    # Step 1: 提取演讲者备注
    run_script("total_md_split.py", project_path)
    
    # Step 2: SVG 后处理（路径优化、字体检查）
    run_script("finalize_svg.py", project_path)
    
    # Step 3: SVG → DrawingML 转换
    run_script("svg_to_pptx.py", project_path, "-s", "final")
    
    # Step 4: 嵌入字体（zipfile 操作，不是 python-pptx）
    embed_fonts_in_pptx(
        f"{project_path}/exports/native.pptx",
        get_fonts_for_project(project_path)
    )
    
    # Step 5: 生成双输出
    # native.pptx: DrawingML 原生形状（主要交付物）
    # reference_svg.pptx: SVG 图片参考版
```

### 单页增量回写（关键）

```python
def update_single_slide(pptx_path: str, slide_index: int, new_svg_path: str):
    """
    只更新 PPTX 中的指定页，其余页保持不变。
    ⚠️ 不删除 slide 对象，清空内容后原位更新。
    """
    prs = Presentation(pptx_path)
    slide = prs.slides[slide_index]
    
    # 清空该页所有形状（保留 slide 对象本身）
    sp_tree = slide.shapes._spTree
    for shape in list(slide.shapes):
        sp_tree.remove(shape.element)
    
    # 从新 SVG 生成 DrawingML 并插入
    new_shapes = svg_to_drawingml(new_svg_path)
    for shape_xml in new_shapes:
        sp_tree.append(shape_xml)
    
    prs.save(pptx_path)
    # 更新 OUTLINE.md 中该页 status 为 done
```

### 字体嵌入（必须手动操作 ZIP）

```python
def embed_fonts_in_pptx(pptx_path: str, font_files: list[str]) -> str:
    """
    python-pptx 不支持字体嵌入，必须手动操作 ZIP 结构。
    ⚠️ 在副本上操作，避免原文件损坏。
    """
    work_path = pptx_path.replace('.pptx', '_embedded.pptx')
    shutil.copy2(pptx_path, work_path)
    
    with zipfile.ZipFile(work_path, 'a') as zf:
        for font_path in font_files:
            font_name = Path(font_path).name
            zf.write(font_path, f'ppt/fonts/{font_name}')
        
        # 1. 读取并更新 [Content_Types].xml
        content_types = zf.read('[Content_Types].xml').decode()
        # 添加字体 content type（如果不存在）
        font_ct = '<Override PartName="/ppt/fonts/{name}" ContentType="application/x-fontdata"/>'
        # ... 插入到 content_types 中
        
        # 2. 读取并更新 ppt/_rels/presentation.xml.rels
        # 添加字体 relationship
    
    return work_path
```

---

## LangGraph 状态机

**文件**：`backend/graph/workflow.py`

### PPTState 定义

```python
from typing import TypedDict, Optional, List, Literal

class PPTState(TypedDict):
    project_id: str
    outline_path: str
    design_path: str
    mode: Literal["global", "route", "diagnose"]
    user_message: str
    target_slide_ids: List[str]   # 空=全局，有值=指定页
    planner_output: Optional[dict]
    diagnosis_report: Optional[dict]
    task_queue: List[dict]        # [{agent, slide_id, action, params}]
    awaiting_confirmation: bool
    confirmation_type: Optional[str]
    user_confirmed: bool
    current_agent: Optional[str]
    completed_slides: List[str]
    failed_slides: List[str]
    error_log: List[str]
    export_path: Optional[str]
```

### 图结构

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

workflow = StateGraph(PPTState)

# 节点
workflow.add_node("intent_router", intent_router_node)
workflow.add_node("planner_global", planner_global_node)
workflow.add_node("planner_diagnose", planner_diagnose_node)
workflow.add_node("human_confirm", human_confirm_node)
workflow.add_node("copywriter", copywriter_node)
workflow.add_node("designer", designer_node)
workflow.add_node("effects", effects_node)
workflow.add_node("editor", editor_node)
workflow.add_node("route_handler", route_handler_node)

# 入口
workflow.set_entry_point("intent_router")

# 条件边
workflow.add_conditional_edges("intent_router", route_by_mode, {
    "global": "planner_global",
    "route": "route_handler",
    "diagnose": "planner_diagnose",
})
workflow.add_edge("planner_global", "human_confirm")
workflow.add_edge("planner_diagnose", "human_confirm")
workflow.add_conditional_edges("human_confirm", route_after_confirm, {
    "confirmed_global": "copywriter",
    "confirmed_diagnose": "route_handler",
    "cancelled": END,
})
workflow.add_edge("copywriter", "designer")
workflow.add_edge("designer", "effects")
workflow.add_edge("effects", "editor")
workflow.add_edge("editor", END)
workflow.add_edge("route_handler", END)

# 断点续传
checkpointer = SqliteSaver.from_conn_string("./checkpoints.db")
graph = workflow.compile(
    checkpointer=checkpointer,
    interrupt_before=["human_confirm"]
)
```

### Celery 与 LangGraph 的配合

```python
# backend/tasks/generate.py
@celery_app.task(bind=True)
def run_ppt_generation(self, project_id: str, user_message: str):
    """Celery 负责异步外壳，LangGraph 负责内部编排"""
    import asyncio
    from backend.graph.workflow import graph
    
    config = {"configurable": {"thread_id": project_id}}
    
    # LangGraph 在 Celery worker 中运行
    result = asyncio.run(
        graph.ainvoke(
            {
                "project_id": project_id,
                "user_message": user_message,
                "mode": "global",
            },
            config=config
        )
    )
    return result
```

---

## SSE 事件类型

```typescript
// frontend/src/types/events.ts

type AgentName = 'planner' | 'copywriter' | 'designer' | 'effects' | 'editor'
type SlideStatus = 'todo' | 'generating' | 'done' | 'locked'

type SSEEvent =
  | { type: 'agent_start'; agent: AgentName; message: string }
  | { type: 'agent_progress'; agent: AgentName; progress: number; detail: string }
  | { type: 'agent_complete'; agent: AgentName; output_ref?: string }
  | { type: 'slide_status_change'; slide_id: string; status: SlideStatus }
  | { type: 'confirmation_required'; confirmation_type: 'outline' | 'diagnosis'; payload: object }
  | { type: 'generation_complete'; export_url: string }
  | { type: 'error'; agent: AgentName; message: string; recoverable: boolean }
```
