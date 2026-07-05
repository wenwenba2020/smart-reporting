"""数据源插件抽象基类 — 企业可通过实现此接口接入任意信息源"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class SourceDocument:
    """数据源返回的统一文档结构"""
    source_id: str
    source_type: str
    source_name: str
    title: str
    content: str
    metadata: dict = field(default_factory=dict)
    relevance_score: float = 0.0


@dataclass
class SourceSchema:
    """数据源的字段/分类结构，供前端展示可选范围"""
    source_type: str
    source_name: str
    categories: list[str] = field(default_factory=list)
    fields: list[str] = field(default_factory=list)
    total_documents: int = 0


class DataSourcePlugin(ABC):
    """数据源插槽抽象接口。内置实现: KnowledgeBaseSource / CaseLibrarySource"""

    @property
    @abstractmethod
    def source_type(self) -> str:
        ...

    @property
    @abstractmethod
    def source_name(self) -> str:
        ...

    @abstractmethod
    async def search(self, query: str, top_k: int = 10, **filters) -> list[SourceDocument]:
        ...

    @abstractmethod
    async def get_schema(self, **filters) -> SourceSchema:
        ...

    async def health_check(self) -> bool:
        return True

    def to_config_dict(self) -> dict:
        return {"source_type": self.source_type, "source_name": self.source_name}


class DataSourceRegistry:
    """数据源插件注册表（单例）"""
    _instance: "DataSourceRegistry | None" = None
    _plugins: dict[str, DataSourcePlugin] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(self, plugin: DataSourcePlugin) -> None:
        self._plugins[plugin.source_type] = plugin

    def get(self, source_type: str) -> DataSourcePlugin | None:
        return self._plugins.get(source_type)

    def list_all(self) -> list[DataSourcePlugin]:
        return list(self._plugins.values())

    def list_configs(self) -> list[dict]:
        return [p.to_config_dict() for p in self._plugins.values()]


registry = DataSourceRegistry()
