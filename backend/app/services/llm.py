"""Unified LLM service layer.

Supports multiple providers via OpenAI-compatible APIs.
Provider configs are read from database (admin-managed).

No hardcoded API keys. Base URLs are only used as fallbacks when
database has no config, to help users know where to configure.
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt_value
from app.models.config import LLMProviderConfig

Provider = Literal["openai", "glm", "deepseek", "moonshot", "dashscope"]

# Minimal fallback defaults — base URLs only, no API keys.
# These are used only when no DB config exists, to guide users.
_PROVIDER_DEFAULTS: dict[str, dict] = {
    "openai": {"base_url": "https://api.openai.com/v1", "default_model": "gpt-4o-mini"},
    "glm": {"base_url": "https://open.bigmodel.cn/api/paas/v4", "default_model": "glm-4-flash"},
    "deepseek": {"base_url": "https://api.deepseek.com/v1", "default_model": "deepseek-chat"},
    "moonshot": {"base_url": "https://api.moonshot.cn/v1", "default_model": "moonshot-v1-8k"},
    "dashscope": {"base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "default_model": "qwen-turbo"},
}


@dataclass
class LLMResponse:
    """Standardized LLM response."""

    content: str
    model: str
    provider: str
    usage_prompt_tokens: int
    usage_completion_tokens: int
    finish_reason: str | None


async def _get_provider_config(
    db: AsyncSession | None, provider: str
) -> dict:
    """Get provider config from database.

    Args:
        db: Async database session (optional).
        provider: Provider name.

    Returns:
        Dict with base_url, api_key, default_model.

    Raises:
        ValueError: If no config found in database.
    """
    if db is not None:
        result = await db.execute(
            select(LLMProviderConfig).where(
                LLMProviderConfig.provider == provider,
                LLMProviderConfig.is_active == True,
            )
        )
        config = result.scalar_one_or_none()
        if config:
            decrypted_key = decrypt_value(config.api_key_encrypted)
            return {
                "base_url": config.base_url,
                "api_key": decrypted_key or "",
                "default_model": config.default_model,
            }

    # No DB config — raise so caller knows to configure via admin panel
    raise ValueError(
        f"Provider '{provider}' is not configured. "
        f"Please add it via /api/v1/admin/llm-providers."
    )


async def _get_default_provider(db: AsyncSession | None) -> str:
    """Return the provider marked as default in the database."""
    if db is not None:
        result = await db.execute(
            select(LLMProviderConfig).where(
                LLMProviderConfig.is_default == True,
                LLMProviderConfig.is_active == True,
            )
        )
        config = result.scalar_one_or_none()
        if config:
            return config.provider

    # Fallback: pick first available from hardcoded list
    return "openai"


class LLMService:
    """Unified LLM client supporting multiple providers."""

    def __init__(self, provider: str | None = None, db: AsyncSession | None = None) -> None:
        """Initialize with a specific provider or auto-detect.

        Args:
            provider: Provider name (e.g. openai, glm, deepseek, moonshot, dashscope).
                      Auto-detects from database defaults if not specified.
            db: Async database session for reading provider configs.
        """
        self.provider = provider or "openai"
        self._db = db

    async def _get_client(self) -> AsyncOpenAI:
        """Get configured AsyncOpenAI client."""
        config = await _get_provider_config(self._db, self.provider)
        if not config.get("api_key"):
            raise ValueError(
                f"API key for provider '{self.provider}' is not configured. "
                f"Please add it via /api/v1/admin/llm-providers."
            )

        return AsyncOpenAI(
            base_url=config["base_url"],
            api_key=config["api_key"],
            timeout=60.0,
            max_retries=2,
        )

    async def _get_default_model(self) -> str:
        """Get default model for current provider."""
        try:
            config = await _get_provider_config(self._db, self.provider)
            return config.get("default_model", _PROVIDER_DEFAULTS.get(self.provider, {}).get("default_model", ""))
        except ValueError:
            return _PROVIDER_DEFAULTS.get(self.provider, {}).get("default_model", "")

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """Send a non-streaming chat completion request."""
        client = await self._get_client()
        default_model = await self._get_default_model()

        msgs = list(messages)
        if system_prompt:
            msgs.insert(0, {"role": "system", "content": system_prompt})

        response = await client.chat.completions.create(
            model=model or default_model,
            messages=msgs,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )

        choice = response.choices[0]
        usage = response.usage
        return LLMResponse(
            content=choice.message.content or "",
            model=response.model,
            provider=self.provider,
            usage_prompt_tokens=usage.prompt_tokens if usage else 0,
            usage_completion_tokens=usage.completion_tokens if usage else 0,
            finish_reason=choice.finish_reason,
        )

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        """Send a streaming chat completion request."""
        client = await self._get_client()
        default_model = await self._get_default_model()

        msgs = list(messages)
        if system_prompt:
            msgs.insert(0, {"role": "system", "content": system_prompt})

        stream = await client.chat.completions.create(
            model=model or default_model,
            messages=msgs,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    async def health_check(self) -> dict:
        """Quick health check by listing available models."""
        try:
            client = await self._get_client()
            models = await client.models.list()
            return {
                "status": "ok",
                "provider": self.provider,
                "available_models": [m.id for m in models.data[:5]],
            }
        except Exception as e:
            return {
                "status": "error",
                "provider": self.provider,
                "detail": str(e),
            }
