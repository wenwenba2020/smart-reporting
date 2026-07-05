from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.core.models import StructuredReport, ExportResult


class BaseExporter(ABC):
    """Abstract base class for all report format exporters."""

    format: str = ""

    @abstractmethod
    async def export(
        self,
        report: "StructuredReport",
        output_dir: str = "./data/exports",
    ) -> "ExportResult":
        """Export a structured report to the exporter's target format.

        Args:
            report: The populated StructuredReport to export.
            output_dir: Directory where the output file will be written.

        Returns:
            An ExportResult describing the exported file.
        """
        ...
