import json
import re
import requests as _requests
from utils.llm_client import ask_llm

# ── Web search helper ─────────────────────────────────────────────────────────
SERPER_API_KEY = ""   # optional — set in .env as SERPER_API_KEY for best results

def _web_search(query: str, num: int = 5) -> list[dict]:
    """
    Search the web for salary data.
    Uses Serper.dev if SERPER_API_KEY is set, else falls back to
    DuckDuckGo Instant Answer API (no key needed, limited results).
    Returns list of {"title": ..., "snippet": ...}
    """
    import os
    key = os.getenv("SERPER_API_KEY", SERPER_API_KEY)

    # ── Serper (best results) ─────────────────────────────────────────────
    if key:
        try:
            resp = _requests.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": key, "Content-Type": "application/json"},
                json={"q": query, "num": num},
                timeout=8,
            )
            if resp.status_code == 200:
                data = resp.json()
                results = []
                for item in data.get("organic", [])[:num]:
                    results.append({
                        "title":   item.get("title", ""),
                        "snippet": item.get("snippet", ""),
                        "link":    item.get("link", ""),
                    })
                return results
        except Exception as e:
            print(f"Serper error: {e}")

    # ── DuckDuckGo fallback (no key needed) ───────────────────────────────
    try:
        resp = _requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_redirect": 1, "no_html": 1},
            timeout=8,
        )
        if resp.status_code == 200:
            data = resp.json()
            results = []
            # Abstract text
            if data.get("AbstractText"):
                results.append({"title": data.get("Heading", ""), "snippet": data["AbstractText"], "link": ""})
            # Related topics
            for topic in data.get("RelatedTopics", [])[:num]:
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append({"title": "", "snippet": topic["Text"], "link": topic.get("FirstURL", "")})
            return results
    except Exception as e:
        print(f"DuckDuckGo error: {e}")

    return []


def _gather_salary_context(role: str, company: str, location: str) -> str:
    """
    Run 3 targeted searches and return combined snippets as context string.
    """
    queries = [
        f"{role} salary at {company} {location} 2024 2025",
        f"{role} average salary {location} current market rate",
        f"{company} software engineer compensation package India",
    ]

    all_snippets = []
    for q in queries:
        results = _web_search(q, num=4)
        for r in results:
            snippet = r.get("snippet", "").strip()
            title   = r.get("title",   "").strip()
            if snippet:
                all_snippets.append(f"[{title}] {snippet}" if title else snippet)

    if not all_snippets:
        return "No web data found. Use general market knowledge."

    # Deduplicate and cap at ~2000 chars
    seen, unique = set(), []
    for s in all_snippets:
        key = s[:60]
        if key not in seen:
            seen.add(key)
            unique.append(s)

    context = "\n".join(unique)
    return context[:2500]


# ── Main predictor ────────────────────────────────────────────────────────────
def predict_salary(
    resume_data: dict,
    job_description: str,
    location: str = "India",
    company_name: str = "",
) -> dict:
    """
    Predict salary by:
    1. Searching the web for real salary data for this role + company
    2. Feeding that context + candidate profile to LLM for accurate prediction
    """
    role = resume_data.get("domain", "Software Engineer")

    # Try to extract role title from JD first line
    jd_first_line = job_description.strip().split("\n")[0][:80]
    if jd_first_line:
        role = jd_first_line

    print(f"  💰 Searching web for salary: {role} @ {company_name or 'market'} | {location}")
    web_context = _gather_salary_context(role, company_name or "tech companies", location)
    print(f"  💰 Web context gathered ({len(web_context)} chars)")

    prompt = f"""
You are a salary benchmarking expert. Predict accurate salary for this candidate.

=== WEB RESEARCH DATA (use this as primary source) ===
{web_context}

=== CANDIDATE PROFILE ===
- Skills: {resume_data.get('skills', [])}
- Experience: {resume_data.get('experience_years', 0)} years
- Education: {resume_data.get('education', [])}
- Domain: {resume_data.get('domain', 'Technology')}
- Tools: {resume_data.get('tools', [])}

=== JOB DETAILS ===
- Role: {role}
- Company: {company_name or 'Not specified'}
- Location: {location}
- Job Description: {job_description[:600]}

=== INSTRUCTIONS ===
Use the web research data above to give realistic, market-accurate salary figures.
If company-specific data is available, use it. Otherwise use market averages.
For internships use monthly stipend. For full-time use annual CTC.

Return ONLY valid JSON, no markdown, no code blocks:
{{
  "min_salary": 400000,
  "max_salary": 700000,
  "median_salary": 550000,
  "currency": "INR",
  "salary_period": "annual",
  "salary_display": "₹4,00,000 - ₹7,00,000 per year",
  "experience_level": "Entry Level",
  "data_sources": ["Source 1 used", "Source 2 used"],
  "salary_breakdown": {{
    "base_annual": 500000,
    "bonus_annual": 50000,
    "total_ctc_annual": 550000,
    "monthly_in_hand": 35000
  }},
  "company_specific_insight": "What this specific company pays or N/A",
  "market_insights": [
    "Insight 1 based on web data",
    "Insight 2 based on web data"
  ],
  "negotiation_tips": [
    "Tip 1",
    "Tip 2"
  ],
  "comparable_roles": [
    {{"role": "Software Engineer", "avg_salary": 600000, "period": "annual"}},
    {{"role": "Data Analyst", "avg_salary": 500000, "period": "annual"}}
  ]
}}

Rules:
- salary_period = "annual" for full-time (yearly CTC), "monthly" for internships
- salary_display must say "per year" or "per month"
- monthly_in_hand ≈ (base_annual / 12) * 0.75
- data_sources: list 1-3 short source descriptions you used from the web data
- company_specific_insight: mention actual company pay if found in web data
"""

    result = ask_llm(
        prompt,
        system=(
            "You are a salary benchmarking expert with access to real market data. "
            "Return ONLY valid JSON. No markdown. No code blocks. No explanation."
        ),
    )

    result = result.strip()
    result = re.sub(r'^```json\s*', '', result)
    result = re.sub(r'^```\s*',     '', result)
    result = re.sub(r'\s*```$',     '', result)
    result = result.strip()

    try:
        parsed = json.loads(result)
        # Attach raw web context for transparency
        parsed["_web_data_used"] = bool(web_context and "No web data" not in web_context)
        return parsed
    except Exception:
        match = re.search(r'\{.*\}', result, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
                parsed["_web_data_used"] = True
                return parsed
            except Exception:
                pass

    # Fallback
    return {
        "min_salary": 300000,
        "max_salary": 600000,
        "median_salary": 450000,
        "currency": "INR",
        "salary_period": "annual",
        "salary_display": "₹3,00,000 – ₹6,00,000 per year",
        "experience_level": "Entry Level",
        "data_sources": ["General market knowledge"],
        "salary_breakdown": {
            "base_annual": 400000,
            "bonus_annual": 40000,
            "total_ctc_annual": 440000,
            "monthly_in_hand": 25000,
        },
        "company_specific_insight": "N/A — could not retrieve company data",
        "market_insights": [
            "Salary varies significantly by location and company size",
            "Tech skills command a premium in the current market",
        ],
        "negotiation_tips": [
            "Research market rates before negotiating",
            "Highlight unique skills and project experience",
        ],
        "comparable_roles": [
            {"role": "Junior Developer", "avg_salary": 400000, "period": "annual"},
            {"role": "Data Analyst",     "avg_salary": 450000, "period": "annual"},
        ],
        "_web_data_used": False,
    }