"""SSE 事件总线 — Redis pub/sub 发布/订阅智能体状态事件"""
import asyncio
import json
from typing import AsyncGenerator

import redis
import redis.asyncio as aioredis

from backend.config import settings

# Singleton sync Redis client (connection pooled)
_sync_pool: redis.ConnectionPool | None = None
_async_client: aioredis.Redis | None = None

SSE_KEEPALIVE_SECONDS = 15


def _get_sync_redis() -> redis.Redis:
    """Return a pooled sync Redis client."""
    global _sync_pool
    if _sync_pool is None:
        _sync_pool = redis.ConnectionPool.from_url(settings.REDIS_URL)
    return redis.Redis(connection_pool=_sync_pool)


def _get_async_redis() -> aioredis.Redis:
    """Return an async Redis client."""
    global _async_client
    if _async_client is None:
        _async_client = aioredis.Redis.from_url(settings.REDIS_URL)
    return _async_client


def _channel(project_id: str) -> str:
    return f"project:{project_id}:events"


# ---------- Publish (sync, for Celery workers) ----------

def publish_event(project_id: str, event: dict) -> None:
    """Publish an SSE event from a sync context (Celery worker / agent node)."""
    r = _get_sync_redis()
    r.publish(_channel(project_id), json.dumps(event, ensure_ascii=False))


def publish_agent_start(project_id: str, agent: str, message: str = "") -> None:
    publish_event(project_id, {"type": "agent_start", "agent": agent, "message": message})


def publish_agent_progress(project_id: str, agent: str, progress: float, detail: str = "") -> None:
    publish_event(project_id, {"type": "agent_progress", "agent": agent, "progress": progress, "detail": detail})


def publish_agent_complete(project_id: str, agent: str, output_ref: str = "") -> None:
    publish_event(project_id, {"type": "agent_complete", "agent": agent, "output_ref": output_ref})


def publish_slide_status(project_id: str, slide_id: str, status: str) -> None:
    publish_event(project_id, {"type": "slide_status_change", "slide_id": slide_id, "status": status})


def publish_error(project_id: str, agent: str, message: str, recoverable: bool = False) -> None:
    publish_event(project_id, {"type": "error", "agent": agent, "message": message, "recoverable": recoverable})


def publish_content_ready(project_id: str) -> None:
    publish_event(project_id, {"type": "content_ready"})


def publish_stage_change(project_id: str, stage: str) -> None:
    publish_event(project_id, {"type": "stage_change", "stage": stage})


def publish_slide_content_changed(project_id: str, slide_id: str) -> None:
    publish_event(project_id, {"type": "slide_content_changed", "slide_id": slide_id})


# ---------- Diagnosis-specific publishers ----------

def publish_diagnosis_start(project_id: str) -> None:
    publish_event(project_id, {"type": "diagnosis_start"})


def publish_diagnosis_report(project_id: str, report: dict) -> None:
    publish_event(project_id, {"type": "diagnosis_report", "report": report})


def publish_diagnosis_fix_progress(project_id: str, slide_id: str, status: str, detail: str = "") -> None:
    publish_event(project_id, {
        "type": "diagnosis_fix_progress",
        "slide_id": slide_id,
        "status": status,
        "detail": detail,
    })


def publish_diagnosis_complete(project_id: str, summary: dict) -> None:
    publish_event(project_id, {"type": "diagnosis_complete", "summary": summary})


# ---------- Subscribe (async, for SSE endpoint) ----------

async def subscribe_events(project_id: str) -> AsyncGenerator[str, None]:
    """Async generator that yields SSE-formatted events with keepalive heartbeat."""
    r = _get_async_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe(_channel(project_id))

    try:
        while True:
            try:
                message = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0),
                    timeout=SSE_KEEPALIVE_SECONDS,
                )
            except asyncio.TimeoutError:
                # Send keepalive comment to prevent proxy/client timeout
                yield ": keepalive\n\n"
                continue

            if message is not None and message["type"] == "message":
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                yield f"data: {data}\n\n"
    finally:
        await pubsub.unsubscribe(_channel(project_id))
