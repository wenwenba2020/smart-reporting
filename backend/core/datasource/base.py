"""
Data Source Adapter — abstract base class and registry.

All data-source adapters inherit from DataSourceAdapter and are auto-registered
with the module-level `registry` via the @register_adapter decorator.
"""

from abc import ABC, abstractmethod
from typing import Optional, Type

from backend.core.models import SourceDocument


class DataSourceAdapter(ABC):
    """Abstract base for all data-source adapters.

    Each concrete adapter MUST set `source_type` (a unique string id) and
    implement both `supports()` and `parse()`.
    """

    source_type: str = ""

    @abstractmethod
    async def parse(
        self,
        file_path: str,
        filename: str,
        metadata: Optional[dict] = None,
    ) -> SourceDocument:
        """Parse *file_path* into a SourceDocument.

        Parameters
        ----------
        file_path : str
            Absolute or relative path to the source file on disk.
        filename : str
            Original filename (used for extension / naming heuristics).
        metadata : dict or None
            Optional caller-supplied metadata to merge into the document.
        """
        ...

    @abstractmethod
    def supports(self, filename: str) -> bool:
        """Return True when this adapter can handle *filename*."""
        ...


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class DataSourceRegistry:
    """A simple registry of DataSourceAdapter instances keyed by source_type."""

    def __init__(self) -> None:
        self._adapters: dict[str, DataSourceAdapter] = {}

    def register(self, adapter: DataSourceAdapter) -> None:
        self._adapters[adapter.source_type] = adapter

    def get(self, source_type: str) -> Optional[DataSourceAdapter]:
        return self._adapters.get(source_type)

    def find_by_filename(self, filename: str) -> Optional[DataSourceAdapter]:
        for adapter in self._adapters.values():
            if adapter.supports(filename):
                return adapter
        return None

    def list_types(self) -> list[str]:
        return list(self._adapters.keys())


registry = DataSourceRegistry()


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------

def register_adapter(cls: Type[DataSourceAdapter]) -> Type[DataSourceAdapter]:
    """Class decorator that instantiates and registers an adapter."""
    instance = cls()
    registry.register(instance)
    return cls
