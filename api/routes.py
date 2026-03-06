from agents.skill_gap_bridge import generate_skill_gap_bridge
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Header, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy.orm import Session
import tempfile, os

from agents.coordinator      import run_full_analysis
from agents.mock_interview   import evaluate_answer, generate_questions
from agents.job_recommender  import get_recommended_jobs
from agents.job_matcher      import calculate_match
from agents.ats_optimizer    import optimize_for_ats
from agents.roadmap_agent    import generate_roadmap
from agents.cover_letter     import generate_cover_letter
from agents.salary_predictor import predict_salary
from database.db             import get_db
from database.models         import User, Analysis
from database.auth           import (
    create_user, authenticate_user,
    get_user_by_email, create_token, decode_token
)

router = APIRouter()
bearer = HTTPBearer(auto_error=False)


# ── Auth dependency ───────────────────────────────────────────────────────────
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
):
    if not credentials:
        return None
    payload = decode_token(credentials.credentials)
    if not payload:
        return None
    return db.query(User).filter(User.id == payload.get("sub")).first()

def require_user(user: User = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# ══════════════════════════════════════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════════════════════════════════════
class SignupRequest(BaseModel):
    email:     str
    full_name: str
    password:  str

class LoginRequest(BaseModel):
    email:    str
    password: str

@router.post("/auth/signup")
def signup(req: SignupRequest, db: Session = Depends(get_db)):
    if get_user_by_email(db, req.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    user  = create_user(db, req.email, req.full_name, req.password)
    token = create_token(user.id, user.email)
    return {"token": token, "user": {"id": user.id, "email": user.email, "name": user.full_name}}

@router.post("/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_token(user.id, user.email)
    return {"token": token, "user": {"id": user.id, "email": user.email, "name": user.full_name}}

# ── Compatibility aliases ─────────────────────────────────────────────────────
@router.post("/signup")
def signup_alias(req: SignupRequest, db: Session = Depends(get_db)):
    return signup(req, db)

@router.post("/login")
def login_alias(req: LoginRequest, db: Session = Depends(get_db)):
    return login(req, db)

@router.get("/auth/me")
def me(user: User = Depends(require_user)):
    return {"id": user.id, "email": user.email, "full_name": user.full_name}


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
        "analysis_type":   "resume_jd",
        "created_at":      a.created_at.isoformat(),
    } for a in analyses]}

