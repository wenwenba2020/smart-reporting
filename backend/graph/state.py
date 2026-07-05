"""W3-1: PPTState TypedDict — LangGraph 状态机共享状态"""
from typing import Literal, TypedDict


class PPTState(TypedDict, total=False):
    # Project identity
    project_id: str
    outline_path: str
    design_path: str

    # Mode routing
    mode: Literal["global", "route", "diagnose"]
    user_message: str
    target_slide_ids: list[str]  # empty=global, non-empty=specific slides

    # Planner output
    planner_output: dict | None
    diagnosis_report: dict | None

    # Task dispatch
    task_queue: list[dict]  # [{agent, slide_id, action, params}]

    # Human confirmation flow
    awaiting_confirmation: bool
    confirmation_type: str | None  # "outline" | "diagnosis"
    user_confirmed: bool

    # Execution tracking
    current_agent: str | None
    completed_slides: list[str]
    failed_slides: list[str]
    error_log: list[str]

    # Output
    export_path: str | None
