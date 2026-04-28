"""Unified LLM service layer.

Supports multiple providers via OpenAI-compatible APIs:
- OpenAI (GPT-4o, GPT-4o-mini)
- GLM (ChatGLM-4)
- DeepSeek (DeepSeek-V3, DeepSeek-R1)
- Moonshot / Kimi (kimi-k2.5, kimi-k2.6)
- Dashscope / Qwen (qwen-max, qwen-plus)

Provider configs are read from database (admin-managed), with environment fallbacks.
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.config import LLMProviderConfig

settings = get_settings()

Provider = Literal["openai", "glm", "deepseek", "moonshot", "dashscope"]

# Fallback defaults from environment (base URLs only, no API keys)
_PROVIDER_DEFAULTS: dict[Provider, dict] = {
    "openai": {"base_url": settings.openai_base_url, "default_model": "gpt-4o-mini"},
    "glm": {"base_url": settings.glm_base_url, "default_model": "glm-4-flash"},
    "deepseek": {"base_url": settings.deepseek_base_url, "default_model": "deepseek-chat"},
    "moonshot": {"base_url": settings.moonshot_base_url, "default_model": "moonshot-v1-8k"},
    "dashscope": {"base_url": settings.dashscope_base_url, "default_model": "qwen-turbo"},
}


@dataclass
class LLMResponse:
    """Standardized LLM response."""

    content: str
    model: str
    provider: Provider
    usage_prompt_tokens: int
    usage_completion_tokens: int
    finish_reason: str | None


async def _get_provider_config(
    db: AsyncSession | None, provider: Provider
) -> dict:
    """Get provider config from database or fall back to environment defaults.

    Args:
        db: Async database session (optional).
        provider: Provider name.

    Returns:
        Dict with base_url, api_key, default_model.

    Raises:
        ValueError: If no config found and no DB session available.
    """
    # Try database first
    if db is not None:
        result = await db.execute(
            select(LLMProviderConfig).where(
                LLMProviderConfig.provider == provider,
                LLMProviderConfig.is_active == True,
            )
        )
        config = result.scalar_one_or_none()
        if config:
            return {
                "base_url": config.base_url,
                "api_key": config.api_key,
                "default_model": config.default_model,
            }

    # Fallback: check environment variables for API key
    env_key = None
    if provider == "openai":
        env_key = settings.openai_api_key
    elif provider == "glm":
        env_key = settings.glm_api_key
    elif provider == "deepseek":
        env_key = settings.deepseek_api_key
    elif provider == "moonshot":
        env_key = settings.moonshot_api_key
    elif provider == "dashscope":
        env_key = settings.dashscope_api_key

    defaults = _PROVIDER_DEFAULTS.get(provider, {})
    if env_key:
        return {
            "base_url": defaults.get("base_url", ""),
            "api_key": env_key.get_secret_value(),
            "default_model": defaults.get("default_model", ""),
        }

    raise ValueError(
        f"Provider '{provider}' is not configured. "
        f"Please configure it via /api/v1/admin/llm-providers or set {provider}_api_key in environment."
    )


class LLMService:
    """Unified LLM client supporting multiple providers."""

    def __init__(self, provider: Provider | None = None, db: AsyncSession | None = None) -> None:
        """Initialize with a specific provider or auto-detect.

        Args:
            provider: One of openai/glm/deepseek/moonshot/dashscope.
                      Auto-detects from database defaults if not specified.
            db: Async database session for reading provider configs.
        """
        self.provider = provider or self._infer_default_provider(db)
        self._db = db

    @staticmethod
    def _infer_default_provider(db: AsyncSession | None = None) -> Provider:
        """Infer default provider from database or environment."""
        # Note: This is synchronous; for async DB lookup, caller should specify provider
        for prov in ("openai", "glm", "deepseek", "moonshot", "dashscope"):
            env_key = None
            if prov == "openai":
                env_key = settings.openai_api_key
            elif prov == "glm":
                env_key = settings.glm_api_key
            elif prov == "deepseek":
                env_key = settings.deepseek_api_key
            elif prov == "moonshot":
                env_key = settings.moonshot_api_key
            elif prov == "dashscope":
                env_key = settings.dashscope_api_key
            if env_key:
                return prov  # type: ignore[return-value]
        return "openai"

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
        config = await _get_provider_config(self._db, self.provider)
        return config.get("default_model", _PROVIDER_DEFAULTS[self.provider]["default_model"])

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
            provider=self.provider,  # type: ignore[arg-type]
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
