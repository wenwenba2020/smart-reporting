"""PDF 输出适配器 — Markdown → HTML → PDF"""
from pathlib import Path
from backend.report_engine.output_engine import OutputAdapter, OutputResult


class PdfOutputAdapter(OutputAdapter):

    @property
    def format_type(self) -> str:
        return "pdf"

    async def generate(
        self, report_json: dict, template_path: str | None = None,
        style_rules: dict | None = None, output_dir: str | Path = ".",
    ) -> OutputResult:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        html = _build_html(report_json, style_rules)

        try:
            from weasyprint import HTML
            file_path = output_dir / "report.pdf"
            HTML(string=html).write_pdf(str(file_path))
            return OutputResult(
                file_path=str(file_path), file_type="pdf",
                mime_type="application/pdf",
                file_size=file_path.stat().st_size,
            )
        except ImportError:
            file_path = output_dir / "report.html"
            file_path.write_text(html, encoding="utf-8")
            return OutputResult(
                file_path=str(file_path), file_type="html",
                mime_type="text/html",
                file_size=file_path.stat().st_size,
            )


def _build_html(report_json: dict, style_rules: dict | None = None) -> str:
    colors = (style_rules or {}).get("colors", ["#1E3A5F", "#333333"])
    primary = colors[0] if colors else "#1E3A5F"

    sections_html = ""
    for s in report_json.get("sections", []):
        heading = s.get("heading", "")
        content = s.get("content", "").replace("\n", "<br>")
        sections_html += f"<h2>{heading}</h2>\n<p>{content}</p>\n"

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8">
<style>
  body {{ font-family: 'SimSun', serif; max-width: 210mm; margin: 20mm auto; color: #333; }}
  h1 {{ color: {primary}; text-align: center; font-size: 24pt; }}
  h2 {{ color: {primary}; font-size: 16pt; border-bottom: 1px solid #ddd; }}
  p {{ line-height: 1.8; font-size: 12pt; }}
</style></head>
<body>
  <h1>{report_json.get("title", "报告")}</h1>
  {sections_html}
</body>
</html>"""
