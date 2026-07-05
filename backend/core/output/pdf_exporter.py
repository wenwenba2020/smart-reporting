import os
import re
import html as html_mod
from backend.core.output.base import BaseExporter
from backend.core.models import ExportResult, StructuredReport

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
  @page {{
    size: A4;
    margin: 2.5cm 2cm;
    @bottom-center {{
      content: "— " counter(page) " —";
      font-size: 9pt;
      color: #999;
      font-family: "Noto Sans SC", "SimSun", sans-serif;
    }}
  }}

  body {{
    font-family: "Noto Sans SC", "SimSun", "Microsoft YaHei", sans-serif;
    font-size: 11pt;
    line-height: 1.8;
    color: #333;
  }}

  h1 {{
    text-align: center;
    font-size: 20pt;
    margin-bottom: 0.3cm;
    color: #1a1a2e;
    border-bottom: 3px solid #2d6cdf;
    padding-bottom: 0.5cm;
  }}

  .meta {{
    text-align: center;
    font-size: 9pt;
    color: #888;
    margin-bottom: 1cm;
  }}

  .separator {{
    text-align: center;
    color: #ccc;
    margin: 1cm 0;
  }}

  h2 {{
    font-size: 14pt;
    color: #2d6cdf;
    border-left: 5px solid #2d6cdf;
    padding-left: 10px;
    margin-top: 1.2cm;
    margin-bottom: 0.4cm;
  }}

  h3 {{
    font-size: 12pt;
    color: #444;
    margin-top: 0.8cm;
    margin-bottom: 0.3cm;
  }}

  p {{
    margin: 0.3cm 0;
    text-indent: 0;
  }}

  ul, ol {{
    margin: 0.2cm 0 0.2cm 0.5cm;
    padding-left: 1cm;
  }}

  li {{
    margin-bottom: 0.15cm;
  }}

  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 0.5cm 0;
    font-size: 10pt;
  }}

  table th {{
    background-color: #2d6cdf;
    color: white;
    padding: 8px 10px;
    text-align: left;
    font-weight: bold;
  }}

  table td {{
    border: 1px solid #ddd;
    padding: 6px 10px;
  }}

  table tr:nth-child(even) {{
    background-color: #f7f9fc;
  }}

  hr {{
    border: none;
    border-top: 1px solid #ddd;
    margin: 0.5cm 0;
  }}

  strong {{
    color: #1a1a2e;
  }}
