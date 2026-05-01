"""Notification schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.notification import NotificationPriority, NotificationType


class NotificationBase(BaseModel):
    """Base notification schema."""

    notification_type: NotificationType = NotificationType.DIRECT
    priority: NotificationPriority = NotificationPriority.MEDIUM
    subject: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    action_url: str | None = Field(default=None, max_length=512)


class NotificationCreate(NotificationBase):
    """Create a direct notification (admin or user → user)."""

    recipient_id: uuid.UUID | None = None
    broadcast: bool = False


class NotificationBroadcastCreate(BaseModel):
    """Create a broadcast announcement (admin only)."""

    subject: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    priority: NotificationPriority = NotificationPriority.MEDIUM
    action_url: str | None = Field(default=None, max_length=512)


class NotificationUpdate(BaseModel):
    """Update a notification (mainly used for marking read)."""

    is_read: bool | None = None


class NotificationSender(BaseModel):
    """Compact sender info."""

    id: uuid.UUID
    full_name: str
    role: str

    model_config = ConfigDict(from_attributes=True)


class NotificationRecipient(BaseModel):
    """Compact recipient info."""

    id: uuid.UUID
    full_name: str
    role: str

    model_config = ConfigDict(from_attributes=True)


class NotificationListItem(BaseModel):
    """List item for notification feed."""

    id: uuid.UUID
    notification_type: NotificationType
    priority: NotificationPriority
    subject: str
    content_preview: str
    is_read: bool
    read_at: datetime | None
    broadcast: bool
    sender: NotificationSender | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationDetail(BaseModel):
    """Full notification detail."""

    id: uuid.UUID
    notification_type: NotificationType
    priority: NotificationPriority
    subject: str
    content: str
    action_url: str | None
    is_read: bool
    read_at: datetime | None
    broadcast: bool
    sender: NotificationSender | None
    recipient: NotificationRecipient | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    """Paginated list response."""

    items: list[NotificationListItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    unread_count: int


class NotificationUnreadCount(BaseModel):
    """Unread count per type."""

    total: int
    system: int
    announcement: int
    direct: int
    reminder: int


class NotificationDeleteResponse(BaseModel):
    """Soft delete response."""

    message: str
    deleted_id: uuid.UUID
