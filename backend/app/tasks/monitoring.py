"""Monitoring Celery tasks.

Phase 2d: Heartbeat-based scheduled reminder scanning.
ETA upgrade: precise per-event scheduling (send_reminder) with the
periodic sweep kept as a fallback safety net.

Delivery guarantees:
- Atomic claim (UPDATE ... WHERE status='pending') makes duplicate
  deliveries (Redis visibility-timeout redelivery, ETA+sweep races)
  harmless no-ops.
- 'in_flight' rows older than IN_FLIGHT_STALE_MINUTES are reclaimed
  by the sweeper, so a crashed worker never loses a reminder.
"""
import logging
from datetime import datetime, timedelta, timezone

from celery import shared_task
from sqlalchemy import select, update

from app.db.session import async_session_maker
from app.services.email_service import email_service

_log = logging.getLogger("heartbeat")

# How long an 'in_flight' event may stay unclaimed before the sweeper
# resets it to 'pending' (covers worker crashes between claim and send).
IN_FLIGHT_STALE_MINUTES = 10

# event_type -> default email template name (see DEFAULT_REMINDER_TEMPLATES)
_TEMPLATE_NAME_MAP = {
    "medication_reminder": "medication_reminder",
    "follow_up_reminder": "follow_up_reminder",
    "health_alert": "health_alert",
}

# Default reminder templates, created idempotently at startup.
# Editable from the admin email management page afterwards.
DEFAULT_REMINDER_TEMPLATES = [
    {
        "name": "medication_reminder",
        "description": "用药提醒（Heartbeat 自动发送）",
        "subject": "【MediCareAI】用药提醒",
        "html_body": (
            '<!DOCTYPE html>\n<html><body style="font-family:Arial,sans-serif;">\n'
            '<div style="max-width:500px;margin:0 auto;padding:20px;border:1px solid #eee;border-radius:8px;">\n'
            '<h2 style="color:#E8956A;">💊 用药提醒</h2>\n'
            '<p style="font-size:16px;">{{description}}</p>\n'
            '<p style="color:#999;font-size:12px;">预定时间：{{scheduled_time}}</p>\n'
            '<p style="color:#999;font-size:12px;">自动化提醒 · 如有疑问请联系平台管理员</p>\n'
            '</div></body></html>'
        ),
        "text_body": "【MediCareAI】用药提醒\n{{description}}\n预定时间：{{scheduled_time}}",
        "variables": "description,scheduled_time",
    },
    {
        "name": "follow_up_reminder",
        "description": "复查/随访提醒（Heartbeat 自动发送）",
        "subject": "【MediCareAI】复查提醒",
        "html_body": (
            '<!DOCTYPE html>\n<html><body style="font-family:Arial,sans-serif;">\n'
            '<div style="max-width:500px;margin:0 auto;padding:20px;border:1px solid #eee;border-radius:8px;">\n'
            '<h2 style="color:#E8956A;">📋 复查提醒</h2>\n'
            '<p style="font-size:16px;">{{description}}</p>\n'
            '<p style="color:#999;font-size:12px;">预定时间：{{scheduled_time}}</p>\n'
            '<p style="color:#999;font-size:12px;">自动化提醒 · 如有疑问请联系平台管理员</p>\n'
            '</div></body></html>'
        ),
        "text_body": "【MediCareAI】复查提醒\n{{description}}\n预定时间：{{scheduled_time}}",
        "variables": "description,scheduled_time",
    },
    {
        "name": "health_alert",
        "description": "健康异常告警（Heartbeat 自动发送）",
        "subject": "【MediCareAI】健康告警",
        "html_body": (
            '<!DOCTYPE html>\n<html><body style="font-family:Arial,sans-serif;">\n'
            '<div style="max-width:500px;margin:0 auto;padding:20px;border:1px solid #eee;border-radius:8px;">\n'
            '<h2 style="color:#C0504D;">⚠️ 健康告警</h2>\n'
            '<p style="font-size:16px;">{{description}}</p>\n'
            '<p style="color:#999;font-size:12px;">检测时间：{{scheduled_time}}</p>\n'
            '<p style="color:#999;font-size:12px;">自动化提醒 · 如有疑问请联系平台管理员</p>\n'
            '</div></body></html>'
        ),
        "text_body": "【MediCareAI】健康告警\n{{description}}\n检测时间：{{scheduled_time}}",
        "variables": "description,scheduled_time",
    },
]


async def ensure_default_templates() -> None:
    """Idempotently create the default reminder email templates.

    Runs at backend startup (and lazily inside the sweeper) so templates
    are provisioned through the normal Git deploy flow — never by direct
    production DB edits.
    """
    from app.models.email import EmailTemplate

    async with async_session_maker() as db:
        created = 0
        for tpl in DEFAULT_REMINDER_TEMPLATES:
            result = await db.execute(
                select(EmailTemplate).where(EmailTemplate.name == tpl["name"])
            )
            if result.scalar_one_or_none():
                continue
            db.add(
                EmailTemplate(
                    name=tpl["name"],
                    description=tpl["description"],
                    subject=tpl["subject"],
                    html_body=tpl["html_body"],
                    text_body=tpl["text_body"],
                    variables=tpl["variables"],
                    is_active=True,
                )
            )
            created += 1
        if created:
            await db.commit()
            _log.info(f"[HEARTBEAT] created {created} default reminder templates")


