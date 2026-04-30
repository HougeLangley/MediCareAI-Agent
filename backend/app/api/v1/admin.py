"""Admin configuration endpoints.

Manage LLM provider configs and system settings.
Requires admin role.
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_role
from app.core.encryption import decrypt_value, encrypt_value, mask_api_key
from app.db.session import get_db
from app.models.audit import AuditActionType, AuditLog, AuditResourceType
from app.models.config import LLMProviderConfig, SystemSetting
from app.models.user import User, UserRole
from app.schemas.audit import AuditLogDetail, AuditLogListItem, AuditLogStats
from app.schemas.config import (
    BatchSettingsRequest,
    DoctorVerifyRequest,
    LLMProviderConfigCreate,
    LLMProviderConfigResponse,
    LLMProviderConfigUpdate,
    SystemSettingCreate,
    SystemSettingResponse,
    SystemSettingUpdate,
    UserAdminUpdate,
    UserListItem,
)
from app.services.audit import AuditService
from app.services.llm import LLMService

router = APIRouter(dependencies=[Depends(require_role(UserRole.ADMIN))])

# ─── Predefined Business Settings ─────────────────────────────
# These settings are auto-created on first access if missing.
# Admins can modify their values but should not delete core keys.

DEFAULT_SETTINGS: list[SystemSettingCreate] = [
    # ── General ──
    SystemSettingCreate(
        key="site.name",
        value="MediCareAI-Agent",
        description="站点显示名称",
        category="general",
        value_type="string",
    ),
    SystemSettingCreate(
        key="site.description",
        value="您的智能医疗助手",
        description="站点副标题/SEO描述",
        category="general",
        value_type="string",
    ),
    # ── Auth ──
    SystemSettingCreate(
        key="auth.registration_enabled",
        value="true",
        description="是否开放新用户注册",
        category="auth",
        value_type="boolean",
    ),
    SystemSettingCreate(
        key="auth.invite_code_required",
        value="false",
        description="注册时是否需要邀请码",
        category="auth",
        value_type="boolean",
    ),
    SystemSettingCreate(
        key="auth.guest_max_messages",
        value="10",
        description="访客模式允许的最大对话轮数",
        category="auth",
        value_type="number",
    ),
    SystemSettingCreate(
        key="auth.password_min_length",
        value="8",
        description="用户密码最小长度",
        category="auth",
        value_type="number",
    ),
    # ── Diagnosis ──
    SystemSettingCreate(
        key="diagnosis.confidence_threshold",
        value="0.7",
        description="诊断建议的最小置信度阈值 (0-1)",
        category="diagnosis",
        value_type="number",
    ),
    SystemSettingCreate(
        key="diagnosis.max_followup_days",
        value="14",
        description="自动随访计划的最大天数",
        category="diagnosis",
        value_type="number",
    ),
    SystemSettingCreate(
        key="diagnosis.require_symptom_count",
        value="3",
        description="生成诊断建议所需的最少症状数量",
        category="diagnosis",
        value_type="number",
    ),
    # ── Agent ──
    SystemSettingCreate(
        key="agent.max_tool_calls",
        value="5",
        description="单次对话中 Agent 最大工具调用次数",
        category="agent",
        value_type="number",
    ),
    SystemSettingCreate(
        key="agent.enable_followup",
        value="true",
        description="是否启用自动随访提醒",
        category="agent",
        value_type="boolean",
    ),
    SystemSettingCreate(
        key="agent.response_timeout_seconds",
        value="60",
        description="Agent 响应超时时间（秒）",
        category="agent",
        value_type="number",
    ),
    # ── Notification ──
    SystemSettingCreate(
        key="notification.email_enabled",
        value="true",
        description="是否启用邮件通知",
        category="notification",
        value_type="boolean",
    ),
    # ── Security ──
    SystemSettingCreate(
        key="security.max_login_attempts",
        value="5",
        description="同一 IP 最大登录失败次数",
        category="security",
        value_type="number",
    ),
    SystemSettingCreate(
        key="security.lockout_duration_minutes",
        value="30",
        description="登录失败超过阈值后的锁定时间（分钟）",
        category="security",
        value_type="number",
    ),
    # ── Audit ──
    SystemSettingCreate(
        key="audit.retention_days",
        value="30",
        description="审计日志保留天数（过期自动清理）",
        category="audit",
        value_type="number",
    ),
]


async def _ensure_default_settings(db: AsyncSession) -> None:
    """Create default settings if they don't exist."""
    for item in DEFAULT_SETTINGS:
        result = await db.execute(select(SystemSetting).where(SystemSetting.key == item.key))
        if not result.scalar_one_or_none():
            setting = SystemSetting(**item.model_dump())
            db.add(setting)
    await db.commit()


