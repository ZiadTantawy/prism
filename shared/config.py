from typing import Optional

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    # PostgreSQL — set DATABASE_URL to override individual fields (e.g. inside Docker)
    POSTGRES_USER: str
    POSTGRES_PASSWORD: SecretStr
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    DATABASE_URL: Optional[str] = None
    DATABASE_POOL_SIZE: int = 5
    DATABASE_POOL_MAX_OVERFLOW: int = 10
    DATABASE_ECHO: bool = False

    # Qdrant (set QDRANT_URL or both QDRANT_HOST and QDRANT_PORT)
    QDRANT_HOST: str
    QDRANT_PORT: int
    QDRANT_URL: Optional[str] = None

    # RabbitMQ (set RABBITMQ_URL or RABBITMQ_USER, PASSWORD, HOST, PORT)
    RABBITMQ_USER: str
    RABBITMQ_PASSWORD: SecretStr
    RABBITMQ_HOST: str
    RABBITMQ_PORT: int
    RABBITMQ_URL: Optional[str] = None

    # API
    API_PORT: int
    API_V1_STR: str
    PROJECT_NAME: str
    VERSION: str
    DESCRIPTION: str

    # LLM providers
    OLLAMA_BASE_URL: str
    OLLAMA_MODEL: str

    GROQ_BASE_URL: str
    GROQ_API_KEY: Optional[SecretStr] = None
    GROQ_MODEL: Optional[str] = None

    GEMINI_BASE_URL: str
    GEMINI_API_KEY: Optional[SecretStr] = None
    GEMINI_MODEL: Optional[str] = None

    OPENROUTER_BASE_URL: str
    OPENROUTER_API_KEY: Optional[SecretStr] = None
    OPENROUTER_MODEL: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def postgres_sync_url(self) -> str:
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            if url.startswith("postgresql+asyncpg://"):
                return url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
            return url
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD.get_secret_value()}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def postgres_async_url(self) -> str:
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            if url.startswith("postgresql+psycopg://"):
                return url.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)
            return url
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD.get_secret_value()}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def qdrant_url(self) -> str:
        if self.QDRANT_URL:
            return self.QDRANT_URL.rstrip("/")
        return f"http://{self.QDRANT_HOST}:{self.QDRANT_PORT}"

    @property
    def rabbitmq_url(self) -> str:
        if self.RABBITMQ_URL:
            return self.RABBITMQ_URL.rstrip("/") + "/"
        return (
            f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD.get_secret_value()}"
            f"@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/"
        )


settings = Settings()