@router.get("/history/{analysis_id}")
def get_analysis(analysis_id: str, user: User = Depends(require_user), db: Session = Depends(get_db)):
    a = db.query(Analysis).filter(Analysis.id == analysis_id, Analysis.user_id == user.id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return {
        "id":             a.id,
        "company_name":   a.company_name,
        "resume_data":    a.resume_data,
        "match":          a.match_data,
        "ats":            a.ats_data,
        "roadmap":        a.roadmap_data,
        "interview":      a.interview_data,
        "cover_letter":   a.cover_letter_data,
        "salary":         a.salary_data,
        "created_at":     a.created_at.isoformat(),
    }

@router.delete("/history/{analysis_id}")
def delete_analysis(analysis_id: str, user: User = Depends(require_user), db: Session = Depends(get_db)):
    a = db.query(Analysis).filter(Analysis.id == analysis_id, Analysis.user_id == user.id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(a)
    db.commit()
    return {"message": "Deleted"}

@router.post("/history/save")
async def save_history(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    body = await request.json()
    a = Analysis(
        user_id          = user.id if user else None,
        company_name     = body.get("company_name"),
        job_description  = body.get("job_description"),
        match_percentage = body.get("match_score", 0),
        matched_skills   = [],
        missing_skills   = [],
        resume_filename  = "job_recommendation",
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

        # Add skill gap bridge
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
# REVERSE PITCH
# ══════════════════════════════════════════════════════════════════════════════
from agents.reverse_pitch_agent import analyze_project
from utils.email_service        import send_interest_notification, send_interest_confirmation
from database.models            import Project, ProjectInterest, Notification

class ProjectSubmitRequest(BaseModel):
    submitter_name:  str
    submitter_email: str
    title:           str
    description:     str
    github_url:      str = ""
    demo_url:        str = ""
    tech_stack:      list = []

@router.post("/projects/submit")
async def submit_project(
    req: ProjectSubmitRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Submit a project to the Reverse Pitch feed. Anyone can submit."""
    # AI analysis
    ai_result = analyze_project(
        title=req.title,
        description=req.description,
        tech_stack=req.tech_stack,
        github_url=req.github_url,
        demo_url=req.demo_url,
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
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    return JSONResponse(content={
        "status":     "submitted",
        "project_id": project.id,
        "ai_summary": project.ai_summary,
        "ai_tags":    project.ai_tags,
        "message":    "Your project is now live in the discovery feed!",
        **ai_result,
    })


@router.get("/projects")
def get_projects(
    domain:   str = "",
    tag:      str = "",
    limit:    int = 20,
    offset:   int = 0,
    db: Session = Depends(get_db),
):
    """Get all projects for the discovery feed. Public — no auth needed."""
    query = db.query(Project).filter(Project.is_active == True)
    projects = query.order_by(Project.created_at.desc()).offset(offset).limit(limit).all()

    # Increment views
    for p in projects:
        p.views = (p.views or 0) + 1
    db.commit()

    return JSONResponse(content={"projects": [
        {
            "id":             p.id,
            "title":          p.title,
            "description":    p.description[:300] + "..." if len(p.description) > 300 else p.description,
            "submitter_name": p.submitter_name,
            "github_url":     p.github_url,
            "demo_url":       p.demo_url,
            "tech_stack":     p.tech_stack or [],
            "ai_tags":        p.ai_tags or [],
            "ai_summary":     p.ai_summary or "",
            "views":          p.views or 0,
            "interest_count": p.interest_count or 0,
            "created_at":     p.created_at.isoformat(),
        }
        for p in projects
    ]})


class InterestRequest(BaseModel):
    recruiter_name:  str
    recruiter_email: str
    company_name:    str
    message:         str = ""

@router.post("/projects/{project_id}/interest")
def express_interest(
    project_id: str,
    req: InterestRequest,
    db: Session = Depends(get_db),
):
    """Recruiter expresses interest in a project. Sends email to candidate."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Save interest to DB
    interest = ProjectInterest(
        project_id      = project_id,
        recruiter_name  = req.recruiter_name,
        recruiter_email = req.recruiter_email,
        company_name    = req.company_name,
        message         = req.message,
    )
    db.add(interest)

    # Update interest count
    project.interest_count = (project.interest_count or 0) + 1

    # Save in-app notification
    notif = Notification(
        user_id  = project.user_id,
        email    = project.submitter_email,
        type     = "interest_received",
        title    = f"🎉 {req.recruiter_name} from {req.company_name} is interested!",
        message  = f"They're interested in your project: {project.title}",
        is_read  = False,
        data     = {
            "project_id":      project_id,
            "project_title":   project.title,
            "recruiter_name":  req.recruiter_name,
            "recruiter_email": req.recruiter_email,
            "company_name":    req.company_name,
            "message":         req.message,
        },
    )
    db.add(notif)
    db.commit()

    # Send emails
    send_interest_notification(
        candidate_name  = project.submitter_name,
        candidate_email = project.submitter_email,
        project_title   = project.title,
        recruiter_name  = req.recruiter_name,
        recruiter_email = req.recruiter_email,
        company_name    = req.company_name,
        message         = req.message,
    )
    send_interest_confirmation(
        recruiter_name  = req.recruiter_name,
        recruiter_email = req.recruiter_email,
        project_title   = project.title,
        candidate_name  = project.submitter_name,
        candidate_email = project.submitter_email,
    )

    return JSONResponse(content={
        "status":  "sent",
        "message": f"Your interest has been sent to {project.submitter_name}!",
    })


@router.get("/notifications")
def get_notifications(
    user: User = Depends(require_user),
    db:   Session = Depends(get_db),
):
    """Get in-app notifications for logged-in user."""
    notifs = (
        db.query(Notification)
        .filter(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(20)
        .all()
    )
    # Mark all as read
    for n in notifs:
        n.is_read = True
    db.commit()

    return {"notifications": [
        {
            "id":         n.id,
            "type":       n.type,
            "title":      n.title,
            "message":    n.message,
            "is_read":    n.is_read,
            "data":       n.data,
            "created_at": n.created_at.isoformat(),
        }
        for n in notifs
    ]}