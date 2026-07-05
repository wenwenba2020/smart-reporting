"""文件存储抽象层 — 本地实现，接口保留 COS 替换能力"""
from abc import ABC, abstractmethod
from pathlib import Path

from backend.config import settings


class BaseStorage(ABC):
    """Abstract base for project file storage."""

    @abstractmethod
    def create_project_dir(self, project_id: str) -> Path:
        ...

    @abstractmethod
    def save_file(self, project_id: str, rel_path: str, data: bytes) -> Path:
        ...

    @abstractmethod
    def read_file(self, project_id: str, rel_path: str) -> bytes:
        ...

    @abstractmethod
    def list_files(self, project_id: str, subdir: str = "") -> list[str]:
        ...

    @abstractmethod
    def get_project_path(self, project_id: str) -> Path:
        ...


class LocalStorage(BaseStorage):
    """Local filesystem implementation."""

    def __init__(self, base_path: str | None = None):
        self._base = Path(base_path or settings.LOCAL_STORAGE_PATH).resolve()
        self._base.mkdir(parents=True, exist_ok=True)

    def get_project_path(self, project_id: str) -> Path:
        return self._base / project_id

    def _safe_resolve(self, project_id: str, rel_path: str) -> Path:
        """Resolve path and verify it stays within the project directory."""
        project_root = self.get_project_path(project_id).resolve()
        resolved = (project_root / rel_path).resolve()
        if not str(resolved).startswith(str(project_root)):
            raise ValueError(f"Path traversal rejected: {rel_path}")
        return resolved

    def create_project_dir(self, project_id: str) -> Path:
        project_dir = self.get_project_path(project_id)
        for subdir in [
            "sources", "assets/uploads", "assets/extracted", "assets/ai_generated",
            "data", "svg_output", "fonts", "snapshots", "exports",
        ]:
            (project_dir / subdir).mkdir(parents=True, exist_ok=True)
        return project_dir

    def save_file(self, project_id: str, rel_path: str, data: bytes) -> Path:
        full_path = self._safe_resolve(project_id, rel_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(data)
        return full_path

    def read_file(self, project_id: str, rel_path: str) -> bytes:
        full_path = self._safe_resolve(project_id, rel_path)
        return full_path.read_bytes()

    def list_files(self, project_id: str, subdir: str = "") -> list[str]:
        target = self.get_project_path(project_id)
        if subdir:
            target = self._safe_resolve(project_id, subdir)
        if not target.exists():
            return []
        return [str(p.relative_to(target)) for p in target.rglob("*") if p.is_file()]


class ProjectStorage:
    """Factory that returns the right storage backend based on settings."""

    _instance: BaseStorage | None = None

    @classmethod
    def get(cls) -> BaseStorage:
        if cls._instance is None:
            if settings.STORAGE_TYPE == "local":
                cls._instance = LocalStorage()
            else:
                raise ValueError(f"Unsupported storage type: {settings.STORAGE_TYPE}")
        return cls._instance
