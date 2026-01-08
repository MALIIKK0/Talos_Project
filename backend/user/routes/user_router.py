from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session

from backend.auth.services.auth_service import get_current_active_user
from backend.core.database import get_db
from backend.user.models.user import User
from backend.user.schemas.user import UserSchema, UserCreate
from backend.user.services.user_service import get_users, create_user, get_user, delete_user, update_user
from backend.auth.permission import require_roles
from backend.core.security.roles import UserRole

user_router = APIRouter(
    prefix='/users',
    tags=['Users']
)


@user_router.get('/', response_model=list[UserSchema])
def user_list(db: Session = Depends(get_db) ,_: User = Depends(require_roles(UserRole.ADMIN))):
    db_users = get_users(db)

    return db_users


@user_router.get('/me', response_model=UserSchema)
def get_current_user(current_user: User = Depends(require_roles(UserRole.ADMIN))):
    return current_user



@user_router.get('/{user_id}', response_model=UserSchema)
def user_detail(user_id: int, db: Session = Depends(get_db) ,_: User = Depends(require_roles(UserRole.ADMIN))):
    db_user = get_user(db, user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return db_user


@user_router.delete('/{user_id}')
def user_delete(user_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN))):
    db_user = get_user(db, user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    delete_user(db, db_user.id)
    return {"message": "User deleted"}


@user_router.post("/", response_model=UserSchema)
def user_post(user: UserCreate, db:Session = Depends(get_db)):
    return create_user(db, user)
@user_router.put("/{user_id}", response_model=UserSchema)
def user_put(user_id: int, user: UserCreate, db:Session = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN))):
    return update_user(db, user_id, user)