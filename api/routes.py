from agents.skill_gap_bridge import generate_skill_gap_bridge
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Header, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy.orm import Session
from datetime import datetime
import tempfile, os

from agents.coordinator      import run_full_analysis
from agents.mock_interview   import evaluate_answer, generate_questions
from agents.job_recommender  import get_recommended_jobs
from agents.job_matcher      import calculate_match
from agents.ats_optimizer    import optimize_for_ats
from agents.roadmap_agent    import generate_roadmap
from agents.cover_letter     import generate_cover_letter
from agents.salary_predictor import predict_salary
from agents.reverse_pitch_agent import analyze_project
from utils.email_service        import send_interest_notification, send_interest_confirmation
from utils.otp_service          import (
    is_work_email, detect_company, extract_domain,
    generate_otp, hash_otp, verify_otp_hash, otp_expiry, send_otp_email,
)
from database.db             import get_db
from database.models         import (
    User, Analysis, Project, ProjectInterest,
    Notification, Recruiter, RecruiterBookmark,
)
from database.auth           import (
    create_user, authenticate_user,
    get_user_by_email, create_token, decode_token,
    hash_password, verify_password,
)

router = APIRouter()
bearer = HTTPBearer(auto_error=False)


# ── Candidate auth dependency ─────────────────────────────────────────────────
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
):
    if not credentials:
        return None
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("role", "candidate") != "candidate":
        return None
    return db.query(User).filter(User.id == payload.get("sub")).first()

