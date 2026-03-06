from sqlalchemy import Column, String, Float, DateTime, Text, ForeignKey, JSON, Boolean, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    id              = Column(String, primary_key=True, default=generate_uuid)
    email           = Column(String, unique=True, nullable=False, index=True)
    full_name       = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at      = Column(DateTime, default=datetime.utcnow)
    analyses        = relationship("Analysis", back_populates="user", cascade="all, delete")
    projects        = relationship("Project", back_populates="user", cascade="all, delete")
    notifications   = relationship("Notification", back_populates="user", cascade="all, delete")

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

class Project(Base):
    __tablename__ = "projects"
    id              = Column(String, primary_key=True, default=generate_uuid)
    # nullable user_id — anyone can submit, logged-in users get linked
    user_id         = Column(String, ForeignKey("users.id"), nullable=True)
    # Submitter info (for non-logged-in users)
    submitter_name  = Column(String, nullable=False)
    submitter_email = Column(String, nullable=False, index=True)
    # Project details
    title           = Column(String, nullable=False)
    description     = Column(Text, nullable=False)
    github_url      = Column(String, nullable=True)
    demo_url        = Column(String, nullable=True)
    tech_stack      = Column(JSON)       # ["Python", "React", "FastAPI"]
    ai_tags         = Column(JSON)       # AI-generated role tags ["Backend Dev", "ML Engineer"]
    ai_summary      = Column(Text)       # AI-generated 1-line summary
    # Stats
    views           = Column(Integer, default=0)
    interest_count  = Column(Integer, default=0)
    # Status
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    # Relations
    user            = relationship("User", back_populates="projects")
    interests       = relationship("ProjectInterest", back_populates="project", cascade="all, delete")

class ProjectInterest(Base):
    __tablename__ = "project_interests"
    id               = Column(String, primary_key=True, default=generate_uuid)
    project_id       = Column(String, ForeignKey("projects.id"), nullable=False)
    # Recruiter info
    recruiter_name   = Column(String, nullable=False)
    recruiter_email  = Column(String, nullable=False)
    company_name     = Column(String, nullable=False)
    message          = Column(Text, nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow)
    # Relations
    project          = relationship("Project", back_populates="interests")

class Notification(Base):
    __tablename__ = "notifications"
    id         = Column(String, primary_key=True, default=generate_uuid)
    user_id    = Column(String, ForeignKey("users.id"), nullable=True)
    email      = Column(String, nullable=False)  # for non-logged-in users too
    type       = Column(String)   # "interest_received"
    title      = Column(String)
    message    = Column(Text)
    is_read    = Column(Boolean, default=False)
    data       = Column(JSON)     # extra context e.g. project_id, recruiter info
    created_at = Column(DateTime, default=datetime.utcnow)
    user       = relationship("User", back_populates="notifications")