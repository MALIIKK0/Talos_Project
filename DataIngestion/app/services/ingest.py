# app/services/ingest.py

from sqlalchemy.ext.asyncio import AsyncSession
from DataIngestion.app.models.error_event import ErrorEvent
from DataIngestion.app.kafka.producer import publish_event
from typing import Dict, Any
from loguru import logger
from datetime import datetime
from fastapi.encoders import jsonable_encoder


# ---------------------------------------------------------
# DATETIME PARSER → ensures createdDate is always datetime
# ---------------------------------------------------------
def parse_datetime_safe(value):
    """
    Convert ISO8601 / Salesforce / Z-format into Python datetime.
    Always returns a timezone-aware datetime or None.
    """
    if not value:
        return None

    if isinstance(value, datetime):
        return value

    # Normalize Z → +00:00
    if isinstance(value, str):
        v = value.replace("Z", "+00:00")

        # Fix Salesforce "+0000" → "+00:00"
        if "+" in v and len(v.split("+")[-1]) == 4:
            v = v[:-2] + ":" + v[-2:]

        try:
            return datetime.fromisoformat(v)
        except Exception:
            pass

    logger.warning(f"Could not parse datetime: {value}")
    return None


# ---------------------------------------------------------
# PERSIST TO POSTGRES
# ---------------------------------------------------------
async def persist_event(db: AsyncSession, normalized: Dict[str, Any]) -> ErrorEvent:
    """
    Save normalized payload into DB and return ORM object.
    """

    # Convert createdDate → datetime for DB
    created_dt = parse_datetime_safe(normalized.get("createdDate"))

    # Make raw_payload JSON serializable
    raw_payload_safe = jsonable_encoder(normalized)

    obj = ErrorEvent(
        source=normalized.get("source"),
        function=normalized.get("function"),
        message=normalized.get("message"),
        message_court=normalized.get("messageCourt") or normalized.get("message_court"),
        reference_id=normalized.get("referenceId"),
        stack_trace=normalized.get("stackTrace"),
        log_code=normalized.get("logCode"),
        created_date=created_dt,            # REAL datetime stored in DB
        status=normalized.get("status", "processing"),
        #raw_payload=raw_payload_safe        # JSON-safe sanitized payload
    )

    db.add(obj)
    await db.flush()
    await db.commit()
    await db.refresh(obj)

    logger.info(f"Persisted event with id {obj.id}")
    return obj


# ---------------------------------------------------------
# KAFKA + DB PIPELINE
# ---------------------------------------------------------
async def publish_and_store(db: AsyncSession, normalized: Dict[str, Any], kafka_topic: str):
    """
    Publish to Kafka then save to DB.
    """

    # Publish event (non-blocking)
    try:
        key = normalized.get("referenceId")
        await publish_event(kafka_topic, key, jsonable_encoder(normalized))
    except Exception as e:
        logger.warning(f"Kafka publish failed: {e}")

    # Always persist into DB
    return await persist_event(db, normalized)