"""Report generation and management API with SSE streaming."""
import asyncio
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.core.engine.filler import SectionFiller
from backend.core.engine.intent import IntentRecognizer
from backend.core.engine.slide_matcher import SlideMatcher
from backend.core.engine.summarizer import SourceSummarizer
from backend.core.engine.template_matcher import TemplateMatcher
from backend.core.engine.validator import ReportValidator
from backend.core.llm.client import get_llm_client
from backend.core.models import (
    ReportMeta,
    ReportSection,
    SectionDef,
    StructuredReport,
)
from backend.core.templates import template_store

router = APIRouter(prefix="/reports", tags=["reports"])

_reports: dict[str, StructuredReport] = {}


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class IntentRequest(BaseModel):
    user_query: str
    source_ids: list[str] = []


class GenerateRequest(BaseModel):
    template_id: str
    source_ids: list[str] = []
    title: str = ""


class SectionUpdateRequest(BaseModel):
    content: str


class ChatCommandRequest(BaseModel):
    command: str
    target_context: str = ""


# ---------------------------------------------------------------------------
# POST /intent
# ---------------------------------------------------------------------------

@router.post("/intent")
async def recognize_intent(body: IntentRequest):
    """Recognize user intent and recommend matching templates."""
    from backend.api.routes.datasources import _source_store

    # Gather source documents
    source_docs = []
    for sid in body.source_ids:
        doc = _source_store.get(sid)
        if doc:
            source_docs.append(doc)

    # Recognize intent (with graceful fallback if LLM is unavailable)
    try:
        recognizer = IntentRecognizer()
        intent = await recognizer.recognize(body.user_query, source_docs)
    except Exception as e:
        # Fallback: build a basic intent from the query
        from backend.core.models import ReportIntent
        intent = ReportIntent(
            raw_query=body.user_query,
            report_type="general",
            category="general",
        )

    # Match templates
    matcher = TemplateMatcher()
    recommendations = matcher.match(intent, top_k=5)

    return {
        "intent": {
            "raw_query": intent.raw_query,
            "report_type": intent.report_type,
            "category": intent.category,
            "period": intent.period,
            "scope": intent.scope,
            "key_themes": intent.key_themes,
        },
        "recommendations": [
            {
                "template_id": r.template_id,
                "name": r.name,
                "match_score": r.match_score,
                "match_reason": r.match_reason,
                "is_selected": r.is_selected,
            }
            for r in recommendations
        ],
    }


# ---------------------------------------------------------------------------
# POST /generate  (SSE streaming)
# ---------------------------------------------------------------------------

