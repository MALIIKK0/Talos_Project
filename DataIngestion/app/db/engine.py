"""
Database engine management (optimized).
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.pool import AsyncAdaptedQueuePool
from DataIngestion.app.core.config import settings
from loguru import logger

_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    """
    Return the singleton engine. Raises error if not initialized.
    """
    if _engine is None:
        raise RuntimeError("Engine not initialized. Call init_engine() first.")
    return _engine


async def init_engine() -> AsyncEngine:
    """
    Initialize the async SQLAlchemy engine once.
    """
    global _engine

    if _engine is not None:
        return _engine

    logger.info("Initializing database engine...")

    _engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=AsyncAdaptedQueuePool,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_pre_ping=True,
        echo=settings.DB_ECHO and settings.is_development,
        future=True,
    )

    logger.info("Database engine initialized")
    return _engine


async def dispose_engine():
    """
    Dispose the engine on shutdown.
    """
    global _engine

    if _engine:
        await _engine.dispose()
        _engine = None
        logger.info("Database engine disposed")
