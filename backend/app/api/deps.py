"""FastAPI dependencies: DB session, current user, permissions, platform."""

import uuid
from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@dataclass
class UserContext:
    """Authenticated user with platform context."""

    user: User
    platform: str


async def _resolve_token(
    token: str, db: AsyncSession
) -> tuple[User, str]:
    """Decode JWT and resolve to (user, platform).

    Raises:
        HTTPException: 401/403 on any validation failure.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        token_type = payload.get("type")
        if token_type != "access":
            raise credentials_exception
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        platform: str = payload.get("platform") or "unknown"
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive or pending",
        )
    return user, platform


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db),
) -> User:
    """Decode JWT and return the current authenticated user."""
    user, _ = await _resolve_token(token, db)
    return user


async def get_current_user_context(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db),
) -> UserContext:
    """Decode JWT and return user + platform context."""
    user, platform = await _resolve_token(token, db)
    return UserContext(user=user, platform=platform)


async def get_current_platform(
    request: Request,
    x_platform: Annotated[str | None, Header(alias="X-Platform")] = None,
) -> str:
    """Return the current platform from header or request state.

    Priority:
    1. X-Platform header (for unauthenticated or pre-auth requests)
    2. request.state.platform (set by middleware after auth)
    3. Default to 'unknown'
    """
    if x_platform:
        return x_platform.strip().lower()
    if hasattr(request.state, "platform"):
        return request.state.platform
    return "unknown"


def require_platform(*allowed: str):
    """Dependency factory to restrict endpoints to specific platforms.

    Usage:
        @router.get("/miniapp-only", dependencies=[Depends(require_platform("miniapp"))])
    """

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
    """Dependency factory to require specific role(s).

    Usage:
        @router.get("/admin-only", dependencies=[Depends(require_role(UserRole.ADMIN))])
    """

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
CurrentUserContext = Annotated[UserContext, Depends(get_current_user_context)]
