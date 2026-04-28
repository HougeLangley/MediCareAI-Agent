"""Dynamic configuration service.

Reads business-level configuration from the system_settings table.
All values are admin-configurable via /api/v1/admin/settings.

Infrastructure configs (DB URL, Redis URL, secret keys) remain in
app.core.config (environment variables).
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import SystemSetting


class DynamicConfigService:
    """Read configuration values from system_settings table.

    All methods accept a default value that is returned when:
    - The key does not exist in the database
    - The database is unavailable
    - The value cannot be parsed to the expected type
    """

    @staticmethod
    async def get_str(
        db: AsyncSession,
        key: str,
        default: str | None = None,
    ) -> str | None:
        """Read a string value from system_settings."""
        try:
            result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
            setting = result.scalar_one_or_none()
            if setting:
                return setting.value
        except Exception:
            pass
        return default

    @staticmethod
    async def get_int(
        db: AsyncSession,
        key: str,
        default: int = 0,
    ) -> int:
        """Read an integer value from system_settings."""
        raw = await DynamicConfigService.get_str(db, key)
        if raw is None:
            return default
        try:
            return int(raw)
        except (ValueError, TypeError):
            return default

    @staticmethod
    async def get_bool(
        db: AsyncSession,
        key: str,
        default: bool = False,
    ) -> bool:
        """Read a boolean value from system_settings."""
        raw = await DynamicConfigService.get_str(db, key)
        if raw is None:
            return default
        return raw.lower() in ("true", "1", "yes", "on", "enabled")

    @staticmethod
    async def get_json(
        db: AsyncSession,
        key: str,
        default: dict[str, Any] | list[Any] | None = None,
    ) -> dict[str, Any] | list[Any] | None:
        """Read a JSON-encoded value from system_settings."""
        raw = await DynamicConfigService.get_str(db, key)
        if raw is None:
            return default
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return default

    @staticmethod
    async def get_float(
        db: AsyncSession,
        key: str,
        default: float = 0.0,
    ) -> float:
        """Read a float value from system_settings."""
        raw = await DynamicConfigService.get_str(db, key)
        if raw is None:
            return default
        try:
            return float(raw)
        except (ValueError, TypeError):
            return default

    # ------------------------------------------------------------------
    # Convenience accessors for commonly used business configs
    # ------------------------------------------------------------------

    @classmethod
    async def guest_session_ttl_hours(cls, db: AsyncSession) -> int:
        return await cls.get_int(db, "guest.session_ttl_hours", default=24)

    @classmethod
    async def guest_max_messages(cls, db: AsyncSession) -> int:
        return await cls.get_int(db, "guest.max_messages", default=10)

    @classmethod
    async def cors_origins(cls, db: AsyncSession) -> list[str]:
        origins = await cls.get_json(db, "cors.origins")
        if origins is None:
            return ["*"]
        if isinstance(origins, list):
            return origins
        return ["*"]

    @classmethod
    async def max_upload_size_mb(cls, db: AsyncSession) -> int:
        return await cls.get_int(db, "app.max_upload_size_mb", default=10)

    @classmethod
    async def rag_chunk_size(cls, db: AsyncSession) -> int:
        return await cls.get_int(db, "rag.chunk_size", default=500)

    @classmethod
    async def rag_chunk_overlap(cls, db: AsyncSession) -> int:
        return await cls.get_int(db, "rag.chunk_overlap", default=50)
