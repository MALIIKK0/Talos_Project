from datetime import datetime, timedelta, timezone
import secrets

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from DataIngestion.app.models.refresh_token import RefreshToken
from DataIngestion.app.models.user import User
from DataIngestion.app.exceptions.refresh_token_exception import (
    InvalidRefreshTokenException,
    RevokedRefreshTokenException,
    ExpiredRefreshTokenException,
    RefreshTokenCreationException,
)
from sqlalchemy import update

REFRESH_TOKEN_EXPIRE_DAYS = 7


async def create_refresh_token(
    db: AsyncSession,
    user: User,
) -> RefreshToken:
    try:
        #  Revoke any existing tokens first
        await revoke_existing_refresh_tokens(db, user.id)

        # Generate new token
        token = secrets.token_urlsafe(64)
        expires_at = (
            datetime.now(timezone.utc)
            + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        )

        refresh_token = RefreshToken(
            token=token,
            user_id=user.id,
            expires_at=expires_at,
            revoked=False,
        )

        db.add(refresh_token)
        await db.commit()
        await db.refresh(refresh_token)

        return refresh_token

    except SQLAlchemyError:
        await db.rollback()
        raise RefreshTokenCreationException()


async def validate_refresh_token(
    db: AsyncSession,
    token: str,
) -> RefreshToken:
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == token)
    )
    refresh_token = result.scalar_one_or_none()

    if not refresh_token:
        raise InvalidRefreshTokenException()

    if refresh_token.revoked:
        raise RevokedRefreshTokenException()

    if refresh_token.expires_at < datetime.now(timezone.utc):
        raise ExpiredRefreshTokenException()

    return refresh_token


async def revoke_refresh_token(
    db: AsyncSession,
    token: str,
) -> None:
    refresh_token = await validate_refresh_token(db, token)

    refresh_token.revoked = True
    await db.commit()

async def revoke_existing_refresh_tokens(
    db: AsyncSession,
    user_id: int,
):
    """
    Revoke all existing refresh tokens for a user.
    """
    await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked == False,
        )
        .values(revoked=True)
    )