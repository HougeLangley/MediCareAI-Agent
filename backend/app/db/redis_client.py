"""Async Redis client for token blacklist and caching.

Lazy initialization to avoid connecting at import time.
"""

from __future__ import annotations

import redis.asyncio as redis

from app.core.config import get_settings

_settings = get_settings()
_redis_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    """Return cached async Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            str(_settings.redis_url),
            decode_responses=True,
        )
    return _redis_client
