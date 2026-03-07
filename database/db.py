from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=5, max_overflow=10)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base is defined HERE — models.py imports Base from db.py (not the other way around)
Base = declarative_base()

def init_db():
    # Import models here (inside function) to avoid circular import
    import database.models  # noqa — ensures all models are registered
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created!")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()