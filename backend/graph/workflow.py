"""W3-1: LangGraph 状态机 — 图结构 + 条件边 + 断点续传"""
from langgraph.graph import END, StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver

from backend.graph.state import PPTState


# ---------- Node functions ----------

def intent_router_node(state: PPTState) -> dict:
    """Determine work mode based on user message."""
    from backend.agents.planner import classify_intent

    mode, target_ids = classify_intent(
        state["user_message"],
        state.get("outline_path", ""),
    )
    return {
        "mode": mode,
        "target_slide_ids": target_ids,
        "current_agent": "planner",
    }


def planner_global_node(state: PPTState) -> dict:
    """Full generation: analyze requirements → generate outline → persist to OUTLINE.md."""
    from datetime import datetime, timezone
    from pathlib import Path

    from backend.agents.planner import run_global_mode
    from backend.models.outline import OutlineDoc, OutlineMeta, SlideItem, save_outline
    from backend.storage.file_manager import ProjectStorage

    project_id = state["project_id"]
    outline_path = state.get("outline_path", "")

    # Ensure project directory exists
    storage = ProjectStorage.get()
    storage.create_project_dir(project_id)

    result = run_global_mode(
        user_message=state["user_message"],
        project_id=project_id,
        outline_path=outline_path,
    )

    # Persist planner output to OUTLINE.md so downstream nodes can read it
    slides_data = result.get("slides", [])
    if slides_data and not result.get("error"):
        now = datetime.now(timezone.utc).isoformat()
        slides = []
        for s in slides_data:
            slides.append(SlideItem(
                slide_id=s.get("slide_id", "01"),
                layout=s.get("layout", "title-content"),
                title=s.get("title", ""),
                subtitle=s.get("subtitle"),
                points=s.get("points", []),
                visual_intent=s.get("visual_intent"),
                status="todo",
            ))
        outline = OutlineDoc(
            meta=OutlineMeta(
                title=slides[0].title if slides else "Untitled",
                total_slides=len(slides),
                status="draft",
                created_at=now,
                updated_at=now,
            ),
            slides=slides,
        )
        save_outline(outline, outline_path)

    return {
        "planner_output": result,
        "outline_path": outline_path,
        "awaiting_confirmation": True,
        "confirmation_type": "outline",
    }


def planner_diagnose_node(state: PPTState) -> dict:
    """Diagnose mode: scan outline for issues → generate fix proposals."""
    from backend.agents.planner import run_diagnose_mode

    report = run_diagnose_mode(
        user_message=state["user_message"],
        outline_path=state["outline_path"],
    )
    return {
        "diagnosis_report": report,
        "awaiting_confirmation": True,
        "confirmation_type": "diagnosis",
    }


def human_confirm_node(state: PPTState) -> dict:
    """Human-in-the-loop confirmation point. LangGraph pauses here via interrupt_before.

    Resume flow: caller invokes graph.invoke({"user_confirmed": True}, config=config)
    to continue past this node. If user_confirmed=False, route_after_confirm → "cancelled" → END.
    """
    return {
        "awaiting_confirmation": False,
    }


def copywriter_node(state: PPTState) -> dict:
    """Fill in slide content (title, points, notes) for each page."""
    from backend.agents.copywriter import run_copywriter

    result = run_copywriter(
        project_id=state["project_id"],
        outline_path=state["outline_path"],
    )
    return {
        "current_agent": "copywriter",
        "completed_slides": result.get("completed_slides", []),
    }


def designer_node(state: PPTState) -> dict:
    """Generate SVG for each slide (sequential, NOT concurrent)."""
    from backend.agents.designer import run_designer
    from backend.agents.events import publish_agent_start

    publish_agent_start(state["project_id"], "designer", "开始生成 SVG 排版...")
    result = run_designer(
        project_id=state["project_id"],
        outline_path=state["outline_path"],
        design_path=state.get("design_path", ""),
    )
    return {
        "current_agent": "designer",
        "completed_slides": result.get("completed_slides", []),
        "failed_slides": result.get("failed_slides", []),
    }


