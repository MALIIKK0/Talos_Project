"""
Async database session dependency.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from DataIngestion.app.db.engine import get_engine


def get_session_factory():
    """
    Create a sessionmaker bound to the engine.
    """
    return sessionmaker(
        get_engine(),
        expire_on_commit=False,
        class_=AsyncSession,
    )


async def get_db():
    """
    FastAPI dependency that yields a DB session.
    """
    session = get_session_factory()()

    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