def require_user(user: User = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# ── Recruiter auth dependency ─────────────────────────────────────────────────
def get_current_recruiter(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
):
    if not credentials:
        return None
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("role") != "recruiter":
        return None
    return db.query(Recruiter).filter(Recruiter.id == payload.get("sub")).first()

def require_recruiter(recruiter: Recruiter = Depends(get_current_recruiter)):
    if not recruiter:
        raise HTTPException(status_code=401, detail="Recruiter authentication required")
    return recruiter


# ══════════════════════════════════════════════════════════════════════════════
# AUTH (candidates)
# ══════════════════════════════════════════════════════════════════════════════
class SignupRequest(BaseModel):
    email:     str
    full_name: str
    password:  str

class LoginRequest(BaseModel):
    email:    str
    password: str

class CandidateForgotRequest(BaseModel):
    email: str

class CandidateResetRequest(BaseModel):
    email:    str
    otp:      str
    password: str


@router.post("/auth/signup")
def signup(req: SignupRequest, db: Session = Depends(get_db)):
    if get_user_by_email(db, req.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    user  = create_user(db, req.email, req.full_name, req.password)
    token = create_token(user.id, user.email, role="candidate")
    return {"token": token, "user": {"id": user.id, "email": user.email, "name": user.full_name}}

@router.post("/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_token(user.id, user.email, role="candidate")
    return {"token": token, "user": {"id": user.id, "email": user.email, "name": user.full_name}}

@router.post("/signup")
def signup_alias(req: SignupRequest, db: Session = Depends(get_db)):
    return signup(req, db)

@router.post("/login")
def login_alias(req: LoginRequest, db: Session = Depends(get_db)):
    return login(req, db)

@router.get("/auth/me")
def me(user: User = Depends(require_user)):
    return {"id": user.id, "email": user.email, "full_name": user.full_name}


# ── Candidate Forgot Password ─────────────────────────────────────────────────
@router.post("/auth/forgot-password")
def candidate_forgot_password(req: CandidateForgotRequest, db: Session = Depends(get_db)):
    email = req.email.strip().lower()
    user  = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="No account found with this email.")

    otp = generate_otp()
    user.otp_code    = hash_otp(otp)
    user.otp_expires = otp_expiry()
    db.commit()

    email_sent = send_otp_email(email, user.full_name or "User", otp, "AI Career Copilot")
    return {
        "status":     "otp_sent",
        "email_sent": email_sent,
        "message":    f"Verification code sent to {email}. Valid for 10 minutes.",
    }


@router.post("/auth/reset-password")
def candidate_reset_password(req: CandidateResetRequest, db: Session = Depends(get_db)):
    email     = req.email.strip().lower()
    otp_input = req.otp.strip()
    password  = req.password.strip()

    if not password or len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="No account found with this email.")

    if not user.otp_expires or datetime.utcnow() > user.otp_expires:
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")

    if not verify_otp_hash(otp_input, user.otp_code or ""):
        raise HTTPException(status_code=400, detail="Incorrect code. Please try again.")

    user.hashed_password = hash_password(password)
    user.otp_code        = None
    user.otp_expires     = None
    db.commit()
    db.refresh(user)

    token = create_token(user.id, user.email, role="candidate")
    return {
        "token": token,
        "user":  {"id": user.id, "email": user.email, "name": user.full_name},
    }


# ══════════════════════════════════════════════════════════════════════════════
# HISTORY
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/history")
def get_history(user: User = Depends(require_user), db: Session = Depends(get_db)):
    analyses = (
        db.query(Analysis)
        .filter(Analysis.user_id == user.id)
        .order_by(Analysis.created_at.desc())
        .limit(20)
        .all()
    )
    return {"history": [{
        "id":              a.id,
        "company":         a.company_name,
        "job_description": (a.job_description or "")[:100] + "...",
        "match_score":     a.match_percentage,
        "matched_skills":  a.matched_skills or [],
        "missing_skills":  a.missing_skills or [],
        "resume_filename": a.resume_filename,
        "analysis_type":   a.analysis_type or "resume_jd",
        "created_at":      (a.created_at.isoformat() if a.created_at else ""),
    } for a in analyses]}

@router.get("/history/{analysis_id}")
def get_analysis(analysis_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)):
    a = db.query(Analysis).filter(Analysis.id == analysis_id, Analysis.user_id == user.id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return {
        "id":           a.id,
        "company_name": a.company_name,
        "resume_data":  a.resume_data,
        "match":        a.match_data,
        "ats":          a.ats_data,
        "roadmap":      a.roadmap_data,
        "interview":    a.interview_data,
        "cover_letter": a.cover_letter_data,
        "salary":       a.salary_data,
        "created_at":   (a.created_at.isoformat() if a.created_at else ""),
    }

@router.delete("/history/{analysis_id}")
def delete_analysis(analysis_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)):
    a = db.query(Analysis).filter(Analysis.id == analysis_id, Analysis.user_id == user.id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(a)
    db.commit()
    return {"message": "Deleted"}

@router.post("/history/save")
async def save_history(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user:
        return {"status": "skipped"}
    body = await request.json()
    a = Analysis(
        user_id          = user.id,
        company_name     = body.get("company_name"),
        job_description  = body.get("job_description"),
        match_percentage = body.get("match_score", 0),
        matched_skills   = [],
        missing_skills   = [],
        resume_filename  = "job_recommendation",
        analysis_type    = body.get("analysis_type", "resume_jd"),
    )
    db.add(a)
    db.commit()
    return {"status": "saved"}


# ══════════════════════════════════════════════════════════════════════════════
# ANALYZE
# ══════════════════════════════════════════════════════════════════════════════
@router.post("/analyze")
async def analyze(
    resume:          UploadFile = File(...),
    job_description: str = Form(...),
    company_name:    str = Form("the company"),
    location:        str = Form("India"),
    user:   User    = Depends(get_current_user),
    db:     Session = Depends(get_db),
):
    suffix = ".pdf" if resume.filename.endswith(".pdf") else ".docx"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await resume.read())
        tmp_path = tmp.name
    try:
        result = run_full_analysis(tmp_path, job_description, company_name, location)

        missing   = result.get("match", {}).get("missing_skills", [])
        match_pct = result.get("match", {}).get("match_percentage", 0)
        result["skill_bridge"] = generate_skill_gap_bridge(missing, match_pct, company_name)

        if user:
            match = result.get("match", {})
            a = Analysis(
                user_id           = user.id,
                resume_filename   = resume.filename,
                job_description   = job_description,
                company_name      = company_name,
                location          = location,
                resume_data       = result.get("resume"),
                match_data        = match,
                ats_data          = result.get("ats"),
                roadmap_data      = result.get("roadmap"),
                interview_data    = result.get("interview"),
                cover_letter_data = result.get("cover_letter"),
                salary_data       = result.get("salary"),
                match_percentage  = match.get("match_percentage", 0),
                matched_skills    = match.get("matched_skills", []),
                missing_skills    = match.get("missing_skills", []),
            )
            db.add(a)
            db.commit()
            result["analysis_id"] = a.id

        return JSONResponse(content=result)
    finally:
        os.unlink(tmp_path)


@router.post("/evaluate-answer")
async def evaluate(
    question:        str = Form(...),
    answer:          str = Form(...),
    job_description: str = Form(...),
):
    return JSONResponse(content=evaluate_answer(question, answer, job_description))


@router.get("/health")
def health():
    return {"status": "ok", "agents": 9}


# ══════════════════════════════════════════════════════════════════════════════
# JOB RECOMMENDATIONS
# ══════════════════════════════════════════════════════════════════════════════
class JobRecommendRequest(BaseModel):
    resume_data:    dict
    adzuna_app_id:  str = ""
    adzuna_app_key: str = ""
    max_results:    int = 15

@router.post("/recommend-jobs")
async def recommend_jobs(req: JobRecommendRequest):
    jobs = get_recommended_jobs(
        resume_data    = req.resume_data,
        adzuna_app_id  = req.adzuna_app_id,
        adzuna_app_key = req.adzuna_app_key,
        max_results    = req.max_results,
    )
    return JSONResponse(content={"jobs": jobs})


# ══════════════════════════════════════════════════════════════════════════════
# JOB ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
class JobAnalysisRequest(BaseModel):
    resume_data:     dict
    job_title:       str
    job_description: str
    company_name:    str = "the company"

@router.post("/analyze-job")
async def analyze_job(req: JobAnalysisRequest):
    resume_data = req.resume_data
    jd          = req.job_description
    company     = req.company_name

    match_data = calculate_match(resume_data, jd)
    missing    = match_data.get("missing_skills", [])
    match_pct  = match_data.get("match_percentage", 0)

    def run_ats():
        r = optimize_for_ats(resume_data, jd, missing)
        if "keywords_to_add" not in r:
            r["keywords_to_add"] = missing[:10]
        return "ats", r

    results = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(run_ats),
            executor.submit(lambda: ("roadmap",      generate_roadmap(resume_data, jd, missing))),
            executor.submit(lambda: ("interview",    generate_questions(resume_data, jd))),
            executor.submit(lambda: ("cover_letter", generate_cover_letter(resume_data, jd, company))),
            executor.submit(lambda: ("salary",       predict_salary(resume_data, jd, company_name=company))),
        ]
        for f in as_completed(futures):
            key, val = f.result()
            results[key] = val

    return JSONResponse(content={
        "match":        match_data,
        "ats":          results.get("ats",          {}),
        "roadmap":      results.get("roadmap",      {}),
        "interview":    results.get("interview",    {}),
        "cover_letter": results.get("cover_letter", {}),
        "salary":       results.get("salary",       {}),
        "skill_bridge": generate_skill_gap_bridge(missing, match_pct, req.job_title),
    })


