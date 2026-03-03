import json
import re
from utils.llm_client import ask_llm

def generate_cover_letter(resume_data: dict, job_description: str, company_name: str = "the company") -> dict:
    prompt = f"""
Write a professional cover letter for this candidate.

Candidate:
- Name: {resume_data.get('name', 'Candidate')}
- Skills: {resume_data.get('skills', [])}
- Projects: {resume_data.get('projects', [])}
- Education: {resume_data.get('education', [])}
- Domain: {resume_data.get('domain', 'Technology')}
- Experience: {resume_data.get('experience_years', 0)} years

Company: {company_name}
Job Description: {job_description[:1500]}

Return ONLY valid JSON:
{{
  "subject_line": "Application for [Role] at [Company]",
  "cover_letter": "Full cover letter text here (3-4 paragraphs)",
  "key_points_highlighted": ["Point 1", "Point 2", "Point 3"],
  "tone": "Professional and enthusiastic",
  "word_count": 250
}}
"""
    result = ask_llm(prompt, system="You are an expert career coach who writes compelling cover letters. Return ONLY valid JSON.")
    try:
        return json.loads(result.strip())
    except:
        match = re.search(r'\{.*\}', result, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {"error": "Could not parse response"}