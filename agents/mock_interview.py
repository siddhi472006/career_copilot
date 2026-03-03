import json
import re
from utils.llm_client import ask_llm

def generate_questions(resume_data: dict, job_description: str) -> dict:
    prompt = f"""
Generate a mock interview for this candidate.

Candidate:
- Skills: {resume_data.get('skills', [])}
- Projects: {resume_data.get('projects', [])}
- Domain: {resume_data.get('domain', 'General')}
- Experience: {resume_data.get('experience_years', 0)} years

Job Description: {job_description[:1000]}

Return ONLY valid JSON:
{{
  "technical_questions": [
    {{"question": "Question text", "difficulty": "Easy/Medium/Hard", "topic": "Topic name"}},
    {{"question": "Question text", "difficulty": "Easy/Medium/Hard", "topic": "Topic name"}},
    {{"question": "Question text", "difficulty": "Easy/Medium/Hard", "topic": "Topic name"}}
  ],
  "behavioral_questions": [
    "Tell me about a challenging project you worked on.",
    "How do you handle tight deadlines?"
  ],
  "tips": [
    "Research the company before the interview",
    "Prepare STAR format answers for behavioral questions"
  ]
}}
"""
    result = ask_llm(prompt, system="You are an expert technical interviewer. Return ONLY valid JSON.")
    try:
        return json.loads(result.strip())
    except:
        match = re.search(r'\{.*\}', result, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {"error": "Could not parse response"}

def evaluate_answer(question: str, answer: str, job_description: str) -> dict:
    prompt = f"""
Evaluate this interview answer.

Question: {question}
Candidate's Answer: {answer}
Job Context: {job_description[:500]}

Return ONLY valid JSON:
{{
  "score": 7,
  "score_out_of": 10,
  "strengths": ["What they did well"],
  "improvements": ["What could be better"],
  "ideal_answer_hint": "Brief hint at what a great answer looks like",
  "follow_up_question": "A follow-up question to dig deeper"
}}
"""
    result = ask_llm(prompt, system="You are a technical interview evaluator. Return ONLY valid JSON.")
    try:
        return json.loads(result.strip())
    except:
        match = re.search(r'\{.*\}', result, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {"error": "Could not parse response"}