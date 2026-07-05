"""知识库文档摄取：解析 + 分块 + embedding"""
import re
from pathlib import Path

import numpy as np


CHUNK_SIZE = 800
CHUNK_OVERLAP = 100


def parse_file_to_text(file_path: str | Path) -> tuple[str, dict]:
    """将支持的文件类型解析为纯文本。

    Returns (text, metadata_dict).
    """
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()
    metadata = {"source_type": suffix.lstrip("."), "filename": file_path.name}

    if suffix == ".pdf":
        import fitz
        doc = fitz.open(str(file_path))
        texts: list[str] = []
        for page in doc:
            texts.append(page.get_text())
        doc.close()
        return "\n\n".join(texts), {**metadata, "pages": len(texts)}

    elif suffix == ".docx":
        from docx import Document
        doc = Document(str(file_path))
        paras = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paras), metadata

    elif suffix in (".txt", ".md"):
        text = file_path.read_text(encoding="utf-8")
        return text, metadata

    elif suffix == ".csv":
        text = file_path.read_text(encoding="utf-8")
        return text, {**metadata, "format": "csv"}

    else:
        raise ValueError(f"Unsupported file type: {suffix}")


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """将长文本切分为重叠块。按段落边界优先切分。"""
    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current_chunk) + len(para) + 2 <= chunk_size:
            current_chunk = (current_chunk + "\n\n" + para).strip()
        else:
            if current_chunk:
                chunks.append(current_chunk)
            if len(para) > chunk_size:
                sentences = re.split(r"(?<=[。！？.!?])\s*", para)
                current_chunk = ""
                for sent in sentences:
                    if len(current_chunk) + len(sent) <= chunk_size:
                        current_chunk = (current_chunk + sent).strip()
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = sent
            else:
                current_chunk = para
                if chunks and overlap > 0:
                    prev = chunks[-1]
                    overlap_text = prev[-overlap:] if len(prev) > overlap else prev
                    current_chunk = overlap_text + "\n\n" + current_chunk

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def compute_embedding(text: str) -> list[float]:
    """通过 OpenRouter text-embedding-3-small 计算 embedding 向量。"""
    from backend.agents.llm_client import get_client

    client = get_client()
    text = text[:8000]
    resp = client.embeddings.create(
        model="openai/text-embedding-3-small",
        input=[text],
        timeout=30,
    )
    return resp.data[0].embedding


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """余弦相似度。"""
    a_np = np.array(a)
    b_np = np.array(b)
    return float(np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np) + 1e-10))


def ingest_file(
    file_path: str | Path,
    kb_id: str,
    source_name: str,
) -> list[dict]:
    """解析文件、分块、计算 embedding，返回 entry 数据列表。"""
    file_path = Path(file_path)
    text, file_meta = parse_file_to_text(file_path)
    chunks = chunk_text(text)
    if not chunks:
        return []

    entries: list[dict] = []
    for i, chunk in enumerate(chunks):
        short_title = chunk[:80].replace("\n", " ").strip()
        if len(short_title) < len(chunk):
            short_title += "..."

        try:
            emb = compute_embedding(chunk)
        except Exception:
            emb = None

        entries.append({
            "kb_id": kb_id,
            "source_name": source_name,
            "title": short_title,
            "content": chunk,
            "chunk_index": i,
            "embedding": emb,
            "metadata_": {
                **file_meta,
                "chunk_index": i,
                "total_chunks": len(chunks),
            },
        })

    return entries
