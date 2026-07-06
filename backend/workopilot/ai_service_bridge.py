"""WorkoPilot AI Service bridge — expose report engine as WorkoPilot-compatible API."""
import uuid
from fastapi import APIRouter, HTTPException
from backend.core.engine.intent import IntentRecognizer
from backend.core.engine.template_matcher import TemplateMatcher
from backend.core.engine.summarizer import SourceSummarizer
from backend.core.engine.filler import SectionFiller
from backend.core.templates import template_store
from backend.api.routes.datasources import _source_store

router = APIRouter(prefix="/workopilot", tags=["workopilot"])


@router.post("/run")
async def run_ai_service(req: dict):
    """Bridge endpoint: WorkoPilot AI service → Smart Reporting Engine.

    Request format (matching WorkoPilot AI service convention):
    {
        "serviceCode": "report_intent" | "report_generate",
        "inputs": {
            "user_query": "...",
            "source_ids": [...],
            "template_id": "...",
        }
    }
    """
    service_code = req.get("serviceCode", "")
    inputs = req.get("inputs", {})

    if service_code == "report_intent":
        return await _handle_intent(inputs)
    elif service_code == "report_generate":
        return await _handle_generate(inputs)
    else:
        raise HTTPException(400, f"Unknown serviceCode: {service_code}")


async def _handle_intent(inputs: dict) -> dict:
    user_query = inputs.get("user_query", "")
    source_ids = inputs.get("source_ids", [])
    sources = [_source_store[sid] for sid in source_ids if sid in _source_store]

    try:
        recognizer = IntentRecognizer()
        matcher = TemplateMatcher()
        intent = await recognizer.recognize(user_query, sources)
        recommendations = matcher.match(intent)
    except Exception as e:
        # Graceful fallback when LLM is unavailable
        matcher = TemplateMatcher()
        from backend.core.models import ReportIntent
        intent = ReportIntent(report_type="general", category="进度类", period="", scope="", key_themes=[])
        recommendations = matcher.match(intent)

    return {
        "intent": {
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


async def _handle_generate(inputs: dict) -> dict:
    template_id = inputs.get("template_id", "")
    source_ids = inputs.get("source_ids", [])
    title = inputs.get("title", "")

    tmpl = template_store.get(template_id)
    if not tmpl:
        raise HTTPException(404, f"Template not found: {template_id}")

    sources = [_source_store[sid] for sid in source_ids if sid in _source_store]

    summarizer = SourceSummarizer()
    filler = SectionFiller()

    merged = await summarizer.summarize(sources)
    report = await filler.fill(tmpl, merged, sources, title or tmpl.name)

    return {
        "report_id": report.report_id,
        "title": report.title,
        "sections": [
            {
                "key": s.key,
                "title": s.title,
                "content": s.content[:500],
                "confidence": s.confidence,
                "status": s.status,
            }
            for s in report.sections
        ],
    }