def _config_to_response(config: LLMProviderConfig) -> dict[str, Any]:
    """Build a response dict with masked API key."""
    decrypted = decrypt_value(config.api_key_encrypted)
    return {
        "id": config.id,
        "provider": config.provider,
        "platform": config.platform,
        "name": config.name,
        "base_url": config.base_url,
        "default_model": config.default_model,
        "model_type": config.model_type,
        "is_active": config.is_active,
        "is_default": config.is_default,
        "api_key_masked": mask_api_key(decrypted),
        "created_at": config.created_at,
        "updated_at": config.updated_at,
    }


# ─── LLM Provider Configs ──────────────────────────────────────


@router.get("/llm-providers", response_model=list[LLMProviderConfigResponse])
async def list_llm_providers(
    platform: Annotated[str | None, Query(description="Filter by platform (web/miniapp/ios/android)")] = None,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List all LLM provider configurations, optionally filtered by platform."""
    stmt = select(LLMProviderConfig).order_by(LLMProviderConfig.provider)
    if platform:
        stmt = stmt.where(LLMProviderConfig.platform == platform.strip().lower())
    result = await db.execute(stmt)
    return [_config_to_response(c) for c in result.scalars().all()]


@router.post(
    "/llm-providers",
    response_model=LLMProviderConfigResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_llm_provider(
    data: LLMProviderConfigCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create a new LLM provider configuration.

    The API key is encrypted before storage.
    """
    # Check (provider, platform, model_type) uniqueness
    existing = await db.execute(
        select(LLMProviderConfig).where(
            LLMProviderConfig.provider == data.provider,
            LLMProviderConfig.platform == data.platform,
            LLMProviderConfig.model_type == data.model_type,
        )
    )
    if existing.scalar_one_or_none():
        platform_label = data.platform or "global"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Provider '{data.provider}' for platform '{platform_label}' with model type '{data.model_type}' already exists",
        )

    # Encrypt API key before storage
    encrypted_key = encrypt_value(data.api_key)

    if data.is_default:
        stmt = select(LLMProviderConfig).where(
            LLMProviderConfig.is_default == True,
            LLMProviderConfig.platform == data.platform,
            LLMProviderConfig.model_type == data.model_type,
        )
        result = await db.execute(stmt)
        for conf in result.scalars():
            conf.is_default = False

    config = LLMProviderConfig(
        provider=data.provider,
        platform=data.platform,
        name=data.name,
        base_url=data.base_url,
        api_key_encrypted=encrypted_key,
        default_model=data.default_model,
        model_type=data.model_type,
        is_active=data.is_active,
        is_default=data.is_default,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)

    # Record audit log
    await AuditService.record(
        db,
        action=AuditActionType.LLM_CONFIG_CREATE,
        user_id=str(current_user.id),
        user_email=current_user.email,
        user_role=current_user.role.value,
        resource_type=AuditResourceType.LLM_PROVIDER,
        resource_id=str(config.id),
        details={"provider": config.provider, "model_type": config.model_type, "name": config.name},
    )
    await db.commit()

    return _config_to_response(config)


