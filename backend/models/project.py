import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_id)
    name: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[str] = mapped_column(String, nullable=False, default="admin")
    status: Mapped[str] = mapped_column(String, nullable=False, default="draft")
    template_id: Mapped[str | None] = mapped_column(String, nullable=True)
    total_slides: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    stage: Mapped[str] = mapped_column(String, nullable=False, default="idle")
    outline_path: Mapped[str | None] = mapped_column(String, nullable=True)
    export_path: Mapped[str | None] = mapped_column(String, nullable=True)
    snapshot_count: Mapped[int] = mapped_column(Integer, default=0)
