"""Embedding service for vectorizing text chunks.

Reads embedding provider config from llm_provider_configs (model_type='embedding').
"""

from __future__ import annotations

import math
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.encryption import decrypt_value
from app.models.config import LLMProviderConfig


class EmbeddingService:
    """Unified embedding client with cosine-similarity helpers."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._client: AsyncOpenAI | None = None
        self._model: str = ""

    async def _get_client(self) -> AsyncOpenAI:
        """Lazy-init embedding client from admin config."""
        if self._client is not None:
            return self._client

        config = await self._resolve_provider()
        self._model = config["default_model"]
        self._client = AsyncOpenAI(
            base_url=config["base_url"],
            api_key=config["api_key"],
            timeout=30.0,
            max_retries=2,
        )
        return self._client

    async def _resolve_provider(self) -> dict[str, str]:
        """Fetch active embedding provider from database."""
        result = await self.db.execute(
            select(LLMProviderConfig).where(
                LLMProviderConfig.model_type == "embedding",
                LLMProviderConfig.is_active == True,
            ).limit(1)
        )
        cfg = result.scalars().first()
        if cfg is None:
            raise ValueError(
                "No active embedding provider configured. "
                "Please add one via Admin > LLM Providers (model_type='embedding')."
            )

        api_key = decrypt_value(cfg.api_key_encrypted)
        if not api_key:
            raise ValueError(f"Embedding provider '{cfg.provider}' has no API key.")

        return {
            "base_url": cfg.base_url,
            "api_key": api_key,
            "default_model": cfg.default_model,
        }

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts into dense vectors."""
        client = await self._get_client()
        response = await client.embeddings.create(
            model=self._model,
            input=texts,
        )
        return [item.embedding for item in response.data]

    async def health_check(self) -> dict[str, Any]:
        """Quick health check."""
        try:
            await self._resolve_provider()
            return {"status": "ok", "model": self._model or "pending"}
        except ValueError as e:
            return {"status": "error", "detail": str(e)}

    # ------------------------------------------------------------------
    # Static similarity helpers (used in RAGService.search)
    # ------------------------------------------------------------------

    @staticmethod
    def cosine_similarity(a: list[float], b: list[float]) -> float:
        """Cosine similarity between two vectors [-1, 1]."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
