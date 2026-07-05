"""Report export and file download API."""
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.report_engine.output_engine import output_engine

router = APIRouter(prefix="/export", tags=["export"])

EXPORTS_DIR = Path("./data/exports")


class ExportRequest(BaseModel):
    formats: list[str]  # e.g. ["pptx", "docx", "pdf"]


@router.post("/{report_id}/export")
async def export_report(report_id: str, body: ExportRequest):
    """Export a report to the requested formats."""
    from backend.api.routes.reports import _reports

    report = _reports.get(report_id)
    if report is None:
        raise HTTPException(404, f"Report not found: {report_id}")

    if not body.formats:
        raise HTTPException(400, "At least one format is required")

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    errors = []

    for fmt in body.formats:
        try:
            result = await output_engine.generate(
                report_json=report.report_json,
                format_type=fmt,
                output_dir=str(EXPORTS_DIR),
            )
            results.append({
                "format": result.file_type,
                "mime_type": result.mime_type,
                "file_size": result.file_size,
                "file_path": result.file_path,
                "download_url": f"/api/v1/export/download/{Path(result.file_path).name}",
            })
        except ValueError as e:
            errors.append({"format": fmt, "error": str(e)})
        except Exception as e:
            errors.append({"format": fmt, "error": f"Export failed: {e}"})

    return {
        "report_id": report_id,
        "results": results,
        "errors": errors,
    }


@router.get("/download/{file_name}")
async def download_file(file_name: str):
    """Download an exported file by name."""
    file_path = EXPORTS_DIR / file_name
    if not file_path.exists():
        raise HTTPException(404, f"File not found: {file_name}")

    # Determine media type from extension
    ext = file_path.suffix.lower()
    media_type_map = {
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pdf": "application/pdf",
        ".md": "text/markdown",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }
    media_type = media_type_map.get(ext, "application/octet-stream")

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=file_name,
    )
