import logging
import uuid
from pathlib import Path
from typing import Optional

import aiofiles

from backend.config import settings

logger = logging.getLogger(__name__)


class LocalFileStore:
    """Local filesystem storage with UUID-based filenames."""

    def __init__(self, base_path: Optional[str] = None):
        self.base_path = Path(base_path or settings.local_storage_path).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _make_path(self, file_id: str) -> Path:
        return self.base_path / file_id

    async def save(self, filename: str, content: bytes) -> str:
        """Save file content and return its UUID-based ID."""
        ext = Path(filename).suffix
        file_id = f"{uuid.uuid4().hex}{ext}"
        file_path = self._make_path(file_id)
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)
        logger.info("Saved file %s -> %s", filename, file_path)
        return file_id

    async def read(self, file_id: str) -> bytes:
        """Read file content by ID."""
        file_path = self._make_path(file_id)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_id}")
        async with aiofiles.open(file_path, "rb") as f:
            return await f.read()

    def get_url(self, file_id: str) -> str:
        """Return a relative URL for accessing the file via the static mount."""
        return f"/static/files/{file_id}"


# Singleton instance
file_store = LocalFileStore()
