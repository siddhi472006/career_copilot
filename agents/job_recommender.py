"""
Agent 8: Job Recommender
Fetches jobs/internships from 3 free APIs:
  1. Remotive   — remote tech jobs globally (no auth needed)
  2. Arbeitnow  — real jobs, no key needed, 100+ results
  3. Adzuna     — broad job board India + global (free API key)
"""

import requests
import json
import re as _re
from utils.llm_client import ask_llm


def _clean(text: str, limit: int = 1500) -> str:
    clean = _re.sub(r'<[^>]+>', ' ', text)
    clean = _re.sub(r'\s+', ' ', clean).strip()
    return clean[:limit]


def fetch_remotive(skills: list, domain: str) -> list:
    results, seen = [], set()
    queries = (
        [s.lower() for s in skills[:2]]
        + ["software engineer", "data scientist", "machine learning", "software intern"]
    )
    for query in queries[:6]:
        try:
            resp = requests.get(
                f"https://remotive.com/api/remote-jobs?search={requests.utils.quote(query)}&limit=6",
                timeout=8,
            )
            if resp.status_code != 200:
                continue
            for j in resp.json().get("jobs", []):
                key = j.get("title", "").lower()
                if key in seen:
                    continue
                seen.add(key)
                is_intern = "intern" in key
                results.append({
                    "title":       j.get("title", ""),
                    "company":     j.get("company_name", ""),
                    "location":    j.get("candidate_required_location", "Remote / Global"),
                    "url":         j.get("url", ""),
                    "description": _clean(j.get("description", "")),
                    "tags":        j.get("tags", [])[:6],
                    "salary":      j.get("salary", "") or "Not specified",
                    "job_type":    "Internship" if is_intern else j.get("job_type", "Full-time"),
                    "source":      "Remotive 🌐",
                    "posted_date": j.get("publication_date", "")[:10],
                    "is_intern":   is_intern,
                })
        except Exception as e:
            print(f"Remotive [{query}] error: {e}")
    return results


def fetch_arbeitnow(skills: list, domain: str, max_results: int = 15) -> list:
    try:
        jobs, seen = [], set()
        for page in range(1, 3):
            r = requests.get(
                f"https://www.arbeitnow.com/api/job-board-api?page={page}",
                timeout=10,
            )
            if r.status_code != 200:
                break
            for j in r.json().get("data", []):
                title = j.get("title", "")
                key   = title.lower()
                if key in seen or not title.strip():
                    continue
                seen.add(key)
                is_intern = "intern" in key
                jobs.append({
                    "title":       title,
                    "company":     j.get("company_name", ""),
                    "location":    j.get("location", "Remote"),
                    "url":         j.get("url", ""),
                    "description": _clean(j.get("description", "")),
                    "tags":        j.get("tags", [])[:6],
                    "salary":      "Not specified",
                    "job_type":    "Internship" if is_intern else "Full-time",
                    "source":      "Arbeitnow 🌍",
                    "posted_date": str(j.get("created_at", ""))[:10],
                    "is_intern":   is_intern,
                })
            if len(jobs) >= max_results:
                break
        return jobs[:max_results]
    except Exception as e:
        print(f"Arbeitnow error: {e}")
        return []


