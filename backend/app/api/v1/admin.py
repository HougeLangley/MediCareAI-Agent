"""Admin configuration endpoints.

Manage LLM provider configs and system settings.
Requires admin role.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
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

# ─── LLM Provider Configs ──────────────────────────────────────


@router.get("/llm-providers", response_model=list[LLMProviderConfigResponse])
async def list_llm_providers(
    db: AsyncSession = Depends(get_db),
) -> list[LLMProviderConfig]:
    """List all LLM provider configurations."""
    result = await db.execute(
        select(LLMProviderConfig).order_by(LLMProviderConfig.provider)
    )
    return list(result.scalars().all())


@router.post(
    "/llm-providers",
    response_model=LLMProviderConfigResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_llm_provider(
    data: LLMProviderConfigCreate,
    db: AsyncSession = Depends(get_db),
) -> LLMProviderConfig:
    """Create a new LLM provider configuration."""
    existing = await db.execute(
        select(LLMProviderConfig).where(LLMProviderConfig.provider == data.provider)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Provider '{data.provider}' already exists",
        )

    if data.is_default:
        await db.execute(
            select(LLMProviderConfig).where(LLMProviderConfig.is_default == True)
        )
        for conf in (await db.execute(select(LLMProviderConfig))).scalars():
            conf.is_default = False

    config = LLMProviderConfig(**data.model_dump())
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return config


@router.get("/llm-providers/{provider}", response_model=LLMProviderConfigResponse)
async def get_llm_provider(
    provider: str,
    db: AsyncSession = Depends(get_db),
) -> LLMProviderConfig:
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
    return config


@router.patch("/llm-providers/{provider}", response_model=LLMProviderConfigResponse)
async def update_llm_provider(
    provider: str,
    data: LLMProviderConfigUpdate,
    db: AsyncSession = Depends(get_db),
) -> LLMProviderConfig:
    """Update an LLM provider configuration."""
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
    for field, value in update_data.items():
        setattr(config, field, value)

    await db.commit()
    await db.refresh(config)
    return config


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
