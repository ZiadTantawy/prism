import os
from typing import Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_SECRETS_DIR = "/run/secrets" if os.path.isdir("/run/secrets") else None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        secrets_dir=_SECRETS_DIR,
        case_sensitive=False,
        extra="ignore",
    )

    # Prism API
    API_STR: str = Field(default="/api/v1")
    PROJECT_NAME: str = Field(default="Prism")
    DESCRIPTION: str = Field(default="Prism is an AI-powered news intelligence platform")
    VERSION: str = Field(default="1.0.0")

    # Postgres (aliases match docker-compose / .env)
    DATABASE_USER: str = Field(alias="POSTGRES_USER", default="prism")
    DATABASE_PASSWORD: SecretStr = Field(alias="POSTGRES_PASSWORD")
    DATABASE_NAME: str = Field(alias="POSTGRES_DB", default="prism")
    DATABASE_HOST: str = Field(alias="POSTGRES_HOST", default="postgres")
    DATABASE_PORT: int = Field(alias="POSTGRES_PORT", default=5432)
    DATABASE_POOL_SIZE: int = Field(default=5, description="SQLAlchemy async pool size")
    DATABASE_POOL_MAX_OVERFLOW: int = Field(default=10, description="SQLAlchemy pool max overflow")
    DATABASE_ECHO: bool = Field(default=False, description="Log SQL statements (dev/debug)")

    # RabbitMQ
    RABBITMQ_USER: str = Field(alias="RABBITMQ_DEFAULT_USER", default="prism")
    RABBITMQ_PASSWORD: SecretStr = Field(alias="RABBITMQ_DEFAULT_PASS")
    RABBITMQ_HOST: str = Field(default="rabbitmq")
    RABBITMQ_PORT: int = Field(default=5672)

    # Redis
    REDIS_HOST: str = Field(default="redis")
    REDIS_PORT: int = Field(default=6379)
    REDIS_PASSWORD: Optional[SecretStr] = Field(default=None)

    # MinIO
    MINIO_USER: str = Field(alias="MINIO_ROOT_USER", default="minioadmin")
    MINIO_PASSWORD: SecretStr = Field(alias="MINIO_ROOT_PASSWORD")
    MINIO_HOST: str = Field(default="minio")
    MINIO_PORT: int = Field(default=9000)

    # Qdrant
    QDRANT_HOST: str = Field(default="qdrant")
    QDRANT_PORT: int = Field(default=6333)
    QDRANT_PASSWORD: Optional[SecretStr] = Field(default=None)

    # Airflow (metadata DB)
    AIRFLOW_USER: str = Field(alias="AIRFLOW_POSTGRES_USER", default="airflow")
    AIRFLOW_PASSWORD: SecretStr = Field(alias="AIRFLOW_POSTGRES_PASSWORD")
    AIRFLOW_DB: str = Field(alias="AIRFLOW_POSTGRES_DB", default="airflow")
    AIRFLOW_HOST: str = Field(default="airflow-db")
    AIRFLOW_PORT: int = Field(default=5432)

    # Prometheus
    PROMETHEUS_HOST: str = Field(default="prometheus")
    PROMETHEUS_PORT: int = Field(default=9090)

    # Grafana
    GRAFANA_USER: str = Field(alias="GRAFANA_ADMIN_USER", default="admin")
    GRAFANA_PASSWORD: SecretStr = Field(alias="GRAFANA_ADMIN_PASSWORD")
    GRAFANA_HOST: str = Field(default="grafana")
    GRAFANA_PORT: int = Field(default=3000)

    # Ollama
    OLLAMA_HOST: str = Field(default="localhost")
    OLLAMA_PORT: int = Field(default=11434)

    # LLM API keys (optional; set when using that provider)
    OPENAI_API_KEY: Optional[SecretStr] = Field(default=None)
    ANTHROPIC_API_KEY: Optional[SecretStr] = Field(default=None)
    GROQ_API_KEY: Optional[SecretStr] = Field(default=None)

    # Observability (optional)
    SENTRY_DSN: Optional[SecretStr] = Field(default=None)
    LANGSMITH_API_KEY: Optional[SecretStr] = Field(default=None)
    LANGFUSE_PUBLIC_KEY: Optional[SecretStr] = Field(default=None)
    LANGFUSE_SECRET_KEY: Optional[SecretStr] = Field(default=None)
    LANGFUSE_HOST: Optional[str] = Field(default=None)

    # LLM defaults
    LLM_DEFAULT_PROVIDER: str = Field(default="ollama")
    LLM_DEFAULT_MODEL: str = Field(default="llama3.2")

    # Per-role LLM overrides
    LLM_MAP_PROVIDER: Optional[str] = Field(default=None)
    LLM_MAP_MODEL: Optional[str] = Field(default=None)
    LLM_JUDGE_PROVIDER: Optional[str] = Field(default=None)
    LLM_JUDGE_MODEL: Optional[str] = Field(default=None)
    LLM_RAG_PROVIDER: Optional[str] = Field(default=None)
    LLM_RAG_MODEL: Optional[str] = Field(default=None)
    LLM_CHAT_PROVIDER: Optional[str] = Field(default=None)
    LLM_CHAT_MODEL: Optional[str] = Field(default=None)

    @property
    def postgres_async_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.DATABASE_USER}:{self.DATABASE_PASSWORD.get_secret_value()}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

    @property
    def postgres_sync_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.DATABASE_USER}:{self.DATABASE_PASSWORD.get_secret_value()}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

    @property
    def rabbitmq_url(self) -> str:
        return (
            f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD.get_secret_value()}"
            f"@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/"
        )

    @property
    def redis_url(self) -> str:
        if self.REDIS_PASSWORD is not None and self.REDIS_PASSWORD.get_secret_value():
            return f"redis://:{self.REDIS_PASSWORD.get_secret_value()}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    @property
    def minio_url(self) -> str:
        return (
            f"http://{self.MINIO_USER}:{self.MINIO_PASSWORD.get_secret_value()}"
            f"@{self.MINIO_HOST}:{self.MINIO_PORT}"
        )

    @property
    def qdrant_url(self) -> str:
        if self.QDRANT_PASSWORD is not None and self.QDRANT_PASSWORD.get_secret_value():
            return (
                f"http://{self.QDRANT_HOST}:{self.QDRANT_PORT}"
                f"?api_key={self.QDRANT_PASSWORD.get_secret_value()}"
            )
        return f"http://{self.QDRANT_HOST}:{self.QDRANT_PORT}"

    @property
    def airflow_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.AIRFLOW_USER}:{self.AIRFLOW_PASSWORD.get_secret_value()}"
            f"@{self.AIRFLOW_HOST}:{self.AIRFLOW_PORT}/{self.AIRFLOW_DB}"
        )

    @property
    def prometheus_url(self) -> str:
        return f"http://{self.PROMETHEUS_HOST}:{self.PROMETHEUS_PORT}"

    @property
    def grafana_url(self) -> str:
        return (
            f"http://{self.GRAFANA_USER}:{self.GRAFANA_PASSWORD.get_secret_value()}"
            f"@{self.GRAFANA_HOST}:{self.GRAFANA_PORT}"
        )

    @property
    def ollama_url(self) -> str:
        return f"http://{self.OLLAMA_HOST}:{self.OLLAMA_PORT}"


settings = Settings()