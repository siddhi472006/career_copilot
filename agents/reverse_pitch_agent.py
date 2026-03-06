"""
Reverse Pitch Agent
Analyzes a submitted project and generates:
- AI role tags (what kind of jobs this project suits)
- AI summary (1-line pitch)
- Relevant skills detected
"""

import json
import re
from utils.llm_client import ask_llm


def analyze_project(
    title: str,
    description: str,
    tech_stack: list,
    github_url: str = "",
    demo_url: str = "",
) -> dict:
    """Analyze a project and return AI tags, summary, and role matches."""

    prompt = f"""
You are a technical recruiter analyzing a candidate's project.

Project Title: {title}
Description: {description}
Tech Stack: {", ".join(tech_stack) if tech_stack else "Not specified"}
GitHub: {github_url or "Not provided"}
Demo: {demo_url or "Not provided"}

Analyze this project and return ONLY valid JSON:
{{
  "ai_summary": "One compelling sentence describing this project for recruiters (max 20 words)",
  "role_tags": ["Backend Developer", "ML Engineer"],
  "skill_tags": ["Python", "FastAPI", "Machine Learning"],
  "complexity": "Beginner|Intermediate|Advanced",
  "wow_factor": "One sentence about what makes this project impressive",
  "suitable_for": ["Internship", "Full-time", "Freelance"],
  "domain": "Web Development|Data Science|Mobile|DevOps|AI/ML|Other"
}}

role_tags must be 2-4 specific job roles this project demonstrates.
skill_tags must be actual technical skills visible in the project.
"""

    result = ask_llm(prompt, system="You are a technical recruiter. Return ONLY valid JSON, no other text.")
    try:
        data = json.loads(result.strip())
    except Exception:
        m = re.search(r'\{.*\}', result, re.DOTALL)
        data = json.loads(m.group()) if m else {}

    return {
        "ai_summary":   data.get("ai_summary", f"{title} — a {', '.join(tech_stack[:2])} project"),
        "ai_tags":      data.get("role_tags", ["Software Developer"]),
        "skill_tags":   data.get("skill_tags", tech_stack[:5]),
        "complexity":   data.get("complexity", "Intermediate"),
        "wow_factor":   data.get("wow_factor", ""),
        "suitable_for": data.get("suitable_for", ["Internship", "Full-time"]),
        "domain":       data.get("domain", "Other"),
    }