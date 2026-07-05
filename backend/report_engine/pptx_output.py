"""PPT 输出适配器 — 将 report_json 渲染为 PPTX"""
from pathlib import Path
from backend.report_engine.output_engine import OutputAdapter, OutputResult


class PptOutputAdapter(OutputAdapter):

    @property
    def format_type(self) -> str:
        return "pptx"

    async def generate(
        self, report_json: dict, template_path: str | None = None,
        style_rules: dict | None = None, output_dir: str | Path = ".",
    ) -> OutputResult:
        """遍历 report_json.slides，调用现有 designer + editor pipeline。"""
        from backend.models.outline import SlideItem, OutlineDoc, save_outline
        from backend.storage.file_manager import ProjectStorage

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        slides_data = report_json.get("slides", [])
        slides = [
            SlideItem(
                slide_id=s.get("slide_id", f"{i+1:02d}"),
                layout=s.get("layout", "title-content"),
                title=s.get("title", ""),
                points=s.get("points", []),
                visual_intent=s.get("visual_intent"),
                notes_speaker=s.get("notes_speaker", ""),
            )
            for i, s in enumerate(slides_data)
        ]

        from datetime import datetime, timezone
        outline = OutlineDoc(
            meta={"title": report_json.get("title", "报告"), "total_slides": len(slides),
                  "created_at": datetime.now(timezone.utc).isoformat(),
                  "updated_at": datetime.now(timezone.utc).isoformat()},
            slides=slides,
        )

        storage = ProjectStorage.get()
        project_path = storage.get_project_path(output_dir.name)
        project_path.mkdir(parents=True, exist_ok=True)
        save_outline(outline, str(project_path / "OUTLINE.md"))

        from backend.agents.designer import run_designer
        from backend.agents.editor import run_editor

        await run_designer(str(project_path))
        await run_editor(str(project_path))

        pptx_file = project_path / "exports" / "native.pptx"
        return OutputResult(
            file_path=str(pptx_file), file_type="pptx",
            mime_type="application/vnd.openxmlformats-officedocument.presentationml.document",
            file_size=pptx_file.stat().st_size if pptx_file.exists() else 0,
        )
