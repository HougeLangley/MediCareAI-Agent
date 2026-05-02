"""Application settings loaded from environment variables.

No hardcoded secrets. All sensitive values come from .env or environment.
Business-level configs (guest session TTL, max messages, LLM providers, etc.)
have been moved to the system_settings / llm_provider_configs tables and are
managed via /api/v1/admin/*. See app.services.config.DynamicConfigService.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "MediCareAI-Agent"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"
    secret_key: SecretStr  # No default — must be provided via env

    # Database
    database_url: PostgresDsn = PostgresDsn("postgresql+asyncpg://postgres:postgres@localhost:5432/medicareai")
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "medicareai"
    db_user: str = "postgres"
    db_password: SecretStr = SecretStr("postgres")

    # Redis
    redis_url: RedisDsn = RedisDsn("redis://localhost:6379/0")
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    celery_task_always_eager: bool = False

    # Monitoring
    sentry_dsn: str | None = None
    prometheus_port: int = 9090

    # CORS（生产环境必须通过环境变量配置，禁用 * ）
    cors_origins_raw: str = Field(default="*", alias="CORS_ORIGINS")

    @property
    def cors_origins(self) -> list[str]:
        origins = [o.strip() for o in self.cors_origins_raw.split(",") if o.strip()]
        if self.is_production and "*" in origins:
            return ["https://openmedicareagent.online"]
        return origins

    # Default admin credentials (auto-created if no admin exists)
    default_admin_email: str = "admin@medicareai.dev"
    default_admin_password: SecretStr | None = None  # No default — must be provided via env

    # Encryption master key for API keys at rest
    api_key_master_key: SecretStr | None = None

    # RAG (Retrieval-Augmented Generation) chunking & search tuning
    rag_chunk_size: int = 1000
    rag_chunk_overlap: int = 200
    rag_coarse_multiplier: int = 10        # coarse_k = top_k * multiplier
    rag_coarse_min: int = 50               # minimum coarse results
    rag_query_term_length: int = 3         # char length per search term
    rag_llm_temperature: float = 0.3
    rag_llm_max_tokens: int = 2048

    @property
    def async_database_url(self) -> str:
        """Return async-compatible database URL."""
        return str(self.database_url)

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance."""
    return Settings()
