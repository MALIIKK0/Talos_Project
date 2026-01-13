from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from DataIngestion.app.models.user import User
from DataIngestion.app.schemas.user import UserCreate
from DataIngestion.app.utils.auth_utils import get_password_hash

from DataIngestion.app.exceptions.user_exception import (
    UserNotFoundException,
    UserAlreadyExistsException,
    UserCreationException,
    UserUpdateException,
    UserDeleteException,
)

# -------------------------
# READ
# -------------------------
async def get_users(db: AsyncSession) -> list[User]:
    result = await db.execute(select(User))
    return list(result.scalars().all())


async def get_user(db: AsyncSession, user_id: int) -> User:
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise UserNotFoundException()

    return user


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(
        select(User).where(User.email == email)
    )
    return result.scalar_one_or_none()


# -------------------------
# CREATE
# -------------------------
async def create_user(db: AsyncSession, user: UserCreate) -> User:
    existing_user = await get_user_by_email(db, str(user.email))
    if existing_user:
        raise UserAlreadyExistsException("Email already registered")

    db_user = User(
        username=user.username,
        email=str(user.email),
        password=get_password_hash(user.password),
        role=user.role,
        is_active=True,
    )

    db.add(db_user)

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise UserCreationException()

    await db.refresh(db_user)
    return db_user


# -------------------------
# DELETE
# -------------------------
async def delete_user(db: AsyncSession, user_id: int) -> None:
    user = await get_user(db, user_id)

    await db.delete(user)

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise UserDeleteException()


# -------------------------
# UPDATE
# -------------------------
async def update_user(
    db: AsyncSession,
    user_id: int,
    updated_user: UserCreate,
) -> User:
    db_user = await get_user(db, user_id)

    db_user.username = updated_user.username
    db_user.email = str(updated_user.email)
    db_user.password = get_password_hash(updated_user.password)

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise UserUpdateException()

    await db.refresh(db_user)
    return db_user
