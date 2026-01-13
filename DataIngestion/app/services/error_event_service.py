from sqlalchemy import update
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from loguru import logger

from DataIngestion.app.models.error_event import ErrorEvent
from DataIngestion.app.exceptions.error_event_exception import (
    ErrorEventNotFoundException,
    ErrorEventDatabaseException,
)
async def mark_error_resolved(
    db: AsyncSession,
    reference_id: str,
) -> None:
    stmt = (
        update(ErrorEvent)
        .where(ErrorEvent.reference_id == reference_id)
        .values(status="resolved")
    )

    result = await db.execute(stmt)

    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Error event not found",
        )

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update error status",
        )
async def get_all_errors(db: AsyncSession) -> list[ErrorEvent]:
    try:
        result = await db.execute(
            select(ErrorEvent).order_by(ErrorEvent.created_date.desc())
        )
        return list(result.scalars().all())
    except SQLAlchemyError:
        logger.exception("Database error while fetching error events")
        raise ErrorEventDatabaseException()


async def get_error_by_id(db: AsyncSession, error_id: int) -> ErrorEvent:
    try:
        result = await db.execute(
            select(ErrorEvent).where(ErrorEvent.id == error_id)
        )
        error = result.scalar_one_or_none()

        if not error:
            raise ErrorEventNotFoundException(error_id)

        return error

    except SQLAlchemyError:
        logger.exception("Database error while fetching error event")
        raise ErrorEventDatabaseException()