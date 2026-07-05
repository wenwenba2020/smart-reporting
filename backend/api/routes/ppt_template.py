"""PPT template selection API — works with enterprise PPT decks marked as templates."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/ppt-template", tags=["ppt_template"])


class SelectTemplateRequest(BaseModel):
    deck_id: str


@router.get("/recommend")
async def recommend_templates():
    """List template-type decks as PPT template recommendations."""
    from backend.api.routes.enterprise_ppt import _decks

    template_decks = [
        d for d in _decks.values() if d.get("deck_type") == "template"
    ]

    return {
        "data": [
            {
                "deck_id": d["id"],
                "name": d["name"],
                "category": d.get("category", "general"),
                "tags": d.get("tags", []),
                "slide_count": d.get("slide_count", 0),
                "outline": d.get("outline", {}),
            }
            for d in template_decks
        ]
    }


@router.post("/select")
async def select_template(body: SelectTemplateRequest):
    """Select a specific template deck for use."""
    from backend.api.routes.enterprise_ppt import _decks

    deck = _decks.get(body.deck_id)
    if deck is None:
        raise HTTPException(404, f"Deck not found: {body.deck_id}")

    if deck.get("deck_type") != "template":
        raise HTTPException(400, f"Deck {body.deck_id} is not a template (type={deck.get('deck_type')})")

    return {
        "selected": {
            "deck_id": deck["id"],
            "name": deck["name"],
            "category": deck.get("category", "general"),
            "tags": deck.get("tags", []),
            "slide_count": deck.get("slide_count", 0),
            "file_path": deck.get("file_path", ""),
            "outline": deck.get("outline", {}),
            "slides": deck.get("slides", []),
        }
    }
