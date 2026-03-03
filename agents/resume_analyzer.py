import json
import re
from utils.pdf_parser import extract_text
from utils.llm_client import ask_llm

def analyze_resume(file_path: str) -> dict:
    # Step 1: Extract raw text
    raw_text = extract_text(file_path)

    # Step 2: Send to LLM for structured extraction
    prompt = f"""
Extract structured information from this resume.
Return ONLY valid JSON with exactly these keys:

{{
  "name": "Full Name",
  "email": "email@example.com",
  "phone": "phone number or empty string",
  "skills": ["Python", "Machine Learning"],
  "experience_years": 2,
  "education": [
    {{"degree": "B.Tech", "field": "Computer Science", "year": 2024}}
  ],
  "projects": ["Project 1 description", "Project 2 description"],
  "domain": "AI/ML",
  "tools": ["Git", "Docker", "VS Code"]
}}

Resume text:
{raw_text[:4000]}
"""
    result = ask_llm(prompt, system="You are a resume parser. Return ONLY valid JSON, no extra text.")

    # Step 3: Parse JSON safely
    try:
        return json.loads(result.strip())
    except:
        match = re.search(r'\{.*\}', result, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {"error": "Could not parse resume", "raw": result}