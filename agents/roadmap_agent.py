import json
import re
from utils.llm_client import ask_llm

def generate_roadmap(resume_data: dict, job_description: str, missing_skills: list) -> dict:
    prompt = f"""
You are a career coach creating a personalized learning roadmap.

Candidate:
- Current skills: {resume_data.get('skills', [])}
- Experience: {resume_data.get('experience_years', 0)} years
- Domain: {resume_data.get('domain', 'General')}

Target Job: {job_description[:800]}
Skills to learn: {missing_skills}

Return ONLY valid JSON, no markdown, no explanation:
{{"total_weeks": 8, "goal": "One sentence career goal", "weeks": [{{"week": 1, "focus": "Topic", "tasks": ["Task 1", "Task 2"], "resources": ["Resource 1"], "milestone": "What you achieve"}}], "final_outcome": "What candidate achieves"}}
"""
    result = ask_llm(prompt, system="You are a career coach. Return ONLY valid compact JSON on a single line. No markdown code blocks.")
    
    # Strip markdown code blocks if present
    result = result.strip()
    result = re.sub(r'^```json\s*', '', result)
    result = re.sub(r'^```\s*', '', result)
    result = re.sub(r'\s*```$', '', result)
    result = result.strip()
    
    try:
        return json.loads(result)
    except:
        match = re.search(r'\{.*\}', result, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
        return {
            "total_weeks": 6,
            "goal": "Build skills for target role",
            "weeks": [{"week": 1, "focus": "Foundation", "tasks": ["Review job requirements", "Identify learning resources"], "resources": ["YouTube", "Documentation"], "milestone": "Clear learning plan"}],
            "final_outcome": "Ready to apply for target role"
        }