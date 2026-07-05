"""
Source Summarizer — consolidate multiple source documents into a unified summary.
"""
from backend.core.models import SourceDocument
from backend.core.llm.client import get_llm_client
from backend.core.llm.prompts import SUMMARIZE_PROMPT


class SourceSummarizer:
    """Summarize one or more source documents into a coherent text."""

    def __init__(self):
        self.llm = get_llm_client()

    async def summarize(self, source_docs: list[SourceDocument]) -> str:
        """Summarize source documents.

        If there is only one source, return its content directly.
        For multiple sources, call the LLM with SUMMARIZE_PROMPT.
        Falls back to raw concatenation on error.

        Parameters
        ----------
        source_docs : list[SourceDocument]
            Source documents to summarize.

        Returns
        -------
        str
            Summarized content.
        """
        if not source_docs:
            return ""

        if len(source_docs) == 1:
            return source_docs[0].content

        # Multiple sources — use LLM summarization
        source_contents = "\n\n---\n\n".join(
            f"### [{d.source_type}] {d.title}\n{d.content}" for d in source_docs
        )
        try:
            prompt = SUMMARIZE_PROMPT.format(source_contents=source_contents)
            result = await self.llm.chat(
                system_prompt="Summarize multiple data sources into a structured summary.",
                user_message=prompt,
                max_tokens=4096,
            )
            return result
        except Exception:
            # Fallback: raw concatenation
            parts = []
            for d in source_docs:
                parts.append(f"## {d.title}\n\n{d.content}")
            return "\n\n---\n\n".join(parts)
