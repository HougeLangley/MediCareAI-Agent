"""Notification (站内信) admin endpoints.

Supports broadcast, direct messaging, and full inbox management.
All endpoints require admin role.
"""

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_role
from app.db.session import get_db
from app.models.audit import AuditActionType, AuditResourceType
from app.models.notification import Notification, NotificationPriority, NotificationType
from app.models.user import User, UserRole
from app.schemas.notification import (
    NotificationBroadcastCreate,
    NotificationCreate,
    NotificationDeleteResponse,
    NotificationDetail,
    NotificationListItem,
    NotificationListResponse,
    NotificationSender,
    NotificationUnreadCount,
    NotificationUpdate,
)
from app.services.audit import AuditService

router = APIRouter(dependencies=[Depends(require_role(UserRole.ADMIN))])


# ═══════════════════════════════════════════════════════════════
# Helper: build sender / recipient compact objects
# ═══════════════════════════════════════════════════════════════

def _build_sender(user: User | None) -> NotificationSender | None:
    if not user:
        return None
    return NotificationSender(
        id=user.id,
        full_name=user.full_name,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
    )


async def _get_user_name(db: AsyncSession, user_id: uuid.UUID | None) -> str:
    if not user_id:
        return "System"
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    return user.full_name if user else "Unknown"


# ═══════════════════════════════════════════════════════════════
# Admin endpoints
# ═══════════════════════════════════════════════════════════════

