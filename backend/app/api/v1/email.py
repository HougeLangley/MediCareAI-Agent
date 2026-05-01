"""Email management admin endpoints.

Manage SMTP configs, email templates, send history, and provider presets.
All endpoints require admin role.
"""

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_role
from app.db.session import get_db
from app.models.audit import AuditActionType, AuditResourceType
from app.models.email import (
    EmailConfiguration,
    EmailLog,
    EmailSendStatus,
    EmailTemplate,
)
from app.models.user import User, UserRole
from app.schemas.email import (
    EmailConfigCreate,
    EmailConfigListResponse,
    EmailConfigResponse,
    EmailConfigTestRequest,
    EmailConfigTestResponse,
    EmailConfigUpdate,
    EmailLogListResponse,
    EmailLogResponse,
    EmailProviderCategory,
    EmailProviderPreset,
    EmailProviderPresetsResponse,
    EmailSendRequest,
    EmailSendResponse,
    EmailServiceStatus,
    EmailTemplateCreate,
    EmailTemplateListResponse,
    EmailTemplateResponse,
    EmailTemplateUpdate,
    SmtpPresetConfig,
)
from app.services.audit import AuditService
from app.services.email_service import (
    EMAIL_PROVIDER_CATEGORIES,
    EMAIL_PROVIDER_PRESETS,
    email_service,
)

router = APIRouter(dependencies=[Depends(require_role(UserRole.ADMIN))])


# ═════════════════════════════════════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════════════════════════════════════

async def _clear_default_config(
    db: AsyncSession, exclude_id: uuid.UUID | None = None
) -> None:
    """Unset default flag on all configs (optionally except one)."""
    stmt = select(EmailConfiguration).where(EmailConfiguration.is_default == True)
    if exclude_id:
        stmt = stmt.where(EmailConfiguration.id != exclude_id)
    result = await db.execute(stmt)
    for cfg in result.scalars().all():
        cfg.is_default = False
        cfg.updated_at = datetime.utcnow()
    await db.commit()


# ═════════════════════════════════════════════════════════════════════════════
# Email Configuration
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/configs", response_model=EmailConfigListResponse)
async def list_email_configs(
    db: AsyncSession = Depends(get_db),
) -> EmailConfigListResponse:
    """List all SMTP configurations."""
    stmt = select(EmailConfiguration).order_by(EmailConfiguration.created_at.desc())
    result = await db.execute(stmt)
    configs = result.scalars().all()
    return EmailConfigListResponse(
        items=[EmailConfigResponse.model_validate(c) for c in configs],
        total=len(configs),
    )


@router.get("/configs/{config_id}", response_model=EmailConfigResponse)
async def get_email_config(
    config_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> EmailConfigResponse:
    """Get single config details."""
    result = await db.execute(
        select(EmailConfiguration).where(EmailConfiguration.id == config_id)
    )
    cfg = result.scalar_one_or_none()
    if not cfg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Configuration not found"
        )
    return EmailConfigResponse.model_validate(cfg)


