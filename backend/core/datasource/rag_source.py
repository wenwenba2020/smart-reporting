"""RAG knowledge base data source — semantic search over ingested documents."""
import uuid
import logging
from pathlib import Path
from typing import Optional
from backend.core.datasource.base import DataSourceAdapter, register_adapter
from backend.core.models import SourceDocument

logger = logging.getLogger(__name__)

# Lazy imports — chromadb and sentence_transformers are heavy
_chroma_client = None
_embedding_model = None
_collection = None

CHROMA_DIR = Path("./data/chroma")
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


def _get_collection():
    global _chroma_client, _embedding_model, _collection
    if _collection is not None:
        return _collection

    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR), settings=ChromaSettings(anonymized_telemetry=False))
        _collection = _chroma_client.get_or_create_collection(name="knowledge_base")
        return _collection
    except ImportError:
        logger.warning("chromadb not installed — RAG features disabled")
        return None
    except Exception as e:
        logger.error(f"Failed to init ChromaDB: {e}")
        return None


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model

    try:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer(MODEL_NAME)
        return _embedding_model
    except ImportError:
        logger.warning("sentence-transformers not installed — RAG features disabled")
        return None
    except Exception as e:
        logger.error(f"Failed to load embedding model: {e}")
        return None


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


@register_adapter
class RAGKnowledgeBase(DataSourceAdapter):
    """Semantic search over ingested documents using ChromaDB + sentence-transformers."""

    source_type = "knowledge_base"

    def supports(self, filename: str) -> bool:
        return False

    async def parse(self, file_path: str, filename: str, metadata: Optional[dict] = None) -> SourceDocument:
        raise NotImplementedError("Use ingest() and search() for RAG knowledge base")

    async def fetch(self, config) -> SourceDocument:
        """Not used directly — use ingest() and search() instead."""
        raise NotImplementedError("Use ingest() and search() for RAG knowledge base")

    async def ingest(self, source_ids: list[str], source_store: dict) -> dict:
        """Ingest documents from source_store into the vector database.

        Args:
            source_ids: List of source document IDs to ingest
            source_store: Dict mapping source_id → SourceDocument

        Returns:
            {"status": "indexed", "chunks": N, "documents": M}
        """
        model = _get_embedding_model()
        collection = _get_collection()

        if model is None or collection is None:
            return {"status": "failed", "error": "RAG dependencies not available (chromadb + sentence-transformers required)"}

        total_chunks = 0
        ingested_count = 0

        for source_id in source_ids:
            doc = source_store.get(source_id)
            if doc is None:
                continue

            chunks = _chunk_text(doc.content)
            if not chunks:
                continue

            embeddings = model.encode(chunks, show_progress_bar=False).tolist()
            metadatas = [{"source_id": source_id, "title": doc.title, "source_type": doc.source_type, "chunk_index": i} for i in range(len(chunks))]
            ids = [f"{source_id}_chunk_{i}" for i in range(len(chunks))]

            # Remove existing chunks for this source before re-ingesting
            try:
                existing = collection.get(where={"source_id": source_id})
                if existing and existing.get("ids"):
                    collection.delete(ids=existing["ids"])
            except Exception:
                pass

            collection.add(embeddings=embeddings, documents=chunks, metadatas=metadatas, ids=ids)
            total_chunks += len(chunks)
            ingested_count += 1

        return {"status": "indexed", "chunks": total_chunks, "documents": ingested_count}

    async def search(self, query: str, top_k: int = 5, source_store: dict = None) -> SourceDocument:
        """Semantic search the knowledge base.

        Args:
            query: Natural language search query
            top_k: Number of chunks to retrieve
            source_store: Optional dict mapping source_id → SourceDocument (for metadata enrichment)

        Returns:
            SourceDocument with concatenated relevant chunks
        """
        model = _get_embedding_model()
        collection = _get_collection()

        if model is None or collection is None:
            return SourceDocument(
                id=str(uuid.uuid4()),
                title=f"RAG Search: {query[:50]}",
                content="[RAG 知识库未就绪]\n\n请安装 chromadb 和 sentence-transformers 后重试。",
                source_type=self.source_type,
                metadata={"query": query, "status": "not_configured"},
            )

        try:
            query_embedding = model.encode([query], show_progress_bar=False).tolist()
            results = collection.query(query_embeddings=query_embedding, n_results=min(top_k, 50))

            chunks = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]

            if not chunks:
                return SourceDocument(
                    id=str(uuid.uuid4()),
                    title=f"RAG Search: {query[:50]}",
                    content=f"[未找到相关结果]\n\n查询: {query}",
                    source_type=self.source_type,
                    metadata={"query": query, "results": 0},
                )

            # Build result content with source attribution
            lines = [f"## RAG 检索结果", f"**查询**: {query}", f"**匹配片段**: {len(chunks)}\n"]
            for i, (chunk, meta, dist) in enumerate(zip(chunks, metadatas, distances)):
                similarity = max(0, 1 - dist) if dist else 1.0
                src_title = meta.get("title", "unknown") if meta else "unknown"
                lines.append(f"### 片段 {i+1} [来源: {src_title}] [相似度: {similarity:.2f}]")
                lines.append(chunk)
                lines.append("")

            return SourceDocument(
                id=str(uuid.uuid4()),
                title=f"RAG Search: {query[:50]}",
                content="\n".join(lines),
                source_type=self.source_type,
                metadata={"query": query, "results": len(chunks), "top_k": top_k},
            )

        except Exception as e:
            logger.error(f"RAG search failed: {e}")
            return SourceDocument(
                id=str(uuid.uuid4()),
                title=f"RAG Error: {query[:50]}",
                content=f"[RAG 检索失败]\n\n错误: {str(e)}",
                source_type=self.source_type,
                metadata={"query": query, "error": str(e)},
            )


# Module-level singleton
rag_kb = RAGKnowledgeBase()
