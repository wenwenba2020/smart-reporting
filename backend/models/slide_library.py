"""企业幻灯片库数据模型"""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import String, Integer, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex


class SlideLibrary(Base):
    __tablename__ = "slide_libraries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_id)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    original_filename: Mapped[str] = mapped_column(String, nullable=False)
    slide_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    scenario_type: Mapped[str | None] = mapped_column(String, nullable=True)
    source_type: Mapped[str] = mapped_column(String, nullable=False, default="manual")
    is_excellent: Mapped[bool] = mapped_column(Boolean, default=False)
    tags: Mapped[Any] = mapped_column(JSON, default=list)

    slides: Mapped[list["LibrarySlide"]] = relationship(
        "LibrarySlide", back_populates="library", cascade="all, delete-orphan",
        order_by="LibrarySlide.slide_index"
    )


class LibrarySlide(Base):
    __tablename__ = "library_slides"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_id)
    library_id: Mapped[str] = mapped_column(String, ForeignKey("slide_libraries.id", ondelete="CASCADE"), nullable=False, index=True)
    slide_index: Mapped[int] = mapped_column(Integer, nullable=False)
    slide_number: Mapped[str | None] = mapped_column(String, nullable=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    text_summary: Mapped[str | None] = mapped_column(String, nullable=True)
    tags: Mapped[Any] = mapped_column(JSON, default=list)
    thumbnail_path: Mapped[str | None] = mapped_column(String, nullable=True)
    raw_slide_xml_path: Mapped[str | None] = mapped_column(String, nullable=True)
    layout_hint: Mapped[str | None] = mapped_column(String, nullable=True)
    business_tags: Mapped[Any] = mapped_column(JSON, default=list)
    design_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    design_images: Mapped[Any] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    library: Mapped[SlideLibrary] = relationship("SlideLibrary", back_populates="slides")