@router.post("/configs", response_model=EmailConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_email_config(
    data: EmailConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmailConfigResponse:
    """Create new SMTP configuration."""
    if data.is_default:
        await _clear_default_config(db)

    new_cfg = EmailConfiguration(
        smtp_host=data.smtp_host,
        smtp_port=data.smtp_port,
        smtp_user=data.smtp_user,
        smtp_password_encrypted=email_service.encrypt_password(data.smtp_password),
        smtp_from_email=data.smtp_from_email,
        smtp_from_name=data.smtp_from_name,
        smtp_security=data.smtp_security,
        description=data.description,
        is_default=data.is_default,
        is_active=True,
        created_by=current_user.id,
    )
    db.add(new_cfg)
    await db.commit()
    await db.refresh(new_cfg)

    audit = AuditService(db)
    await audit.log(
        user_id=current_user.id,
        action=AuditActionType.CREATE,
        resource_type=AuditResourceType.SYSTEM_SETTING,
        resource_id=str(new_cfg.id),
        details={"smtp_host": data.smtp_host, "smtp_user": data.smtp_user},
    )

    return EmailConfigResponse.model_validate(new_cfg)


@router.put("/configs/{config_id}", response_model=EmailConfigResponse)
async def update_email_config(
    config_id: uuid.UUID,
    data: EmailConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmailConfigResponse:
    """Update SMTP configuration."""
    result = await db.execute(
        select(EmailConfiguration).where(EmailConfiguration.id == config_id)
    )
    cfg = result.scalar_one_or_none()
    if not cfg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Configuration not found"
        )

    if data.is_default:
        await _clear_default_config(db, exclude_id=config_id)

    update_fields = data.model_dump(exclude_unset=True)
    # Handle password separately (encrypt it)
    if "smtp_password" in update_fields:
        password = update_fields.pop("smtp_password")
        if password:
            cfg.smtp_password_encrypted = email_service.encrypt_password(password)

    for field, value in update_fields.items():
        if hasattr(cfg, field):
            setattr(cfg, field, value)

    cfg.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(cfg)

    audit = AuditService(db)
    await audit.log(
        user_id=current_user.id,
        action=AuditActionType.UPDATE,
        resource_type=AuditResourceType.SYSTEM_SETTING,
        resource_id=str(cfg.id),
        details={"updated_fields": list(update_fields.keys())},
    )

    return EmailConfigResponse.model_validate(cfg)


@router.delete("/configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_email_config(
    config_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete SMTP configuration."""
    result = await db.execute(
        select(EmailConfiguration).where(EmailConfiguration.id == config_id)
    )
    cfg = result.scalar_one_or_none()
    if not cfg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Configuration not found"
        )

    await db.delete(cfg)
    await db.commit()

    audit = AuditService(db)
    await audit.log(
        user_id=current_user.id,
        action=AuditActionType.DELETE,
        resource_type=AuditResourceType.SYSTEM_SETTING,
        resource_id=str(config_id),
    )


@router.post("/configs/{config_id}/test", response_model=EmailConfigTestResponse)
async def test_email_config(
    config_id: uuid.UUID,
    data: EmailConfigTestRequest,
    db: AsyncSession = Depends(get_db),
) -> EmailConfigTestResponse:
    """Send test email using specific config."""
    result = await db.execute(
        select(EmailConfiguration).where(
            EmailConfiguration.id == config_id,
            EmailConfiguration.is_active == True,
        )
    )
    cfg = result.scalar_one_or_none()
    if not cfg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found or inactive",
        )

    success, message = await email_service.test_config(db, cfg, data.test_email)
    return EmailConfigTestResponse(success=success, message=message)


@router.post("/configs/{config_id}/set-default", response_model=EmailConfigResponse)
async def set_default_email_config(
    config_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmailConfigResponse:
    """Set a config as the default."""
    result = await db.execute(
        select(EmailConfiguration).where(EmailConfiguration.id == config_id)
    )
    cfg = result.scalar_one_or_none()
    if not cfg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Configuration not found"
        )

    await _clear_default_config(db, exclude_id=config_id)
    cfg.is_default = True
    cfg.is_active = True
    cfg.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(cfg)

    return EmailConfigResponse.model_validate(cfg)


@router.get("/status", response_model=EmailServiceStatus)
async def get_email_status(
    db: AsyncSession = Depends(get_db),
) -> EmailServiceStatus:
    """Get current email service status."""
    await email_service.load_config(db)
    is_available = email_service.is_configured

    cfg = email_service._config
    return EmailServiceStatus(
        is_available=is_available,
        config_source="database" if cfg else "none",
        smtp_host=cfg.smtp_host if cfg else None,
        smtp_port=cfg.smtp_port if cfg else None,
        smtp_user=cfg.smtp_user if cfg else None,
        from_email=cfg.smtp_from_email if cfg else None,
        from_name=cfg.smtp_from_name if cfg else None,
        smtp_security=cfg.smtp_security if cfg else None,
    )


# ═════════════════════════════════════════════════════════════════════════════
# Email Templates
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/templates", response_model=EmailTemplateListResponse)
async def list_email_templates(
    db: AsyncSession = Depends(get_db),
) -> EmailTemplateListResponse:
    """List all email templates."""
    stmt = select(EmailTemplate).order_by(EmailTemplate.created_at.desc())
    result = await db.execute(stmt)
    templates = result.scalars().all()
    return EmailTemplateListResponse(
        items=[EmailTemplateResponse.model_validate(t) for t in templates],
        total=len(templates),
    )


@router.get("/templates/{template_id}", response_model=EmailTemplateResponse)
async def get_email_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> EmailTemplateResponse:
    """Get single template."""
    result = await db.execute(
        select(EmailTemplate).where(EmailTemplate.id == template_id)
    )
    tpl = result.scalar_one_or_none()
    if not tpl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Template not found"
        )
    return EmailTemplateResponse.model_validate(tpl)


@router.post("/templates", response_model=EmailTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_email_template(
    data: EmailTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmailTemplateResponse:
    """Create email template."""
    # Check name uniqueness
    existing = await db.execute(
        select(EmailTemplate).where(EmailTemplate.name == data.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Template name '{data.name}' already exists",
        )

    tpl = EmailTemplate(
        name=data.name,
        description=data.description,
        subject=data.subject,
        html_body=data.html_body,
        text_body=data.text_body,
        variables=data.variables,
        is_active=data.is_active,
        created_by=current_user.id,
    )
    db.add(tpl)
    await db.commit()
    await db.refresh(tpl)
    return EmailTemplateResponse.model_validate(tpl)


@router.put("/templates/{template_id}", response_model=EmailTemplateResponse)
async def update_email_template(
    template_id: uuid.UUID,
    data: EmailTemplateUpdate,
    db: AsyncSession = Depends(get_db),
) -> EmailTemplateResponse:
    """Update email template."""
    result = await db.execute(
        select(EmailTemplate).where(EmailTemplate.id == template_id)
    )
    tpl = result.scalar_one_or_none()
    if not tpl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Template not found"
        )

    update_fields = data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        if hasattr(tpl, field):
            setattr(tpl, field, value)

    tpl.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(tpl)
    return EmailTemplateResponse.model_validate(tpl)


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_email_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete email template."""
    result = await db.execute(
        select(EmailTemplate).where(EmailTemplate.id == template_id)
    )
    tpl = result.scalar_one_or_none()
    if not tpl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Template not found"
        )
    await db.delete(tpl)
    await db.commit()


# ═════════════════════════════════════════════════════════════════════════════
# Email Logs
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/logs", response_model=EmailLogListResponse)
async def list_email_logs(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status: Annotated[EmailSendStatus | None, Query()] = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
    db: AsyncSession = Depends(get_db),
) -> EmailLogListResponse:
    """List email send history."""
    conditions: list[Any] = []
    if status:
        conditions.append(EmailLog.status == status)
    if search:
        conditions.append(
            EmailLog.recipient_email.ilike(f"%{search}%")
            | EmailLog.subject.ilike(f"%{search}%")
        )

    base_stmt = select(EmailLog)
    if conditions:
        from sqlalchemy import and_
        base_stmt = base_stmt.where(and_(*conditions))

    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one() or 0

    stmt = (
        base_stmt.order_by(desc(EmailLog.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    logs = result.scalars().all()

    return EmailLogListResponse(
        items=[EmailLogResponse.model_validate(l) for l in logs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


# ═════════════════════════════════════════════════════════════════════════════
# Send Email (Admin)
# ═════════════════════════════════════════════════════════════════════════════

@router.post("/send", response_model=EmailSendResponse)
async def send_email(
    data: EmailSendRequest,
    db: AsyncSession = Depends(get_db),
) -> EmailSendResponse:
    """Send email using a template (admin)."""
    tpl_result = await db.execute(
        select(EmailTemplate).where(
            EmailTemplate.id == data.template_id,
            EmailTemplate.is_active == True,
        )
    )
    tpl = tpl_result.scalar_one_or_none()
    if not tpl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found or inactive",
        )

    success, error, log_id = await email_service.send_templated_email(
        db=db,
        template=tpl,
        to_email=data.recipient_email,
        variables=data.variables,
    )

    if success:
        return EmailSendResponse(success=True, log_id=uuid.UUID(log_id) if log_id else None, message="Email queued successfully")
    else:
        return EmailSendResponse(success=False, log_id=uuid.UUID(log_id) if log_id else None, message=error or "Unknown error")


# ═════════════════════════════════════════════════════════════════════════════
# Provider Presets
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/providers", response_model=EmailProviderPresetsResponse)
async def get_email_provider_presets() -> EmailProviderPresetsResponse:
    """Get built-in email provider presets."""
    providers = []
    for pid, pdata in EMAIL_PROVIDER_PRESETS.items():
        providers.append(
            EmailProviderPreset(
                id=pid,
                name=pdata["name"],
                category=pdata["category"],
                category_label=pdata["category_label"],
                icon=pdata["icon"],
                description=pdata["description"],
                smtp=SmtpPresetConfig(
                    host=pdata["smtp"]["host"],
                    port=pdata["smtp"]["port"],
                    security=pdata["smtp"]["security"],
                ),
                help_text=pdata["help_text"],
                help_link=pdata["help_link"],
            )
        )

    categories = {
        cid: EmailProviderCategory(
            label=cdata["label"],
            description=cdata["description"],
            icon=cdata["icon"],
        )
        for cid, cdata in EMAIL_PROVIDER_CATEGORIES.items()
    }

    return EmailProviderPresetsResponse(providers=providers, categories=categories)


@router.get("/providers/{provider_id}", response_model=EmailProviderPreset)
async def get_email_provider_preset(provider_id: str) -> EmailProviderPreset:
    """Get single provider preset."""
    pdata = EMAIL_PROVIDER_PRESETS.get(provider_id)
    if not pdata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider preset '{provider_id}' not found",
        )
    return EmailProviderPreset(
        id=provider_id,
        name=pdata["name"],
        category=pdata["category"],
        category_label=pdata["category_label"],
        icon=pdata["icon"],
        description=pdata["description"],
        smtp=SmtpPresetConfig(
            host=pdata["smtp"]["host"],
            port=pdata["smtp"]["port"],
            security=pdata["smtp"]["security"],
        ),
        help_text=pdata["help_text"],
        help_link=pdata["help_link"],
    )
