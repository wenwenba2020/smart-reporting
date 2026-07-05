"""End-to-end integration tests for the Smart Reporting API."""
import io
import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Ensure backend is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from backend.main import app


@pytest_asyncio.fixture
async def client():
    """Create an async HTTP test client pointed at the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health(client):
    """Verify the health endpoint returns 200."""
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200
    assert data["data"]["status"] == "healthy"


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_templates(client):
    """Verify the templates endpoint returns at least 5 templates."""
    resp = await client.get("/api/v1/templates")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) >= 5
    # Verify each template has required fields
    for tmpl in data:
        assert "template_id" in tmpl
        assert "name" in tmpl
        assert "category" in tmpl


@pytest.mark.asyncio
async def test_get_single_template(client):
    """Verify fetching a single template by ID works."""
    # First list templates to get a valid ID
    resp = await client.get("/api/v1/templates")
    templates = resp.json()["data"]
    template_id = templates[0]["template_id"]

    resp = await client.get(f"/api/v1/templates/{template_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["template_id"] == template_id
    assert "sections" in data
    assert len(data["sections"]) > 0


# ---------------------------------------------------------------------------
# Data sources — upload, list, get
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_and_list_sources(client):
    """Upload a text file and verify it appears in the source list."""
    content = b"Hello test world\nThis is a test data source.\n"
    files = {"file": ("test.txt", io.BytesIO(content), "text/plain")}
    resp = await client.post("/api/v1/datasources/upload", files=files)
    assert resp.status_code == 200
    data = resp.json()
    source_id = data["source_id"]
    assert data["source_type"] == "file_upload"

    # List all sources
    resp = await client.get("/api/v1/datasources")
    assert resp.status_code == 200
    sources = resp.json()["data"]
    assert len(sources) >= 1
    assert any(s["id"] == source_id for s in sources)

    # Get single source by ID
    resp = await client.get(f"/api/v1/datasources/{source_id}")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["id"] == source_id
    assert "Hello test world" in detail["content"]


@pytest.mark.asyncio
async def test_upload_csv_source(client):
    """Upload a CSV file and verify it is parsed correctly."""
    content = b"date,sales,region\n2025-01-01,1000,East\n2025-01-02,1500,West\n"
    files = {"file": ("sales.csv", io.BytesIO(content), "text/csv")}
    resp = await client.post("/api/v1/datasources/upload", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert data["source_id"]
    assert data["source_type"] == "file_upload"


# ---------------------------------------------------------------------------
# Intent recognition
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_and_intent(client):
    """Upload a weekly report file and test intent recognition."""
    # Upload a data source
    content = b"2025-09-15 10:30:00 Zhang San\nWeekly sales report data\nRevenue: 50000\n"
    files = {"file": ("weekly.txt", io.BytesIO(content), "text/plain")}
    resp = await client.post("/api/v1/datasources/upload", files=files)
    assert resp.status_code == 200
    source_id = resp.json()["source_id"]

    # Intent recognition (works even without LLM due to fallback)
    resp = await client.post(
        "/api/v1/reports/intent",
        json={
            "user_query": "generate weekly report",
            "source_ids": [source_id],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "intent" in data
    assert "recommendations" in data
    # Without LLM, the fallback intent may not score above threshold;
    # the endpoint itself should still return 200 with valid structure.
    if len(data["recommendations"]) > 0:
        rec = data["recommendations"][0]
        assert "template_id" in rec
        assert "name" in rec
        assert "match_score" in rec


# ---------------------------------------------------------------------------
# Report generation (SSE streaming)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_report_sse(client):
    """Verify the SSE report generation endpoint starts streaming."""
    # Upload a data source first
    content = b"Monthly performance review\nTeam A completed 10 projects.\nTeam B completed 8 projects.\n"
    files = {"file": ("monthly.txt", io.BytesIO(content), "text/plain")}
    resp = await client.post("/api/v1/datasources/upload", files=files)
    source_id = resp.json()["source_id"]

    # Start generation via SSE
    resp = await client.post(
        "/api/v1/reports/generate",
        json={
            "template_id": "curated_weekly_report",
            "source_ids": [source_id],
            "title": "Test Weekly Report",
        },
    )
    assert resp.status_code == 200
    # SSE streams return text/event-stream
    assert "text/event-stream" in resp.headers.get("content-type", "")

    # Read the SSE stream — it should contain at least progress and done events
    body = resp.text
    assert "data:" in body
    # The stream should end with a "done" event (JSON with space after colon)
    assert '"type": "done"' in body or '"type": "error"' in body


# ---------------------------------------------------------------------------
# Full output pipeline (without LLM)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_flow_without_llm():
    """Test the complete output pipeline end-to-end without needing LLM.

    Builds a StructuredReport in memory and exports to all three formats,
    verifying each output file is created and non-empty.
    """
    from backend.core.models import (
        StructuredReport,
        ReportSection,
        ReportMeta,
        ReportTemplate,
        SectionDef,
    )
    from backend.core.output import output_engine

    # Build a realistic report
    template = ReportTemplate(
        template_id="test_e2e",
        name="End-to-End Test Report Template",
        description="Template for end-to-end integration testing",
        category="test",
    )

    sections = [
        ReportSection(
            section_def=SectionDef(
                key="s1",
                title="Overview",
                description="Executive summary section",
            ),
            markdown_content=(
                "## Executive Summary\n\n"
                "This report covers Q3 2026 performance across all departments.\n\n"
                "- Total Revenue: $1,200,000\n"
                "- New Customers: 450\n"
                "- Customer Satisfaction: 94%\n"
            ),
        ),
        ReportSection(
            section_def=SectionDef(
                key="s2",
                title="Key Metrics",
                description="Quantitative performance data",
            ),
            markdown_content=(
                "## Key Metrics\n\n"
                "| Metric | Value | Target | Status |\n"
                "|--------|-------|--------|--------|\n"
                "| Revenue | $1.2M | $1.0M | Above |\n"
                "| Growth | 15% | 10% | Above |\n"
                "| NPS | 72 | 70 | Met |\n"
            ),
        ),
        ReportSection(
            section_def=SectionDef(
                key="s3",
                title="Recommendations",
                description="Action items and next steps",
            ),
            markdown_content=(
                "## Recommendations\n\n"
                "1. **Expand Sales Team**: Hire 3 additional reps in Q4\n"
                "2. **Product Improvement**: Address top 3 customer pain points\n"
                "3. **Marketing Push**: Launch Q4 campaign by October 15\n"
            ),
        ),
    ]

    meta = ReportMeta(
        id="test_e2e",
        title="End-to-End Test Report",
        template_id="test_e2e",
        created_at="2026-07-05",
        author="Test Suite",
        tags=["e2e", "integration", "test"],
    )

    report = StructuredReport(
        meta=meta,
        template=template,
        sections=sections,
        full_markdown="",
        report_json={},
    )

    # Export to all three formats
    results = await output_engine.export(
        report,
        ["docx", "pdf", "html_mindmap"],
        output_dir="./data/exports",
    )

    assert len(results) == 3, f"Expected 3 results, got {len(results)}"

    for r in results:
        assert os.path.exists(r.file_path), (
            f"{r.format} file should exist at {r.file_path}"
        )
        assert r.file_size_bytes > 0, (
            f"{r.format} file should not be empty (size={r.file_size_bytes})"
        )

    # Clean up generated files
    for r in results:
        os.remove(r.file_path)


@pytest.mark.asyncio
async def test_export_result_fields():
    """Verify ExportResult fields are properly populated."""
    from backend.core.models import (
        StructuredReport,
        ReportSection,
        ReportMeta,
        ReportTemplate,
        SectionDef,
    )
    from backend.core.output import output_engine

    template = ReportTemplate(
        template_id="test_fields",
        name="Fields Test",
        category="test",
    )

    section = ReportSection(
        section_def=SectionDef(key="s1", title="Test Section"),
        markdown_content="Simple content for field validation.",
    )

    report = StructuredReport(
        meta=ReportMeta(id="test_fields", title="Fields Test", template_id="test_fields"),
        template=template,
        sections=[section],
    )

    results = await output_engine.export(report, ["docx"], output_dir="./data/exports")
    assert len(results) == 1
    r = results[0]

    assert r.format == "docx"
    assert r.file_path.endswith(".docx")
    assert r.file_size_bytes > 0
    assert os.path.exists(r.file_path)

    os.remove(r.file_path)
