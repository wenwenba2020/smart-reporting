"""案例库数据源插件"""
from backend.data_source.base import DataSourcePlugin, SourceDocument, SourceSchema
from backend.models.database import async_session
from backend.models.slide_library import SlideLibrary, LibrarySlide
from sqlalchemy import select


class CaseLibrarySource(DataSourcePlugin):

    @property
    def source_type(self) -> str:
        return "case_library"

    @property
    def source_name(self) -> str:
        return "企业PPT案例库"

    async def search(self, query: str, top_k: int = 10, **filters) -> list[SourceDocument]:
        async with async_session() as db:
            q = select(LibrarySlide).join(SlideLibrary).where(
                SlideLibrary.user_id == filters.get("user_id", "")
            )
            if filters.get("scenario_type"):
                q = q.where(SlideLibrary.scenario_type == filters["scenario_type"])
            if filters.get("is_excellent"):
                q = q.where(SlideLibrary.is_excellent == True)

            result = await db.execute(q)
            slides = list(result.scalars().all())

        query_lower = query.lower()
        scored = []
        for s in slides:
            text = f"{s.title or ''} {s.text_summary or ''} {' '.join(s.tags or [])}"
            score = 1.0 if query_lower in text.lower() else 0.3
            scored.append((score, s))
        scored.sort(key=lambda x: x[0], reverse=True)

        return [
            SourceDocument(
                source_id=s.id, source_type=self.source_type,
                source_name=self.source_name,
                title=s.title or f"Slide {s.slide_index}",
                content=(s.text_summary or "")[:600],
                metadata={
                    "tags": s.tags or [], "business_tags": s.business_tags or [],
                    "layout_hint": s.layout_hint, "slide_index": s.slide_index,
                    "library_id": s.library_id,
                },
                relevance_score=round(score, 3),
            )
            for score, s in scored[:top_k]
        ]

    async def get_schema(self, **filters) -> SourceSchema:
        async with async_session() as db:
            result = await db.execute(
                select(SlideLibrary).where(SlideLibrary.user_id == filters.get("user_id", ""))
            )
            decks = list(result.scalars().all())

        total = sum(d.slide_count or 0 for d in decks)
        scenario_types = list({d.scenario_type for d in decks if d.scenario_type})
        return SourceSchema(
            source_type=self.source_type, source_name=self.source_name,
            categories=scenario_types,
            fields=["title", "text_summary", "tags", "business_tags", "layout_hint"],
            total_documents=total,
        )