</style>
</head>
<body>
{body}
</body>
</html>"""

# Regex patterns
_PIPE_ROW_RE = re.compile(r"^\|(.+)\|$")
_PIPE_SEP_RE = re.compile(r"^\|[\s\-:]+\|$")


class PdfExporter(BaseExporter):
    format = "pdf"

    async def export(
        self,
        report: StructuredReport,
        output_dir: str = "./data/exports",
    ) -> ExportResult:
        from weasyprint import HTML

        os.makedirs(output_dir, exist_ok=True)

        body_parts = []

        # -- Title --
        body_parts.append(f"<h1>{html_mod.escape(report.meta.title)}</h1>")

        # -- Meta line --
        meta = report.meta
        meta_items = []
        if meta.author:
            meta_items.append(f"作者：{html_mod.escape(meta.author)}")
        if meta.created_at:
            meta_items.append(f"日期：{html_mod.escape(meta.created_at)}")
        if meta.template_id:
            meta_items.append(f"模板：{html_mod.escape(meta.template_id)}")
        if meta.tags:
            meta_items.append(f"标签：{html_mod.escape(', '.join(meta.tags))}")
        if meta_items:
            body_parts.append(
                f'<div class="meta">{" &nbsp;|&nbsp; ".join(meta_items)}</div>'
            )

        body_parts.append('<div class="separator">────────────────────────</div>')

        # -- Sections --
        for section in report.sections:
            heading_text = section.section_def.title or section.section_def.heading
            if heading_text:
                body_parts.append(f"<h2>{html_mod.escape(heading_text)}</h2>")

            content = section.markdown_content or ""
            body_parts.append(self._md_to_html(content))

        # Fallback to full_markdown if no sections
        if not report.sections and report.full_markdown:
            body_parts.append(self._md_to_html(report.full_markdown))

        html_content = HTML_TEMPLATE.format(body="\n".join(body_parts))

        file_name = f"{report.meta.id}.pdf"
        file_path = os.path.join(output_dir, file_name)
        HTML(string=html_content).write_pdf(file_path)

        file_size = os.path.getsize(file_path)

        return ExportResult(
            file_path=file_path,
            format=self.format,
            file_size_bytes=file_size,
        )

    @staticmethod
    def _md_to_html(content: str) -> str:
        """Convert simple markdown content to HTML."""
        lines = content.split("\n")
        result: list[str] = []
        table_buffer: list[str] = []
        in_list = False
        list_type = ""  # "ul" or "ol"

        def close_list():
            nonlocal in_list, list_type
            if in_list:
                result.append(f"</{list_type}>")
                in_list = False
                list_type = ""

        for line in lines:
            stripped = line.strip()

            # Table buffering
            if table_buffer:
                table_buffer.append(stripped)
                continue

            # Table row detection
            if _PIPE_ROW_RE.match(stripped):
                table_buffer.append(stripped)
                continue

            # Flush table
            if not stripped and table_buffer:
                result.append(PdfExporter._table_to_html(table_buffer))
                table_buffer = []
                continue

            # Heading H3
            if stripped.startswith("### "):
                close_list()
                result.append(f"<h3>{html_mod.escape(stripped[4:])}</h3>")
                continue

            # Heading H2
            if stripped.startswith("## "):
                close_list()
                result.append(f"<h2>{html_mod.escape(stripped[3:])}</h2>")
                continue

            # Horizontal rule
            if stripped in ("---", "***", "___"):
                close_list()
                result.append("<hr>")
                continue

            # Unordered list
            if stripped.startswith(("- ", "* ", "+ ")):
                if not in_list or list_type != "ul":
                    close_list()
                    result.append("<ul>")
                    in_list = True
                    list_type = "ul"
                text = stripped[2:].strip()
                result.append(f"<li>{PdfExporter._inline_format(text)}</li>")
                continue

            # Ordered list
            ol_match = re.match(r"^(\d+)\.\s+(.*)", stripped)
            if ol_match:
                if not in_list or list_type != "ol":
                    close_list()
                    result.append("<ol>")
                    in_list = True
                    list_type = "ol"
                text = ol_match.group(2).strip()
                result.append(f"<li>{PdfExporter._inline_format(text)}</li>")
                continue

            # Empty line
            if not stripped:
                close_list()
                continue

            # Regular paragraph
            close_list()
            result.append(f"<p>{PdfExporter._inline_format(stripped)}</p>")

        # Flush remaining
        close_list()
        if table_buffer:
            result.append(PdfExporter._table_to_html(table_buffer))

        return "\n".join(result)

    @staticmethod
    def _table_to_html(rows: list[str]) -> str:
        """Convert buffered pipe-table rows to HTML table."""
        if not rows:
            return ""

        header_cells = [c.strip() for c in rows[0].strip("|").split("|")]
        data_start = 1
        if len(rows) > 1 and _PIPE_SEP_RE.match(rows[1].strip()):
            data_start = 2

        data_rows = []
        for row in rows[data_start:]:
            data_rows.append([c.strip() for c in row.strip("|").split("|")])

        html_parts = ["<table>", "<thead><tr>"]
        for cell in header_cells:
            html_parts.append(f"<th>{html_mod.escape(cell)}</th>")
        html_parts.append("</tr></thead>")

        if data_rows:
            html_parts.append("<tbody>")
            for row_data in data_rows:
                html_parts.append("<tr>")
                for cell in row_data[: len(header_cells)]:
                    html_parts.append(f"<td>{html_mod.escape(cell)}</td>")
                html_parts.append("</tr>")
            html_parts.append("</tbody>")

        html_parts.append("</table>")
        return "\n".join(html_parts)

    @staticmethod
    def _inline_format(text: str) -> str:
        """Convert inline markdown: **bold** → <strong>."""
        # Escape HTML first
        text = html_mod.escape(text)
        # Bold
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        return text
