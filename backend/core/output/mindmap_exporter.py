import os
import html as html_mod
from backend.core.output.base import BaseExporter
from backend.core.models import ExportResult, StructuredReport

MARKMAP_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body, #mindmap {{ width: 100vw; height: 100vh; }}
  .toolbar {{
    position: fixed; top: 12px; right: 16px; z-index: 10;
    display: flex; gap: 8px;
  }}
  .toolbar button {{
    padding: 6px 14px; font-size: 12px; border: 1px solid #ccc;
    border-radius: 6px; background: #fff; cursor: pointer;
  }}
  .toolbar button:hover {{ background: #f0f4ff; border-color: #2d6cdf; }}
</style>
</head>
<body>
<div class="toolbar">
  <button id="zoom-in" title="放大">+</button>
  <button id="zoom-out" title="缩小">−</button>
  <button id="fit" title="适应画面">适应</button>
</div>
<svg id="mindmap"></svg>

<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
<script src="https://cdn.jsdelivr.net/npm/markmap-view@0.15.4/dist/browser/index.js"></script>
<script src="https://cdn.jsdelivr.net/npm/markmap-lib@0.15.4/dist/browser/index.js"></script>
<script>
  (function() {{
    const markdown = {markdown_json};
    const {{ Transformer }} = window.markmap;
    const {{ Markmap }} = window.markmap;

    const transformer = new Transformer();
    const mm = Markmap.create("#mindmap", null, transformer.transform(markdown));

    // Controls
    document.getElementById("zoom-in").addEventListener("click", () => {{
      mm.rescale(mm.state.scale * 1.3);
    }});
    document.getElementById("zoom-out").addEventListener("click", () => {{
      mm.rescale(mm.state.scale * 0.7);
    }});
    document.getElementById("fit").addEventListener("click", () => {{
      mm.fit();
    }});
  }})();
</script>
</body>
</html>"""


class MindmapExporter(BaseExporter):
    format = "html_mindmap"

    async def export(
        self,
        report: StructuredReport,
        output_dir: str = "./data/exports",
    ) -> ExportResult:
        os.makedirs(output_dir, exist_ok=True)

        md_outline = self._build_markdown_outline(report)

        html_content = MARKMAP_TEMPLATE.format(
            title=html_mod.escape(report.meta.title),
            markdown_json=self._to_json_string(md_outline),
        )

        file_name = f"{report.meta.id}_mindmap.html"
        file_path = os.path.join(output_dir, file_name)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        file_size = os.path.getsize(file_path)

        return ExportResult(
            file_path=file_path,
            format=self.format,
            file_size_bytes=file_size,
        )

    def _build_markdown_outline(self, report: StructuredReport) -> str:
        """Build a markdown outline from the structured report for markmap rendering."""
        lines = [f"# {report.meta.title}", ""]

        for section in report.sections:
            heading_text = section.section_def.title or section.section_def.heading
            if heading_text:
                lines.append(f"## {heading_text}")
                lines.append("")

            content = section.markdown_content or ""
            items = self._extract_bullets(content)
            for item in items:
                lines.append(f"- {item}")
            if items:
                lines.append("")

        # Fallback to full_markdown
        if not report.sections and report.full_markdown:
            items = self._extract_bullets(report.full_markdown)
            for item in items:
                lines.append(f"- {item}")

        return "\n".join(lines)

    @staticmethod
    def _extract_bullets(content: str) -> list[str]:
        """Extract bullet/list items and key sentences from markdown content."""
        items = []
        for line in content.split("\n"):
            stripped = line.strip()
            # Skip empty lines, headings, table rows, horizontal rules
            if not stripped:
                continue
            if stripped.startswith("#"):
                continue
            if stripped.startswith("|"):
                continue
            if stripped in ("---", "***", "___"):
                continue

            # List items
            if stripped.startswith(("- ", "* ", "+ ")):
                items.append(stripped[2:].strip())
                continue
            if stripped[0].isdigit() and ". " in stripped[:5]:
                text = stripped.split(". ", 1)[1] if ". " in stripped else stripped
                items.append(text.strip())
                continue

            # Regular paragraph — take first sentence (up to 80 chars)
            # Remove bold markers for mindmap display
            clean = stripped.replace("**", "")
            if len(clean) > 80:
                clean = clean[:77] + "..."
            if clean:
                items.append(clean)

        return items

    @staticmethod
    def _to_json_string(text: str) -> str:
        """Escape a string for safe embedding in a JS template literal."""
        import json
        return json.dumps(text, ensure_ascii=False)
