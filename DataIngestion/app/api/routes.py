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
