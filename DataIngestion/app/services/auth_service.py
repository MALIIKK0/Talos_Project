from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from DataIngestion.app.core.config import settings
from DataIngestion.app.db.session import get_db
from DataIngestion.app.models.user import User
from DataIngestion.app.services.user_service import get_user_by_email
from DataIngestion.app.utils.auth_utils import verify_password
from DataIngestion.app.exceptions.auth_exception import (
    InvalidCredentialsException,
    InactiveUserException,
    TokenExpiredException,
    InvalidTokenException,
    UserFromTokenNotFoundException,
)

SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


# -------------------------
# AUTHENTICATION
# -------------------------
async def authenticate_user(
    email: str,
    password: str,
    db: AsyncSession,
) -> User:
    user = await get_user_by_email(db, email)

    if not user or not verify_password(password, str(user.password)):
        raise InvalidCredentialsException()

    if not user.is_active:
        raise InactiveUserException()

    return user


# -------------------------
# JWT
# -------------------------
def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None,
) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=15)
    )

    to_encode = data | {"exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# -------------------------
# CURRENT USER
# -------------------------
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise InvalidTokenException()

    except ExpiredSignatureError:
        raise TokenExpiredException()
    except InvalidTokenError:
        raise InvalidTokenException()

    user = await get_user_by_email(db, email)
    if not user:
        raise UserFromTokenNotFoundException()

    if not user.is_active:
        raise InactiveUserException()

    return user
