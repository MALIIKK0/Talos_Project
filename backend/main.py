from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from backend.core.config_loader import settings
from backend.core.database import engine, Base

from backend.auth.routes.auth_router import auth_router
from backend.user.routes.user_router import user_router

openapi_tags = [
    {
        "name": "Users",
        "description": "User operations",
    },
    {
        "name": "Health Checks",
        "description": "Application health checks",
    }
]

app = FastAPI(openapi_tags=openapi_tags)
Base.metadata.create_all(bind=engine)

if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            str(origin).strip("/") for origin in settings.BACKEND_CORS_ORIGINS
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(auth_router, prefix='/api')
app.include_router(user_router, prefix='/api', tags=['Users'])

@app.get("/health", tags=['Health Checks'])
def read_root():
    return {"health": "true"}






















'''from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from pydantic import BaseModel
from typing import List , Optional

#database setup
DATABASE_URL = "sqlite:///./dash.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

#Database models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    role = Column(String, index=True)
    
Base.metadata.create_all(engine)    

class UserCreate(BaseModel):
    name: str
    email: str
    role: str
    
class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    
    class Config:
        from_attributes = True 

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
                   
get_db()

app = FastAPI(title = "User Management API")

@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/users/", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    if(db.query(User).filter(User.email == user.email).first()):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    db_user = User(name=user.name, email=user.email, role=user.role)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


#update user
@app.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db_user.name = user.name
    db_user.email = user.email
    db_user.role = user.role
    db.commit()
    db.refresh(db_user)
    return db_user


#delete user
@app.delete("/users/{user_id}")
def delete_user(user_id: int , db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(db_user)
    db.commit()
    return {"detail": "User deleted successfully"}


#get all users
@app.get("/users/", response_model=List[UserResponse])
def get_users(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    users = db.query(User).offset(skip).limit(limit).all()
    return users'''