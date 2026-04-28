"""Health check and maintenance tasks."""

from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, max_retries=3)
def ping(self) -> str:
    """Simple liveness check task."""
    return "pong"
