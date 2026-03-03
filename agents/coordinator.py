from concurrent.futures import ThreadPoolExecutor, as_completed
from agents.resume_analyzer import analyze_resume
from agents.job_matcher import calculate_match
from agents.ats_optimizer import optimize_for_ats
from agents.roadmap_agent import generate_roadmap
from agents.mock_interview import generate_questions
from agents.cover_letter import generate_cover_letter
from agents.salary_predictor import predict_salary

def run_full_analysis(file_path: str, job_description: str, company_name: str = "the company", location: str = "India") -> dict:
    
    # Step 1: Analyze resume first (everything depends on this)
    print("📄 Analyzing resume...")
    resume_data = analyze_resume(file_path)
    
    # Step 2: Get job match (needed by ATS + Roadmap)
    print("🔍 Calculating job match...")
    match_data = calculate_match(resume_data, job_description)
    missing_skills = match_data.get("missing_skills", [])

    # Step 3: Run remaining agents in parallel
    print("⚡ Running all agents in parallel...")
    results = {}

    def run_ats():
        return "ats", optimize_for_ats(resume_data, job_description, missing_skills)

    def run_roadmap():
        return "roadmap", generate_roadmap(resume_data, job_description, missing_skills)

    def run_interview():
        return "interview", generate_questions(resume_data, job_description)

    def run_cover_letter():
        return "cover_letter", generate_cover_letter(resume_data, job_description, company_name)

    def run_salary():
        return "salary", predict_salary(resume_data, job_description, location)

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(run_ats),
            executor.submit(run_roadmap),
            executor.submit(run_interview),
            executor.submit(run_cover_letter),
            executor.submit(run_salary),
        ]
        for future in as_completed(futures):
            key, value = future.result()
            results[key] = value
            print(f"  ✅ {key} done")

    return {
        "resume": resume_data,
        "match": match_data,
        "ats": results.get("ats"),
        "roadmap": results.get("roadmap"),
        "interview": results.get("interview"),
        "cover_letter": results.get("cover_letter"),
        "salary": results.get("salary"),
    }