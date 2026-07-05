"""
Template Matcher — score and rank templates against a parsed ReportIntent.
"""
from backend.core.models import ReportIntent, ReportTemplate, TemplateRecommendation
from backend.core.templates import template_store


class TemplateMatcher:
    """Match a user's ReportIntent to the best-fitting report templates."""

    def match(self, intent: ReportIntent, top_k: int = 5) -> list[TemplateRecommendation]:
        """Score all available templates and return top-k recommendations.

        Parameters
        ----------
        intent : ReportIntent
            The recognized user intent.
        top_k : int
            Maximum number of recommendations to return.

        Returns
        -------
        list[TemplateRecommendation]
            Ranked list of template matches (highest score first).
        """
        results = []
        for tmpl in template_store.list_all():
            score = self._calculate_score(intent, tmpl)
            if score > 0.3:
                results.append(TemplateRecommendation(
                    template_id=tmpl.template_id,
                    name=tmpl.name,
                    match_score=round(score, 2),
                    match_reason=self._explain_match(intent, tmpl),
                    template=tmpl,
                ))
        results.sort(key=lambda x: x.match_score, reverse=True)
        if results:
            results[0].is_selected = True
        return results[:top_k]

    def _calculate_score(self, intent: ReportIntent, tmpl: ReportTemplate) -> float:
        """Calculate a match score between an intent and a template.

        Scoring rules:
        - +0.5 if categories match exactly
        - +0.3 if template has a parent_meta and intent category appears in description
        - +0.1 for each keyword from report_type + scope found in template name or description
        - -0.1 if template has no parent_meta (not derived from a meta template)
        """
        score = 0.0
        if intent.category == tmpl.category:
            score += 0.5
        elif tmpl.parent_meta and intent.category in tmpl.description:
            score += 0.3
        keywords = intent.report_type + intent.scope
        for kw in keywords:
            if kw in tmpl.name or kw in tmpl.description:
                score += 0.1
        if tmpl.parent_meta is None:
            score -= 0.1
        return min(score, 1.0)

    def _explain_match(self, intent: ReportIntent, tmpl: ReportTemplate) -> str:
        """Generate a human-readable explanation for the match."""
        if tmpl.category == intent.category:
            return f"匹配{intent.category}场景"
        return f"可适配{intent.report_type}场景"
