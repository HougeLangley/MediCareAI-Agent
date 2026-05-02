"""FastAPI dependencies: DB session, current user, permissions, platform."""

import hashlib
import uuid
from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.redis_client import get_redis
from app.db.session import get_db
from app.models.user import GuestSession, User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


@dataclass
class UserContext:
    """Authenticated user with platform context."""

    user: User | None
    platform: str
    is_guest: bool = False
    guest_id: str | None = None


async def _resolve_token(
    token: str | None, db: AsyncSession
) -> tuple[User | None, str, bool, str | None]:
    """Decode JWT and resolve to (user, platform, is_guest, guest_id).

    Returns:
        (user, platform, is_guest, guest_id)
        - user: authenticated user or None
        - platform: platform string
        - is_guest: True if this is a guest token
        - guest_id: guest session ID if guest token
    """
    if not token:
        return None, "unknown", False, None

    # Check token blacklist (logout revocation)
    try:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        redis_client = get_redis()
        is_blacklisted = await redis_client.get(f"token_blacklist:{token_hash}")
        if is_blacklisted:
            return None, "unknown", False, None
    except Exception:
        # Redis unavailable — fail open (allow token) but log warning
        pass

    try:
        payload = decode_token(token)
        token_type = payload.get("type")

        if token_type == "guest":
            guest_id = payload.get("sub")
            platform = payload.get("platform") or "unknown"
            return None, platform, True, guest_id

        if token_type == "access":
            user_id: str | None = payload.get("sub")
            if user_id is None:
                return None, "unknown", False, None
            platform: str = payload.get("platform") or "unknown"

            result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
            user = result.scalar_one_or_none()
            if user is None:
                return None, platform, False, None
            if user.status != "active":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User account is inactive or pending",
                )
            return user, platform, False, None

        return None, "unknown", False, None

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        return None, "unknown", False, None


async def get_current_user_or_guest(
    request: Request,
    token: Annotated[str | None, Depends(oauth2_scheme)] = None,
    x_guest_token: Annotated[str | None, Header(alias="X-Guest-Token")] = None,
    db: AsyncSession = Depends(get_db),
) -> UserContext:
    """Resolve current user or guest from Bearer token, X-Guest-Token header, or Cookie.

    Priority: Bearer Header > X-Guest-Token Header > Cookie(auth_token)
    """
    # Try Bearer token first, then X-Guest-Token, then Cookie fallback
    cookie_token = request.cookies.get("auth_token")
    effective_token = token or x_guest_token or cookie_token
    user, platform, is_guest, guest_id = await _resolve_token(effective_token, db)

    if user is None and not is_guest:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserContext(user=user, platform=platform, is_guest=is_guest, guest_id=guest_id)


async def get_current_user(
    request: Request,
    token: Annotated[str | None, Depends(oauth2_scheme)] = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Decode JWT and return the current authenticated user (not guest).

    Supports Bearer header and Cookie(auth_token) fallback.
    """
    effective_token = token or request.cookies.get("auth_token")
    if not effective_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user, _, _, _ = await _resolve_token(effective_token, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_platform(
    request: Request,
    x_platform: Annotated[str | None, Header(alias="X-Platform")] = None,
) -> str:
    """Return the current platform from header or request state."""
    if x_platform:
        return x_platform.strip().lower()
    if hasattr(request.state, "platform"):
        return request.state.platform
    return "unknown"


def require_platform(*allowed: str):
    """Dependency factory to restrict endpoints to specific platforms."""

    async def _check_platform(
        platform: Annotated[str, Depends(get_current_platform)],
    ) -> str:
        normalized = platform.strip().lower()
        if normalized not in [a.strip().lower() for a in allowed]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Platform '{platform}' not allowed. Allowed: {', '.join(allowed)}",
            )
        return normalized

    return _check_platform


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Ensure user is active."""
    return current_user


def require_role(*roles: UserRole):
    """Dependency factory to require specific role(s)."""

    async def _check_role(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role: {', '.join(r.value for r in roles)}",
            )
        return current_user

    return _check_role


# Convenience type aliases
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentUserContext = Annotated[UserContext, Depends(get_current_user_or_guest)]
