"""Authentication endpoints.

Supports:
- Patient/Doctor/Admin login & register
- Guest mode token issuance
- Role switch with audit logging
- Platform-aware token issuance (X-Platform header)
"""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from typing import Annotated, Any

import jwt
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user
from app.core.config import get_settings
from app.core.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    create_guest_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.db.redis_client import get_redis
from app.db.session import get_db
from app.models.user import GuestSession, RoleSwitchLog, User, UserRole, UserStatus
from app.schemas.auth import (
    GuestSessionResponse,
    LoginResponse,
    PasswordChangeRequest,
    RoleSwitchRequest,
    RoleSwitchResponse,
    Token,
    UserRegister,
    UserResponse,
)

from app.services.config import DynamicConfigService

router = APIRouter()
settings = get_settings()


def _read_platform(request: Request, x_platform: str | None) -> str:
    """Read platform from header or User-Agent fallback."""
    if x_platform:
        return x_platform.strip().lower()
    # Fallback heuristic based on User-Agent
    ua = (request.headers.get("User-Agent") or "").lower()
    if "miniprogram" in ua or "wechat" in ua:
        return "miniapp"
    if "android" in ua:
        return "android"
    if "iphone" in ua or "ipad" in ua or "ios" in ua:
        return "ios"
    return "web"


