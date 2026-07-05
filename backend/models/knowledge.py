"""企业知识库数据模型"""
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import String, Integer, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex


class KnowledgeBase(Base):
    """知识库分类（如：产品参数、客户资料、周会纪要）"""
    __tablename__ = "knowledge_bases"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_id)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    category: Mapped[str] = mapped_column(String, nullable=False, default="general")
    # category 枚举: product / customer / meeting / general
    entry_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    entries: Mapped[list["KnowledgeEntry"]] = relationship(
        "KnowledgeEntry", back_populates="kb", cascade="all, delete-orphan"
    )


class KnowledgeEntry(Base):
    """知识条目（文档分块或独立条目）"""
    __tablename__ = "knowledge_entries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_id)
    kb_id: Mapped[str] = mapped_column(String, ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True)
    source_name: Mapped[str | None] = mapped_column(String, nullable=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    embedding: Mapped[Any] = mapped_column(JSON, nullable=True)
    metadata_: Mapped[Any] = mapped_column("metadata_json", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    kb: Mapped["KnowledgeBase"] = relationship("KnowledgeBase", back_populates="entries")
