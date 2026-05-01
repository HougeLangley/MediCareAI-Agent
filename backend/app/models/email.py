"""Email management models.

Improvements over legacy:
- Encrypted SMTP password storage (via app.core.encryption)
- Email template system with variable substitution
- Email send history / log for debugging
- Support for both STARTTLS and SSL
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class SmtpSecurity(str, PyEnum):
    STARTTLS = "starttls"
    SSL = "ssl"
    NONE = "none"


class EmailConfiguration(Base):
    """SMTP server configuration.

    Passwords are encrypted at rest using app.core.encryption.
    Only the active default config is used by the email service.
    """

    __tablename__ = "email_configurations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    smtp_host: Mapped[str] = mapped_column(String(255), nullable=False)
    smtp_port: Mapped[int] = mapped_column(Integer, nullable=False, default=587)
    smtp_user: Mapped[str] = mapped_column(String(255), nullable=False)
    # Password is encrypted before storage and decrypted on use
    smtp_password_encrypted: Mapped[str] = mapped_column(String(512), nullable=False)
    smtp_from_email: Mapped[str] = mapped_column(String(255), nullable=False)
    smtp_from_name: Mapped[str] = mapped_column(String(255), nullable=False, default="MediCareAI-Agent")
    smtp_security: Mapped[SmtpSecurity] = mapped_column(
        Enum(SmtpSecurity), default=SmtpSecurity.STARTTLS, nullable=False
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Test status tracking
    test_status: Mapped[str] = mapped_column(String(50), default="untested", nullable=False)
    test_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationship to send logs
    send_logs: Mapped[list["EmailLog"]] = relationship(
        "EmailLog", back_populates="config", lazy="selectin"
    )


class EmailTemplate(Base):
    """Reusable email template with variable substitution.

    Variables are denoted as {{variable_name}} and replaced at send time.
    """

    __tablename__ = "email_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    html_body: Mapped[str] = mapped_column(Text, nullable=False)
    text_body: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Comma-separated list of expected variables, e.g. "user_name,reset_url"
    variables: Mapped[str | None] = mapped_column(String(512), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class EmailSendStatus(str, PyEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RETRYING = "retrying"


class EmailLog(Base):
    """History of email send attempts.

    Provides full traceability for debugging deliverability issues.
    """

    __tablename__ = "email_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Link to config used
    config_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("email_configurations.id", ondelete="SET NULL"), nullable=True
    )

    # Template used (nullable for ad-hoc sends)
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("email_templates.id", ondelete="SET NULL"), nullable=True
    )

    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    # Truncated preview of sent content
    body_preview: Mapped[str] = mapped_column(String(500), nullable=True)

    status: Mapped[EmailSendStatus] = mapped_column(
        Enum(EmailSendStatus), default=EmailSendStatus.PENDING, nullable=False, index=True
    )

    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationship
    config: Mapped["EmailConfiguration"] = relationship(
        "EmailConfiguration", back_populates="send_logs", lazy="selectin"
    )

    __table_args__ = (
        # Fast status-based queries for admin dashboard
        Index("ix_email_logs_status_created", "status", "created_at"),
    )