def effects_node(state: PPTState) -> dict:
    """Process charts and images for slides that need them."""
    from backend.agents.effects import run_effects
    from backend.agents.events import publish_agent_start

    try:
        publish_agent_start(state["project_id"], "effects", "处理图表和图片...")
        result = run_effects(
            project_id=state["project_id"],
            outline_path=state["outline_path"],
        )
    except Exception:
        pass  # Effects are optional, don't block the pipeline

    return {"current_agent": "effects"}


def editor_node(state: PPTState) -> dict:
    """Convert SVGs to PPTX, embed fonts, produce final output."""
    from backend.agents.editor import run_editor
    from backend.agents.events import publish_agent_start, publish_error

    # Warn if some slides failed, but continue with what we have
    failed = state.get("failed_slides", [])
    if failed:
        publish_error(state["project_id"], "editor",
                      f"注意：{len(failed)} 页生成失败（{', '.join(failed)}），将生成不完整的 PPTX",
                      recoverable=True)

    publish_agent_start(state["project_id"], "editor", "转换为 PPTX...")
    result = run_editor(
        project_id=state["project_id"],
        outline_path=state["outline_path"],
    )
    return {
        "current_agent": "editor",
        "export_path": result.get("export_path", ""),
    }


def route_handler_node(state: PPTState) -> dict:
    """Diagnosis dispatch: parse diagnosis report → build task_queue → dispatch fixes.

    For route mode (single-slide dispatch): task_queue should already be populated
    by planner.run_route_mode() before reaching this node.
    For confirmed diagnose: builds task_queue from diagnosis_report["issues"],
    mapping each issue's affected_slides to individual fix tasks.
    Content fixes (copywriter) run in parallel; design fixes run sequentially.
    """
    from backend.tasks.generate import _build_task_queue, run_diagnosis_dispatch

    diagnosis_report = state.get("diagnosis_report") or {}
    task_queue = state.get("task_queue", [])

    # Build task_queue from diagnosis_report if not already set
    if not task_queue and diagnosis_report:
        task_queue = _build_task_queue(diagnosis_report)

    # Dispatch fixes asynchronously via Celery
    if task_queue:
        run_diagnosis_dispatch.delay(state["project_id"], diagnosis_report)

    return {
        "current_agent": "route_handler",
        "task_queue": task_queue,
        "completed_slides": [t.get("slide_id", "") for t in task_queue],
    }


# ---------- Routing functions ----------

def route_by_mode(state: PPTState) -> str:
    """Route based on detected mode."""
    return state.get("mode", "global")


def route_after_confirm(state: PPTState) -> str:
    """Route after human confirmation."""
    if not state.get("user_confirmed", False):
        return "cancelled"
    if state.get("confirmation_type") == "outline":
        return "confirmed_global"
    return "confirmed_diagnose"


# ---------- Build graph ----------

def build_workflow() -> StateGraph:
    """Construct the LangGraph state machine."""
    workflow = StateGraph(PPTState)

    # Nodes
    workflow.add_node("intent_router", intent_router_node)
    workflow.add_node("planner_global", planner_global_node)
    workflow.add_node("planner_diagnose", planner_diagnose_node)
    workflow.add_node("human_confirm", human_confirm_node)
    workflow.add_node("copywriter", copywriter_node)
    workflow.add_node("designer", designer_node)
    workflow.add_node("effects", effects_node)
    workflow.add_node("editor", editor_node)
    workflow.add_node("route_handler", route_handler_node)

    # Entry point
    workflow.set_entry_point("intent_router")

    # Conditional edges
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

    return workflow


def get_graph(checkpointer=None):
    """Compile the graph with optional checkpointer for persistence."""
    import sqlite3
    from pathlib import Path

    workflow = build_workflow()
    if checkpointer is None:
        db_path = str(Path(__file__).resolve().parent.parent.parent / "checkpoints.db")
        conn = sqlite3.connect(db_path, check_same_thread=False)
        checkpointer = SqliteSaver(conn)
    return workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_confirm"],
    )
