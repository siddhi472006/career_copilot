from sqlalchemy import Column, String, Float, DateTime, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    id               = Column(String, primary_key=True, default=generate_uuid)
    email            = Column(String, unique=True, nullable=False, index=True)
    full_name        = Column(String, nullable=False)
    hashed_password  = Column(String, nullable=False)
    created_at       = Column(DateTime, default=datetime.utcnow)
    analyses         = relationship("Analysis", back_populates="user", cascade="all, delete")

class Analysis(Base):
    __tablename__ = "analyses"
    id                = Column(String, primary_key=True, default=generate_uuid)
    user_id           = Column(String, ForeignKey("users.id"), nullable=False)
    resume_filename   = Column(String)
    job_description   = Column(Text)
    company_name      = Column(String)
    location          = Column(String)
    resume_data       = Column(JSON)
    match_data        = Column(JSON)
    ats_data          = Column(JSON)
    roadmap_data      = Column(JSON)
    interview_data    = Column(JSON)
    cover_letter_data = Column(JSON)
    salary_data       = Column(JSON)
    match_percentage  = Column(Float, default=0.0)
    matched_skills    = Column(JSON)
    missing_skills    = Column(JSON)
    created_at        = Column(DateTime, default=datetime.utcnow)
    user              = relationship("User", back_populates="analyses")