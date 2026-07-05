"""文件上传端点 — PDF/DOCX/PPTX 上传 + 解析 + URL 调研"""
import asyncio
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_current_user
from backend.models.database import get_db
from backend.models.project import Project
from backend.storage.file_manager import ProjectStorage
from backend.parsers.doc_parser import parse_document
from backend.parsers.ppt_parser import analyze_reference_pptx

router = APIRouter(prefix="/projects", tags=["upload"])

ALLOWED_DOC_TYPES = {".pdf", ".docx", ".txt", ".md"}
ALLOWED_PPT_TYPES = {".pptx"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


@router.post("/{project_id}/upload/document")
async def upload_document(
    project_id: str,
    file: UploadFile = File(...),
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a source document (PDF/DOCX/TXT/MD) and parse to Markdown."""
    project = await db.get(Project, project_id)
    if not project or project.user_id != user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_DOC_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {suffix}. Allowed: {ALLOWED_DOC_TYPES}")

    # Save file
    storage = ProjectStorage.get()
    storage.create_project_dir(project_id)
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")

    saved_path = storage.save_file(project_id, f"sources/{file.filename}", content)

    # Parse to Markdown
    try:
        markdown = parse_document(str(saved_path))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Parse failed: {e}")

    # Save parsed markdown
    md_path = storage.save_file(project_id, "sources/parsed.md", markdown.encode("utf-8"))

    return {
        "filename": file.filename,
        "size": len(content),
        "markdown_preview": markdown[:500],
        "markdown_path": str(md_path),
    }


@router.post("/{project_id}/upload/reference-pptx")
async def upload_reference_pptx(
    project_id: str,
    file: UploadFile = File(...),
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a reference PPTX for style/image extraction."""
    project = await db.get(Project, project_id)
    if not project or project.user_id != user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_PPT_TYPES:
        raise HTTPException(status_code=400, detail="Only .pptx files allowed")

    storage = ProjectStorage.get()
    storage.create_project_dir(project_id)
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")

    saved_path = storage.save_file(project_id, f"sources/{file.filename}", content)

    # Analyze: extract images + style info
    project_dir = storage.get_project_path(project_id)
    extracted_dir = project_dir / "assets" / "extracted"

    try:
        analysis = analyze_reference_pptx(str(saved_path), str(extracted_dir))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Analysis failed: {e}")

    return {
        "filename": file.filename,
        "images_extracted": len(analysis.get("images", [])),
        "style": analysis.get("style", {}),
    }


class ResearchRequest(BaseModel):
    urls: list[str]
    deep: bool = False
    provider: str = "exa"  # "exa" | "tavily"


@router.post("/{project_id}/research")
async def research_urls(
    project_id: str,
    body: ResearchRequest,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """抓取用户提供的 URL 列表，保存为 sources/url_*.md 供规划师/文案师使用。

    deep=True 时用 Tavily crawl 抓站内多页（较慢，但内容更丰富）。
    """
    project = await db.get(Project, project_id)
    if not project or project.user_id != user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    urls = [u.strip() for u in body.urls if u and u.strip()]
    if not urls:
        raise HTTPException(status_code=400, detail="至少提供一个 URL")
    if len(urls) > 10:
        raise HTTPException(status_code=400, detail="单次最多 10 个 URL")
    if body.deep and len(urls) > 3:
        raise HTTPException(status_code=400, detail="深度抓取单次最多 3 个 URL")

    from backend.agents.planner import fetch_urls_content

    # Tavily SDK 是同步的，直接在 async route 里跑会阻塞事件循环。
    # 用 to_thread + 超时包一层（深度 150s / 普通 60s）。
    overall_timeout = 150.0 if body.deep else 60.0
    try:
        fetched = await asyncio.wait_for(
            asyncio.to_thread(fetch_urls_content, urls, body.deep, body.provider),
            timeout=overall_timeout,
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail=f"抓取超时（{int(overall_timeout)}s）。深度抓取对大型站点可能耗时过长，请改用浅抓取或换更具体的页面 URL。",
        )

    storage = ProjectStorage.get()
    storage.create_project_dir(project_id)
    response_items: list[dict] = []
    for i, r in enumerate(fetched):
        if r.get("error"):
            response_items.append({
                "url": r["url"],
                "status": "failed",
                "error": r["error"],
            })
            continue
        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        rel_path = f"sources/url_{ts}_{i}.md"
        md = f"# {r['title']}\n\nSource: {r['url']}\n\n{r['content']}"
        storage.save_file(project_id, rel_path, md.encode("utf-8"))
        response_items.append({
            "url": r["url"],
            "title": r["title"],
            "status": "ok",
            "chars": len(r["content"]),
            "preview": r["content"][:200],
            "saved_path": rel_path,
        })

    return {"results": response_items}
