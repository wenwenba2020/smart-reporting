"""
Tests for intent recognition and template matching (Task 9).
"""
import pytest

from backend.core.models import ReportIntent, ReportTemplate, SectionDef
from backend.core.engine.template_matcher import TemplateMatcher


def _make_template(template_id, name, category, parent_meta=None, description=""):
    """Helper to create a ReportTemplate for testing."""
    return ReportTemplate(
        template_id=template_id,
        name=name,
        category=category,
        parent_meta=parent_meta,
        description=description,
        sections=[],
    )


class TestTemplateMatcher:
    """Tests for TemplateMatcher — non-LLM scoring logic."""

    def test_weekly_intent_matches_progress_templates(self):
        """A weekly-report intent should match progress-category templates."""
        matcher = TemplateMatcher()
        intent = ReportIntent(
            raw_query="帮我写一份本周业务周报",
            report_type="周报",
            category="进度类",
            period="本周",
            scope="团队",
            key_themes=["业务进展", "核心数据", "下周计划"],
        )

        # Register templates that mimic what template_store would have
        templates = [
            _make_template("t1", "业务周报", "进度类", parent_meta="meta_progress",
                           description="适用于团队每周业务进展汇报"),
            _make_template("t2", "项目进展报告", "进度类", parent_meta="meta_progress",
                           description="适用于项目进度跟踪"),
            _make_template("t3", "员工KPI报告", "指标类", parent_meta="meta_indicator",
                           description="适用于员工KPI绩效考核"),
        ]

        results = []
        for tmpl in templates:
            score = matcher._calculate_score(intent, tmpl)
            if score > 0.3:
                results.append((tmpl, score))

        # Should find at least the weekly report itself
        assert len(results) >= 1, f"Expected at least 1 match, got {len(results)}"

        # The weekly report should have the highest score
        results.sort(key=lambda x: x[1], reverse=True)
        assert results[0][0].name == "业务周报", \
            f"Expected '业务周报' to be top match, got '{results[0][0].name}'"

        # All scores should be reasonable (between 0.0 and 1.0)
        for _, score in results:
            assert 0.0 <= score <= 1.0, f"Score {score} out of range"

    def test_kpi_intent_matches_indicator_templates(self):
        """A KPI-report intent should match indicator-category templates."""
        matcher = TemplateMatcher()
        intent = ReportIntent(
            raw_query="生成一份员工KPI考核报告",
            report_type="KPI报告",
            category="指标类",
            period="Q2",
            scope="个人",
            key_themes=["KPI达成", "行为评估", "发展建议"],
        )

        templates = [
            _make_template("t1", "业务周报", "进度类", parent_meta="meta_progress",
                           description="适用于团队每周业务进展汇报"),
            _make_template("t2", "员工KPI报告", "指标类", parent_meta="meta_indicator",
                           description="适用于员工KPI绩效考核"),
            _make_template("t3", "销售业绩报告", "指标类", parent_meta="meta_indicator",
                           description="适用于销售业绩分析"),
        ]

        results = []
        for tmpl in templates:
            score = matcher._calculate_score(intent, tmpl)
            if score > 0.3:
                results.append((tmpl, score))

        assert len(results) >= 1, f"Expected at least 1 match, got {len(results)}"

        results.sort(key=lambda x: x[1], reverse=True)
        assert results[0][0].name == "员工KPI报告", \
            f"Expected '员工KPI报告' to be top match, got '{results[0][0].name}'"

    def test_match_returns_recommendations(self):
        """The full match() method should return TemplateRecommendation objects."""
        matcher = TemplateMatcher()
        intent = ReportIntent(
            raw_query="写一份本周工作周报",
            report_type="周报",
            category="进度类",
            period="本周",
            scope="团队",
            key_themes=["业务进展"],
        )

        results = matcher.match(intent, top_k=3)

        assert len(results) >= 1, f"Expected at least 1 result, got {len(results)}"
        assert len(results) <= 3

        # First result should be selected
        if results:
            assert results[0].is_selected is True

        # All should have valid scores
        for r in results:
            assert 0.0 <= r.match_score <= 1.0
            assert r.template_id
            assert r.name
            assert r.match_reason

    def test_category_mismatch_scores_lower(self):
        """Templates with mismatched categories should score lower."""
        matcher = TemplateMatcher()
        intent = ReportIntent(
            raw_query="写一份分析报告",
            report_type="分析报告",
            category="分析类",
            period="",
            scope="公司",
            key_themes=["数据分析"],
        )

        matching = _make_template("t1", "数据分析报告", "分析类", parent_meta="meta_analysis",
                                  description="数据分析")
        non_matching = _make_template("t2", "业务周报", "进度类", parent_meta="meta_progress",
                                      description="周报")

        score_match = matcher._calculate_score(intent, matching)
        score_non = matcher._calculate_score(intent, non_matching)

        assert score_match > score_non, \
            f"Expected matching score ({score_match}) > non-matching ({score_non})"

    def test_explain_match(self):
        """_explain_match should return a descriptive string."""
        matcher = TemplateMatcher()
        intent = ReportIntent(
            raw_query="周报",
            report_type="周报",
            category="进度类",
            period="本周",
            scope="团队",
        )
        tmpl = _make_template("t1", "业务周报", "进度类", parent_meta="meta_progress")

        explanation = matcher._explain_match(intent, tmpl)
        assert "进度类" in explanation or "周报" in explanation
        assert len(explanation) > 0