def fetch_adzuna(skills: list, domain: str, app_id: str = "", app_key: str = "") -> list:
    if not app_id or not app_key:
        return _adzuna_mock(skills, domain)
    results, seen = [], set()
    countries = ["in", "gb", "us"]
    queries = [
        " ".join(skills[:2]) if skills else "software engineer",
        "machine learning intern",
    ]
    for country in countries:
        for query in queries[:2]:
            try:
                resp = requests.get(
                    f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
                    f"?app_id={app_id}&app_key={app_key}"
                    f"&results_per_page=5&what={requests.utils.quote(query)}"
                    f"&content-type=application/json",
                    timeout=8,
                )
                if resp.status_code != 200:
                    continue
                for j in resp.json().get("results", []):
                    key = j.get("title", "").lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    is_intern = "intern" in key
                    sal_min   = j.get("salary_min", 0) or 0
                    sal_max   = j.get("salary_max", 0) or 0
                    currency  = "₹" if country == "in" else ("£" if country == "gb" else "$")
                    salary    = f"{currency}{sal_min:,.0f} – {currency}{sal_max:,.0f}" if sal_min else "Not specified"
                    results.append({
                        "title":       j.get("title", ""),
                        "company":     j.get("company", {}).get("display_name", ""),
                        "location":    j.get("location", {}).get("display_name", ""),
                        "url":         j.get("redirect_url", ""),
                        "description": j.get("description", "")[:1500],
                        "tags":        [j.get("category", {}).get("label", "")],
                        "salary":      salary,
                        "job_type":    "Internship" if is_intern else "Full-time",
                        "source":      f"Adzuna 🔍 ({country.upper()})",
                        "posted_date": j.get("created", "")[:10],
                        "is_intern":   is_intern,
                    })
            except Exception as e:
                print(f"Adzuna [{country}/{query}] error: {e}")
    return results


def _adzuna_mock(skills: list, domain: str) -> list:
    return []


def rank_jobs_with_ai(jobs: list, resume_data: dict) -> list:
    if not jobs:
        return []
    summary = [
        {
            "index": i, "title": j["title"], "company": j["company"],
            "job_type": j.get("job_type", ""), "is_intern": j.get("is_intern", False),
            "description": j["description"][:400], "tags": j.get("tags", []),
        }
        for i, j in enumerate(jobs)
    ]
    prompt = f"""
You are a career advisor scoring job-candidate fit.

Candidate:
- Skills: {resume_data.get('skills', [])}
- Experience: {resume_data.get('experience_years', 0)} years
- Domain: {resume_data.get('domain', 'Technology')}
- Projects: {[p.get('name','') if isinstance(p, dict) else str(p) for p in resume_data.get('projects', [])]}

Jobs to score:
{json.dumps(summary, indent=2)}

Return ONLY valid JSON array sorted best to worst:
[{{"index": 0, "match_score": 87, "match_level": "Strong Match", "reason": "One sentence"}}]

match_level must be one of: "Strong Match", "Good Match", "Partial Match", "Stretch Role"
"""
    result = ask_llm(prompt, system="Return ONLY valid JSON array, no other text.")
    try:
        scores = json.loads(result.strip())
    except Exception:
        m = _re.search(r'\[.*\]', result, _re.DOTALL)
        scores = json.loads(m.group()) if m else []

    score_map = {s["index"]: s for s in scores}
    ranked = []
    for i, job in enumerate(jobs):
        s = score_map.get(i, {"match_score": 40, "reason": "General match", "match_level": "Partial Match"})
        ranked.append({**job, **s})
    ranked.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    return ranked


def get_recommended_jobs(
    resume_data:    dict,
    adzuna_app_id:  str = "",
    adzuna_app_key: str = "",
    max_results:    int = 15,
) -> list:
    skills = resume_data.get("skills", [])
    domain = resume_data.get("domain", "Software Engineering")
    print(f"Fetching jobs | Domain: {domain} | Skills: {skills[:5]}")

    remotive_jobs  = fetch_remotive(skills, domain)
    arbeitnow_jobs = fetch_arbeitnow(skills, domain, max_results=max_results)
    adzuna_jobs    = fetch_adzuna(skills, domain, adzuna_app_id, adzuna_app_key)

    print(f"  Remotive: {len(remotive_jobs)} | Arbeitnow: {len(arbeitnow_jobs)} | Adzuna: {len(adzuna_jobs)}")

    all_jobs = remotive_jobs + arbeitnow_jobs + adzuna_jobs
    seen, unique = set(), []
    for j in all_jobs:
        key = f"{j['title'].lower()}|{j['company'].lower()}"
        if key not in seen and j["title"].strip():
            seen.add(key)
            unique.append(j)

    print(f"  Ranking {len(unique)} unique jobs with AI...")
    return rank_jobs_with_ai(unique, resume_data)[:max_results]