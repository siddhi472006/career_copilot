from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text,
    DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.db import Base


class User(Base):
    __tablename__ = "users"
    id              = Column(Integer, primary_key=True, index=True)
    email           = Column(String, unique=True, index=True, nullable=False)
    full_name       = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    otp_code        = Column(String,   nullable=True)   # for forgot-password flow
    otp_expires     = Column(DateTime, nullable=True)   # for forgot-password flow
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    analyses      = relationship("Analysis",      back_populates="user")
    projects      = relationship("Project",       back_populates="user")
    notifications = relationship("Notification",  back_populates="user")

    @property
    def name(self):
        return self.full_name


class Analysis(Base):
    __tablename__ = "analyses"
    id                = Column(Integer, primary_key=True, index=True)
    user_id           = Column(Integer, ForeignKey("users.id"), nullable=True)
    resume_filename   = Column(String,  nullable=True)
    job_description   = Column(Text,    nullable=True)
    company_name      = Column(String,  nullable=True)
    location          = Column(String,  nullable=True)
    match_percentage  = Column(Float,   default=0.0)
    resume_data       = Column(JSON,    nullable=True)
    match_data        = Column(JSON,    nullable=True)
    ats_data          = Column(JSON,    nullable=True)
    roadmap_data      = Column(JSON,    nullable=True)
    interview_data    = Column(JSON,    nullable=True)
    cover_letter_data = Column(JSON,    nullable=True)
    salary_data       = Column(JSON,    nullable=True)
    matched_skills    = Column(JSON,    default=list)
    missing_skills    = Column(JSON,    default=list)
    analysis_type     = Column(String,  default="resume_jd")
    created_at        = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="analyses")


class Project(Base):
    __tablename__ = "projects"
    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=True)
    submitter_name  = Column(String,  nullable=False)
    submitter_email = Column(String,  nullable=False, index=True)
    title           = Column(String,  nullable=False)
    description     = Column(Text,    nullable=False)
    github_url      = Column(String,  nullable=True)
    demo_url        = Column(String,  nullable=True)
    tech_stack      = Column(JSON,    default=list)
    ai_tags         = Column(JSON,    default=list)
    ai_summary      = Column(Text,    nullable=True)
    relevance_score = Column(Float,   default=0.0)
    views           = Column(Integer, default=0)
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    user      = relationship("User",             back_populates="projects")
    interests = relationship("ProjectInterest",  back_populates="project")
    bookmarks = relationship("RecruiterBookmark", back_populates="project")


class ProjectInterest(Base):
    __tablename__ = "project_interests"
    id              = Column(Integer, primary_key=True, index=True)
    project_id      = Column(Integer, ForeignKey("projects.id"),   nullable=False)
    recruiter_id    = Column(Integer, ForeignKey("recruiters.id"), nullable=True)
    recruiter_name  = Column(String,  nullable=False)
    recruiter_email = Column(String,  nullable=False)
    company_name    = Column(String,  nullable=False)
    message         = Column(Text,    nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    project   = relationship("Project",   back_populates="interests")
    recruiter = relationship("Recruiter", back_populates="interests")


class Notification(Base):
    __tablename__ = "notifications"
    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    type       = Column(String,  default="info")
    title      = Column(String,  nullable=True)
    message    = Column(Text,    nullable=False)
    is_read    = Column(Boolean, default=False)
    data       = Column(JSON,    nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="notifications")


class Recruiter(Base):
    __tablename__ = "recruiters"
    id              = Column(Integer, primary_key=True, index=True)
    email           = Column(String,  unique=True, index=True, nullable=False)
    full_name       = Column(String,  nullable=True)
    company_name    = Column(String,  nullable=True)
    email_domain    = Column(String,  nullable=True)
    hashed_password = Column(String,  nullable=True)
    is_verified     = Column(Boolean, default=False)
    otp_code        = Column(String,  nullable=True)
    otp_expires     = Column(DateTime, nullable=True)
    last_login      = Column(DateTime, nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    bookmarks = relationship("RecruiterBookmark", back_populates="recruiter")
    interests = relationship("ProjectInterest",   back_populates="recruiter")


class RecruiterBookmark(Base):
    __tablename__ = "recruiter_bookmarks"
    id           = Column(Integer, primary_key=True, index=True)
    recruiter_id = Column(Integer, ForeignKey("recruiters.id"), nullable=False)
    project_id   = Column(Integer, ForeignKey("projects.id"),   nullable=False)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    recruiter = relationship("Recruiter", back_populates="bookmarks")
    project   = relationship("Project",   back_populates="bookmarks")