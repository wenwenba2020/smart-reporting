"""多格式报告输出引擎"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class OutputResult:
    file_path: str
    file_type: str
    mime_type: str
    file_size: int


class OutputAdapter(ABC):
    """输出格式适配器抽象基类"""

    @property
    @abstractmethod
    def format_type(self) -> str:
        ...

    @abstractmethod
    async def generate(
        self, report_json: dict, template_path: str | None = None,
        style_rules: dict | None = None, output_dir: str | Path = ".",
    ) -> OutputResult:
        ...


class ReportOutputEngine:
    """统一报告输出引擎"""

    _adapters: dict[str, OutputAdapter] = {}

    def register(self, adapter: OutputAdapter) -> None:
        self._adapters[adapter.format_type] = adapter

    async def generate(
        self, report_json: dict, format_type: str,
        template_path: str | None = None, style_rules: dict | None = None,
        output_dir: str | Path = ".",
    ) -> OutputResult:
        adapter = self._adapters.get(format_type)
        if not adapter:
            raise ValueError(f"Unsupported format: {format_type}. Available: {list(self._adapters.keys())}")
        return await adapter.generate(
            report_json=report_json, template_path=template_path,
            style_rules=style_rules, output_dir=output_dir,
        )

    def list_formats(self) -> list[str]:
        return list(self._adapters.keys())


output_engine = ReportOutputEngine()
