from sqlalchemy.orm import Session

from backend.auth.utils.auth_utils import get_password_hash
from backend.user.models.user import User
from backend.user.schemas.user import UserCreate


def get_users(db: Session):
    return db.query(User).all()


def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, user: UserCreate):

    db_user = get_user_by_email(db, user.email)
    if db_user:
        raise ValueError("Email already registered")
    db_user = User(
        email=str(user.email),
        username=user.username,
        password=get_password_hash(user.password),
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, user_id: int):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        db.delete(db_user)
        db.commit()
    return

def update_user(db: Session, user_id: int, updated_user: UserCreate):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise ValueError("User not found")
    db_user.username = updated_user.username
    db_user.email = str(updated_user.email)
    db_user.password = get_password_hash(updated_user.password)
    db.commit()
    db.refresh(db_user)
    return db_user