@router.post("/generate")
async def generate_report(body: GenerateRequest):
    """Generate a report with SSE streaming progress events."""
    from backend.api.routes.datasources import _source_store

    template = template_store.get(body.template_id)
    if template is None:
        raise HTTPException(404, f"Template not found: {body.template_id}")

    source_docs = []
    for sid in body.source_ids:
        doc = _source_store.get(sid)
        if doc:
            source_docs.append(doc)

    report_id = str(uuid.uuid4())
    report_meta = ReportMeta(
        id=report_id,
        title=body.title or template.name,
        template_id=body.template_id,
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    async def event_stream():
        # Phase 1: Summarize sources
        yield _sse_event("progress", {"phase": "summarize", "message": "汇总数据源..."})
        summarizer = SourceSummarizer()
        summarized = await summarizer.summarize(source_docs)
        yield _sse_event("progress", {"phase": "summarize", "message": "数据源汇总完成", "done": True})

        # Phase 2: Fill sections one by one (streaming preview + accumulate for final report)
        filler = SectionFiller()
        leaf_sections = filler._collect_leaf_sections(template.sections)
        source_text = "\n\n---\n\n".join(
            f"### [{d.source_type}] {d.title}\n{d.content}" for d in source_docs
        )
        filled_sections = []  # accumulate during Phase 2, reuse in Phase 3

        for i, section in enumerate(leaf_sections):
            yield _sse_event("progress", {
                "phase": "fill",
                "message": f"正在生成: {section.title}",
                "current": i + 1,
                "total": len(leaf_sections),
            })

            filled = await filler._fill_section(section, template, source_text)
            filled_sections.append(filled)  # store for later reuse
            yield _sse_event("section", {
                "key": section.key,
                "title": section.title,
                "content": filled.markdown_content,
                "index": i + 1,
            })

        # Phase 3: Build full report from previously filled sections (no double LLM call)
        full_md_parts = [f"# {template.name}"]
        for rs in filled_sections:
            full_md_parts.append(f"\n## {rs.section_def.title}\n{rs.markdown_content}")

        report = StructuredReport(
            meta=report_meta,
            template=template,
            sections=filled_sections,
            full_markdown="\n".join(full_md_parts),
            report_json={},
        )

        # Phase 4: Validate
        yield _sse_event("progress", {"phase": "validate", "message": "正在校验内容质量..."})
        validator = ReportValidator()
        validation = await validator.validate(report.full_markdown, summarized)
        yield _sse_event("validation", validation)

        # Phase 5: Match enterprise PPT slides
        yield _sse_event("progress", {"phase": "slide_match", "message": "正在匹配企业PPT案例..."})
        matcher = SlideMatcher()
        from backend.api.routes.enterprise_ppt import _decks

        all_slides = []
        for deck in _decks.values():
            for slide in deck.get("slides", []):
                from backend.core.models import SlideAsset
                all_slides.append(SlideAsset(
                    id=slide.get("slide_asset_id", str(uuid.uuid4())),
                    title=slide.get("title", ""),
                    description=slide.get("summary", ""),
                    category=slide.get("type", "content"),
                    tags=slide.get("keywords", []),
                    file_path=deck.get("file_path", ""),
                    slide_index=slide.get("index", 0),
                ))

        match_results = matcher.match_for_template(template.sections, all_slides)
        yield _sse_event("slide_matches", {"matches": {
            k: [{"title": m.title, "score": m.quality_score} for m in v]
            for k, v in match_results.items()
        }})

        # Store report
        _reports[report_id] = report

        # Done
        yield _sse_event("done", {
            "report_id": report_id,
            "title": report.meta.title,
            "section_count": len(report.sections),
        })

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# GET /{report_id}
# ---------------------------------------------------------------------------

@router.get("/{report_id}")
async def get_report(report_id: str):
    """Get a generated report by ID."""
    report = _reports.get(report_id)
    if report is None:
        raise HTTPException(404, f"Report not found: {report_id}")

    return {
        "report_id": report.meta.id,
        "title": report.meta.title,
        "template_id": report.meta.template_id,
        "created_at": report.meta.created_at,
        "sections": [
            {
                "key": s.section_def.key,
                "title": s.section_def.title,
                "content": s.markdown_content,
                "source": s.section_def.source,
                "data_sources": s.data_sources,
            }
            for s in report.sections
        ],
        "full_markdown": report.full_markdown,
    }


# ---------------------------------------------------------------------------
# PATCH /{report_id}/section/{section_key}
# ---------------------------------------------------------------------------

@router.patch("/{report_id}/section/{section_key}")
async def update_section(report_id: str, section_key: str, body: SectionUpdateRequest):
    """Update a single section's content."""
    report = _reports.get(report_id)
    if report is None:
        raise HTTPException(404, f"Report not found: {report_id}")

    updated = False
    for section in report.sections:
        if section.section_def.key == section_key:
            section.markdown_content = body.content
            updated = True
            break

    if not updated:
        raise HTTPException(404, f"Section not found: {section_key}")

    # Rebuild full_markdown
    parts = [f"# {report.meta.title}"]
    for s in report.sections:
        parts.append(f"\n## {s.section_def.title}\n{s.markdown_content}")
    report.full_markdown = "\n".join(parts)

    return {"updated": section_key, "report_id": report_id}


# ---------------------------------------------------------------------------
# POST /{report_id}/chat-command
# ---------------------------------------------------------------------------

@router.post("/{report_id}/chat-command")
async def chat_command(report_id: str, body: ChatCommandRequest):
    """Process a natural language command on a report (add_section, rewrite, etc.)."""
    report = _reports.get(report_id)
    if report is None:
        raise HTTPException(404, f"Report not found: {report_id}")

    # Use LLM to parse the command
    llm = get_llm_client()
    sections_summary = "\n".join(
        f"- key={s.section_def.key}, title={s.section_def.title}"
        for s in report.sections
    )

    prompt = f"""Parse the following user command about a report and return a JSON list of operations.

Report sections:
{sections_summary}

Current context: {body.target_context or "whole report"}

User command: {body.command}

Return a JSON array of operations. Each operation has:
- "action": "add_section" or "rewrite"
- "target": section key (for rewrite) or "new" (for add_section)
- "params": dict with relevant parameters (for add_section: title, content; for rewrite: new_content)

Example:
[{{"action": "rewrite", "target": "background", "params": {{"new_content": "..."}}}}]
[{{"action": "add_section", "target": "new", "params": {{"title": "新章节", "content": "..."}}}}]
"""

    try:
        result = await llm.chat_json(
            system_prompt="Parse report editing commands into structured operations.",
            user_message=prompt,
        )
    except Exception:
        result = [{"action": "unknown", "target": "", "params": {}}]

    # Execute operations
    executed = []
    for op in result:
        action = op.get("action", "")
        target = op.get("target", "")
        params = op.get("params", {})

        if action == "add_section":
            new_key = f"section_{uuid.uuid4().hex[:8]}"
            new_section_def = SectionDef(
                key=new_key,
                title=params.get("title", "New Section"),
                description=params.get("title", ""),
                source="generated",
            )
            new_section = ReportSection(
                section_def=new_section_def,
                markdown_content=params.get("content", ""),
            )
            report.sections.append(new_section)
            op["result"] = {"added": new_key, "title": new_section_def.title}
            executed.append(op)

        elif action == "rewrite":
            for section in report.sections:
                if section.section_def.key == target or section.section_def.title == target:
                    section.markdown_content = params.get("new_content", section.markdown_content)
                    op["result"] = {"rewritten": target}
                    executed.append(op)
                    break
            else:
                op["result"] = {"error": f"Section not found: {target}"}
                executed.append(op)

        else:
            op["result"] = {"error": f"Unknown action: {action}"}
            executed.append(op)

    # Rebuild full_markdown
    parts = [f"# {report.meta.title}"]
    for s in report.sections:
        parts.append(f"\n## {s.section_def.title}\n{s.markdown_content}")
    report.full_markdown = "\n".join(parts)

    return {"operations": executed}


# ---------------------------------------------------------------------------
# POST /{report_id}/confirm
# ---------------------------------------------------------------------------

@router.post("/{report_id}/confirm")
async def confirm_report(report_id: str):
    """Mark all sections of a report as confirmed."""
    report = _reports.get(report_id)
    if report is None:
        raise HTTPException(404, f"Report not found: {report_id}")

    confirmed_sections = []
    for section in report.sections:
        confirmed_sections.append(section.section_def.key)

    return {
        "report_id": report_id,
        "status": "confirmed",
        "confirmed_sections": confirmed_sections,
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sse_event(event_type: str, data: dict) -> str:
    """Format a single SSE event."""
    return f"data: {json.dumps({'type': event_type, **data}, ensure_ascii=False)}\n\n"