# ══════════════════════════════════════════════════════════════════════════════
# REVERSE PITCH — PROJECTS
# ══════════════════════════════════════════════════════════════════════════════
class ProjectSubmitRequest(BaseModel):
    submitter_name:  str
    submitter_email: str
    title:           str
    description:     str
    github_url:      str = ""
    demo_url:        str = ""
    tech_stack:      list = []

def _calc_relevance_score(ai_result: dict) -> float:
    score = 40.0
    complexity = (ai_result.get("complexity") or "").lower()
    if "advanced" in complexity:   score += 25
    elif "intermediate" in complexity: score += 15
    elif "beginner" in complexity: score += 5
    tags = ai_result.get("ai_tags") or []
    score += min(len(tags) * 5, 15)
    suitable = ai_result.get("suitable_for") or []
    if "Full-time"  in suitable: score += 10
    if "Internship" in suitable: score += 5
    wow = ai_result.get("wow_factor") or ""
    if len(wow) > 20: score += 5
    return min(round(score, 1), 100.0)


@router.post("/projects/submit")
async def submit_project(
    req: ProjectSubmitRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ai_result = analyze_project(
        title=req.title, description=req.description,
        tech_stack=req.tech_stack, github_url=req.github_url, demo_url=req.demo_url,
    )
    project = Project(
        user_id         = user.id if user else None,
        submitter_name  = req.submitter_name,
        submitter_email = req.submitter_email,
        title           = req.title,
        description     = req.description,
        github_url      = req.github_url or None,
        demo_url        = req.demo_url or None,
        tech_stack      = req.tech_stack,
        ai_tags         = ai_result.get("ai_tags", []),
        ai_summary      = ai_result.get("ai_summary", ""),
        relevance_score = _calc_relevance_score(ai_result),
        views           = 0,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return JSONResponse(content={
        "status": "submitted", "project_id": project.id,
        "ai_summary": project.ai_summary, "ai_tags": project.ai_tags,
        "relevance_score": project.relevance_score,
        "message": "Your project is now live in the discovery feed!",
        **ai_result,
    })


# ── Helper: ensure project_views table exists ─────────────────────────────────
_views_table_ensured = False

def _ensure_views_table(db: Session):
    global _views_table_ensured
    if _views_table_ensured:
        return
    try:
        db.execute(__import__("sqlalchemy").text("""
            CREATE TABLE IF NOT EXISTS project_views (
                id           SERIAL PRIMARY KEY,
                project_id   INTEGER NOT NULL,
                recruiter_id INTEGER NOT NULL,
                viewed_at    TIMESTAMP DEFAULT NOW(),
                UNIQUE(project_id, recruiter_id)
            )
        """))
        db.commit()
        _views_table_ensured = True
    except Exception:
        db.rollback()


@router.get("/projects")
def get_projects(
    search:       str = "",
    sort_by:      str = "relevance",
    role_filter:  str = "",
    recruiter_id: int = 0,
    track_views:  str = "false",
    limit:        int = 50,
    offset:       int = 0,
    db: Session = Depends(get_db),
):
    from sqlalchemy import or_, cast, Text, text

    query = db.query(Project).filter(Project.is_active == True)

    if search.strip():
        term = f"%{search.strip().lower()}%"
        query = query.filter(or_(
            Project.title.ilike(term), Project.description.ilike(term),
            Project.submitter_name.ilike(term),
            cast(Project.tech_stack, Text).ilike(term),
            cast(Project.ai_tags, Text).ilike(term),
        ))

    if role_filter.strip():
        role_map = {
            "Frontend": "Frontend", "Backend": "Backend", "Full Stack": "Full Stack",
            "ML/AI": "ML", "Data Science": "Data", "DevOps": "DevOps", "Mobile": "Mobile",
        }
        search_term = role_map.get(role_filter, role_filter)
        query = query.filter(cast(Project.ai_tags, Text).ilike(f"%{search_term}%"))

    if sort_by in ("newest", "recent"):
        query = query.order_by(Project.created_at.desc())
    elif sort_by == "interest":
        from sqlalchemy import func
        query = (
            query.outerjoin(ProjectInterest, ProjectInterest.project_id == Project.id)
            .group_by(Project.id)
            .order_by(func.count(ProjectInterest.id).desc(), Project.created_at.desc())
        )
    else:
        query = query.order_by(Project.relevance_score.desc(), Project.created_at.desc())

    projects = query.offset(offset).limit(limit).all()

    if track_views == "true" and recruiter_id and projects:
        _ensure_views_table(db)
        try:
            for p in projects:
                result = db.execute(text("""
                    INSERT INTO project_views (project_id, recruiter_id)
                    VALUES (:pid, :rid)
                    ON CONFLICT (project_id, recruiter_id) DO NOTHING
                """), {"pid": p.id, "rid": recruiter_id})
                if result.rowcount > 0:
                    p.views = (p.views or 0) + 1
            db.commit()
        except Exception:
            db.rollback()

    bookmarked_ids = set()
    if recruiter_id:
        bmarks = db.query(RecruiterBookmark).filter(
            RecruiterBookmark.recruiter_id == recruiter_id
        ).all()
        bookmarked_ids = {b.project_id for b in bmarks}

    return JSONResponse(content={"projects": [
        {
            "id": p.id, "title": p.title,
            "description": p.description[:300] + "..." if len(p.description) > 300 else p.description,
            "submitter_name": p.submitter_name,
            "github_url": p.github_url, "demo_url": p.demo_url,
            "tech_stack": p.tech_stack or [], "ai_tags": p.ai_tags or [],
            "ai_summary": p.ai_summary or "",
            "relevance_score": p.relevance_score or 0,
            "views": p.views or 0,
            "interest_count": len(p.interests),
            "is_bookmarked": p.id in bookmarked_ids,
            "created_at": (p.created_at.isoformat() if p.created_at else ""),
        }
        for p in projects
    ]})


class InterestRequest(BaseModel):
    recruiter_id:    int = 0
    recruiter_name:  str
    recruiter_email: str
    company_name:    str
    message:         str = ""

@router.post("/projects/{project_id}/interest")
def express_interest(project_id: int, req: InterestRequest, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    existing = db.query(ProjectInterest).filter(
        ProjectInterest.project_id      == project_id,
        ProjectInterest.recruiter_email == req.recruiter_email,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You have already expressed interest in this project")

    interest = ProjectInterest(
        project_id=project_id, recruiter_id=req.recruiter_id or None,
        recruiter_name=req.recruiter_name, recruiter_email=req.recruiter_email,
        company_name=req.company_name, message=req.message,
    )
    db.add(interest)

    if project.user_id:
        db.add(Notification(
            user_id=project.user_id, type="interest_received",
            title=f"🎉 {req.recruiter_name} from {req.company_name} is interested!",
            message=f"They're interested in your project: {project.title}",
            is_read=False,
            data={
                "project_id": project_id, "project_title": project.title,
                "recruiter_name": req.recruiter_name, "recruiter_email": req.recruiter_email,
                "company_name": req.company_name, "message": req.message,
            },
        ))

    db.commit()

    try:
        send_interest_notification(
            candidate_name=project.submitter_name, candidate_email=project.submitter_email,
            project_title=project.title, recruiter_name=req.recruiter_name,
            recruiter_email=req.recruiter_email, company_name=req.company_name, message=req.message,
        )
        send_interest_confirmation(
            recruiter_name=req.recruiter_name, recruiter_email=req.recruiter_email,
            project_title=project.title, candidate_name=project.submitter_name,
            candidate_email=project.submitter_email,
        )
    except Exception:
        pass

    return JSONResponse(content={"status": "sent", "message": f"Your interest has been sent to {project.submitter_name}!"})


@router.post("/projects/{project_id}/bookmark")
def toggle_bookmark(project_id: int, db: Session = Depends(get_db), recruiter: Recruiter = Depends(require_recruiter)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    existing = db.query(RecruiterBookmark).filter(
        RecruiterBookmark.recruiter_id == recruiter.id,
        RecruiterBookmark.project_id   == project_id,
    ).first()
    if existing:
        db.delete(existing); db.commit()
        return {"action": "removed", "bookmarked": False}
    else:
        db.add(RecruiterBookmark(recruiter_id=recruiter.id, project_id=project_id)); db.commit()
        return {"action": "saved", "bookmarked": True}


@router.get("/recruiter/bookmarks")
def get_bookmarks(db: Session = Depends(get_db), recruiter: Recruiter = Depends(require_recruiter)):
    bmarks = db.query(RecruiterBookmark).filter(
        RecruiterBookmark.recruiter_id == recruiter.id
    ).order_by(RecruiterBookmark.created_at.desc()).all()
    projects = []
    for b in bmarks:
        p = b.project
        if p and p.is_active:
            projects.append({
                "id": p.id, "title": p.title, "submitter_name": p.submitter_name,
                "description": p.description[:300] + "..." if len(p.description) > 300 else p.description,
                "github_url": p.github_url, "demo_url": p.demo_url,
                "tech_stack": p.tech_stack or [], "ai_tags": p.ai_tags or [],
                "ai_summary": p.ai_summary or "", "relevance_score": p.relevance_score or 0,
                "views": p.views or 0, "interest_count": len(p.interests),
                "is_bookmarked": True,
                "bookmarked_at": (b.created_at.isoformat() if b.created_at else ""),
                "created_at": (p.created_at.isoformat() if p.created_at else ""),
            })
    return {"bookmarks": projects}


@router.get("/recruiter/activity")
def get_recruiter_activity(db: Session = Depends(get_db), recruiter: Recruiter = Depends(require_recruiter)):
    from sqlalchemy import or_
    interests = db.query(ProjectInterest).filter(
        or_(
            ProjectInterest.recruiter_id    == recruiter.id,
            ProjectInterest.recruiter_email == recruiter.email,
        )
    ).order_by(ProjectInterest.created_at.desc()).limit(50).all()
    return {"activities": [
        {
            "project_title":  i.project.title if i.project else "Unknown",
            "candidate_name": i.project.submitter_name if i.project else "Unknown",
            "company_name":   i.company_name,
            "message":        i.message or "",
            "created_at":     (i.created_at.isoformat() if i.created_at else ""),
        }
        for i in interests
    ]}


# ══════════════════════════════════════════════════════════════════════════════
# NOTIFICATIONS
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/notifications")
def get_notifications(user: User = Depends(require_user), db: Session = Depends(get_db)):
    notifs = (
        db.query(Notification)
        .filter(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(20).all()
    )
    result = [{
        "id": n.id, "type": n.type or "info", "title": n.title or "",
        "message": n.message, "is_read": n.is_read,
        "data": n.data or {},
        "created_at": (n.created_at.isoformat() if n.created_at else ""),
    } for n in notifs]
    for n in notifs:
        n.is_read = True
    db.commit()
    return {"notifications": result}


# ══════════════════════════════════════════════════════════════════════════════
# RECRUITER AUTH
# ══════════════════════════════════════════════════════════════════════════════
class RecruiterCheckRequest(BaseModel):
    email: str

class RecruiterLoginRequest(BaseModel):
    email:    str
    password: str

class RecruiterOTPRequest(BaseModel):
    email:     str
    full_name: str = ""

class RecruiterVerifyRequest(BaseModel):
    email:     str
    otp:       str
    full_name: str = ""
    password:  str = ""


@router.post("/recruiter/check-email")
def recruiter_check_email(req: RecruiterCheckRequest, db: Session = Depends(get_db)):
    email = req.email.strip().lower()
    if not is_work_email(email):
        raise HTTPException(status_code=400, detail="Please use your work email address (not Gmail, Yahoo, Hotmail, etc.)")
    recruiter = db.query(Recruiter).filter(Recruiter.email == email).first()
    has_password = bool(recruiter and recruiter.hashed_password)
    return {
        "exists": bool(recruiter), "has_password": has_password,
        "company": recruiter.company_name if recruiter else detect_company(email),
    }


@router.post("/recruiter/login")
def recruiter_login(req: RecruiterLoginRequest, db: Session = Depends(get_db)):
    email     = req.email.strip().lower()
    recruiter = db.query(Recruiter).filter(Recruiter.email == email).first()
    if not recruiter or not recruiter.hashed_password:
        raise HTTPException(status_code=400, detail="No password set for this account. Please sign in with OTP.")
    if not verify_password(req.password, recruiter.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect password.")
    recruiter.last_login = datetime.utcnow()
    db.commit(); db.refresh(recruiter)
    token = create_token(recruiter.id, recruiter.email, role="recruiter")
    return {"token": token, "recruiter": {
        "id": recruiter.id, "email": recruiter.email,
        "full_name": recruiter.full_name, "company_name": recruiter.company_name,
        "email_domain": recruiter.email_domain,
    }}


@router.post("/recruiter/send-otp")
def recruiter_send_otp(req: RecruiterOTPRequest, db: Session = Depends(get_db)):
    email = req.email.strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    if not is_work_email(email):
        raise HTTPException(status_code=400, detail="Please use your work email address (not Gmail, Yahoo, Hotmail, etc.)")
    company = detect_company(email)
    domain  = extract_domain(email)
    otp     = generate_otp()
    recruiter = db.query(Recruiter).filter(Recruiter.email == email).first()
    if recruiter:
        recruiter.otp_code    = hash_otp(otp)
        recruiter.otp_expires = otp_expiry()
        if req.full_name: recruiter.full_name = req.full_name
    else:
        recruiter = Recruiter(
            email=email, full_name=req.full_name or "", company_name=company,
            email_domain=domain, is_verified=False,
            otp_code=hash_otp(otp), otp_expires=otp_expiry(),
        )
        db.add(recruiter)
    db.commit()
    email_sent = send_otp_email(email, req.full_name or "Recruiter", otp, company)
    return {
        "status": "otp_sent", "company_detected": company,
        "email_sent": email_sent,
        "message": f"Verification code sent to {email}. Valid for 10 minutes.",
    }


@router.post("/recruiter/verify-otp")
def recruiter_verify_otp(req: RecruiterVerifyRequest, db: Session = Depends(get_db)):
    email     = req.email.strip().lower()
    otp_input = req.otp.strip()
    full_name = req.full_name.strip()
    password  = req.password.strip()
    if not email or not otp_input:
        raise HTTPException(status_code=400, detail="Email and OTP are required")
    if not password or len(password) < 6:
        raise HTTPException(status_code=400, detail="Please set a password of at least 6 characters")
    recruiter = db.query(Recruiter).filter(Recruiter.email == email).first()
    if not recruiter:
        raise HTTPException(status_code=404, detail="No OTP request found. Please request a new code.")
    if not recruiter.otp_expires or datetime.utcnow() > recruiter.otp_expires:
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")
    if not verify_otp_hash(otp_input, recruiter.otp_code or ""):
        raise HTTPException(status_code=400, detail="Incorrect code. Please try again.")
    recruiter.is_verified     = True
    recruiter.otp_code        = None
    recruiter.otp_expires     = None
    recruiter.last_login      = datetime.utcnow()
    recruiter.hashed_password = hash_password(password)
    if full_name: recruiter.full_name = full_name
    db.commit(); db.refresh(recruiter)
    token = create_token(recruiter.id, recruiter.email, role="recruiter")
    return {"token": token, "recruiter": {
        "id": recruiter.id, "email": recruiter.email,
        "full_name": recruiter.full_name, "company_name": recruiter.company_name,
        "email_domain": recruiter.email_domain,
    }}


@router.get("/recruiter/me")
def recruiter_me(recruiter: Recruiter = Depends(require_recruiter), db: Session = Depends(get_db)):
    bookmark_count = db.query(RecruiterBookmark).filter(RecruiterBookmark.recruiter_id == recruiter.id).count()
    interest_count = db.query(ProjectInterest).filter(ProjectInterest.recruiter_id == recruiter.id).count()
    return {
        "id": recruiter.id, "email": recruiter.email,
        "full_name": recruiter.full_name, "company_name": recruiter.company_name,
        "email_domain": recruiter.email_domain,
        "bookmark_count": bookmark_count, "interest_count": interest_count,
        "member_since": recruiter.created_at.strftime("%b %Y"),
    }