"""Report template listing API."""
from fastapi import APIRouter, HTTPException, Query

from backend.core.templates import template_store

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("")
async def list_templates(category: str = Query(default="")):
    """List all report templates, optionally filtered by category."""
    if category:
        templates = template_store.list_by_category(category)
    else:
        templates = template_store.list_all()

    return {
        "code": 200,
        "msg": "ok",
        "data": [
            {
                "template_id": t.template_id,
                "name": t.name,
                "category": t.category,
                "description": t.description,
                "section_count": len(t.sections),
                "parent_meta": t.parent_meta,
                "suggested_charts": t.suggested_charts,
            }
            for t in templates
        ],
    }


@router.get("/{template_id}")
async def get_template(template_id: str):
    """Get full template detail including all sections."""
    tmpl = template_store.get(template_id)
    if tmpl is None:
        raise HTTPException(404, f"Template not found: {template_id}")

    return {
        "template_id": tmpl.template_id,
        "name": tmpl.name,
        "category": tmpl.category,
        "description": tmpl.description,
        "parent_meta": tmpl.parent_meta,
        "suggested_charts": tmpl.suggested_charts,
        "system_prompt": tmpl.system_prompt,
        "sections": [
            {
                "key": s.key,
                "title": s.title,
                "required": s.required,
                "description": s.description,
                "source": s.source,
                "match_keywords": s.match_keywords,
                "max_matches": s.max_matches,
                "fallback": s.fallback,
                "suggested_length": s.suggested_length,
            }
            for s in tmpl.sections
        ],
    }
