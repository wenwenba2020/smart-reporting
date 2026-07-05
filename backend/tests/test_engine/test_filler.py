"""
Tests for summarizer and filler (Task 10).
"""
import pytest

from backend.core.models import (
    ReportMeta,
    ReportTemplate,
    SectionDef,
    SourceDocument,
)
from backend.core.engine.summarizer import SourceSummarizer
from backend.core.engine.filler import SectionFiller


def _make_weekly_template():
    """Create a weekly report template matching the curated template structure."""
    sections = [
        SectionDef(key="weekly_summary", title="本周概要", required=True,
                   description="本周整体情况一句话总结，核心亮点",
                   source="generated", suggested_length="short"),
        SectionDef(key="key_tasks", title="重点工作进展", required=True,
                   description="本周完成的重点任务、里程碑节点",
                   source="generated", suggested_length="long"),
        SectionDef(key="data_metrics", title="核心数据指标", required=True,
                   description="本周关键业务数据与变化趋势",
                   source="generated", suggested_length="medium"),
        SectionDef(key="issues_risks", title="问题与风险", required=False,
                   description="本周遇到的问题、待解决的风险项",
                   source="generated", suggested_length="medium"),
        SectionDef(key="next_week_plan", title="下周计划", required=True,
                   description="下周重点任务安排与优先级",
                   source="generated", suggested_length="medium"),
        SectionDef(key="team_highlights", title="团队亮点", required=False,
                   description="团队成员的突出贡献、值得分享的好消息",
                   source="generated", suggested_length="short"),
    ]
    return ReportTemplate(
        template_id="curated_weekly_report",
        name="业务周报",
        category="进度类",
        parent_meta="meta_progress",
        description="适用于团队每周业务进展汇报",
        sections=sections,
        system_prompt="你是一个业务运营专家。请基于数据源中的周报数据，简洁清晰地总结本周工作。",
    )


class TestSectionFiller:
    """Tests for SectionFiller — focused on non-LLM logic."""

    def test_collect_leaf_sections_weekly_report(self):
        """Weekly report template should yield 6 leaf sections."""
        filler = SectionFiller()
        template = _make_weekly_template()
        leaves = filler._collect_leaf_sections(template.sections)

        assert len(leaves) == 6, f"Expected 6 leaf sections, got {len(leaves)}"

        # All should be SectionDef instances
        for leaf in leaves:
            assert isinstance(leaf, SectionDef)

    def test_collect_leaf_sections_empty(self):
        """Empty section list should return empty list."""
        filler = SectionFiller()
        leaves = filler._collect_leaf_sections([])
        assert leaves == []

    def test_collect_leaf_sections_nested(self):
        """Nested sections — only top-level leaves should be collected."""
        filler = SectionFiller()
        sections = [
            SectionDef(key="parent1", title="Parent 1", level=1, description="Top level"),
            SectionDef(key="child1", title="Child 1", level=2, description="Nested"),
            SectionDef(key="parent2", title="Parent 2", level=1, description="Top level"),
        ]
        leaves = filler._collect_leaf_sections(sections)
        assert len(leaves) == 2
        assert leaves[0].key == "parent1"
        assert leaves[1].key == "parent2"


class TestSourceSummarizer:
    """Tests for SourceSummarizer — focused on single-source and edge cases."""

    @pytest.mark.asyncio
    async def test_single_source_returns_content_directly(self):
        """With one source, the content should be returned without LLM call."""
        summarizer = SourceSummarizer()
        doc = SourceDocument(
            id="doc1",
            title="测试文档",
            content="这是测试内容。",
            source_type="knowledge_base",
        )
        result = await summarizer.summarize([doc])
        assert result == "这是测试内容。"

    @pytest.mark.asyncio
    async def test_empty_sources_returns_empty(self):
        """No sources should return empty string."""
        summarizer = SourceSummarizer()
        result = await summarizer.summarize([])
        assert result == ""