async def _is_patient_busy(db, patient_id) -> bool:
    """skipWhenBusy: patient has an active diagnosis session."""
    from app.models.agent import AgentSession

    result = await db.execute(
        select(AgentSession).where(
            AgentSession.user_id == patient_id,
            AgentSession.status == "ACTIVE",
            AgentSession.session_type == "DIAGNOSIS",
        ).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def _send_reminder_email(db, evt) -> None:
    """Send the reminder email, templated when a matching active template
    exists, falling back to the built-in inline HTML otherwise."""
    from app.models.email import EmailTemplate
    from app.models.user import User

    payload = evt.payload or {}
    desc = payload.get("description", payload.get("name", "医疗提醒"))

    to_email = payload.get("email") or ""
    if not to_email:
        patient = await db.get(User, evt.patient_id)
        if patient:
            to_email = patient.email

    scheduled_time = (
        evt.scheduled_at.astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")
        if evt.scheduled_at
        else ""
    )
    variables = {"description": desc, "scheduled_time": scheduled_time}

    template = None
    template_name = _TEMPLATE_NAME_MAP.get(evt.event_type)
    if template_name:
        result = await db.execute(
            select(EmailTemplate).where(
                EmailTemplate.name == template_name,
                EmailTemplate.is_active.is_(True),
            )
        )
        template = result.scalar_one_or_none()

    if template:
        await email_service.send_templated_email(
            db=db, template=template, to_email=to_email, variables=variables,
        )
    else:
        await email_service.send_email(
            db=db,
            to_email=to_email,
            subject=f"【MediCareAI】{evt.event_type}",
            html_content=f"""<!DOCTYPE html>
<html><body style="font-family:Arial,sans-serif;">
<div style="max-width:500px;margin:0 auto;padding:20px;border:1px solid #eee;border-radius:8px;">
<h2 style="color:#E8956A;">📋{evt.event_type}</h2>
<p style="font-size:16px;">{desc}</p>
<p style="color:#999;font-size:12px;">自动化提醒 · 如有疑问请联系平台管理员</p>
</div></body></html>""",
        )


async def _claim_and_send(event_id: str) -> str:
    """Atomically claim one pending event and send its reminder.

    Returns: 'sent' | 'failed' | 'busy' | 'skipped'.
    'skipped' means the event was already handled/acknowledged/claimed —
    the normal outcome for duplicate ETA deliveries.
    """
    from app.models.agent import MonitoringEvent

    async with async_session_maker() as db:
        now = datetime.now(timezone.utc)

        # Atomic claim — only one caller can flip pending -> in_flight.
        result = await db.execute(
            update(MonitoringEvent)
            .where(
                MonitoringEvent.id == event_id,
                MonitoringEvent.status == "pending",
            )
            .values(status="in_flight", triggered_at=now)
            .returning(MonitoringEvent.id)
        )
        if result.scalar_one_or_none() is None:
            return "skipped"
        await db.commit()

        evt = await db.get(MonitoringEvent, event_id)

        # skipWhenBusy: release the claim, let the sweeper retry later.
        if await _is_patient_busy(db, evt.patient_id):
            evt.status = "pending"
            evt.triggered_at = None
            await db.commit()
            return "busy"

        try:
            await _send_reminder_email(db, evt)
            evt.status = "sent"
            outcome = "sent"
        except Exception as e:
            evt.status = "pending"
            evt.retry_count = (evt.retry_count or 0) + 1
            evt.error_message = str(e)
            outcome = "failed"
        await db.commit()
        return outcome


@shared_task(name="app.tasks.monitoring.send_reminder")
def send_reminder(event_id: str) -> dict:
    """ETA-scheduled precise reminder, fired at event.scheduled_at.

    Safe against duplicates: the atomic claim makes redeliveries no-ops.
    The periodic sweep remains as a fallback for worker restarts.
    """
    import asyncio

    outcome = asyncio.run(_claim_and_send(event_id))
    _log.info(f"[HEARTBEAT-ETA] event={event_id} outcome={outcome}")
    return {"event_id": event_id, "outcome": outcome}


@shared_task(name="app.tasks.monitoring.scan_pending_events")
def scan_pending_events() -> dict:
    """Fallback sweeper: send any due event that ETA scheduling missed
    (worker restarts, enqueue failures), and reclaim stale in_flight rows
    left behind by crashed workers.

    Features (openclaw pattern):
    - skipWhenBusy: defer if patient in active diagnosis
    - retry: max 3 attempts per event
    - batch: limit 50 per scan
    """
    import asyncio

    async def _run():
        from app.models.agent import MonitoringEvent

        await ensure_default_templates()

        async with async_session_maker() as db:
            now = datetime.now(timezone.utc)
            stale_before = now - timedelta(minutes=IN_FLIGHT_STALE_MINUTES)

            # Reclaim events stuck in_flight after a worker crash.
            await db.execute(
                update(MonitoringEvent)
                .where(
                    MonitoringEvent.status == "in_flight",
                    MonitoringEvent.triggered_at < stale_before,
                )
                .values(status="pending")
            )
            await db.commit()

            result = await db.execute(
                select(MonitoringEvent.id).where(
                    MonitoringEvent.status == "pending",
                    MonitoringEvent.scheduled_at <= now,
                    MonitoringEvent.retry_count < 3,
                ).limit(50)
            )
            event_ids = [str(eid) for eid in result.scalars().all()]

        outcomes = {"sent": 0, "failed": 0, "busy": 0, "skipped": 0}
        for eid in event_ids:
            outcome = await _claim_and_send(eid)
            outcomes[outcome] += 1

        _log.info(
            f"[HEARTBEAT] sent={outcomes['sent']} failed={outcomes['failed']} "
            f"busy={outcomes['busy']} skipped={outcomes['skipped']}"
        )
        return outcomes

    return asyncio.run(_run())
