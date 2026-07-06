"""Tests for RAG knowledge base adapter."""
import pytest
from backend.core.datasource.rag_source import RAGKnowledgeBase, _chunk_text


def test_chunk_text_short():
    """Short text returns as single chunk."""
    text = "Hello world"
    chunks = _chunk_text(text, chunk_size=100)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_text_long():
    """Long text is split into overlapping chunks."""
    text = "A" * 450  # just under chunk size
    chunks = _chunk_text(text, chunk_size=200, overlap=50)
    assert len(chunks) >= 2
    # Each chunk should be at most chunk_size
    for chunk in chunks:
        assert len(chunk) <= 200


def test_chunk_text_exact():
    """Exact chunk size text."""
    text = "B" * 500
    chunks = _chunk_text(text, chunk_size=500)
    assert len(chunks) == 1


@pytest.mark.asyncio
async def test_rag_source_supports():
    adapter = RAGKnowledgeBase()
    assert adapter.supports("anything") is False


@pytest.mark.asyncio
async def test_rag_search_without_deps():
    """RAG search should return graceful error when deps not installed."""
    adapter = RAGKnowledgeBase()
    doc = await adapter.search("test query", top_k=3)
    assert doc.source_type == "knowledge_base"
    # Either returns results (if deps installed) or graceful error message
    assert len(doc.content) > 0
