"""数据源插件注册"""
from backend.data_source.base import registry
from backend.data_source.knowledge_source import KnowledgeBaseSource
from backend.data_source.case_library_source import CaseLibrarySource


def register_builtin_sources():
    """应用启动时注册所有内置数据源插件（幂等）。"""
    existing = {p.source_type for p in registry.list_all()}
    if "knowledge_base" not in existing:
        registry.register(KnowledgeBaseSource())
    if "case_library" not in existing:
        registry.register(CaseLibrarySource())