@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserRegister,
    request: Request,
    x_platform: Annotated[str | None, Header(alias="X-Platform")] = None,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Register a new user (patient or doctor)."""
    platform = _read_platform(request, x_platform)

    # Check email+role uniqueness
    result = await db.execute(
        select(User).where(User.email == data.email, User.role == data.role)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email {data.email} and role {data.role.value} already exists",
        )

    user = User(
        email=data.email,
        hashed_password=get_password_hash(data.password),
        full_name=data.full_name,
        phone=data.phone,
        role=data.role,
        status=UserStatus.ACTIVE,
        license_number=data.license_number,
        hospital=data.hospital,
        department=data.department,
        title=data.title,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id, platform=platform)
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    x_platform: Annotated[str | None, Header(alias="X-Platform")] = None,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Authenticate and issue JWT (OAuth2 password flow)."""
    platform = _read_platform(request, x_platform)

    # OAuth2 form uses username field for email
    result = await db.execute(select(User).where(User.email == form_data.username))
    users = result.scalars().all()

    if not users:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Find user(s) with matching password
    matched_users = [
        u for u in users
        if u.hashed_password and verify_password(form_data.password, u.hashed_password)
    ]

    if not matched_users:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # If multiple identities share this email, deterministically pick one:
    # ADMIN > DOCTOR > PATIENT, then most-recently-updated as tie-breaker.
    role_priority = {UserRole.ADMIN: 0, UserRole.DOCTOR: 1, UserRole.PATIENT: 2}
    user = min(
        matched_users,
        key=lambda u: (
            role_priority.get(u.role, 99),
            -(u.updated_at.timestamp() if u.updated_at else 0),
        ),
    )

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    token = create_access_token(user.id, platform=platform)
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
        password_change_required=user.password_change_required,
    )


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    data: PasswordChangeRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Change current user's password.

    If password_change_required is set, old_password can be omitted
    for the initial password change after default login.
    """
    # Verify old password (skip if admin doing first-time change)
    if not current_user.password_change_required:
        if not data.old_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Old password is required",
            )
        if not verify_password(data.old_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect old password",
            )

    current_user.hashed_password = get_password_hash(data.new_password)
    current_user.password_change_required = False
    await db.commit()


@router.post("/guest", response_model=GuestSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_guest_session(
    request: Request,
    x_platform: Annotated[str | None, Header(alias="X-Platform")] = None,
    db: AsyncSession = Depends(get_db),
) -> GuestSessionResponse:
    """Create a time-limited guest session."""
    platform = _read_platform(request, x_platform)
    session_token = uuid.uuid4().hex
    fingerprint = request.headers.get("User-Agent", "")[:255] or None

    # Read dynamic business config from system_settings
    ttl_hours = await DynamicConfigService.guest_session_ttl_hours(db)
    max_messages = await DynamicConfigService.guest_max_messages(db)

    expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)

    guest = GuestSession(
        session_token=session_token,
        fingerprint=fingerprint,
        max_messages=max_messages,
        expires_at=expires_at,
    )
    db.add(guest)
    await db.commit()
    await db.refresh(guest)

    # Embed token in response — client stores it in localStorage/sessionStorage
    token = create_guest_token(str(guest.id), fingerprint, platform=platform)

    # Return session with token included
    return GuestSessionResponse(
        id=guest.id,
        session_token=token,
        message_count=guest.message_count,
        max_messages=guest.max_messages,
        expires_at=guest.expires_at,
        created_at=guest.created_at,
    )


@router.post("/switch-role", response_model=RoleSwitchResponse)
async def switch_role(
    data: RoleSwitchRequest,
    request: Request,
    current_user: CurrentUser,
    x_platform: Annotated[str | None, Header(alias="X-Platform")] = None,
    db: AsyncSession = Depends(get_db),
) -> RoleSwitchResponse:
    """Switch between patient and doctor identities.

    Restrictions:
    - Cannot switch to the same role.
    - Only PATIENT <-> DOCTOR switches are allowed.
    - Requires both roles to be registered separately.
    """
    platform = _read_platform(request, x_platform)

    if current_user.role == data.target_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot switch to the same role",
        )

    if data.target_role not in (UserRole.PATIENT, UserRole.DOCTOR):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only switch between patient and doctor roles",
        )

    # Check if target role account exists for this email
    result = await db.execute(
        select(User).where(
            User.email == current_user.email,
            User.role == data.target_role,
        )
    )
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No {data.target_role.value} account found for this email. Please register first.",
        )

    # Log the switch
    log = RoleSwitchLog(
        user_id=current_user.id,
        from_role=current_user.role,
        to_role=data.target_role,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    db.add(log)
    await db.commit()

    # Issue new token for the target identity
    new_token = create_access_token(target_user.id, platform=platform)

    return RoleSwitchResponse(
        new_token=new_token,
        previous_role=current_user.role,
        current_role=data.target_role,
        switched_at=datetime.now(timezone.utc),
    )


@router.get("/guest/status")
async def get_guest_status(
    x_guest_token: Annotated[str | None, Header(alias="X-Guest-Token")] = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Query current guest session status and remaining quota."""
    if not x_guest_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No guest token provided",
        )

    try:
        payload = decode_token(x_guest_token)
        if payload.get("type") != "guest":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid guest token",
            )
        guest_id = payload.get("sub")
        if not guest_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid guest token",
            )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid guest token",
        )

    result = await db.execute(
        select(GuestSession).where(GuestSession.id == uuid.UUID(guest_id))
    )
    guest = result.scalar_one_or_none()

    if not guest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Guest session not found",
        )

    if guest.expires_at and guest.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Guest session has expired",
        )

    remaining = max(0, guest.max_messages - guest.message_count)
    return {
        "interaction_count": guest.message_count,
        "max_interactions": guest.max_messages,
        "remaining": remaining,
        "can_interact": remaining > 0 and not guest.is_blocked,
        "expires_at": guest.expires_at.isoformat() if guest.expires_at else None,
    }


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser) -> UserResponse:
    """Return current authenticated user profile."""
    return UserResponse.model_validate(current_user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    current_user: CurrentUser,
) -> None:
    """Invalidate the current access token (logout).

    Supports Bearer header and Cookie(auth_token).
    Adds the token to a Redis blacklist with TTL equal to token remaining lifetime.
    """
    # Extract token from Authorization header or Cookie
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else None
    token = token or request.cookies.get("auth_token")

    if not token:
        return  # Nothing to revoke

    try:
        payload = decode_token(token)
        exp = payload.get("exp")
        if exp:
            ttl = int(exp - datetime.now(timezone.utc).timestamp())
            if ttl > 0:
                token_hash = hashlib.sha256(token.encode()).hexdigest()
                redis_client = get_redis()
                await redis_client.setex(
                    f"token_blacklist:{token_hash}",
                    ttl,
                    "1",
                )
    except jwt.ExpiredSignatureError:
        # Token already expired — nothing to blacklist
        pass
    except jwt.InvalidTokenError:
        # Invalid token — ignore
        pass
    except Exception:
        # Redis unavailable — ignore (token will expire naturally)
        pass
