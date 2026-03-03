from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=5, max_overflow=10)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created!")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()