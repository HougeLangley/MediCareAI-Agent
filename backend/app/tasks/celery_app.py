"""Celery application factory.

Configured entirely from environment — no hardcoded values.
"""

from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "medicareai_agent",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.health",
        "app.tasks.agent",
        "app.tasks.audit",
        "app.tasks.planning",
        "app.tasks.monitoring",
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
    # Long-ETA reminders (medication plans span weeks) must not be
    # redelivered by the broker while held in the worker's ETA heap.
    broker_transport_options={"visibility_timeout": 2592000},
    beat_schedule={
        "cleanup-audit-logs-daily": {
            "task": "app.tasks.audit.cleanup_old_audit_logs",
            "schedule": crontab(hour=3, minute=0),
            "kwargs": {},
        },
        # Fallback sweep: ETA tasks (send_reminder) fire at exact times;
        # this catches events missed by worker restarts or enqueue failures.
        "scan-pending-events": {
            "task": "app.tasks.monitoring.scan_pending_events",
            "schedule": crontab(minute="*/30"),
            "kwargs": {},
        },
    },
)
