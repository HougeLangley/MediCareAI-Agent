"""Configuration management schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LLMProviderConfigBase(BaseModel):
    """Base LLM provider config schema."""

    provider: str = Field(..., min_length=1, max_length=50)
    # NULL = global; otherwise web/miniapp/ios/android
    platform: str | None = Field(default=None, max_length=20)
    name: str = Field(..., min_length=1, max_length=100)
    base_url: str = Field(..., max_length=500)
    default_model: str = Field(..., min_length=1, max_length=100)
    model_type: str = Field(default="diagnosis", max_length=50)
    is_active: bool = True
    is_default: bool = False


class LLMProviderConfigCreate(LLMProviderConfigBase):
    """Create LLM provider config.

    api_key is accepted in plaintext and encrypted before storage.
    """

    api_key: str = Field(..., min_length=1)


class LLMProviderConfigUpdate(BaseModel):
    """Update LLM provider config."""

    name: str | None = Field(None, max_length=100)
    base_url: str | None = Field(None, max_length=500)
    api_key: str | None = None
    default_model: str | None = Field(None, max_length=100)
    model_type: str | None = Field(None, max_length=50)
    platform: str | None = Field(None, max_length=20)
    is_active: bool | None = None
    is_default: bool | None = None


class LLMProviderConfigResponse(LLMProviderConfigBase):
    """LLM provider config response (API key masked)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    api_key_masked: str = "***"
    created_at: datetime
    updated_at: datetime


class SystemSettingBase(BaseModel):
    """Base system setting schema."""

    key: str = Field(..., min_length=1, max_length=100)
    value: str = Field(..., min_length=1)
    description: str | None = None
    is_sensitive: bool = False
    category: str = Field(default="general", max_length=50)
    value_type: str = Field(default="string", max_length=20)
    options: str | None = None


class SystemSettingCreate(SystemSettingBase):
    """Create system setting."""
    pass


class SystemSettingUpdate(BaseModel):
    """Update system setting."""

    value: str | None = None
    description: str | None = None
    is_sensitive: bool | None = None
    category: str | None = Field(None, max_length=50)
    value_type: str | None = Field(None, max_length=20)
    options: str | None = None


class SystemSettingResponse(SystemSettingBase):
    """System setting response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class BatchSettingsRequest(BaseModel):
    """Batch update system settings request."""

    items: list[SystemSettingCreate]
