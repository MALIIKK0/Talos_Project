# app/api/routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from DataIngestion.app.schemas.error import ErrorPayload
from DataIngestion.app.services.sanitizer import normalize_payload
from DataIngestion.app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from DataIngestion.app.services.ingest import publish_and_store
from DataIngestion.app.core.config import settings
from loguru import logger
from datetime import datetime
from sqlalchemy.future import select
from DataIngestion.app.models.error_event import ErrorEvent
from fastapi import Path

router = APIRouter(prefix="/api/logs")

# -------------------------
# FIX: helper for JSON serialization
# -------------------------
def convert_datetimes(o):
    if isinstance(o, dict):
        return {k: convert_datetimes(v) for k, v in o.items()}
    if isinstance(o, list):
        return [convert_datetimes(i) for i in o]
    if isinstance(o, datetime):
        return o.isoformat()
    return o

@router.post("/error", status_code=201)
async def receive_error(payload: ErrorPayload, db: AsyncSession = Depends(get_db)):
    """
    Receives a JSON error event from Salesforce, validates (Pydantic),
    sanitizes, normalizes, persists to Postgres and publishes to Kafka.
    """
    try:
        raw = payload.dict(by_alias=True, exclude_none=False)
        normalized = normalize_payload(raw)

        # 🔥 APPLY FIX HERE
        normalized = convert_datetimes(normalized)

        saved = await publish_and_store(db, normalized, settings.KAFKA_TOPIC)
        return {"status": "ok", "id": saved.id}

    except Exception as e:
        logger.exception("Failed to process incoming error: {}", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal ingestion error"
        )


@router.get("/errors")
async def get_all_errors(db: AsyncSession = Depends(get_db)):
    """
    Returns all error events from the database.
    """
    result = await db.execute(select(ErrorEvent).order_by(ErrorEvent.created_date.desc()))
    errors = result.scalars().all()

    # Serialize for JSON response
    def serialize(e: ErrorEvent):
        return {
            "id": e.id,
            "source": e.source,
            "function": e.function,
            "message": e.message,
            "message_court": e.message_court,
            "reference_id": e.reference_id,
            "stack_trace": e.stack_trace,
            "log_code": e.log_code,
            "created_date": e.created_date.isoformat() if e.created_date else None,
           # "raw_payload": e.raw_payload,
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "status": e.status,
        }

    return [serialize(e) for e in errors]

@router.get("/errors/{error_id}")
async def get_error_by_id(
    error_id: int = Path(..., description="ID of the error event"),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns a single error event by its ID.
    """
    result = await db.execute(select(ErrorEvent).where(ErrorEvent.id == error_id))
    error = result.scalar_one_or_none()

    if not error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Error event with id {error_id} not found"
        )

    # Serialize for JSON response
    return {
        "id": error.id,
        "source": error.source,
        "function": error.function,
        "message": error.message,
        "message_court": error.message_court,
        "reference_id": error.reference_id,
        "stack_trace": error.stack_trace,
        "log_code": error.log_code,
        "created_date": error.created_date.isoformat() if error.created_date else None,
        # "raw_payload": error.raw_payload,
        "created_at": error.created_at.isoformat() if error.created_at else None,
        "status": error.status,
    }