@router.get("/llm-providers/{provider_id}", response_model=LLMProviderConfigResponse)
async def get_llm_provider(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get a specific LLM provider configuration."""
    result = await db.execute(
        select(LLMProviderConfig).where(LLMProviderConfig.id == provider_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider config '{provider_id}' not found",
        )
    return _config_to_response(config)


@router.patch("/llm-providers/{provider_id}", response_model=LLMProviderConfigResponse)
async def update_llm_provider(
    provider_id: str,
    data: LLMProviderConfigUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Update an LLM provider configuration.

    If api_key is provided, it is encrypted before storage.
    """
    result = await db.execute(
        select(LLMProviderConfig).where(LLMProviderConfig.id == provider_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider config '{provider_id}' not found",
        )

    update_data = data.model_dump(exclude_unset=True)
    if "api_key" in update_data:
        # Encrypt new API key
        new_key = update_data.pop("api_key")
        if new_key:
            config.api_key_encrypted = encrypt_value(new_key)

    for field, value in update_data.items():
        setattr(config, field, value)

    await db.commit()
    await db.refresh(config)

    # Record audit log
    await AuditService.record(
        db,
        action=AuditActionType.LLM_CONFIG_UPDATE,
        user_id=str(current_user.id),
        user_email=current_user.email,
        user_role=current_user.role.value,
        resource_type=AuditResourceType.LLM_PROVIDER,
        resource_id=provider_id,
        details={"provider": config.provider, "model_type": config.model_type, "fields_updated": list(update_data.keys())},
    )
    await db.commit()

    return _config_to_response(config)


@router.delete("/llm-providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_llm_provider(
    provider_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an LLM provider configuration."""
    result = await db.execute(
        select(LLMProviderConfig).where(LLMProviderConfig.id == provider_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider config '{provider_id}' not found",
        )
    provider_name = config.provider
    model_type = config.model_type
    await db.delete(config)
    await db.commit()

    # Record audit log
    await AuditService.record(
        db,
        action=AuditActionType.LLM_CONFIG_DELETE,
        user_id=str(current_user.id),
        user_email=current_user.email,
        user_role=current_user.role.value,
        resource_type=AuditResourceType.LLM_PROVIDER,
        resource_id=provider_id,
        details={"provider": provider_name, "model_type": model_type},
    )
    await db.commit()


# ─── LLM Provider Testing ───────────────────────────────────────────────


@router.post("/llm-providers/{provider_id}/test")
async def test_llm_provider(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Test LLM provider connectivity by listing models."""
    result = await db.execute(
        select(LLMProviderConfig).where(LLMProviderConfig.id == provider_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider config '{provider_id}' not found",
        )
    try:
        service = LLMService(provider=config.provider, platform=config.platform, db=db)
        result = await service.health_check()
        return {
            "provider": config.provider,
            "platform": config.platform or "global",
            "status": result.get("status", "unknown"),
            "detail": result.get("detail") if result.get("status") != "ok" else None,
            "available_models": result.get("available_models", []),
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Provider test failed: {e}",
        )


# ─── System Settings ───────────────────────────────────────────


@router.get("/settings", response_model=list[SystemSettingResponse])
async def list_settings(
    category: Annotated[str | None, Query(description="Filter by category (general/auth/diagnosis/agent/notification/security)")] = None,
    db: AsyncSession = Depends(get_db),
) -> list[SystemSetting]:
    """List all system settings, optionally filtered by category.

    Automatically creates default settings on first access.
    """
    await _ensure_default_settings(db)
    stmt = select(SystemSetting).order_by(SystemSetting.category, SystemSetting.key)
    if category:
        stmt = stmt.where(SystemSetting.category == category.strip().lower())
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post(
    "/settings",
    response_model=SystemSettingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_setting(
    data: SystemSettingCreate,
    db: AsyncSession = Depends(get_db),
) -> SystemSetting:
    """Create a system setting."""
    existing = await db.execute(
        select(SystemSetting).where(SystemSetting.key == data.key)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Setting '{data.key}' already exists",
        )

    setting = SystemSetting(**data.model_dump())
    db.add(setting)
    await db.commit()
    await db.refresh(setting)
    return setting


# ─── Batch Settings ───────────────────────────────────────────────────
# NOTE: Must be defined BEFORE dynamic routes like /settings/{key}
#       so FastAPI matches /settings/batch first.


@router.patch("/settings/batch", response_model=list[SystemSettingResponse])
async def batch_update_settings(
    req: BatchSettingsRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[SystemSetting]:
    """Batch create or update system settings.

    If a key exists, it is updated; otherwise it is created.
    """
    await _ensure_default_settings(db)
    updated: list[SystemSetting] = []
    for item in req.items:
        result = await db.execute(select(SystemSetting).where(SystemSetting.key == item.key))
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = item.value
            if item.description is not None:
                setting.description = item.description
            if item.is_sensitive is not None:
                setting.is_sensitive = item.is_sensitive
            if item.category is not None:
                setting.category = item.category
            if item.value_type is not None:
                setting.value_type = item.value_type
            if item.options is not None:
                setting.options = item.options
        else:
            setting = SystemSetting(**item.model_dump())
            db.add(setting)
        updated.append(setting)

    await db.commit()
    for s in updated:
        await db.refresh(s)

    # Record audit log
    await AuditService.record(
        db,
        action=AuditActionType.SETTINGS_CHANGE,
        user_id=str(current_user.id),
        user_email=current_user.email,
        user_role=current_user.role.value,
        resource_type=AuditResourceType.SYSTEM_SETTING,
        details={"keys_updated": [item.key for item in req.items]},
    )
    await db.commit()

    return updated


@router.get("/settings/{key}", response_model=SystemSettingResponse)
async def get_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
) -> SystemSetting:
    """Get a specific system setting."""
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting '{key}' not found",
        )
    return setting


@router.patch("/settings/{key}", response_model=SystemSettingResponse)
async def update_setting(
    key: str,
    data: SystemSettingUpdate,
    db: AsyncSession = Depends(get_db),
) -> SystemSetting:
    """Update a system setting."""
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting '{key}' not found",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(setting, field, value)

    await db.commit()
    await db.refresh(setting)
    return setting


@router.delete("/settings/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a system setting."""
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting '{key}' not found",
        )
    await db.delete(setting)
    await db.commit()


# ─── Dashboard Stats ───────────────────────────────────────────────────────


@router.get("/dashboard/stats")
async def dashboard_stats(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return admin dashboard statistics."""
    from sqlalchemy import func

    # User counts by role
    user_counts = {}
    for role in UserRole:
        count_result = await db.execute(
            select(func.count(User.id)).where(User.role == role)
        )
        user_counts[role.value] = count_result.scalar() or 0

    # Total users
    total_users = sum(user_counts.values())

    # Provider configs
    provider_result = await db.execute(select(func.count(LLMProviderConfig.id)))
    provider_count = provider_result.scalar() or 0

    active_providers = await db.execute(
        select(func.count(LLMProviderConfig.id)).where(LLMProviderConfig.is_active == True)
    )
    active_provider_count = active_providers.scalar() or 0

    # System settings
    settings_result = await db.execute(select(func.count(SystemSetting.id)))
    settings_count = settings_result.scalar() or 0

    return {
        "users": {
            "total": total_users,
            "by_role": user_counts,
        },
        "llm_providers": {
            "total": provider_count,
            "active": active_provider_count,
        },
        "system_settings": settings_count,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ─── User Management ────────────────────────────────────────────


@router.get("/users", response_model=list[UserListItem])
async def list_users(
    role: Annotated[str | None, Query(description="Filter by role (patient/doctor/admin)")] = None,
    status: Annotated[str | None, Query(description="Filter by status (active/inactive/pending)")] = None,
    search: Annotated[str | None, Query(description="Search by email or full_name", max_length=100)] = None,
    skip: Annotated[int, Query(ge=0, description="Number of records to skip")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Max records to return")] = 50,
    db: AsyncSession = Depends(get_db),
) -> list[User]:
    """List all users with optional filtering, search, and pagination."""
    stmt = select(User).order_by(User.created_at.desc())

    if role:
        stmt = stmt.where(User.role == role.strip().lower())
    if status:
        stmt = stmt.where(User.status == status.strip().lower())
    if search:
        search_term = f"%{search.strip()}%"
        stmt = stmt.where(
            (User.email.ilike(search_term)) | (User.full_name.ilike(search_term))
        )

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/users/{user_id}", response_model=UserListItem)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get a specific user by ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found",
        )
    return user


@router.patch("/users/{user_id}", response_model=UserListItem)
async def update_user(
    user_id: str,
    data: UserAdminUpdate,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Update a user (admin only).

    Allows modifying status, verification, and doctor-specific fields.
    Does NOT allow changing role or password — use dedicated endpoints.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found",
        )

    # Prevent modifying the last admin's status
    if user.role == UserRole.ADMIN and data.status is not None and data.status != "active":
        # Count active admins
        from sqlalchemy import func as sql_func
        admin_count = await db.execute(
            select(sql_func.count(User.id)).where(
                User.role == UserRole.ADMIN, User.status == "active"
            )
        )
        if (admin_count.scalar() or 0) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate the only active admin account",
            )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return user


# ─── Doctor Verification ──────────────────────────────────────


@router.get("/doctors", response_model=list[UserListItem])
async def list_doctors(
    is_verified: Annotated[bool | None, Query(description="Filter by verification status")] = None,
    status: Annotated[str | None, Query(description="Filter by account status (active/inactive/pending)")] = None,
    search: Annotated[str | None, Query(description="Search by email or full_name", max_length=100)] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    db: AsyncSession = Depends(get_db),
) -> list[User]:
    """List all doctor users with optional filtering and search."""
    stmt = select(User).where(User.role == UserRole.DOCTOR).order_by(User.created_at.desc())

    if is_verified is not None:
        stmt = stmt.where(User.is_verified == is_verified)
    if status:
        stmt = stmt.where(User.status == status.strip().lower())
    if search:
        search_term = f"%{search.strip()}%"
        stmt = stmt.where(
            (User.email.ilike(search_term)) | (User.full_name.ilike(search_term))
        )

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/doctors/{doctor_id}/verify", response_model=UserListItem)
async def verify_doctor(
    doctor_id: str,
    data: DoctorVerifyRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Approve or reject a doctor's verification application."""
    result = await db.execute(
        select(User).where(User.id == doctor_id, User.role == UserRole.DOCTOR)
    )
    doctor = result.scalar_one_or_none()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )

    previous_verified = doctor.is_verified
    if data.action == "approve":
        doctor.is_verified = True
        doctor.status = "active"
        audit_action = AuditActionType.DOCTOR_VERIFY
    else:
        doctor.is_verified = False
        doctor.status = "inactive"
        audit_action = AuditActionType.DOCTOR_REJECT

    await db.commit()
    await db.refresh(doctor)

    # Record audit log
    await AuditService.record(
        db,
        action=audit_action,
        user_id=str(current_user.id),
        user_email=current_user.email,
        user_role=current_user.role.value,
        resource_type=AuditResourceType.DOCTOR,
        resource_id=doctor_id,
        details={
            "doctor_email": doctor.email,
            "doctor_name": doctor.name,
            "action": data.action,
            "reason": data.reason,
            "previous_verified": previous_verified,
        },
    )
    await db.commit()

    return doctor


# ─── Knowledge Base Management ─────────────────────────────────

from app.models.rag import Document, DocumentReview, ReviewStatus
from app.schemas.config import (
    DocumentAdminCreate,
    DocumentAdminUpdate,
    DocumentDetail,
    DocumentListItem,
    DocumentReviewAction,
    DocumentReviewItem,
    ReviewQueueItem,
)


@router.get("/knowledge", response_model=list[DocumentListItem])
async def list_documents(
    doc_type: Annotated[str | None, Query(description="Filter by doc_type")] = None,
    status: Annotated[str | None, Query(description="Filter by review_status")] = None,
    search: Annotated[str | None, Query(description="Search by title", max_length=100)] = None,
    is_active: Annotated[bool | None, Query(description="Filter by is_active")] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    db: AsyncSession = Depends(get_db),
) -> list[Document]:
    """List knowledge base documents with filtering and pagination."""
    stmt = select(Document).order_by(Document.created_at.desc())

    if doc_type:
        stmt = stmt.where(Document.doc_type == doc_type)
    if status:
        stmt = stmt.where(Document.review_status == status)
    if is_active is not None:
        stmt = stmt.where(Document.is_active == is_active)
    if search:
        search_term = f"%{search.strip()}%"
        stmt = stmt.where(Document.title.ilike(search_term))

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/knowledge/{doc_id}", response_model=DocumentDetail)
async def get_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
) -> Document:
    """Get a specific document by ID."""
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_id}' not found",
        )
    return doc


@router.post("/knowledge", response_model=DocumentDetail, status_code=status.HTTP_201_CREATED)
async def create_document_admin(
    data: DocumentAdminCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> Document:
    """Create a new knowledge document (admin only).

    Automatically chunks and indexes the content.
    """
    from app.services.rag import RAGService

    service = RAGService(db)
    doc = await service.create_document(
        title=data.title,
        content=data.content,
        doc_type=data.doc_type,
        source_url=data.source_url,
        department=data.department,
        disease_tags=data.disease_tags,
        drug_name=data.drug_name,
        language=data.language,
    )
    # Update admin-specific fields
    doc.is_featured = data.is_featured
    doc.source_type = "admin_upload"
    await db.commit()
    await db.refresh(doc)

    # Record audit log
    await AuditService.record(
        db,
        action=AuditActionType.DOCUMENT_CREATE,
        user_id=str(current_user.id) if current_user else None,
        user_email=current_user.email if current_user else None,
        user_role=current_user.role.value if current_user else None,
        resource_type=AuditResourceType.DOCUMENT,
        resource_id=str(doc.id),
        details={"title": doc.title, "doc_type": doc.doc_type.value},
    )
    await db.commit()

    return doc


@router.patch("/knowledge/{doc_id}", response_model=DocumentDetail)
async def update_document_admin(
    doc_id: str,
    data: DocumentAdminUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> Document:
    """Update a knowledge document (admin only)."""
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_id}' not found",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(doc, field, value)

    doc.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(doc)

    # Record audit log
    await AuditService.record(
        db,
        action=AuditActionType.DOCUMENT_UPDATE,
        user_id=str(current_user.id),
        user_email=current_user.email,
        user_role=current_user.role.value,
        resource_type=AuditResourceType.DOCUMENT,
        resource_id=doc_id,
        details={"title": doc.title, "doc_type": doc.doc_type.value, "fields_updated": list(update_data.keys())},
    )
    await db.commit()

    return doc


@router.delete("/knowledge/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document_admin(
    doc_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a knowledge document (admin only)."""
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_id}' not found",
        )
    doc_title = doc.title
    doc_type = doc.doc_type.value
    await db.delete(doc)
    await db.commit()

    # Record audit log
    await AuditService.record(
        db,
        action=AuditActionType.DOCUMENT_DELETE,
        user_id=str(current_user.id),
        user_email=current_user.email,
        user_role=current_user.role.value,
        resource_type=AuditResourceType.DOCUMENT,
        resource_id=doc_id,
        details={"title": doc_title, "doc_type": doc_type},
    )
    await db.commit()


@router.patch("/knowledge/{doc_id}/toggle")
async def toggle_document_active(
    doc_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Toggle document active status."""
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_id}' not found",
        )
    doc.is_active = not doc.is_active
    await db.commit()
    await db.refresh(doc)

    # Record audit log
    await AuditService.record(
        db,
        action=AuditActionType.DOCUMENT_TOGGLE,
        user_id=str(current_user.id),
        user_email=current_user.email,
        user_role=current_user.role.value,
        resource_type=AuditResourceType.DOCUMENT,
        resource_id=doc_id,
        details={"title": doc.title, "new_is_active": doc.is_active},
    )
    await db.commit()

    return {"id": str(doc.id), "is_active": doc.is_active}


# ─── Document Review Queue ─────────────────────────────────


@router.get("/knowledge/reviews", response_model=list[ReviewQueueItem])
async def list_review_queue(
    status: Annotated[str | None, Query(description="Filter by review_status")] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    db: AsyncSession = Depends(get_db),
) -> list[Document]:
    """List documents in the review queue.

    By default shows agent_reviewed documents awaiting doctor review.
    """
    stmt = select(Document).where(
        Document.doc_type == DocType.CASE_REPORT
    ).order_by(Document.created_at.desc())

    if status:
        stmt = stmt.where(Document.review_status == status)
    else:
        # Default: show pending and agent_reviewed
        stmt = stmt.where(Document.review_status.in_([ReviewStatus.PENDING, ReviewStatus.AGENT_REVIEWED]))

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/knowledge/reviews/{doc_id}/history", response_model=list[DocumentReviewItem])
async def get_document_review_history(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[DocumentReview]:
    """Get review history for a specific document."""
    result = await db.execute(
        select(DocumentReview).where(DocumentReview.document_id == doc_id)
        .order_by(DocumentReview.reviewed_at.desc())
    )
    return list(result.scalars().all())


@router.post("/knowledge/reviews/{doc_id}")
async def review_document(
    doc_id: str,
    data: DocumentReviewAction,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Submit a review decision for a document (admin or doctor).

    Actions: approve, reject, request_revision
    """
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_id}' not found",
        )

    previous_status = doc.review_status.value
    # Update document review status
    if data.action == "approve":
        doc.review_status = ReviewStatus.APPROVED
        doc.is_active = True
    elif data.action == "reject":
        doc.review_status = ReviewStatus.REJECTED
        doc.is_active = False
    elif data.action == "request_revision":
        doc.review_status = ReviewStatus.REVISION_REQUESTED

    # Create review log
    review = DocumentReview(
        document_id=doc.id,
        reviewer_type="admin",  # TODO: detect doctor vs admin from current_user
        action=data.action,
        score=data.score,
        comments=data.comments,
    )
    review.reviewer_id = current_user.id
    db.add(review)
    await db.commit()
    await db.refresh(doc)

    # Record audit log
    await AuditService.record(
        db,
        action=AuditActionType.DOCUMENT_REVIEW,
        user_id=str(current_user.id),
        user_email=current_user.email,
        user_role=current_user.role.value,
        resource_type=AuditResourceType.DOCUMENT,
        resource_id=doc_id,
        details={
            "title": doc.title,
            "action": data.action,
            "score": data.score,
            "previous_status": previous_status,
        },
    )
    await db.commit()

    return {
        "id": str(doc.id),
        "review_status": doc.review_status.value,
        "action": data.action,
        "message": f"Document {data.action}d successfully",
    }


# ─── Audit Logs ─────────────────────────────────────────────────────────────────────────


@router.get("/audit-logs", response_model=list[AuditLogListItem])
async def list_audit_logs(
    action: Annotated[str | None, Query(description="Filter by action type")] = None,
    user_id: Annotated[str | None, Query(description="Filter by user UUID")] = None,
    resource_type: Annotated[str | None, Query(description="Filter by resource type")] = None,
    date_from: Annotated[datetime | None, Query(description="Start date (ISO 8601)")] = None,
    date_to: Annotated[datetime | None, Query(description="End date (ISO 8601)")] = None,
    success: Annotated[bool | None, Query(description="Filter by success status")] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    db: AsyncSession = Depends(get_db),
) -> list[AuditLog]:
    """List audit logs with filtering and pagination.

    Only admin operations are logged — patient-side operations are
    intentionally excluded for privacy protection.
    """
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc())

    if action:
        stmt = stmt.where(AuditLog.action == action)
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if resource_type:
        stmt = stmt.where(AuditLog.resource_type == resource_type)
    if date_from:
        stmt = stmt.where(AuditLog.created_at >= date_from)
    if date_to:
        stmt = stmt.where(AuditLog.created_at <= date_to)
    if success is not None:
        stmt = stmt.where(AuditLog.success == success)

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/audit-logs/{log_id}", response_model=AuditLogDetail)
async def get_audit_log(
    log_id: str,
    db: AsyncSession = Depends(get_db),
) -> AuditLog:
    """Get a single audit log entry with full details."""
    result = await db.execute(select(AuditLog).where(AuditLog.id == log_id))
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit log '{log_id}' not found",
        )
    return log


@router.get("/audit-logs/stats/overview", response_model=AuditLogStats)
async def audit_log_stats(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get audit log statistics for the dashboard."""
    from sqlalchemy import func

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)

    # Total today
    total_today_result = await db.execute(
        select(func.count(AuditLog.id)).where(AuditLog.created_at >= today_start)
    )
    total_today = total_today_result.scalar() or 0

    # Total week
    total_week_result = await db.execute(
        select(func.count(AuditLog.id)).where(AuditLog.created_at >= week_start)
    )
    total_week = total_week_result.scalar() or 0

    # Failed today
    failed_today_result = await db.execute(
        select(func.count(AuditLog.id)).where(
            AuditLog.created_at >= today_start,
            AuditLog.success == False,
        )
    )
    failed_today = failed_today_result.scalar() or 0

    # Action breakdown (today)
    action_result = await db.execute(
        select(AuditLog.action, func.count(AuditLog.id))
        .where(AuditLog.created_at >= today_start)
        .group_by(AuditLog.action)
        .order_by(func.count(AuditLog.id).desc())
    )
    action_breakdown = [
        {"action": action, "count": count}
        for action, count in action_result.all()
    ]

    return {
        "total_today": total_today,
        "total_week": total_week,
        "failed_today": failed_today,
        "action_breakdown": action_breakdown,
    }
