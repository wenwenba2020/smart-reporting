"""
Intent Recognition — parse user query into structured ReportIntent.
"""
from backend.core.models import ReportIntent
from backend.core.llm.client import get_llm_client
from backend.core.llm.prompts import INTENT_RECOGNITION_V2_PROMPT


class IntentRecognizer:
    """Recognize user intent for report generation from natural language query."""

    def __init__(self):
        self.llm = get_llm_client()

    async def recognize(self, user_query: str, source_docs: list) -> ReportIntent:
        """Analyze user query and available source documents to produce a ReportIntent.

        Parameters
        ----------
        user_query : str
            The user's natural language query describing desired report.
        source_docs : list[SourceDocument]
            Available data source documents.

        Returns
        -------
        ReportIntent
            Structured intent with report type, category, period, scope, and key themes.
        """
        data_summary = "\n".join(
            f"- [{d.source_type}] {d.title}: {d.content[:200]}..." for d in source_docs
        ) or "无数据源"
        prompt = INTENT_RECOGNITION_V2_PROMPT.format(
            user_query=user_query, data_summary=data_summary
        )
        result = await self.llm.chat_json(
            system_prompt="Recognize report intent.",
            user_message=prompt,
        )
        return ReportIntent(
            raw_query=user_query,
            report_type=result.get("report_type", ""),
            category=result.get("category", ""),
            period=result.get("period", ""),
            scope=result.get("scope", ""),
            key_themes=result.get("key_themes", []),
        )
