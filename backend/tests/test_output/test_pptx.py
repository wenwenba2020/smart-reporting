"""Tests for PPTX exporter."""
import os
import pytest
from pathlib import Path
from backend.core.models import (
    StructuredReport, ReportMeta, ReportTemplate, ReportSection, SectionDef,
)
from backend.core.output.pptx_exporter import PptxExporter
from backend.core.output import output_engine


def _make_report(title="Test Report", sections=None):
    """Helper to create a minimal StructuredReport for testing."""
    if sections is None:
        sections = [
            ReportSection(
                section_def=SectionDef(key="cover", title="封面", heading="封面"),
                markdown_content="# Test Report\n智能报告平台",
            ),
            ReportSection(
                section_def=SectionDef(key="intro", title="项目概述", heading="项目概述"),
                markdown_content="- 项目背景：企业数字化转型\n- 项目目标：提升效率30%\n- 项目周期：2026 Q3-Q4",
            ),
            ReportSection(
                section_def=SectionDef(key="data", title="数据分析", heading="数据分析"),
                markdown_content="- 核心指标达标率95%\n- 用户满意度4.2/5\n- 成本节约200万元",
            ),
            ReportSection(
                section_def=SectionDef(key="ending", title="总结", heading="总结"),
                markdown_content="- 项目阶段性成果显著\n- 下一步：推广到更多部门",
            ),
        ]
    return StructuredReport(
        meta=ReportMeta(
            id="test_001",
            title=title,
            template_id="curated_weekly_report",
            author="Test",
        ),
        template=ReportTemplate(id="t1", name="Test Template"),
        sections=sections,
        full_markdown="test content",
    )


def test_pptx_exporter_format():
    exporter = PptxExporter()
    assert exporter.format == "pptx"


def test_pptx_registered_in_engine():
    formats = output_engine.get_formats()
    assert "pptx" in formats


def test_svg_generation():
    """Test that SVGs are generated correctly from report sections."""
    exporter = PptxExporter()
    report = _make_report()
    svg_dir = Path("./data/exports/svg_test")
    svg_dir.mkdir(parents=True, exist_ok=True)

    svg_files, notes = exporter._generate_svgs(report, svg_dir)
    assert len(svg_files) == 4
    assert len(notes) == 4

    # Check cover slide
    cover_svg = svg_files[0].read_text(encoding="utf-8")
    assert "Test Report" in cover_svg
    assert "viewBox" in cover_svg
    assert "1280" in cover_svg

    # Check content slide
    content_svg = svg_files[1].read_text(encoding="utf-8")
    assert "项目概述" in content_svg
    assert "项目背景" in content_svg


@pytest.mark.asyncio
async def test_pptx_export():
    """Test full PPTX export pipeline."""
    exporter = PptxExporter()
    report = _make_report()
    output_dir = "./data/exports"

    result = await exporter.export(report, output_dir)
    assert result.format == "pptx"
    assert os.path.exists(result.file_path)
    assert result.file_size_bytes > 0

    # Verify the PPTX is a valid ZIP (all PPTX files are ZIP archives)
    import zipfile
    assert zipfile.is_zipfile(result.file_path), "PPTX should be a valid ZIP archive"
