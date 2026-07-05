from backend.core.output.base import BaseExporter
from backend.core.output.docx_exporter import DocxExporter
from backend.core.output.pdf_exporter import PdfExporter
from backend.core.output.mindmap_exporter import MindmapExporter
from backend.core.models import ExportResult, StructuredReport


class ReportOutputEngine:
    """Orchestrates multi-format export of a StructuredReport."""

    def __init__(self):
        self._exporters = {
            "docx": DocxExporter(),
            "pdf": PdfExporter(),
            "html_mindmap": MindmapExporter(),
        }

    async def export(
        self,
        report: StructuredReport,
        formats: list[str],
        output_dir: str = "./data/exports",
    ) -> list[ExportResult]:
        """Export a structured report to one or more formats.

        Args:
            report: The populated StructuredReport to export.
            formats: List of format identifiers (e.g. ["docx", "pdf"]).
            output_dir: Directory where output files will be written.

        Returns:
            A list of ExportResult objects, one per successfully exported format.
        """
        results: list[ExportResult] = []
        for fmt in formats:
            if fmt in self._exporters:
                result = await self._exporters[fmt].export(report, output_dir)
                results.append(result)
        return results

    def get_formats(self) -> list[str]:
        """Return the list of supported format identifiers."""
        return list(self._exporters.keys())


# Convenience singleton
output_engine = ReportOutputEngine()
