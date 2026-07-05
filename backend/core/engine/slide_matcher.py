"""
Slide Matcher — match report sections against reusable slides from the case library.
"""
from backend.core.models import SectionDef, SlideAsset, SlideRef


class SlideMatcher:
    """Match report sections to reusable slides from the enterprise PPT case library."""

    def match(
        self,
        section: SectionDef,
        decks: list[SlideAsset],
        threshold: float = 0.7,
    ) -> list[SlideRef]:
        """Match a single section against all slides across all decks.

        Parameters
        ----------
        section : SectionDef
            The section to find matching slides for.
        decks : list[SlideAsset]
            Available slide assets from the case library.
        threshold : float
            Minimum similarity score (0.0-1.0) for a match to be included.

        Returns
        -------
        list[SlideRef]
            Matching slide references, sorted by score descending.
        """
        results = []
        for deck in decks:
            score = self._calculate_similarity(section, deck)
            if score >= threshold:
                results.append(SlideRef(
                    id=deck.id,
                    title=deck.title,
                    slide_index=deck.slide_index,
                    source_file=deck.file_path,
                    tags=deck.tags,
                    quality_score=score,
                    thumbnail_url=deck.thumbnail_path,
                ))
        results.sort(key=lambda x: x.quality_score, reverse=True)
        return results

    def _calculate_similarity(self, section: SectionDef, slide: SlideAsset) -> float:
        """Calculate a similarity score between a section and a slide asset.

        Scoring components:
        - Title overlap: up to 0.3 (Jaccard-like word overlap between titles)
        - Tag match: 0.15 per matching tag (capped at 0.45)
        - Word overlap: up to 0.25 (content description overlap)

        Parameters
        ----------
        section : SectionDef
            The section definition.
        slide : SlideAsset
            The slide asset to compare against.

        Returns
        -------
        float
            Similarity score between 0.0 and 1.0.
        """
        score = 0.0

        # Title overlap (0.3 max)
        title_overlap = self._word_overlap(section.title, slide.title)
        score += min(title_overlap, 1.0) * 0.3

        # Tag match (0.15 per tag)
        if section.match_keywords and slide.tags:
            matched_tags = set(kw.lower() for kw in section.match_keywords) & set(
                t.lower() for t in slide.tags
            )
            score += min(len(matched_tags) * 0.15, 0.45)

        # Word overlap between section description and slide description (0.25 max)
        desc_overlap = self._word_overlap(
            section.description, slide.description or slide.title
        )
        score += min(desc_overlap, 1.0) * 0.25

        return min(score, 1.0)

    def _word_overlap(self, text_a: str, text_b: str) -> float:
        """Calculate word-level overlap between two strings.

        Uses a Jaccard-like coefficient: intersection / union of token sets.
        For Chinese text (no spaces between words), uses character-level bigrams.
        For whitespace-separated text, splits by whitespace.

        Parameters
        ----------
        text_a : str
            First text.
        text_b : str
            Second text.

        Returns
        -------
        float
            Overlap ratio (0.0 to 1.0).
        """
        if not text_a or not text_b:
            return 0.0

        tokens_a = self._tokenize(text_a)
        tokens_b = self._tokenize(text_b)

        if not tokens_a or not tokens_b:
            return 0.0
        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b
        return len(intersection) / len(union)

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        """Tokenize text for overlap comparison.

        If the text contains mostly CJK characters (no whitespace word boundaries),
        uses character bigrams. Otherwise splits by whitespace.
        """
        text = text.lower().strip()
        if not text:
            return set()

        # Detect if text is predominantly CJK (no spaces between words)
        cjk_count = sum(1 for ch in text if '一' <= ch <= '鿿')
        if cjk_count > len(text) * 0.3:
            # Character bigram tokenization for Chinese
            bigrams = set()
            for i in range(len(text) - 1):
                bigram = text[i:i + 2]
                bigrams.add(bigram)
            # Also include single characters for single-char matches
            bigrams.update(set(text))
            return bigrams

        return set(text.split())

    def match_for_template(
        self,
        sections: list[SectionDef],
        decks: list[SlideAsset],
        threshold: float = 0.7,
    ) -> dict[str, list[SlideRef]]:
        """Match all enterprise_ppt sections in a template against slide decks.

        Only sections whose ``source`` is ``"enterprise_ppt"`` are processed.

        Parameters
        ----------
        sections : list[SectionDef]
            All sections from a template.
        decks : list[SlideAsset]
            Available slide assets.
        threshold : float
            Minimum similarity score.

        Returns
        -------
        dict[str, list[SlideRef]]
            Mapping from section key to list of matching slide references.
        """
        result = {}
        for section in sections:
            if section.source == "enterprise_ppt":
                matches = self.match(section, decks, threshold)
                if matches:
                    result[section.key] = matches
        return result
