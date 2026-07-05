"""知识库数据源插件"""
from backend.data_source.base import DataSourcePlugin, SourceDocument, SourceSchema
from backend.models.database import async_session
from backend.models.knowledge import KnowledgeEntry, KnowledgeBase
from backend.parsers.knowledge_ingest import compute_embedding, cosine_similarity
from sqlalchemy import select


class KnowledgeBaseSource(DataSourcePlugin):

    @property
    def source_type(self) -> str:
        return "knowledge_base"

    @property
    def source_name(self) -> str:
        return "企业知识库"

    async def search(self, query: str, top_k: int = 10, **filters) -> list[SourceDocument]:
        async with async_session() as db:
            q = select(KnowledgeEntry).join(KnowledgeBase).where(
                KnowledgeBase.user_id == filters.get("user_id", "")
            )
            if filters.get("category"):
                q = q.where(KnowledgeBase.category == filters["category"])
            if filters.get("kb_id"):
                q = q.where(KnowledgeEntry.kb_id == filters["kb_id"])

            result = await db.execute(q)
            entries = list(result.scalars().all())

        if not entries:
            return []

        try:
            query_emb = compute_embedding(query)
            scored = [
                (cosine_similarity(query_emb, e.embedding), e)
                for e in entries if e.embedding
            ]
            scored.sort(key=lambda x: x[0], reverse=True)
        except Exception:
            return [
                SourceDocument(
                    source_id=e.id, source_type=self.source_type,
                    source_name=self.source_name, title=e.title,
                    content=e.content[:600], metadata=e.metadata_ or {},
                )
                for e in entries[:top_k]
            ]

        return [
            SourceDocument(
                source_id=e.id, source_type=self.source_type,
                source_name=self.source_name, title=e.title,
                content=e.content[:600], metadata=e.metadata_ or {},
                relevance_score=round(s, 3),
            )
            for s, e in scored[:top_k] if s > 0.2
        ]

    async def get_schema(self, **filters) -> SourceSchema:
        async with async_session() as db:
            result = await db.execute(
                select(KnowledgeBase).where(KnowledgeBase.user_id == filters.get("user_id", ""))
            )
            kbs = list(result.scalars().all())

        categories = list({kb.category for kb in kbs})
        total = sum(kb.entry_count or 0 for kb in kbs)
        return SourceSchema(
            source_type=self.source_type, source_name=self.source_name,
            categories=categories, fields=["title", "content", "source_name", "category"],
            total_documents=total,
        )
