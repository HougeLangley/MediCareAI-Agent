"""Audit log maintenance tasks."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete

from app.db.session import AsyncSessionLocal
from app.models.audit import AuditLog
from app.models.config import SystemSetting
from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def cleanup_old_audit_logs(self) -> dict[str, int]:
    """Delete audit logs older than the configured retention period.

    Default retention: 30 days. Configurable via
    ``audit_log_retention_days`` system setting.

    This task is scheduled to run daily at 03:00 via Celery Beat.
    """
    import asyncio

    async def _cleanup() -> tuple[int, int]:
        async with AsyncSessionLocal() as db:
            # Read retention setting (default 30 days)
            result = await db.execute(
                SystemSetting.__table__.select().where(
                    SystemSetting.key == "audit_log_retention_days"
                )
            )
            row = result.fetchone()
            retention_days = 30
            if row:
                try:
                    retention_days = int(row.value)
                except (ValueError, TypeError):
                    retention_days = 30

            cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

            stmt = (
                delete(AuditLog)
                .where(AuditLog.created_at < cutoff)
                .execution_options(synchronize_session=False)
            )
            result = await db.execute(stmt)
            await db.commit()
            return result.rowcount, retention_days

    try:
        deleted, retention_days = asyncio.run(_cleanup())
        return {"deleted": deleted, "retention_days": retention_days}
    except Exception as exc:
        raise self.retry(exc=exc)
