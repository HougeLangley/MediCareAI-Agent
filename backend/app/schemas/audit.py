"""Audit log schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AuditLogListItem(BaseModel):
    """Lightweight audit log entry for list views."""

    id: UUID
    user_email: str | None = None
    user_role: str | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    success: bool
    created_at: datetime


class AuditLogDetail(AuditLogListItem):
    """Full audit log entry with details."""

    details: dict[str, Any] | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    error_message: str | None = None


class AuditLogStats(BaseModel):
    """Audit statistics for dashboard."""

    total_today: int
    total_week: int
    failed_today: int
    action_breakdown: list[dict[str, Any]]  # [{action, count}]


class AuditLogFilter(BaseModel):
    """Filter parameters for audit log queries."""

    action: str | None = None
    user_id: str | None = None
    resource_type: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    success: bool | None = None
