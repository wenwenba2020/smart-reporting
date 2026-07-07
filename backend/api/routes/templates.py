"""Report template listing and CRUD API."""
import yaml
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query

from backend.core.templates import template_store, TEMPLATES_DIR
from backend.core.llm.client import get_llm_client

router = APIRouter(prefix="/templates", tags=["templates"])

CUSTOM_DIR = TEMPLATES_DIR / "curated_templates"


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
                "is_custom": t.template_id.startswith("custom_"),
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
        "code": 200,
        "msg": "ok",
        "data": {
            "template_id": tmpl.template_id,
            "name": tmpl.name,
            "category": tmpl.category,
            "description": tmpl.description,
            "parent_meta": tmpl.parent_meta,
            "suggested_charts": tmpl.suggested_charts,
            "system_prompt": tmpl.system_prompt,
            "is_custom": template_id.startswith("custom_"),
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
                    "example": getattr(s, 'example', ''),
                }
                for s in tmpl.sections
            ],
        },
    }


@router.post("")
async def create_template(body: dict):
    """Create a new custom template."""
    template_id = body.get("template_id", f"custom_{body.get('name', 'untitled').lower().replace(' ', '_')}")
    name = body.get("name", "")
    category = body.get("category", "进度类")
    description = body.get("description", "")
    sections = body.get("sections", [])
    system_prompt = body.get("system_prompt", "")

    if not name:
        raise HTTPException(400, "name is required")

    # Build YAML
    yaml_data = {
        "template_id": template_id,
        "name": name,
        "category": category,
        "description": description,
        "sections": sections,
        "system_prompt": system_prompt,
        "suggested_charts": body.get("suggested_charts", []),
    }

    filepath = CUSTOM_DIR / f"{template_id}.yaml"
    if filepath.exists():
        raise HTTPException(409, f"Template {template_id} already exists")

    with open(filepath, "w", encoding="utf-8") as f:
        yaml.dump(yaml_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    # Reload template store
    template_store._load_all()

    return {"code": 200, "msg": "created", "data": {"template_id": template_id}}


@router.put("/{template_id}")
async def update_template(template_id: str, body: dict):
    """Update an existing custom template."""
    if not template_id.startswith("custom_"):
        raise HTTPException(400, "Only custom templates can be modified")

    filepath = CUSTOM_DIR / f"{template_id}.yaml"
    if not filepath.exists():
        raise HTTPException(404, f"Template not found: {template_id}")

    # Read existing, update fields
    with open(filepath, "r", encoding="utf-8") as f:
        existing = yaml.safe_load(f)

    for key in ("name", "category", "description", "sections", "system_prompt", "suggested_charts"):
        if key in body:
            existing[key] = body[key]

    with open(filepath, "w", encoding="utf-8") as f:
        yaml.dump(existing, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    template_store._load_all()
    return {"code": 200, "msg": "updated", "data": {"template_id": template_id}}


@router.delete("/{template_id}")
async def delete_template(template_id: str):
    """Delete a custom template."""
    if not template_id.startswith("custom_"):
        raise HTTPException(400, "Only custom templates can be deleted")

    filepath = CUSTOM_DIR / f"{template_id}.yaml"
    if not filepath.exists():
        raise HTTPException(404, f"Template not found: {template_id}")

    filepath.unlink()
    template_store._load_all()
    return {"code": 200, "msg": "deleted", "data": None}


@router.post("/magic-wand")
async def magic_wand(body: dict):
    """AI magic wand: convert unstructured example text into structured report JSON.

    Input: {"text": "非结构化示例文本...", "sections": [{"key":"s1","title":"数据概览"},...]}
    Output: structured JSON matching the report format
    """
    text = body.get("text", "")
    sections = body.get("sections", [])

    if not text.strip():
        raise HTTPException(400, "text is required")

    llm = get_llm_client()
    sections_desc = "\n".join(f"- {s.get('key')}: {s.get('title')} — {s.get('description', '')}" for s in sections)

    prompt = f"""你是一个报告结构化专家。请将以下非结构化的示例文本转换为结构化的JSON报告格式。

## 报告章节定义
{sections_desc}

## 非结构化示例文本
{text}

## 要求
1. 为每个章节生成对应的结构化内容
2. 输出格式为 JSON: {{"sections": [{{"key": "章节key", "title": "章节标题", "content": "该章节的结构化Markdown内容"}}]}}
3. 保持原文的数据和关键信息，用专业报告语言组织
4. 只输出 JSON，不要有其他文字

请生成 JSON:"""

    try:
        result = await llm.chat_json(system_prompt="Convert unstructured text to structured report JSON.", user_message=prompt)
        return {"code": 200, "msg": "ok", "data": result}
    except Exception as e:
        raise HTTPException(500, f"Magic wand conversion failed: {str(e)}")
