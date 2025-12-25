from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Optional, List
from urllib.parse import urlparse


class Settings(BaseSettings):

    # ✅ Pydantic v2 configuration (ONLY THIS)
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow",          # allow extra env vars safely
        case_sensitive=False,
    )

    # ---------- APP ----------
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    ENVIRONMENT: str = "development"
    SERVICE_NAME: str = "error-ingestion"
    ORCHESTRATOR_URL: str = "http://localhost:8000/api/orchestrator/event"

    # ---------- DATABASE ----------
    DATABASE_URL: str = Field(...)
    DB_SCHEMA: str = "state_db"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    DB_ECHO: bool = False
    DB_USE_SSL: bool = False

    # ---------- KAFKA ----------
    KAFKA_BOOTSTRAP_SERVERS: str = Field(...)
    KAFKA_TOPIC: str = "error_events"
    KAFKA_CONSUMER_GROUP: str = "data_ingestion_group"
    KAFKA_CLIENT_ID: str = "error-ingestion-service"

    # ---------- LOGGING ----------
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # ---------- SECURITY ----------
    API_KEY: Optional[str] = None
    CORS_ORIGINS: List[str] = ["*"]

    # ---------- VALIDATORS (v2 style) ----------
    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        parsed = urlparse(v)
        if parsed.scheme not in ("postgresql", "postgresql+asyncpg"):
            raise ValueError("Invalid DATABASE_URL scheme")
        return v

    @field_validator("KAFKA_BOOTSTRAP_SERVERS")
    @classmethod
    def validate_kafka_servers(cls, v: str) -> str:
        if not v:
            raise ValueError("KAFKA_BOOTSTRAP_SERVERS is required")
        return v


settings = Settings()
print("KAFKA_BOOTSTRAP_SERVERS =", settings.KAFKA_BOOTSTRAP_SERVERS)
