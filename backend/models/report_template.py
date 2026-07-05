"""企业报告模板数据模型 — 统一 PPT/Word/PDF 模板"""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import String, DateTime, Text, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex


class ReportTemplate(Base):
    """企业报告模板 — 支持 PPTX/DOCX/PDF 及企业自定义导入"""
    __tablename__ = "report_templates"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_id)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    report_type: Mapped[str] = mapped_column(String, nullable=False)
    # report_type: "ppt" | "docx" | "pdf"
    source: Mapped[str] = mapped_column(String, nullable=False, default="builtin")
    # source: "builtin" | "user_uploaded"

    original_filename: Mapped[str | None] = mapped_column(String, nullable=True)
    template_file_path: Mapped[str | None] = mapped_column(String, nullable=True)

    style_rules: Mapped[Any] = mapped_column(JSON, nullable=True)
    content_slots: Mapped[Any] = mapped_column(JSON, nullable=True)

    scenario_type: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_path: Mapped[str | None] = mapped_column(String, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
