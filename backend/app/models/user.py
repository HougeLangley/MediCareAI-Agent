"""User and related models.

Implements:
- Dual identity (patient / doctor)
- Role switch audit
- Guest sessions
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class UserRole(str, PyEnum):
    PATIENT = "patient"
    DOCTOR = "doctor"
    ADMIN = "admin"


class UserStatus(str, PyEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.PATIENT, nullable=False)
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus), default=UserStatus.PENDING, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Doctor-specific fields
    license_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    hospital: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    title: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    role_switches: Mapped[list["RoleSwitchLog"]] = relationship(
        "RoleSwitchLog", back_populates="user", lazy="selectin"
    )

    __table_args__ = (
        # (email, role) unique constraint per architecture spec
        UniqueConstraint("email", "role", name="uq_user_email_role"),
    )


class RoleSwitchLog(Base):
    __tablename__ = "role_switch_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    from_role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    to_role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    switched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="role_switches")


class GuestSession(Base):
    __tablename__ = "guest_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_token: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    fingerprint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_messages: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
