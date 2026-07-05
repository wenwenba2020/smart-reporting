"""Celery application initialization."""
from celery import Celery

from backend.config import settings

celery_app = Celery(
    "ppt_agent",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
)

# Explicitly import task modules so they register with the app
import backend.tasks.generate  # noqa: F401, E402
import backend.tasks.revise  # noqa: F401, E402
