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