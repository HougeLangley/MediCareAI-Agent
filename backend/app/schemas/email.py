"""Email management schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.email import EmailSendStatus, SmtpSecurity


# =============================================================================
# Email Configuration
# =============================================================================

class EmailConfigBase(BaseModel):
    """Base email config schema."""

    smtp_host: str = Field(..., min_length=1, max_length=255)
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_user: str = Field(..., min_length=1, max_length=255)
    smtp_from_email: str = Field(..., min_length=1, max_length=255)
    smtp_from_name: str = Field(default="MediCareAI-Agent", max_length=255)
    smtp_security: SmtpSecurity = SmtpSecurity.STARTTLS
    description: str | None = Field(default=None)


class EmailConfigCreate(EmailConfigBase):
    """Create email config."""

    smtp_password: str = Field(..., min_length=1)
    is_default: bool = False


class EmailConfigUpdate(BaseModel):
    """Update email config."""

    smtp_host: str | None = Field(default=None, max_length=255)
    smtp_port: int | None = Field(default=None, ge=1, le=65535)
    smtp_user: str | None = Field(default=None, max_length=255)
    smtp_password: str | None = Field(default=None)
    smtp_from_email: str | None = Field(default=None, max_length=255)
    smtp_from_name: str | None = Field(default=None, max_length=255)
    smtp_security: SmtpSecurity | None = None
    is_active: bool | None = None
    is_default: bool | None = None
    description: str | None = None


class EmailConfigResponse(BaseModel):
    """Email config response (password never exposed)."""

    id: uuid.UUID
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_from_email: str
    smtp_from_name: str
    smtp_security: SmtpSecurity
    is_active: bool
    is_default: bool
    test_status: str
    test_message: str | None
    tested_at: datetime | None
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmailConfigListResponse(BaseModel):
    """List response."""

    items: list[EmailConfigResponse]
    total: int


class EmailConfigTestRequest(BaseModel):
    """Test email config request."""

    test_email: str = Field(..., min_length=1, max_length=255)


class EmailConfigTestResponse(BaseModel):
    """Test result."""

    success: bool
    message: str


class EmailServiceStatus(BaseModel):
    """Current email service status."""

    is_available: bool
    config_source: str
    smtp_host: str | None
    smtp_port: int | None
    smtp_user: str | None
    from_email: str | None
    from_name: str | None
    smtp_security: SmtpSecurity | None


# =============================================================================
# Email Template
# =============================================================================

class EmailTemplateBase(BaseModel):
    """Base template schema."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    subject: str = Field(..., min_length=1, max_length=255)
    html_body: str = Field(..., min_length=1)
    text_body: str | None = None
    variables: str | None = Field(default=None, max_length=512)
    is_active: bool = True


class EmailTemplateCreate(EmailTemplateBase):
    pass


class EmailTemplateUpdate(BaseModel):
    """Update template."""

    name: str | None = Field(default=None, max_length=100)
    description: str | None = None
    subject: str | None = Field(default=None, max_length=255)
    html_body: str | None = None
    text_body: str | None = None
    variables: str | None = Field(default=None, max_length=512)
    is_active: bool | None = None


class EmailTemplateResponse(EmailTemplateBase):
    """Template response."""

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmailTemplateListResponse(BaseModel):
    """Template list."""

    items: list[EmailTemplateResponse]
    total: int


# =============================================================================
# Email Log
# =============================================================================

class EmailLogResponse(BaseModel):
    """Email send log entry."""

    id: uuid.UUID
    config_id: uuid.UUID | None
    template_id: uuid.UUID | None
    recipient_email: str
    subject: str
    body_preview: str | None
    status: EmailSendStatus
    retry_count: int
    error_message: str | None
    sent_at: datetime | None
    failed_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmailLogListResponse(BaseModel):
    """Paginated log list."""

    items: list[EmailLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class EmailSendRequest(BaseModel):
    """Send email via template (admin)."""

    template_id: uuid.UUID
    recipient_email: str = Field(..., min_length=1, max_length=255)
    variables: dict[str, str] = Field(default_factory=dict)


class EmailSendResponse(BaseModel):
    """Send response."""

    success: bool
    log_id: uuid.UUID | None
    message: str


# =============================================================================
# Email Provider Presets
# =============================================================================

class SmtpPresetConfig(BaseModel):
    """SMTP preset config."""

    host: str
    port: int
    security: SmtpSecurity


class EmailProviderPreset(BaseModel):
    """Built-in email provider preset."""

    id: str
    name: str
    category: str
    category_label: str
    icon: str
    description: str
    smtp: SmtpPresetConfig
    help_text: str
    help_link: str | None


class EmailProviderCategory(BaseModel):
    """Provider category."""

    label: str
    description: str
    icon: str


class EmailProviderPresetsResponse(BaseModel):
    """All presets."""

    providers: list[EmailProviderPreset]
    categories: dict[str, EmailProviderCategory]
