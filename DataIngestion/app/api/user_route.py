from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from DataIngestion.app.db.session import get_db
from DataIngestion.app.models.user import User
from DataIngestion.app.schemas.user import UserSchema, UserCreate
from DataIngestion.app.services.user_service import (
    get_users,
    create_user,
    get_user,
    delete_user,
    update_user,
)
from DataIngestion.app.authorization.permission import require_roles
from DataIngestion.app.authorization.role import UserRole

user_router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@user_router.get("/", response_model=list[UserSchema])
async def user_list(
    db: AsyncSession = Depends(get_db),

):
    return await get_users(db)


@user_router.get("/me", response_model=UserSchema)
async def get_current_user(
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    return current_user


@user_router.get("/{user_id}", response_model=UserSchema)
async def user_detail(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    db_user = await get_user(db, user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@user_router.delete("/{user_id}")
async def user_delete(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    db_user = await get_user(db, user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    await delete_user(db, db_user.id)
    return {"message": "User deleted"}


@user_router.post("/", response_model=UserSchema)
async def user_post(
    user: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await create_user(db, user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@user_router.put("/{user_id}", response_model=UserSchema)
async def user_put(
    user_id: int,
    user: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    try:
        return await update_user(db, user_id, user)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
