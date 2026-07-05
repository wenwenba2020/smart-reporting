"""
Tests for slide matcher (Task 11).
"""
import pytest

from backend.core.models import SectionDef, SlideAsset, SlideRef
from backend.core.engine.slide_matcher import SlideMatcher


def _make_slide(slide_id, title, tags=None, description="", file_path="", slide_index=0):
    """Helper to create a SlideAsset for testing."""
    return SlideAsset(
        id=slide_id,
        title=title,
        tags=tags or [],
        description=description,
        file_path=file_path or f"/data/{slide_id}.pptx",
        slide_index=slide_index,
    )


def _make_section(key="s1", title="测试章节", match_keywords=None, description="", source="enterprise_ppt"):
    """Helper to create a SectionDef for testing."""
    return SectionDef(
        key=key,
        title=title,
        description=description,
        source=source,
        match_keywords=match_keywords or [],
    )


class TestSlideMatcher:
    """Tests for SlideMatcher — non-LLM similarity scoring."""

    def test_exact_title_match(self):
        """Exact title match should produce a high score."""
        matcher = SlideMatcher()
        section = _make_section(key="s1", title="业务周报概览")
        slide = _make_slide(slide_id="slide1", title="业务周报概览")

        score = matcher._calculate_similarity(section, slide)
        assert score >= 0.25, f"Expected score >= 0.25 for exact title match, got {score}"

    def test_exact_title_match_finds_slide(self):
        """An exact title match should find the slide in the deck."""
        matcher = SlideMatcher()
        section = _make_section(key="s1", title="业务周报概览")
        slides = [
            _make_slide(slide_id="s1", title="业务周报概览"),
            _make_slide(slide_id="s2", title="其他内容"),
        ]

        results = matcher.match(section, slides, threshold=0.2)
        assert len(results) >= 1, f"Expected at least 1 match, got {len(results)}"
        assert results[0].id == "s1"

    def test_no_match_with_high_threshold(self):
        """With a high threshold, weak matches should be filtered out."""
        matcher = SlideMatcher()
        section = _make_section(key="s1", title="财务分析")
        slides = [
            _make_slide(slide_id="s1", title="业务周报"),
            _make_slide(slide_id="s2", title="项目进展"),
        ]

        results = matcher.match(section, slides, threshold=0.9)
        assert len(results) == 0, \
            f"Expected no matches with threshold=0.9, got {len(results)}"

    def test_tag_match_increases_score(self):
        """Matching tags should increase the similarity score."""
        matcher = SlideMatcher()
        section = _make_section(
            key="s1", title="财务分析",
            match_keywords=["财务", "分析", "KPI"],
        )
        slide_with_tags = _make_slide(
            slide_id="s1", title="分析页面", tags=["财务", "KPI", "Q3"],
        )
        slide_without_tags = _make_slide(
            slide_id="s2", title="分析页面", tags=["其他"],
        )

        score_with = matcher._calculate_similarity(section, slide_with_tags)
        score_without = matcher._calculate_similarity(section, slide_without_tags)

        assert score_with > score_without, \
            f"Tagged slide ({score_with}) should score higher than untagged ({score_without})"

    def test_word_overlap(self):
        """Word overlap between descriptions should contribute to score."""
        matcher = SlideMatcher()
        section = _make_section(
            key="s1", title="销售业绩", description="销售数据分析和业绩评估"
        )
        slide = _make_slide(
            slide_id="s1", title="业绩报告", description="销售数据分析与评估报告"
        )

        overlap = matcher._word_overlap(section.description, slide.description)
        assert overlap > 0.0, f"Expected word overlap > 0, got {overlap}"

    def test_word_overlap_empty_strings(self):
        """Word overlap with empty strings should return 0."""
        matcher = SlideMatcher()
        assert matcher._word_overlap("", "") == 0.0
        assert matcher._word_overlap("text", "") == 0.0
        assert matcher._word_overlap("", "text") == 0.0

    def test_match_for_template_only_enterprise_ppt(self):
        """match_for_template should only process enterprise_ppt sections."""
        matcher = SlideMatcher()
        sections = [
            _make_section(key="s1", title="企宣章节", source="enterprise_ppt",
                         match_keywords=["公司"]),
            _make_section(key="s2", title="普通章节", source="generated"),
            _make_section(key="s3", title="另一个企宣", source="enterprise_ppt",
                         match_keywords=["产品"]),
        ]
        slides = [
            _make_slide(slide_id="s1", title="公司介绍", tags=["公司"]),
            _make_slide(slide_id="s2", title="产品介绍", tags=["产品"]),
        ]

        result = matcher.match_for_template(sections, slides, threshold=0.1)

        # Only s1 and s3 should be processed (enterprise_ppt source)
        assert "s1" in result
        assert "s3" in result
        assert "s2" not in result, "Generated sections should not be matched"

    def test_score_bounded(self):
        """Similarity score should always be between 0 and 1."""
        matcher = SlideMatcher()
        section = _make_section(key="s1", title="A", match_keywords=["a", "b", "c", "d", "e"])
        slide = _make_slide(slide_id="s1", title="A", tags=["a", "b", "c", "d", "e"])

        score = matcher._calculate_similarity(section, slide)
        assert 0.0 <= score <= 1.0, f"Score {score} out of [0.0, 1.0] range"
