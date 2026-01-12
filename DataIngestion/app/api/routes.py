from fastapi import APIRouter, Depends, status, Path
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from DataIngestion.app.authorization.permission import require_roles
from DataIngestion.app.authorization.role import UserRole
from DataIngestion.app.schemas.error import ErrorPayload
from DataIngestion.app.services.sanitizer import normalize_payload
from DataIngestion.app.db.session import get_db
from DataIngestion.app.services.ingest import publish_and_store
from DataIngestion.app.core.config import settings
from DataIngestion.app.services.error_event_service import (
    get_all_errors,
    get_error_by_id,
)
from DataIngestion.app.exceptions.error_event_exception import (
    ErrorEventIngestionException,
)
from DataIngestion.app.models.user import User

router = APIRouter(prefix="/api/logs")


def convert_datetimes(o):
    if isinstance(o, dict):
        return {k: convert_datetimes(v) for k, v in o.items()}
    if isinstance(o, list):
        return [convert_datetimes(i) for i in o]
    if isinstance(o, datetime):
        return o.isoformat()
    return o


@router.post("/error", status_code=status.HTTP_201_CREATED)
async def receive_error(
    payload: ErrorPayload,
    db: AsyncSession = Depends(get_db),
):
    raw = payload.model_dump(by_alias=True, exclude_none=False)
    normalized = convert_datetimes(normalize_payload(raw))

    try:
        saved = await publish_and_store(
            db=db,
            normalized=normalized,
            kafka_topic=settings.KAFKA_TOPIC,
        )
        return {"status": "ok", "id": saved.id}

    except Exception:
        raise ErrorEventIngestionException()


@router.get("/errors")
async def list_errors(db: AsyncSession = Depends(get_db) , _: User = Depends(require_roles(UserRole.ADMIN)),):
    errors = await get_all_errors(db)

    return [
        {
            "id": e.id,
            "source": e.source,
            "function": e.function,
            "message": e.message,
            "message_court": e.message_court,
            "reference_id": e.reference_id,
            "stack_trace": e.stack_trace,
            "log_code": e.log_code,
            "created_date": e.created_date.isoformat() if e.created_date else None,
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "status": e.status,
        }
        for e in errors
    ]


@router.get("/errors/{error_id}")
async def get_error(
    error_id: int = Path(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    error = await get_error_by_id(db, error_id)

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
        "created_at": error.created_at.isoformat() if error.created_at else None,
        "status": error.status,
    }
