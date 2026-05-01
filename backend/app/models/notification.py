"""Notification (站内信) models.

Improved over legacy design:
- Full role support (not just doctor → admin)
- Broadcast / bulk messaging support
- Message types and priorities
- Soft delete (per side)
- Action URLs for deep linking
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class NotificationType(str, PyEnum):
    SYSTEM = "system"          # System-level events
    ANNOUNCEMENT = "announcement"  # Admin broadcasts
    DIRECT = "direct"          # Private message between users
    REMINDER = "reminder"      # Scheduled reminder


class NotificationPriority(str, PyEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Notification(Base):
    """Unified notification / 站内信 model.

    Supports:
    - Direct 1-to-1 messages between any authenticated roles
    - Admin broadcast (recipient_id=None, broadcast=True)
    - System-generated notifications (sender_id=None)
    - Soft delete per side (sender_deleted / recipient_deleted)
    """

    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Sender — null for system-generated notifications
    sender_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Recipient — null for broadcast messages
    recipient_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Message classification
    notification_type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType), default=NotificationType.DIRECT, nullable=False, index=True
    )
    priority: Mapped[NotificationPriority] = mapped_column(
        Enum(NotificationPriority), default=NotificationPriority.MEDIUM, nullable=False
    )

    # Content
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Interactive action URL (e.g., navigate to a case review)
    action_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Read tracking
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Soft delete — each side controls visibility independently
    sender_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    recipient_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Broadcast flag (sent to all active users)
    broadcast: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    sender: Mapped["User"] = relationship(
        "User",
        foreign_keys="Notification.sender_id",
        lazy="selectin",
        back_populates="sent_notifications",
    )
    recipient: Mapped["User"] = relationship(
        "User",
        foreign_keys="Notification.recipient_id",
        lazy="selectin",
        back_populates="received_notifications",
    )

    __table_args__ = (
        # Fast lookup for a user's inbox
        Index("ix_notifications_recipient_inbox", "recipient_id", "recipient_deleted", "is_read", "created_at"),
        # Fast lookup for a user's outbox
        Index("ix_notifications_sender_outbox", "sender_id", "sender_deleted", "created_at"),
        # Fast lookup for broadcasts per user (joined with user creation date)
        Index("ix_notifications_broadcast", "broadcast", "created_at"),
    )
