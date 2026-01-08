"""
Application configuration management with Pydantic BaseSettings.
Includes validation and environment-specific defaults.
"""
from pydantic.v1 import validator
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, List
import os
from pathlib import Path
from urllib.parse import urlparse


class Settings(BaseSettings):
    # ========== FASTAPI SETTINGS ==========
    APP_HOST: str = Field("0.0.0.0", env="APP_HOST")
    APP_PORT: int = Field(8000, env="APP_PORT")
    ENVIRONMENT: str = Field("development", env="ENVIRONMENT")
    SERVICE_NAME: str = Field("error-ingestion", env="SERVICE_NAME")
    ORCHESTRATOR_URL: str = Field("http://localhost:8000/api/orchestrator/event", env="ORCHESTRATOR_URL")
    # Global database schema
    DB_SCHEMA: str = Field("state_db", env="DB_SCHEMA")
    # ========== DATABASE SETTINGS ==========
    DATABASE_URL: str = Field(
        "postgresql+asyncpg://state_user:state_password@localhost:5432/state_db",
        env="DATABASE_URL"
    )

    # Connection Pool Configuration
    DB_POOL_SIZE: int = Field(20, env="DB_POOL_SIZE",
                              description="Number of connections to keep open in the pool")

    DB_MAX_OVERFLOW: int = Field(10, env="DB_MAX_OVERFLOW",
                                 description="Maximum number of connections beyond pool_size")

    DB_POOL_TIMEOUT: int = Field(30, env="DB_POOL_TIMEOUT",
                                 description="Seconds to wait for a connection")

    DB_POOL_RECYCLE: int = Field(1800, env="DB_POOL_RECYCLE",
                                 description="Seconds after which a connection is recycled")

    DB_ECHO: bool = Field(False, env="DB_ECHO",
                          description="Log SQL statements")

    DB_ECHO_POOL: bool = Field(False, env="DB_ECHO_POOL",
                               description="Log connection pool events")

    DB_STATEMENT_TIMEOUT: int = Field(30000, env="DB_STATEMENT_TIMEOUT",
                                      description="Maximum statement execution time in milliseconds")

    DB_USE_SSL: bool = Field(False, env="DB_USE_SSL",
                             description="Use SSL for database connections")

    # ========== KAFKA SETTINGS ==========
    KAFKA_BOOTSTRAP_SERVERS: str = Field("localhost:29092", env="KAFKA_BOOTSTRAP_SERVERS")
    KAFKA_TOPIC: str = Field("error_events", env="KAFKA_TOPIC")
    KAFKA_CLIENT_ID: str = Field("error-ingestion-service", env="KAFKA_CLIENT_ID")
    KAFKA_CONSUMER_GROUP: str = Field("data_ingestion_group", env="KAFKA_CONSUMER_GROUP")

    # ========== APPLICATION SETTINGS ==========
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field("json", env="LOG_FORMAT")
    API_PREFIX: str = "/api"
    API_V1_STR: str = "/v1"

    # ========== SECURITY SETTINGS ==========
    API_KEY: Optional[str] = Field(None, env="API_KEY")
    CORS_ORIGINS: List[str] = Field(["*"], env="CORS_ORIGINS")

    # ========== VALIDATORS ==========
    @validator("DATABASE_URL")
    def validate_database_url(cls, v):
        """Validate DATABASE_URL format."""
        if not v:
            raise ValueError("DATABASE_URL is required")

        parsed = urlparse(v)
        if parsed.scheme not in ["postgresql", "postgresql+asyncpg"]:
            raise ValueError(f"Unsupported database scheme: {parsed.scheme}")

        return v

    @validator("KAFKA_BOOTSTRAP_SERVERS")
    def validate_kafka_servers(cls, v):
        """Validate Kafka bootstrap servers."""
        if not v:
            raise ValueError("KAFKA_BOOTSTRAP_SERVERS is required")

        servers = v.split(",")
        if len(servers) == 0:
            raise ValueError("At least one Kafka bootstrap server is required")

        return v

    @validator("DB_POOL_SIZE")
    def validate_pool_size(cls, v):
        if v < 1:
            raise ValueError("DB_POOL_SIZE must be at least 1")
        if v > 100:
            raise ValueError("DB_POOL_SIZE should not exceed 100")
        return v

    @validator("DB_POOL_RECYCLE")
    def validate_pool_recycle(cls, v):
        if v < 60:
            raise ValueError("DB_POOL_RECYCLE should be at least 60 seconds")
        return v

    @validator("ENVIRONMENT")
    def validate_environment(cls, v):
        allowed = ["development", "testing", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}")
        return v

    # ========== COMPUTED PROPERTIES ==========
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_testing(self) -> bool:
        return self.ENVIRONMENT == "testing"

    @property
    def database_schema(self) -> str:
        """Extract schema name from DATABASE_URL."""
        parsed = urlparse(self.DATABASE_URL)
        db_path = parsed.path.lstrip('/')
        return db_path.split('?')[0]  # Remove query parameters

    @property
    def database_driver(self) -> str:
        """Extract driver from DATABASE_URL."""
        parsed = urlparse(self.DATABASE_URL)
        return parsed.scheme

    # ========== CONFIGURATION ==========
    class Config:
        env_file = f".env.{os.getenv('ENVIRONMENT', 'development')}"
        env_file_encoding = "utf-8"
        case_sensitive = False

        @classmethod
        def customise_sources(cls, init_settings, env_settings, file_secret_settings):
            """Customize configuration loading order."""
            # 1. Environment variables (.env file)
            # 2. Environment variables (system)
            # 3. Default values
            return (
                env_settings,
                init_settings,
                file_secret_settings,
            )


# Global settings instance
settings = Settings()


# Optional: Create environment-specific .env files
def create_env_file_if_not_exists():
    """Create default .env file if it doesn't exist."""
    env_file = Path(f".env.{settings.ENVIRONMENT}")

    if not env_file.exists():
        env_file.write_text("""# Application Configuration
# Environment: {environment}

# Database
DATABASE_URL=postgresql+asyncpg://state_user:state_password@localhost:5432/state_db
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800
DB_ECHO=false
DB_USE_SSL=false

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC=error_events
KAFKA_CLIENT_ID=error-ingestion-service

# Application
APP_HOST=0.0.0.0
APP_PORT=8000
ENVIRONMENT=development
SERVICE_NAME=error-ingestion
LOG_LEVEL=INFO
LOG_FORMAT=json
API_KEY=

# Security
CORS_ORIGINS=["*"]
""".format(environment=settings.ENVIRONMENT))
        print(f"✅ Created default configuration file: {env_file}")


# Create env file on import (optional)
if __name__ != "__main__":
    create_env_file_if_not_exists()