@router.get("/notifications", response_model=NotificationListResponse)
async def list_notifications(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    notification_type: Annotated[NotificationType | None, Query()] = None,
    priority: Annotated[NotificationPriority | None, Query()] = None,
    is_read: Annotated[bool | None, Query()] = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationListResponse:
    """List notifications sent or received by admin (or broadcast)."""

    # Base query: visible to admin
    # Admin sees: broadcast, sent by admin, or sent to admin
    conditions = [
        or_(
            Notification.broadcast == True,
            Notification.sender_id == current_user.id,
            Notification.recipient_id == current_user.id,
        ),
        # Respect soft delete from admin's perspective
        or_(
            Notification.sender_id == current_user.id,
            Notification.sender_deleted == False,
        ),
        or_(
            Notification.recipient_id == current_user.id,
            Notification.recipient_deleted == False,
        ),
    ]

    if notification_type:
        conditions.append(Notification.notification_type == notification_type)
    if priority:
        conditions.append(Notification.priority == priority)
    if is_read is not None:
        conditions.append(Notification.is_read == is_read)
    if search:
        conditions.append(
            or_(
                Notification.subject.ilike(f"%{search}%"),
                Notification.content.ilike(f"%{search}%"),
            )
        )

    base_stmt = select(Notification).where(and_(*conditions))

    # Total count
    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one() or 0

    # Fetch items
    stmt = (
        base_stmt.order_by(desc(Notification.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()

    # Build response
    item_list: list[NotificationListItem] = []
    for n in items:
        preview = n.content[:200] + "..." if len(n.content) > 200 else n.content
        item_list.append(
            NotificationListItem(
                id=n.id,
                notification_type=n.notification_type,
                priority=n.priority,
                subject=n.subject,
                content_preview=preview,
                is_read=n.is_read,
                read_at=n.read_at,
                broadcast=n.broadcast,
                sender=_build_sender(n.sender),
                created_at=n.created_at,
            )
        )

    # Unread count for current admin
    unread_stmt = select(func.count()).where(
        and_(
            or_(
                Notification.recipient_id == current_user.id,
                Notification.broadcast == True,
            ),
            Notification.is_read == False,
            Notification.recipient_deleted == False,
        )
    )
    unread_result = await db.execute(unread_stmt)
    unread_count = unread_result.scalar_one() or 0

    return NotificationListResponse(
        items=item_list,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
        unread_count=unread_count,
    )


@router.get("/notifications/unread-count", response_model=NotificationUnreadCount)
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationUnreadCount:
    """Get unread notification count per type."""

    counts: dict[str, int] = {}
    for nt in NotificationType:
        stmt = select(func.count()).where(
            and_(
                or_(
                    Notification.recipient_id == current_user.id,
                    Notification.broadcast == True,
                ),
                Notification.notification_type == nt,
                Notification.is_read == False,
                Notification.recipient_deleted == False,
            )
        )
        result = await db.execute(stmt)
        counts[nt.value] = result.scalar_one() or 0

    total_stmt = select(func.count()).where(
        and_(
            or_(
                Notification.recipient_id == current_user.id,
                Notification.broadcast == True,
            ),
            Notification.is_read == False,
            Notification.recipient_deleted == False,
        )
    )
    total_result = await db.execute(total_stmt)
    total = total_result.scalar_one() or 0

    return NotificationUnreadCount(
        total=total,
        system=counts.get("system", 0),
        announcement=counts.get("announcement", 0),
        direct=counts.get("direct", 0),
        reminder=counts.get("reminder", 0),
    )


@router.get("/notifications/{notification_id}", response_model=NotificationDetail)
async def get_notification_detail(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> NotificationDetail:
    """Get single notification detail."""

    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    n = result.scalar_one_or_none()
    if not n:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    return NotificationDetail(
        id=n.id,
        notification_type=n.notification_type,
        priority=n.priority,
        subject=n.subject,
        content=n.content,
        action_url=n.action_url,
        is_read=n.is_read,
        read_at=n.read_at,
        broadcast=n.broadcast,
        sender=_build_sender(n.sender),
        recipient=_build_sender(n.recipient),
        created_at=n.created_at,
        updated_at=n.updated_at,
    )


@router.post("/notifications", response_model=NotificationDetail, status_code=status.HTTP_201_CREATED)
async def create_notification(
    data: NotificationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationDetail:
    """Send a direct notification to a specific user."""

    if data.broadcast:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use /notifications/broadcast for broadcast messages",
        )

    if not data.recipient_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="recipient_id is required for direct messages",
        )

    # Verify recipient exists
    recipient_result = await db.execute(select(User).where(User.id == data.recipient_id))
    recipient = recipient_result.scalar_one_or_none()
    if not recipient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipient not found",
        )

    notification = Notification(
        sender_id=current_user.id,
        recipient_id=data.recipient_id,
        notification_type=data.notification_type,
        priority=data.priority,
        subject=data.subject,
        content=data.content,
        action_url=data.action_url,
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)

    # Audit log
    audit = AuditService(db)
    await audit.log(
        user_id=current_user.id,
        action=AuditActionType.CREATE,
        resource_type=AuditResourceType.SYSTEM_SETTING,  # closest match
        resource_id=str(notification.id),
        details={
            "type": "notification_direct",
            "recipient_id": str(data.recipient_id),
            "subject": data.subject,
        },
    )

    return NotificationDetail(
        id=notification.id,
        notification_type=notification.notification_type,
        priority=notification.priority,
        subject=notification.subject,
        content=notification.content,
        action_url=notification.action_url,
        is_read=notification.is_read,
        read_at=notification.read_at,
        broadcast=notification.broadcast,
        sender=_build_sender(notification.sender),
        recipient=_build_sender(notification.recipient),
        created_at=notification.created_at,
        updated_at=notification.updated_at,
    )


@router.post("/notifications/broadcast", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def broadcast_notification(
    data: NotificationBroadcastCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Broadcast a system announcement to all active users."""

    # Get all active users
    users_result = await db.execute(
        select(User.id).where(User.status == "active")
    )
    user_ids = [row[0] for row in users_result.all()]

    # Create broadcast master notification
    master = Notification(
        sender_id=current_user.id,
        recipient_id=None,
        notification_type=NotificationType.ANNOUNCEMENT,
        priority=data.priority,
        subject=data.subject,
        content=data.content,
        action_url=data.action_url,
        broadcast=True,
    )
    db.add(master)
    await db.commit()
    await db.refresh(master)

    # Also create individual copies for inbox counting (optional optimisation:
    # in production this could be a background Celery task)
    # For simplicity, we use the broadcast flag and let the frontend query
    # with broadcast=True to show it in everyone's inbox.

    # Audit log
    audit = AuditService(db)
    await audit.log(
        user_id=current_user.id,
        action=AuditActionType.CREATE,
        resource_type=AuditResourceType.SYSTEM_SETTING,
        resource_id=str(master.id),
        details={
            "type": "notification_broadcast",
            "recipient_count": len(user_ids),
            "subject": data.subject,
        },
    )

    return {
        "message": "Broadcast sent successfully",
        "notification_id": str(master.id),
        "recipient_count": len(user_ids),
    }


@router.patch("/notifications/{notification_id}/read", response_model=NotificationDetail)
async def mark_notification_read(
    notification_id: uuid.UUID,
    data: NotificationUpdate | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationDetail:
    """Mark a notification as read or unread."""

    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    n = result.scalar_one_or_none()
    if not n:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    # Admin can mark anything; for future user endpoints, restrict to own
    target_read = True if data is None or data.is_read is None else data.is_read

    n.is_read = target_read
    n.read_at = datetime.utcnow() if target_read else None
    await db.commit()
    await db.refresh(n)

    return NotificationDetail(
        id=n.id,
        notification_type=n.notification_type,
        priority=n.priority,
        subject=n.subject,
        content=n.content,
        action_url=n.action_url,
        is_read=n.is_read,
        read_at=n.read_at,
        broadcast=n.broadcast,
        sender=_build_sender(n.sender),
        recipient=_build_sender(n.recipient),
        created_at=n.created_at,
        updated_at=n.updated_at,
    )


@router.delete("/notifications/{notification_id}", response_model=NotificationDeleteResponse)
async def delete_notification(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationDeleteResponse:
    """Soft-delete a notification (from admin's perspective)."""

    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    n = result.scalar_one_or_none()
    if not n:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    # If admin is sender → sender_deleted; if recipient → recipient_deleted
    # If both, we can truly delete
    if n.sender_id == current_user.id:
        n.sender_deleted = True
    if n.recipient_id == current_user.id or n.broadcast:
        n.recipient_deleted = True

    await db.commit()

    # If both sides deleted (and not broadcast), hard delete
    if n.sender_deleted and n.recipient_deleted and not n.broadcast:
        await db.delete(n)
        await db.commit()

    return NotificationDeleteResponse(
        message="Notification deleted",
        deleted_id=notification_id,
    )
