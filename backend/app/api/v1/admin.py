"""Admin configuration endpoints.

Manage LLM provider configs and system settings.
Requires admin role.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.core.encryption import decrypt_value, encrypt_value, mask_api_key
from app.db.session import get_db
from app.models.config import LLMProviderConfig, SystemSetting
from app.models.user import UserRole
from app.schemas.config import (
    LLMProviderConfigCreate,
    LLMProviderConfigResponse,
    LLMProviderConfigUpdate,
    SystemSettingCreate,
    SystemSettingResponse,
    SystemSettingUpdate,
)

router = APIRouter(dependencies=[Depends(require_role(UserRole.ADMIN))])


def _config_to_response(config: LLMProviderConfig) -> dict[str, Any]:
    """Build a response dict with masked API key."""
    decrypted = decrypt_value(config.api_key_encrypted)
    return {
        "id": config.id,
        "provider": config.provider,
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
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List all LLM provider configurations."""
    result = await db.execute(
        select(LLMProviderConfig).order_by(LLMProviderConfig.provider)
    )
    return [_config_to_response(c) for c in result.scalars().all()]


@router.post(
    "/llm-providers",
    response_model=LLMProviderConfigResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_llm_provider(
    data: LLMProviderConfigCreate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create a new LLM provider configuration.

    The API key is encrypted before storage.
    """
    existing = await db.execute(
        select(LLMProviderConfig).where(LLMProviderConfig.provider == data.provider)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Provider '{data.provider}' already exists",
        )

    # Encrypt API key before storage
    encrypted_key = encrypt_value(data.api_key)

    if data.is_default:
        stmt = select(LLMProviderConfig).where(LLMProviderConfig.is_default == True)
        result = await db.execute(stmt)
        for conf in result.scalars():
            conf.is_default = False

    config = LLMProviderConfig(
        provider=data.provider,
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
    return _config_to_response(config)


@router.get("/llm-providers/{provider}", response_model=LLMProviderConfigResponse)
async def get_llm_provider(
    provider: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get a specific LLM provider configuration."""
    result = await db.execute(
        select(LLMProviderConfig).where(LLMProviderConfig.provider == provider)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{provider}' not found",
        )
    return _config_to_response(config)


@router.patch("/llm-providers/{provider}", response_model=LLMProviderConfigResponse)
async def update_llm_provider(
    provider: str,
    data: LLMProviderConfigUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Update an LLM provider configuration.

    If api_key is provided, it is encrypted before storage.
    """
    result = await db.execute(
        select(LLMProviderConfig).where(LLMProviderConfig.provider == provider)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{provider}' not found",
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
    return _config_to_response(config)


@router.delete("/llm-providers/{provider}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_llm_provider(
    provider: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an LLM provider configuration."""
    result = await db.execute(
        select(LLMProviderConfig).where(LLMProviderConfig.provider == provider)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{provider}' not found",
        )
    await db.delete(config)
    await db.commit()


# ─── System Settings ───────────────────────────────────────────


@router.get("/settings", response_model=list[SystemSettingResponse])
async def list_settings(
    db: AsyncSession = Depends(get_db),
) -> list[SystemSetting]:
    """List all system settings."""
    result = await db.execute(select(SystemSetting).order_by(SystemSetting.key))
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
