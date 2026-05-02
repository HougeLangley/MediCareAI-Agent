"""Email service with encrypted credentials and async SMTP.

Improvements over legacy:
- Passwords encrypted at rest via Fernet (app.core.encryption)
- Async aiosmtplib for non-blocking sends
- Automatic DB logging of every send attempt
- Template variable substitution {{var}}
- Preset provider configs baked into code (no JSON file needed)
"""

import asyncio
import logging
import re
from datetime import datetime
from typing import Any

import aiosmtplib
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt_value, encrypt_value
from app.db.session import AsyncSessionLocal
from app.models.email import (
    EmailConfiguration,
    EmailLog,
    EmailSendStatus,
    EmailTemplate,
    SmtpSecurity,
)

logger = logging.getLogger(__name__)

# Simple {{variable}} regex
_VAR_PATTERN = re.compile(r"\{\{\s*(\w+)\s*\}\}")

# Provider help links — centralised to avoid hard-coding domains in presets
_EMAIL_PROVIDER_LINKS: dict[str, str | None] = {
    "qq": "https://mail.qq.com/",
    "163": "https://mail.163.com/",
    "gmail": "https://myaccount.google.com/apppasswords",
    "outlook": "https://outlook.live.com/",
    "custom": None,
}


# =============================================================================
# Provider Presets (baked into code — no external JSON file)
# =============================================================================

EMAIL_PROVIDER_PRESETS: dict[str, dict[str, Any]] = {
    "qq": {
        "name": "QQ 邮箱",
        "category": "domestic",
        "category_label": "国内服务",
        "icon": "📧",
        "description": "腾讯 QQ 邮箱，使用授权码代替密码",
        "smtp": {"host": "smtp.qq.com", "port": 587, "security": "starttls"},
        "help_text": "请在 QQ 邮箱设置 → 账号 → 开启 SMTP 服务，生成授权码后填入密码字段",
        "help_link": _EMAIL_PROVIDER_LINKS["qq"],
    },
    "163": {
        "name": "163 网易邮箱",
        "category": "domestic",
        "category_label": "国内服务",
        "icon": "📧",
        "description": "网易 163 邮箱，使用授权码代替密码",
        "smtp": {"host": "smtp.163.com", "port": 465, "security": "ssl"},
        "help_text": "请在 163 邮箱设置 → POP3/SMTP/IMAP 中开启服务并获取授权码",
        "help_link": _EMAIL_PROVIDER_LINKS["163"],
    },
    "gmail": {
        "name": "Gmail",
        "category": "international",
        "category_label": "国际服务",
        "icon": "🌐",
        "description": "Google Gmail，需开启应用定密码",
        "smtp": {"host": "smtp.gmail.com", "port": 587, "security": "starttls"},
        "help_text": "请在 Google 账户 → 安全性 → 开启应用定密码（App Password）",
        "help_link": _EMAIL_PROVIDER_LINKS["gmail"],
    },
    "outlook": {
        "name": "Outlook / Hotmail",
        "category": "international",
        "category_label": "国际服务",
        "icon": "🌐",
        "description": "Microsoft Outlook / Hotmail",
        "smtp": {"host": "smtp.office365.com", "port": 587, "security": "starttls"},
        "help_text": "使用您的 Microsoft 账户密码登录，如启用了双重验证请使用应用定密码",
        "help_link": _EMAIL_PROVIDER_LINKS["outlook"],
    },
    "custom": {
        "name": "自定义 SMTP",
        "category": "custom",
        "category_label": "自定义",
        "icon": "⚙️",
        "description": "自定义 SMTP 服务器配置",
        "smtp": {"host": "", "port": 587, "security": "starttls"},
        "help_text": "请填入您的 SMTP 服务器地址和端口号",
        "help_link": _EMAIL_PROVIDER_LINKS["custom"],
    },
}

EMAIL_PROVIDER_CATEGORIES: dict[str, dict[str, str]] = {
    "domestic": {"label": "国内服务", "description": "中国大陆主流邮箱服务商", "icon": "🇨🇳"},
    "international": {"label": "国际服务", "description": "全球通用邮箱服务商", "icon": "🌍"},
    "custom": {"label": "自定义", "description": "自行配置的 SMTP 服务器", "icon": "⚙️"},
}


# =============================================================================
# Core Email Service
# =============================================================================

