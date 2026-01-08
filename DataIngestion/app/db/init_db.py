"""
Database initialization (schema + tables).
"""
from sqlalchemy import text
from loguru import logger
from DataIngestion.app.db.engine import get_engine
from DataIngestion.app.models.error_event import Base
from DataIngestion.app.core.config import settings


async def create_schema():
    """
    Ensure the schema exists.
    """
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {settings.DB_SCHEMA}"))
        logger.debug(f"Schema ensured ({settings.DB_SCHEMA})")


async def create_tables():
    """
    Create all ORM tables inside the configured schema.
    """
    engine = get_engine()

    # Apply schema dynamically to ALL models
    for table in Base.metadata.tables.values():
        table.schema = settings.DB_SCHEMA

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info(f"Tables created successfully in schema {settings.DB_SCHEMA}")


async def validate_connection():
    """
    Validate DB connectivity.
    """
    engine = get_engine()

    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT 1"))
        if result.scalar() != 1:
            raise RuntimeError("Database validation failed")

    logger.info("Database connection validated")


async def init_db():
    """
    Full DB initialization pipeline.
    """
    logger.info("Starting DB initialization...")
    await create_schema()
    await create_tables()
    logger.info("DB initialization finished")
