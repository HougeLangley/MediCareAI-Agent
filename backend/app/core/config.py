"""Application settings loaded from environment variables.

No hardcoded secrets. All sensitive values come from .env or environment.
"""

from functools import lru_cache
from typing import Literal

from pydantic import PostgresDsn, RedisDsn, SecretStr
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
    secret_key: SecretStr = SecretStr("change-me-in-production")

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

    # AI Providers
    openai_api_key: SecretStr | None = None
    openai_base_url: str = "https://api.openai.com/v1"

    glm_api_key: SecretStr | None = None
    glm_base_url: str = "https://open.bigmodel.cn/api/paas/v4"

    deepseek_api_key: SecretStr | None = None
    deepseek_base_url: str = "https://api.deepseek.com/v1"

    moonshot_api_key: SecretStr | None = None
    moonshot_base_url: str = "https://api.moonshot.cn/v1"

    dashscope_api_key: SecretStr | None = None
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    default_llm_model: str = "gpt-4o-mini"

    # Vector / RAG
    vector_dimension: int = 1536
    reranker_provider: str = "cohere"
    reranker_api_key: SecretStr | None = None
    reranker_top_k: int = 5

    # Email
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: SecretStr | None = None
    smtp_from: str = "noreply@medicareai.dev"

    # Monitoring
    sentry_dsn: str | None = None
    prometheus_port: int = 9090

    # Guest Mode
    guest_session_ttl_hours: int = 24
    guest_max_messages: int = 10

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
