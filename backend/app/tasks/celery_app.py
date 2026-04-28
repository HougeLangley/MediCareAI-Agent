"""Celery application factory.

Configured entirely from environment — no hardcoded values.
"""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "medicareai_agent",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.health",
        "app.tasks.agent",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    worker_prefetch_multiplier=1,
    task_always_eager=settings.celery_task_always_eager,
)
