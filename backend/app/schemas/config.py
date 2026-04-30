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


# ─── User Management (Admin) ─────────────────────────────

class UserListItem(BaseModel):
    """Simplified user item for admin list view."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role: str
    status: str
    is_verified: bool
    license_number: str | None
    hospital: str | None
    department: str | None
    title: str | None
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None


class UserAdminUpdate(BaseModel):
    """Admin update user request."""

    full_name: str | None = Field(None, min_length=1, max_length=255)
    status: str | None = Field(None, pattern=r"^(active|inactive|pending)$")
    is_verified: bool | None = None
    license_number: str | None = Field(None, max_length=100)
    hospital: str | None = Field(None, max_length=255)
    department: str | None = Field(None, max_length=100)
    title: str | None = Field(None, max_length=50)


class DoctorVerifyRequest(BaseModel):
    """Doctor verification approval / rejection request."""

    action: str = Field(..., pattern=r"^(approve|reject)$")
    reason: str | None = Field(None, max_length=500)


# ─── Knowledge Base (Document) ──────────────────────────────

class DocumentListItem(BaseModel):
    """Simplified document for admin list view."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    doc_type: str
    source_type: str | None
    review_status: str
    department: str | None
    disease_tags: list[str] | None
    drug_name: str | None
    is_active: bool
    is_featured: bool
    chunk_count: int
    vectorized_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DocumentDetail(DocumentListItem):
    """Full document detail including content."""

    content: str
    source_url: str | None
    uploaded_by: uuid.UUID | None
    reviewed_by: uuid.UUID | None
    agent_review_score: float | None
    agent_review_notes: str | None
    embedding_model: str | None


class DocumentAdminCreate(BaseModel):
    """Admin create document request."""

    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=10)
    doc_type: str = Field(default="platform_guideline", pattern=r"^(platform_guideline|case_report|drug_reference)$")
    source_url: str | None = Field(None, max_length=1000)
    department: str | None = Field(None, max_length=100)
    disease_tags: list[str] = Field(default_factory=list)
    drug_name: str | None = Field(None, max_length=200)
    language: str = "zh"
    is_featured: bool = False


class DocumentAdminUpdate(BaseModel):
    """Admin update document request."""

    title: str | None = Field(None, min_length=1, max_length=500)
    content: str | None = Field(None, min_length=10)
    doc_type: str | None = Field(None, pattern=r"^(platform_guideline|case_report|drug_reference)$")
    source_url: str | None = Field(None, max_length=1000)
    department: str | None = Field(None, max_length=100)
    disease_tags: list[str] | None = None
    drug_name: str | None = Field(None, max_length=200)
    language: str | None = None
    is_active: bool | None = None
    is_featured: bool | None = None


class DocumentReviewItem(BaseModel):
    """Document review log item."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    reviewer_type: str
    reviewer_id: uuid.UUID | None
    action: str
    score: float | None
    comments: str | None
    reviewed_at: datetime


class DocumentReviewAction(BaseModel):
    """Admin/doctor review action request."""

    action: str = Field(..., pattern=r"^(approve|reject|request_revision)$")
    comments: str | None = Field(None, max_length=2000)
    score: float | None = Field(None, ge=0, le=100)


class ReviewQueueItem(BaseModel):
    """Item in the review queue (agent-reviewed documents awaiting doctor review)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    doc_type: str
    review_status: str
    agent_review_score: float | None
    agent_review_notes: str | None
    uploaded_by: uuid.UUID | None
    created_at: datetime
