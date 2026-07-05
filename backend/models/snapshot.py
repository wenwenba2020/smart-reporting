import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex


class ProjectSnapshot(Base):
    __tablename__ = "project_snapshots"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_id)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"), nullable=False)
    version: Mapped[str] = mapped_column(String, nullable=False)
    trigger: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    snapshot_path: Mapped[str] = mapped_column(String, nullable=False)
