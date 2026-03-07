from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database.models import User
import os
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET      = os.getenv("JWT_SECRET", "career_copilot_secret_2026")
JWT_ALGORITHM   = "HS256"
JWT_EXPIRE_DAYS = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_token(user_id, email: str, role: str = "candidate") -> str:
    payload = {
        "sub":          str(user_id),   # always store as string
        "email":        email,
        "role":         role,
        "recruiter_id": str(user_id) if role == "recruiter" else None,
        "exp":          datetime.utcnow() + timedelta(days=JWT_EXPIRE_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return {}
    except Exception:
        return {}

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, email: str, full_name: str, password: str):
    user = User(email=email, full_name=full_name, hashed_password=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user