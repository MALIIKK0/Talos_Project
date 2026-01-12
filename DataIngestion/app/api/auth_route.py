from fastapi import APIRouter, Depends, Body
from datetime import timedelta
from typing import Annotated

from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from DataIngestion.app.db.session import get_db
from DataIngestion.app.models.token import Token
from DataIngestion.app.services.auth_service import (
    authenticate_user,
    create_access_token,
)
from DataIngestion.app.services.refresh_token_services import (
    create_refresh_token,
    validate_refresh_token,
    revoke_refresh_token,
)

auth_router = APIRouter(prefix="/api/auth", tags=["Auth"])


@auth_router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_db),
):
    user = await authenticate_user(
        form_data.username,
        form_data.password,
        db,
    )

    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=15),
    )

    refresh_token = await create_refresh_token(db, user)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token.token,
        token_type="bearer",
    )


@auth_router.post("/refresh", response_model=Token)
async def refresh_access_token(
    refresh_token: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
):
    stored_token = await validate_refresh_token(db, refresh_token)

    user = stored_token.user

    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=15),
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@auth_router.post("/logout")
async def logout(
    refresh_token: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
):
    await revoke_refresh_token(db, refresh_token)
    return {"detail": "Logged out successfully"}