class EmailService:
    """Async email service with DB-backed configuration."""

    def __init__(self) -> None:
        self._config: EmailConfiguration | None = None
        self._loaded_at: datetime | None = None

    # ------------------------------------------------------------------
    # Config management
    # ------------------------------------------------------------------

    async def _get_default_config(self, db: AsyncSession) -> EmailConfiguration | None:
        """Load the active default config from DB."""
        stmt = (
            select(EmailConfiguration)
            .where(EmailConfiguration.is_active == True)
            .where(EmailConfiguration.is_default == True)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def load_config(self, db: AsyncSession) -> bool:
        """Load default config into memory. Returns True if available."""
        self._config = await self._get_default_config(db)
        self._loaded_at = datetime.utcnow()
        return self._config is not None

    @property
    def is_configured(self) -> bool:
        return self._config is not None

    # ------------------------------------------------------------------
    # Encryption helpers
    # ------------------------------------------------------------------

    @staticmethod
    def encrypt_password(password: str) -> str:
        return encrypt_value(password)

    @staticmethod
    def decrypt_password(ciphertext: str) -> str | None:
        return decrypt_value(ciphertext)

    # ------------------------------------------------------------------
    # Send email
    # ------------------------------------------------------------------

    async def send_email(
        self,
        db: AsyncSession,
        to_email: str,
        subject: str,
        html_content: str | None = None,
        text_content: str | None = None,
        config: EmailConfiguration | None = None,
        template_id: str | None = None,
    ) -> tuple[bool, str | None, str | None]:
        """Send an email and log the attempt.

        Returns:
            (success: bool, error_message: str | None, log_id: str | None)
        """
        cfg = config or self._config
        if cfg is None:
            cfg = await self._get_default_config(db)
            if cfg is None:
                return False, "No active email configuration found", None

        # Decrypt password
        password = self.decrypt_password(cfg.smtp_password_encrypted)
        if not password:
            return False, "Failed to decrypt SMTP password", None

        # Build message
        from email.message import EmailMessage

        msg = EmailMessage()
        msg["From"] = f"{cfg.smtp_from_name} <{cfg.smtp_from_email}>"
        msg["To"] = to_email
        msg["Subject"] = subject

        if text_content:
            msg.set_content(text_content)
        if html_content:
            msg.add_alternative(html_content, subtype="html")
        if not text_content and not html_content:
            return False, "No email content provided", None

        # Determine TLS/SSL settings
        use_tls = cfg.smtp_security == SmtpSecurity.STARTTLS
        use_ssl = cfg.smtp_security == SmtpSecurity.SSL

        # Create log entry
        log = EmailLog(
            config_id=cfg.id,
            template_id=template_id,
            recipient_email=to_email,
            subject=subject,
            body_preview=(html_content or text_content or "")[:500],
            status=EmailSendStatus.PENDING,
        )
        db.add(log)
        await db.commit()
        await db.refresh(log)
        log_id = str(log.id)

        try:
            await aiosmtplib.send(
                msg,
                hostname=cfg.smtp_host,
                port=cfg.smtp_port,
                username=cfg.smtp_user,
                password=password,
                start_tls=use_tls,
                use_tls=use_ssl,
                timeout=30,
            )
            log.status = EmailSendStatus.SENT
            log.sent_at = datetime.utcnow()
            log.error_message = None
            await db.commit()
            logger.info(f"Email sent to {to_email} via {cfg.smtp_host}")
            return True, None, log_id

        except Exception as exc:
            error_msg = str(exc)
            log.status = EmailSendStatus.FAILED
            log.failed_at = datetime.utcnow()
            log.error_message = error_msg
            log.retry_count += 1
            await db.commit()
            logger.error(f"Email failed to {to_email}: {error_msg}")
            return False, error_msg, log_id

    # ------------------------------------------------------------------
    # Template helpers
    # ------------------------------------------------------------------

    @staticmethod
    def render_template(template_body: str, variables: dict[str, str]) -> str:
        """Replace {{var}} placeholders in template."""
        def _replacer(match: re.Match) -> str:
            key = match.group(1)
            return variables.get(key, match.group(0))

        return _VAR_PATTERN.sub(_replacer, template_body)

    async def send_templated_email(
        self,
        db: AsyncSession,
        template: EmailTemplate,
        to_email: str,
        variables: dict[str, str],
        config: EmailConfiguration | None = None,
    ) -> tuple[bool, str | None, str | None]:
        """Send email using a template with variable substitution."""
        subject = self.render_template(template.subject, variables)
        html_body = self.render_template(template.html_body, variables)
        text_body = None
        if template.text_body:
            text_body = self.render_template(template.text_body, variables)

        return await self.send_email(
            db=db,
            to_email=to_email,
            subject=subject,
            html_content=html_body,
            text_content=text_body,
            config=config,
            template_id=str(template.id),
        )

    # ------------------------------------------------------------------
    # Test helper
    # ------------------------------------------------------------------

    async def test_config(
        self,
        db: AsyncSession,
        config: EmailConfiguration,
        test_email: str,
    ) -> tuple[bool, str]:
        """Send a test email using the given config and update test_status."""
        html = f"""<!DOCTYPE html>
<html><body style="font-family:Arial,sans-serif;line-height:1.6;color:#333;">
<div style="max-width:600px;margin:0 auto;padding:20px;">
<h2 style="color:#667eea;">MediCareAI-Agent 邮件配置测试</h2>
<p>这是一封测试邮件，用于验证 SMTP 配置是否正确。</p>
<p>如果您收到这封邮件，说明邮件服务配置成功！</p>
<hr style="border:1px solid #eee;margin:20px 0;">
<p style="font-size:12px;color:#666;">MediCareAI-Agent 智能医疗助手<br>测试时间: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
</div></body></html>"""
        text = "MediCareAI-Agent 邮件配置测试\n\n这是一封测试邮件。如果您收到，说明配置成功！"

        success, error, _ = await self.send_email(
            db=db,
            to_email=test_email,
            subject="【MediCareAI-Agent】邮件配置测试",
            html_content=html,
            text_content=text,
            config=config,
        )

        if success:
            config.test_status = "success"
            config.test_message = f"测试邮件成功发送到 {test_email}"
        else:
            config.test_status = "failed"
            config.test_message = f"测试失败: {error}"
        config.tested_at = datetime.utcnow()
        await db.commit()

        return success, config.test_message or ""


# Global singleton instance
email_service = EmailService()
