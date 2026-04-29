"""System configuration models.

Stores admin-configurable settings like LLM API keys, embedding configs, etc.
All sensitive values encrypted at application layer via Fernet.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class LLMProviderConfig(Base):
    """LLM provider configuration (admin-managed).

    api_key_encrypted stores the Fernet-encrypted API key.
    api_key column is removed; never store plaintext keys.

    Platform isolation:
    - platform=NULL: global config, available to all platforms.
    - platform='web'|'miniapp'|'ios'|'android': platform-specific.
    """

    __tablename__ = "llm_provider_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    # Platform scope: NULL=global, otherwise web/miniapp/ios/android
    platform: Mapped[str | None] = mapped_column(String(20), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    # Encrypted at application layer via Fernet (see app.core.encryption)
    api_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    default_model: Mapped[str] = mapped_column(String(100), nullable=False)
    # Model type: diagnosis, embedding, rerank, mineru, etc.
    model_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="diagnosis"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        # One provider per platform per model_type (NULL = global)
        UniqueConstraint("provider", "platform", "model_type", name="uq_provider_platform_model_type"),
    )


class SystemSetting(Base):
    """Generic key-value system settings."""

    __tablename__ = "system_settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False)  # Mask in API responses
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
