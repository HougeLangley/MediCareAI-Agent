"""Audit log service.

Centralized helper for recording admin-level operations.
All sensitive values are automatically masked before storage.
"""

from __future__ import annotations

from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditActionType, AuditLog, AuditResourceType


# Fields that must never appear in audit log details
_SENSITIVE_KEYS = {
    "api_key", "api_key_encrypted", "password", "token", "secret",
    "authorization", "cookie", "session", "private_key",
}


def _mask_sensitive(data: dict[str, Any] | None) -> dict[str, Any] | None:
    """Remove or mask sensitive fields from audit details."""
    if not data:
        return data
    safe: dict[str, Any] = {}
    for key, value in data.items():
        lower = key.lower()
        if any(sk in lower for sk in _SENSITIVE_KEYS):
            safe[key] = "***REDACTED***"
        elif isinstance(value, dict):
            safe[key] = _mask_sensitive(value)
        elif isinstance(value, list):
            safe[key] = [
                _mask_sensitive(v) if isinstance(v, dict) else v
                for v in value
            ]
        else:
            safe[key] = value
    return safe


def _get_client_ip(request: Request | None) -> str | None:
    """Extract client IP from request."""
    if request is None:
        return None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


class AuditService:
    """Service for recording audit log entries."""

    @staticmethod
    async def record(
        db: AsyncSession,
        *,
        action: AuditActionType,
        user_id: str | None = None,
        user_email: str | None = None,
        user_role: str | None = None,
        resource_type: AuditResourceType = AuditResourceType.UNKNOWN,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
        request: Request | None = None,
        success: bool = True,
        error_message: str | None = None,
    ) -> AuditLog:
        """Record an audit log entry.

        Args:
            db: Database session.
            action: Type of operation performed.
            user_id: UUID of the acting user.
            user_email: Email of the acting user (redundant storage).
            user_role: Role at time of action.
            resource_type: Type of resource affected.
            resource_id: Identifier of affected resource.
            details: Structured details (sensitive values auto-masked).
            request: FastAPI request for IP/UA extraction.
            success: Whether the operation succeeded.
            error_message: Error message if failed.
        """
        entry = AuditLog(
            user_id=user_id,
            user_email=user_email,
            user_role=user_role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=_mask_sensitive(details),
            ip_address=_get_client_ip(request),
            user_agent=request.headers.get("user-agent") if request else None,
            success=success,
            error_message=error_message,
        )
        db.add(entry)
        await db.flush()
        return entry
