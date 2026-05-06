"""Unified LLM service layer.

Supports:
- Multiple providers via OpenAI-compatible APIs
- Function calling / Tool Use for Agent workflows
- Structured output via JSON Schema (response_format)
- Platform-aware config resolution

All provider configs are read from the encrypted database (admin-managed).
No hardcoded API keys or provider defaults.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt_value
from app.models.config import LLMProviderConfig


@dataclass
class LLMResponse:
    """Standardized LLM response."""

    content: str
    model: str
    provider: str
    usage_prompt_tokens: int
    usage_completion_tokens: int
    finish_reason: str | None
    tool_calls: list[dict[str, Any]] | None = None
    reasoning_content: str | None = None


async def _get_provider_config(
    db: AsyncSession | None,
    provider: str,
    platform: str | None = None,
) -> dict:
    """Get provider config from database with platform resolution."""
    if db is None:
        raise ValueError(
            f"Provider '{provider}' is not configured. "
            f"Please add it via /api/v1/admin/llm-providers."
        )

    # Try exact platform match first
    if platform:
        result = await db.execute(
            select(LLMProviderConfig).where(
                LLMProviderConfig.provider == provider,
                LLMProviderConfig.platform == platform.strip().lower(),
                LLMProviderConfig.is_active == True,
            ).limit(1)
        )
        config = result.scalars().first()
        if config:
            decrypted_key = decrypt_value(config.api_key_encrypted)
            return {
                "base_url": config.base_url,
                "api_key": decrypted_key or "",
                "default_model": config.default_model,
            }

    # Fallback to global config (platform=NULL)
    result = await db.execute(
        select(LLMProviderConfig).where(
            LLMProviderConfig.provider == provider,
            LLMProviderConfig.platform.is_(None),
            LLMProviderConfig.is_active == True,
        ).limit(1)
    )
    config = result.scalars().first()
    if config:
        decrypted_key = decrypt_value(config.api_key_encrypted)
        return {
            "base_url": config.base_url,
            "api_key": decrypted_key or "",
            "default_model": config.default_model,
        }

    raise ValueError(
        f"Provider '{provider}' is not configured for platform '{platform or 'global'}'. "
        f"Please add it via /api/v1/admin/llm-providers."
    )


async def _get_default_provider(
    db: AsyncSession | None,
    platform: str | None = None,
    model_type: str = "diagnosis",
) -> str:
    """Return the provider marked as default in the database."""
    if db is None:
        raise ValueError(
            "No database session available. "
            "Please configure a provider via /api/v1/admin/llm-providers."
        )

    if platform:
        result = await db.execute(
            select(LLMProviderConfig).where(
                LLMProviderConfig.is_default == True,
                LLMProviderConfig.platform == platform.strip().lower(),
                LLMProviderConfig.is_active == True,
                LLMProviderConfig.model_type == model_type,
            ).limit(1)
        )
        config = result.scalars().first()
        if config:
            return config.provider

    result = await db.execute(
        select(LLMProviderConfig).where(
            LLMProviderConfig.is_default == True,
            LLMProviderConfig.platform.is_(None),
            LLMProviderConfig.is_active == True,
            LLMProviderConfig.model_type == model_type,
        ).limit(1)
    )
    config = result.scalars().first()
    if config:
        return config.provider

    result = await db.execute(
        select(LLMProviderConfig).where(
            LLMProviderConfig.is_active == True,
            LLMProviderConfig.model_type == model_type,
        ).limit(1)
    )
    config = result.scalars().first()
    if config:
        return config.provider

    raise ValueError(
        f"No active provider configured for model_type '{model_type}'. "
        "Please add one via /api/v1/admin/llm-providers."
    )


class LLMService:
    """Unified LLM client with Tool Use and structured output support."""

    def __init__(
        self,
        provider: str | None = None,
        platform: str | None = None,
        db: AsyncSession | None = None,
    ) -> None:
        self.provider = provider
        self.platform = platform
        self._db = db

    async def _get_client(self) -> AsyncOpenAI:
        """Get configured AsyncOpenAI client."""
        # Auto-resolve provider if not specified
        if self.provider is None and self._db is not None:
            self.provider = await _get_default_provider(self._db, self.platform)

        config = await _get_provider_config(self._db, self.provider, self.platform)
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
            # Auto-resolve provider if not specified
            if self.provider is None and self._db is not None:
                self.provider = await _get_default_provider(self._db, self.platform)
            config = await _get_provider_config(self._db, self.provider, self.platform)
            return config.get("default_model", "")
        except ValueError:
            return ""

    # ------------------------------------------------------------------
    # Basic chat
    # ------------------------------------------------------------------

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
        if not model and not default_model:
            raise ValueError(
                f"No model specified and provider '{self.provider}' has no default model configured."
            )

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
        message = choice.message

        tool_calls = None
        if message.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                }
                for tc in message.tool_calls
            ]

        return LLMResponse(
            content=message.content or "",
            model=response.model,
            provider=self.provider,
            usage_prompt_tokens=usage.prompt_tokens if usage else 0,
            usage_completion_tokens=usage.completion_tokens if usage else 0,
            finish_reason=choice.finish_reason,
            tool_calls=tool_calls,
            reasoning_content=getattr(message, "reasoning_content", None),
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
        if not model and not default_model:
            raise ValueError(
                f"No model specified and provider '{self.provider}' has no default model configured."
            )

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

    # ------------------------------------------------------------------
    # Tool Use / Function Calling
    # ------------------------------------------------------------------

    async def chat_with_tools(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
        tool_choice: str = "auto",
    ) -> LLMResponse:
        """Chat with function-calling support.

        The LLM may return tool_calls instead of content.
        The caller is responsible for executing tools and calling again.
        """
        client = await self._get_client()
        default_model = await self._get_default_model()
        if not model and not default_model:
            raise ValueError(
                f"No model specified and provider '{self.provider}' has no default model configured."
            )

        msgs = list(messages)
        if system_prompt:
            msgs.insert(0, {"role": "system", "content": system_prompt})

        response = await client.chat.completions.create(
            model=model or default_model,
            messages=msgs,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,  # type: ignore[arg-type]
            tool_choice=tool_choice,  # type: ignore[arg-type]
            stream=False,
        )

        choice = response.choices[0]
        usage = response.usage
        message = choice.message

        tool_calls = None
        if message.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments),
                }
                for tc in message.tool_calls
            ]

        return LLMResponse(
            content=message.content or "",
            model=response.model,
            provider=self.provider,
            usage_prompt_tokens=usage.prompt_tokens if usage else 0,
            usage_completion_tokens=usage.completion_tokens if usage else 0,
            finish_reason=choice.finish_reason,
            tool_calls=tool_calls,
            reasoning_content=getattr(message, "reasoning_content", None),
        )

    # ------------------------------------------------------------------
    # Structured Output (JSON Schema)
    # ------------------------------------------------------------------

    async def generate_structured(
        self,
        messages: list[dict[str, str]],
        output_schema: type[BaseModel],
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
    ) -> BaseModel:
        """Generate structured output conforming to a Pydantic schema.

        Uses OpenAI's response_format with json_schema when supported,
        falling back to strict prompting + manual validation.
        """
        client = await self._get_client()
        default_model = await self._get_default_model()
        if not model and not default_model:
            raise ValueError(
                f"No model specified and provider '{self.provider}' has no default model configured."
            )

        schema = output_schema.model_json_schema()
        schema_name = output_schema.__name__

        msgs = list(messages)
        if system_prompt:
            msgs.insert(0, {"role": "system", "content": system_prompt})

        # Add schema instruction to system prompt
        schema_instruction = (
            f"\n\nYou must respond with a single JSON object matching this schema:\n"
            f"{json.dumps(schema, indent=2, ensure_ascii=False)}\n"
            f"Output ONLY the JSON object, no markdown formatting, no extra text."
        )
        if msgs and msgs[0]["role"] == "system":
            msgs[0]["content"] += schema_instruction
        else:
            msgs.insert(0, {"role": "system", "content": schema_instruction})

        try:
            # Try native json_schema if provider supports it
            response = await client.chat.completions.create(
                model=model or default_model,
                messages=msgs,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": schema_name,
                        "schema": schema,
                        "strict": True,
                    },
                },
                stream=False,
            )
        except Exception:
            # Fallback: standard chat + manual parsing
            response = await client.chat.completions.create(
                model=model or default_model,
                messages=msgs,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
            )

        content = response.choices[0].message.content or "{}"
        # Strip markdown code blocks if present
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        data = json.loads(content)
        return output_schema.model_validate(data)

    async def health_check(self) -> dict:
        """Quick health check by listing available models."""
        try:
            client = await self._get_client()
            models = await client.models.list()
            return {
                "status": "ok",
                "provider": self.provider,
                "platform": self.platform,
                "available_models": [m.id for m in models.data[:5]],
            }
        except Exception as e:
            return {
                "status": "error",
                "provider": self.provider,
                "platform": self.platform,
                "detail": str(e),
            }


async def get_llm_service(
    db: AsyncSession,
    platform: str | None = None,
    model_type: str = "diagnosis",
) -> LLMService:
    """Factory to get an LLMService with platform-aware provider resolution."""
    provider = await _get_default_provider(db, platform=platform, model_type=model_type)
    return LLMService(provider=provider, platform=platform, db=db)
