import yaml
from pathlib import Path
from backend.core.models import ReportTemplate, SectionDef

TEMPLATES_DIR = Path(__file__).parent


def _dict_to_template(data: dict) -> ReportTemplate:
    sections = []
    for s in data.get("sections", []):
        sections.append(SectionDef(
            key=s["key"],
            title=s["title"],
            required=s.get("required", True),
            description=s.get("description", ""),
            source=s.get("source", "generated"),
            match_keywords=s.get("match_keywords", []),
            max_matches=s.get("max_matches", 3),
            fallback=s.get("fallback", "generated"),
            suggested_length=s.get("suggested_length", "medium"),
        ))
    return ReportTemplate(
        template_id=data["template_id"],
        name=data["name"],
        category=data.get("category", ""),
        parent_meta=data.get("parent_meta"),
        description=data.get("description", ""),
        sections=sections,
        suggested_charts=data.get("suggested_charts", []),
        system_prompt=data.get("system_prompt", ""),
    )


class TemplateStore:
    def __init__(self):
        self._templates: dict[str, ReportTemplate] = {}
        self._load_all()

    def _load_all(self):
        for pattern in ["meta_templates/*.yaml", "curated_templates/*.yaml"]:
            for yaml_file in TEMPLATES_DIR.glob(pattern):
                with open(yaml_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    tmpl = _dict_to_template(data)
                    self._templates[tmpl.template_id] = tmpl

    def get(self, template_id: str):
        return self._templates.get(template_id)

    def list_all(self):
        return list(self._templates.values())

    def list_by_category(self, category: str):
        return [t for t in self._templates.values() if t.category == category]


template_store = TemplateStore()
