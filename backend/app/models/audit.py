"""Audit log models.

Records all admin-level operations for security auditing and compliance.
Patient-side operations are intentionally NOT logged to protect privacy.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    Boolean,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AuditActionType(str, PyEnum):
    """Types of admin operations that are audited."""

    # Auth / Identity
    LOGIN = "login"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    ROLE_SWITCH = "role_switch"

    # Doctor verification
    DOCTOR_VERIFY = "doctor_verify"
    DOCTOR_REJECT = "doctor_reject"

    # Knowledge base
    DOCUMENT_CREATE = "document_create"
    DOCUMENT_UPDATE = "document_update"
    DOCUMENT_DELETE = "document_delete"
    DOCUMENT_REVIEW = "document_review"
    DOCUMENT_TOGGLE = "document_toggle"

    # System configuration
    SETTINGS_CHANGE = "settings_change"
    LLM_CONFIG_CREATE = "llm_config_create"
    LLM_CONFIG_UPDATE = "llm_config_update"
    LLM_CONFIG_DELETE = "llm_config_delete"
    LLM_CONFIG_TEST = "llm_config_test"

    # User management
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"

    # Agent operations
    AGENT_SESSION = "agent_session"
    TOOL_CALL = "tool_call"


class AuditResourceType(str, PyEnum):
    """Resource types that can be audited."""

    USER = "user"
    DOCTOR = "doctor"
    DOCUMENT = "document"
    SYSTEM_SETTING = "system_setting"
    LLM_PROVIDER = "llm_provider"
    AGENT_SESSION = "agent_session"
    UNKNOWN = "unknown"


class AuditLog(Base):
    """Audit log entry for admin operations.

    Design decisions:
    - Patient-side operations are NOT logged (privacy protection).
    - Sensitive values (API keys, passwords) are NEVER stored in details.
    - user_email is stored redundantly so audit trail survives user deletion.
    """

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Who performed the action
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    user_email: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
        doc="Redundant email for audit trail persistence",
    )
    user_role: Mapped[str | None] = mapped_column(
        String(20), nullable=True,
        doc="Role at time of action",
    )

    # What happened
    action: Mapped[AuditActionType] = mapped_column(
        Enum(AuditActionType), nullable=False
    )
    resource_type: Mapped[AuditResourceType] = mapped_column(
        Enum(AuditResourceType), default=AuditResourceType.UNKNOWN
    )
    resource_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        doc="UUID or identifier of the affected resource",
    )

    # Details (safe JSON — no sensitive plaintext)
    details: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=dict,
        doc="Structured action details. NEVER contains API keys or passwords.",
    )

    # Context
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Outcome
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_resource_type", "resource_type"),
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_success", "success"),
    )
