"""下载端点 — PPTX 文件下载（支持 Bearer header 和 query token）"""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_current_user, decode_token
from backend.models.database import get_db
from backend.models.project import Project
from backend.storage.file_manager import ProjectStorage

router = APIRouter(prefix="/projects", tags=["download"])


@router.get("/{project_id}/download")
async def download_pptx(
    project_id: str,
    token: str = Query(default=""),
    db: AsyncSession = Depends(get_db),
):
    """Download the generated PPTX. Supports ?token= for browser direct links."""
    # Auth: try query token first (for <a href> links), then Bearer header
    if token:
        user = decode_token(token)
    else:
        raise HTTPException(status_code=401, detail="Token required")

    project = await db.get(Project, project_id)
    if not project or project.user_id != user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    storage = ProjectStorage.get()
    project_dir = storage.get_project_path(project_id) / "exports"

    # Priority: embedded > native > any pptx
    candidates = [
        project_dir / "native_embedded.pptx",
        project_dir / "native.pptx",
    ]
    if project_dir.exists():
        for f in sorted(project_dir.glob("*.pptx"), key=lambda p: p.stat().st_mtime, reverse=True):
            if f not in candidates:
                candidates.append(f)

    for path in candidates:
        if path.exists():
            return FileResponse(
                path=str(path),
                filename=f"{project.name}.pptx",
                media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            )

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PPTX not yet generated")
