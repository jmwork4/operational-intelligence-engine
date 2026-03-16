from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://oie:oie_password@localhost:5432/oie"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Object Storage
    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin123"
    S3_BUCKET_NAME: str = "oie-documents"
    S3_REGION: str = "us-east-1"

    # Application
    ENVIRONMENT: str = "dev"
    LOG_LEVEL: str = "INFO"
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # Auth
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # AI
    DEFAULT_MODEL_PROVIDER: str = "anthropic"
    DEFAULT_MODEL_NAME: str = "claude-sonnet-4-20250514"
    MAX_CONTEXT_TOKENS: int = 128000

    # Rate Limiting (requests per minute, per tenant)
    RATE_LIMIT_BASIC: int = 60
    RATE_LIMIT_PROFESSIONAL: int = 300
    RATE_LIMIT_ENTERPRISE: int = 1000

    # Observability
    OTEL_SERVICE_NAME: str = "oie-api"
    OTEL_EXPORTER_ENDPOINT: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
