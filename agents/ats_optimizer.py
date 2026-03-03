import json
import re
from utils.llm_client import ask_llm

def optimize_for_ats(resume_data: dict, job_description: str, missing_skills: list) -> dict:
    prompt = f"""
You are an expert ATS resume optimization specialist.

Candidate profile:
- Name: {resume_data.get('name')}
- Skills: {resume_data.get('skills', [])}
- Experience: {resume_data.get('experience_years')} years
- Projects: {resume_data.get('projects', [])}
- Tools: {resume_data.get('tools', [])}

Job Description:
{job_description[:2000]}

Missing skills to incorporate: {missing_skills}

Return ONLY valid JSON:
{{
  "optimized_summary": "2-3 sentence professional summary with keywords from JD",
  "improved_bullets": [
    "• Action verb + what you did + result/metric",
    "• Action verb + what you did + result/metric"
  ],
  "keywords_added": ["keyword1", "keyword2"],
  "formatting_tips": [
    "Use standard section headers like Experience, Education, Skills",
    "Keep fonts clean like Arial or Calibri"
  ],
  "ats_score_estimate": 75
}}
"""
    result = ask_llm(prompt, system="You are an ATS expert. Return ONLY valid JSON.")
    try:
        return json.loads(result.strip())
    except:
        match = re.search(r'\{.*\}', result, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {"error": "Could not parse response"}