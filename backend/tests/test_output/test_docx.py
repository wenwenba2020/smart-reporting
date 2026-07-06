import os
import pytest
from backend.core.output import output_engine
from backend.core.models import (
    StructuredReport,
    ReportSection,
    ReportMeta,
    ReportTemplate,
    SectionDef,
)


def _make_test_report() -> StructuredReport:
    """Build a minimal StructuredReport for use across export tests."""
    template = ReportTemplate(
        id="tpl_001",
        name="测试模板",
        description="用于输出引擎测试的模板",
        category="测试",
    )

    section1 = ReportSection(
        section_def=SectionDef(
            id="s1", key="s1", heading="章节一", title="章节一",
        ),
        markdown_content=(
            "这是测试内容的第一段。\n\n"
            "- 要点1：数据完整性\n"
            "- 要点2：格式规范性\n\n"
            "| 指标 | 数值 | 状态 |\n"
            "|------|------|------|\n"
            "| 完成率 | 95% | 正常 |\n"
            "| 错误率 | 0.5% | 正常 |\n\n"
            "以下是一个有序列表：\n\n"
            "1. 第一步：初始化\n"
            "2. 第二步：执行\n"
            "3. 第三步：验证\n"
        ),
    )

    section2 = ReportSection(
        section_def=SectionDef(
            id="s2", key="s2", heading="章节二", title="章节二",
        ),
        markdown_content="这是**加粗**文本的示例段落。",
    )

    meta = ReportMeta(
        id="test_001",
        title="测试报告",
        template_id="tpl_001",
        created_at="2025-07-01",
        author="测试团队",
        tags=["测试", "验证"],
    )

    # Note: StructuredReport.meta.id is used as the file prefix (report.meta.id)
    # Make sure the meta.id and report_id align properly
    return StructuredReport(
        meta=meta,
        template=template,
        sections=[section1, section2],
        full_markdown="",
        report_json={},
    )


@pytest.mark.asyncio
async def test_docx_export():
    """Verify that DocxExporter produces a valid .docx file."""
    report = _make_test_report()
    results = await output_engine.export(report, ["docx"], output_dir="./data/exports")

    assert len(results) == 1
    result = results[0]
    assert result.format == "docx"
    assert os.path.exists(result.file_path), f"File not found: {result.file_path}"
    assert result.file_size_bytes > 0, f"File size is 0: {result.file_path}"

    # Clean up
    os.remove(result.file_path)


@pytest.mark.asyncio
async def test_pdf_export():
    """Verify that PdfExporter produces a valid .pdf file."""
    report = _make_test_report()
    results = await output_engine.export(report, ["pdf"], output_dir="./data/exports")

    assert len(results) == 1
    result = results[0]
    assert result.format == "pdf"
    assert os.path.exists(result.file_path), f"File not found: {result.file_path}"
    assert result.file_size_bytes > 0, f"File size is 0: {result.file_path}"

    # Clean up
    os.remove(result.file_path)


@pytest.mark.asyncio
async def test_mindmap_export():
    """Verify that MindmapExporter produces a valid .html file."""
    report = _make_test_report()
    results = await output_engine.export(report, ["html_mindmap"], output_dir="./data/exports")

    assert len(results) == 1
    result = results[0]
    assert result.format == "html_mindmap"
    assert os.path.exists(result.file_path), f"File not found: {result.file_path}"
    assert result.file_size_bytes > 0, f"File size is 0: {result.file_path}"

    # Verify it contains expected HTML structure
    with open(result.file_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "<!DOCTYPE html>" in content
    assert "markmap" in content.lower()
    assert "测试报告" in content

    # Clean up
    os.remove(result.file_path)


@pytest.mark.asyncio
async def test_multi_format_export():
    """Verify that exporting to multiple formats at once works."""
    report = _make_test_report()
    all_formats = output_engine.get_formats()
    results = await output_engine.export(report, all_formats, output_dir="./data/exports")

    assert len(results) == len(all_formats)
    formats_returned = {r.format for r in results}
    assert formats_returned == set(all_formats)

    for result in results:
        assert os.path.exists(result.file_path), f"File not found for {result.format}"
        assert result.file_size_bytes > 0, f"File size 0 for {result.format}"
        os.remove(result.file_path)


@pytest.mark.asyncio
async def test_get_formats():
    """Verify that get_formats returns the expected keys."""
    formats = output_engine.get_formats()
    assert "docx" in formats
    assert "pdf" in formats
    assert "html_mindmap" in formats
    assert len(formats) >= 4  # docx, pdf, html_mindmap, pptx


@pytest.mark.asyncio
async def test_empty_sections_report():
    """Verify export of a report with no sections but full_markdown set."""
    meta = ReportMeta(
        id="test_empty",
        title="空章节报告",
        template_id="tpl_empty",
    )
    template = ReportTemplate(id="tpl_empty", name="空模板")
    report = StructuredReport(
        meta=meta,
        template=template,
        sections=[],
        full_markdown="- 唯一的内容\n- 另一个要点",
        report_json={},
    )

    results = await output_engine.export(report, ["docx", "pdf"], output_dir="./data/exports")
    assert len(results) == 2
    for r in results:
        assert os.path.exists(r.file_path), f"File not found for {r.format}"
        assert r.file_size_bytes > 0, f"File size 0 for {r.format}"
        os.remove(r.file_path)
