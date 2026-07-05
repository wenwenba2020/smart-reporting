"""Enterprise PPT deck library API."""
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.config import settings
from backend.core.datasource.enterprise_ppt import EnterprisePPTAdapter

router = APIRouter(prefix="/enterprise-ppt", tags=["enterprise_ppt"])

_decks: dict[str, dict] = {}

_adapter = EnterprisePPTAdapter()
UPLOAD_DIR = Path(settings.local_storage_path)


@router.post("/upload")
async def upload_deck(
    file: UploadFile = File(...),
    deck_type: str = Form(default="case_library"),
    name: str = Form(default=""),
    category: str = Form(default="general"),
    tags: str = Form(default=""),
):
    """Upload a .pptx file, parse into a ContentDeck, and store it."""
    if not file.filename:
        raise HTTPException(400, "Filename is required")

    suffix = Path(file.filename).suffix.lower()
    if suffix != ".pptx":
        raise HTTPException(400, "Only .pptx files are supported for enterprise PPT decks")

    # Save file
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_path = UPLOAD_DIR / f"{uuid.uuid4().hex}_{file.filename}"
    content = await file.read()
    file_path.write_bytes(content)

    # Parse deck
    try:
        deck = await _adapter.parse_deck(str(file_path), file.filename)
    except Exception as e:
        file_path.unlink(missing_ok=True)
        raise HTTPException(500, f"Parse error: {e}")

    deck_id = deck.id
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    _decks[deck_id] = {
        "id": deck_id,
        "name": name or deck.title,
        "title": deck.title,
        "deck_type": deck_type,
        "category": category,
        "tags": tag_list,
        "file_path": str(file_path),
        "filename": file.filename,
        "slides": deck.slides,
        "outline": deck.outline,
        "slide_count": len(deck.slides),
    }

    return {
        "deck_id": deck_id,
        "name": name or deck.title,
        "deck_type": deck_type,
        "slide_count": len(deck.slides),
        "slides_preview": [
            {"index": s["index"], "title": s.get("title", ""), "type": s.get("type", "")}
            for s in deck.slides[:5]
        ],
    }


@router.get("/decks")
async def list_decks():
    """List all uploaded decks."""
    return {
        "data": [
            {
                "id": d["id"],
                "name": d["name"],
                "title": d["title"],
                "deck_type": d["deck_type"],
                "category": d["category"],
                "tags": d["tags"],
                "slide_count": d["slide_count"],
            }
            for d in _decks.values()
        ]
    }


@router.get("/decks/{deck_id}")
async def get_deck(deck_id: str):
    """Get full deck detail including slides."""
    deck = _decks.get(deck_id)
    if deck is None:
        raise HTTPException(404, f"Deck not found: {deck_id}")
    return deck


@router.delete("/decks/{deck_id}")
async def delete_deck(deck_id: str):
    """Remove a deck from the store."""
    if deck_id not in _decks:
        raise HTTPException(404, f"Deck not found: {deck_id}")
    del _decks[deck_id]
    return {"deleted": deck_id}


@router.get("/slides/search")
async def search_slides(q: str = "", section_type: str = ""):
    """Search slides across all decks by keyword matching title/summary/tags."""
    results = []
    query_lower = q.lower().strip()
    type_lower = section_type.lower().strip()

    for deck in _decks.values():
        for slide in deck.get("slides", []):
            title = (slide.get("title") or "").lower()
            summary = (slide.get("summary") or "").lower()
            slide_tags = [t.lower() for t in (slide.get("keywords") or [])]
            slide_type = (slide.get("type") or "").lower()

            if type_lower and type_lower not in slide_type:
                continue

            if query_lower:
                if (
                    query_lower not in title
                    and query_lower not in summary
                    and not any(query_lower in t for t in slide_tags)
                ):
                    continue

            results.append({
                "deck_id": deck["id"],
                "deck_name": deck["name"],
                "slide_index": slide["index"],
                "title": slide.get("title", ""),
                "summary": slide.get("summary", ""),
                "type": slide.get("type", ""),
                "keywords": slide.get("keywords", []),
            })

    return {"data": results, "count": len(results)}


@router.get("/templates")
async def list_template_decks():
    """List decks marked as templates (deck_type == 'template')."""
    template_decks = [d for d in _decks.values() if d.get("deck_type") == "template"]
    return {
        "data": [
            {
                "id": d["id"],
                "name": d["name"],
                "category": d["category"],
                "tags": d["tags"],
                "slide_count": d["slide_count"],
            }
            for d in template_decks
        ]
    }
