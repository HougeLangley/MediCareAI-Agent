"""Unified LLM service layer.

Supports multiple providers via OpenAI-compatible APIs:
- OpenAI (GPT-4o, GPT-4o-mini)
- GLM (ChatGLM-4)
- DeepSeek (DeepSeek-V3, DeepSeek-R1)
- Moonshot / Kimi (kimi-k2.5, kimi-k2.6)
- Dashscope / Qwen (qwen-max, qwen-plus)

All providers use the same AsyncOpenAI client with different base_url/api_key.
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal

from openai import AsyncOpenAI

from app.core.config import get_settings

settings = get_settings()

Provider = Literal["openai", "glm", "deepseek", "moonshot", "dashscope"]

_PROVIDER_CONFIG: dict[Provider, tuple[str, str | None]] = {
    "openai": (settings.openai_base_url, settings.openai_api_key),
    "glm": (settings.glm_base_url, settings.glm_api_key),
    "deepseek": (settings.deepseek_base_url, settings.deepseek_api_key),
    "moonshot": (settings.moonshot_base_url, settings.moonshot_api_key),
    "dashscope": (settings.dashscope_base_url, settings.dashscope_api_key),
}

_DEFAULT_MODELS: dict[Provider, str] = {
    "openai": "gpt-4o-mini",
    "glm": "glm-4-flash",
    "deepseek": "deepseek-chat",
    "moonshot": "moonshot-v1-8k",
    "dashscope": "qwen-turbo",
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


class LLMService:
    """Unified LLM client supporting multiple providers."""

    def __init__(self, provider: Provider | None = None) -> None:
        """Initialize with a specific provider or default from settings.

        Args:
            provider: One of openai/glm/deepseek/moonshot/dashscope.
                      Defaults to environment setting.
        """
        self.provider = provider or self._infer_default_provider()
        base_url, api_key = _PROVIDER_CONFIG[self.provider]

        if not api_key:
            raise ValueError(
                f"API key for provider '{self.provider}' is not configured. "
                f"Set {self.provider}_api_key in environment."
            )

        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key.get_secret_value(),
            timeout=60.0,
            max_retries=2,
        )
        self.default_model = _DEFAULT_MODELS[self.provider]

    @staticmethod
    def _infer_default_provider() -> Provider:
        """Infer default provider from which API key is available."""
        for prov in ("openai", "glm", "deepseek", "moonshot", "dashscope"):
            _, key = _PROVIDER_CONFIG[prov]
            if key:
                return prov
        return "openai"  # fallback

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """Send a non-streaming chat completion request.

        Args:
            messages: List of {"role": "user"|"assistant"|"system", "content": "..."}.
            model: Override default model.
            temperature: Sampling temperature (0-2).
            max_tokens: Max tokens to generate.
            system_prompt: Optional system message prepended to messages.

        Returns:
            LLMResponse with content and usage stats.
        """
        msgs = list(messages)
        if system_prompt:
            msgs.insert(0, {"role": "system", "content": system_prompt})

        response = await self.client.chat.completions.create(
            model=model or self.default_model,
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
        """Send a streaming chat completion request.

        Yields:
            Text chunks as they arrive from the LLM.
        """
        msgs = list(messages)
        if system_prompt:
            msgs.insert(0, {"role": "system", "content": system_prompt})

        stream = await self.client.chat.completions.create(
            model=model or self.default_model,
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
        """Quick health check by listing available models.

        Returns:
            {"status": "ok"|"error", "provider": ..., "detail": ...}
        """
        try:
            models = await self.client.models.list()
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
