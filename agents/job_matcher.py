import json
import re
from utils.llm_client import ask_llm

# ── Canonical skill aliases ───────────────────────────────────────────────────
SKILL_ALIASES = {
    # C / C++ variations
    "c/c++":         "C++",
    "c/ c++":        "C++",
    "c/c":           "C++",
    "c++":           "C++",
    "cpp":           "C++",
    "c plus plus":   "C++",
    "c":             "C",

    # C#
    "c#":            "C#",
    "csharp":        "C#",
    "c sharp":       "C#",

    # Languages
    "python":        "Python",
    "java":          "Java",
    "javascript":    "JavaScript",
    "js":            "JavaScript",
    "typescript":    "TypeScript",
    "ts":            "TypeScript",
    "kotlin":        "Kotlin",
    "swift":         "Swift",
    "golang":        "Go",
    "go":            "Go",
    "rust":          "Rust",
    "ruby":          "Ruby",
    "php":           "PHP",
    "scala":         "Scala",

    # CS Fundamentals
    "oop":                                  "OOP",
    "oops":                                 "OOP",
    "object oriented":                      "OOP",
    "object-oriented":                      "OOP",
    "object oriented programming":          "OOP",
    "object-oriented programming":          "OOP",
    "oop using java":                       "OOP",
    "oops concepts":                        "OOP",

    "dsa":                                  "DSA",
    "data structures":                      "Data Structures",
    "data structure":                       "Data Structures",
    "data structures & algorithms":         "DSA",
    "data structures and algorithms":       "DSA",
    "design and analysis of algorithms":    "DSA",
    "algorithms":                           "Algorithms",
    "competitive programming":              "DSA",

    "os":                                   "Operating Systems",
    "operating systems":                    "Operating Systems",
    "unix":                                 "Operating Systems",
    "linux":                                "Linux",

    "dbms":                                 "DBMS",
    "database management":                  "DBMS",
    "database management systems":          "DBMS",

    "cn":                                   "Computer Networks",
    "computer networks":                    "Computer Networks",
    "computer networking":                  "Computer Networks",

    "system design":                        "System Design",
    "software engineering":                 "Software Engineering",
    "theory of computation":                "Theory of Computation",
    "digital systems":                      "Digital Systems",
    "mobile development":                   "Mobile Development",

    # Problem Solving
    "problem solving":                      "Problem Solving",
    "problem-solving":                      "Problem Solving",
    "problem_solving":                      "Problem Solving",
    "logical problem-solving":              "Problem Solving",
    "algorithmic thinking":                 "Problem Solving",

    # Databases
    "sql":                                  "SQL",
    "mysql":                                "SQL",
    "postgresql":                           "PostgreSQL",
    "postgres":                             "PostgreSQL",
    "mongodb":                              "MongoDB",
    "mongo":                                "MongoDB",
    "redis":                                "Redis",
    "sqlite":                               "SQLite",
    "oracle":                               "Oracle DB",
    "databases":                            "SQL",

    # Web
    "html":                                 "HTML",
    "css":                                  "CSS",
    "html/css":                             "HTML/CSS",
    "html, css":                            "HTML/CSS",
    "react":                                "React",
    "reactjs":                              "React",
    "react.js":                             "React",
    "tailwind":                             "Tailwind CSS",
    "tailwind css":                         "Tailwind CSS",
    "nodejs":                               "Node.js",
    "node.js":                              "Node.js",
    "node":                                 "Node.js",
    "express":                              "Express.js",
    "expressjs":                            "Express.js",
    "django":                               "Django",
    "flask":                                "Flask",
    "fastapi":                              "FastAPI",
    "spring":                               "Spring Boot",
    "spring boot":                          "Spring Boot",

    # REST APIs
    "rest":                                 "REST APIs",
    "rest api":                             "REST APIs",
    "rest apis":                            "REST APIs",
    "restful":                              "REST APIs",
    "restful apis":                         "REST APIs",
    "api":                                  "REST APIs",
    "apis":                                 "REST APIs",
    "graphql":                              "GraphQL",

    # Tools
    "git":                                  "Git",
    "github":                               "Git",
    "gitlab":                               "Git",
    "bitbucket":                            "Git",
    "version control":                      "Git",
    "figma":                                "Figma",
    "canva":                                "Canva",
    "java swing":                           "Java Swing",
    "swing":                                "Java Swing",

    # Cloud & DevOps
    "aws":                                  "AWS",
    "azure":                                "Azure",
    "gcp":                                  "GCP",
    "google cloud":                         "GCP",
    "docker":                               "Docker",
    "kubernetes":                           "Kubernetes",
    "k8s":                                  "Kubernetes",
    "ci/cd":                                "CI/CD",
    "cicd":                                 "CI/CD",
    "terraform":                            "Terraform",

    # ML / Data
    "ml":                                   "Machine Learning",
    "machine learning":                     "Machine Learning",
    "deep learning":                        "Deep Learning",
    "ai/ml":                                "Machine Learning",
    "ai":                                   "AI",
    "nlp":                                  "NLP",
    "tensorflow":                           "TensorFlow",
    "pytorch":                              "PyTorch",
    "scikit-learn":                         "scikit-learn",
    "sklearn":                              "scikit-learn",
    "pandas":                               "pandas",
    "numpy":                                "numpy",

    # Soft skills
    "communication":                        "Communication",
    "teamwork":                             "Teamwork",
    "leadership":                           "Leadership",
}


def normalize(skill: str) -> str:
    cleaned = skill.strip().lower()
    cleaned = re.sub(r'[.,;:()]$', '', cleaned).strip()
    return SKILL_ALIASES.get(cleaned, skill.strip())


def normalize_set(skills: list) -> dict:
    result = {}
    for s in skills:
        if not s or not s.strip():
            continue
        display = normalize(s)
        result[display.lower()] = display
    return result


def _simple_semantic_score(text1: str, text2: str) -> float:
    """
    Lightweight keyword-overlap semantic similarity.
    Replaces sentence_transformers — no heavy dependencies needed.
    """
    stop = {"the","a","an","is","in","of","to","and","or","for","with",
            "on","at","by","from","as","be","are","was","were","have",
            "has","will","would","can","could","should","may","might",
            "this","that","these","those","it","its","we","our","your"}

    def tokens(t):
        words = re.findall(r'[a-z0-9#+.]+', t.lower())
        return set(w for w in words if w not in stop and len(w) > 1)

    t1 = tokens(text1)
    t2 = tokens(text2)
    if not t1 or not t2:
        return 0.5
    intersection = t1 & t2
    union        = t1 | t2
    jaccard      = len(intersection) / len(union)
    # Scale to ~0.3–0.9 range so it feels like cosine similarity
    return 0.3 + jaccard * 0.6


def extract_resume_skills_fully(resume_data: dict) -> list:
    all_skills = []

    all_skills.extend(resume_data.get("skills", []))
    all_skills.extend(resume_data.get("tools",  []))

    coursework = resume_data.get("coursework", "")
    if isinstance(coursework, str) and coursework:
        for item in re.split(r'[,\n]', coursework):
            item = item.strip()
            if item and len(item) > 2:
                all_skills.append(item)

    for edu in resume_data.get("education", []):
        if isinstance(edu, dict):
            cw = edu.get("coursework", "")
            if isinstance(cw, str):
                for item in re.split(r'[,\n]', cw):
                    item = item.strip()
                    if item and len(item) > 2:
                        all_skills.append(item)

    achievements_text_parts = []
    for achievement in resume_data.get("achievements", []):
        if isinstance(achievement, dict):
            text = achievement.get("description", "") or achievement.get("text", "") or ""
        elif isinstance(achievement, str):
            text = achievement
        else:
            text = ""
        if text.strip():
            all_skills.append(text)
            achievements_text_parts.append(text)

    achievements_combined = " ".join(achievements_text_parts).lower()

    if any(kw in achievements_combined for kw in [
        "leetcode", "hackerrank", "codechef", "codeforces",
        "competitive", "hackathon", "problem solving", "rank",
        "contest", "programming"
    ]):
        all_skills.extend(["Problem Solving", "DSA", "Competitive Programming"])

    if any(kw in achievements_combined for kw in ["sql", "database", "mysql"]):
        all_skills.append("SQL")

    if any(kw in achievements_combined for kw in ["ml", "machine learning", "ai", "deep learning"]):
        all_skills.extend(["Machine Learning", "AI"])

    if any(kw in achievements_combined for kw in ["react", "frontend", "web"]):
        all_skills.extend(["React", "HTML", "CSS"])

    for proj in resume_data.get("projects", []):
        if isinstance(proj, dict):
            desc       = proj.get("description", "") or ""
            tech_stack = proj.get("tech_stack",   "") or ""
            tech_used  = proj.get("technologies", "") or ""
            combined   = f"{desc} {tech_stack} {tech_used}"
            if combined.strip():
                all_skills.append(combined)
        elif isinstance(proj, str):
            all_skills.append(proj)

    skills_lower = " ".join(str(s) for s in all_skills).lower()

    inferences = {
        "mysql":        ["SQL", "MySQL"],
        "c/c++":        ["C++", "C"],
        "c++":          ["C++"],
        "java":         ["Java", "OOP"],
        "reactjs":      ["React"],
        "github":       ["Git"],
        "gitlab":       ["Git"],
        "postgresql":   ["SQL", "PostgreSQL"],
        "mongodb":      ["NoSQL"],
        "leetcode":     ["Problem Solving", "DSA"],
        "hackerrank":   ["Problem Solving"],
        "competitive":  ["Problem Solving", "DSA"],
        "hackathon":    ["Problem Solving", "Teamwork"],
        "trie":         ["Data Structures", "DSA"],
        "graph":        ["Data Structures", "DSA"],
        "heap":         ["Data Structures", "DSA"],
        "bfs":          ["Algorithms", "DSA"],
        "dfs":          ["Algorithms", "DSA"],
    }

    for trigger, additions in inferences.items():
        if trigger in skills_lower:
            all_skills.extend(additions)

    return list(set(str(s) for s in all_skills if s and str(s).strip()))


# ── Role / Company skill maps ─────────────────────────────────────────────────
ROLE_SKILL_MAP = {
    "sde":              ["Python", "Java", "C++", "Data Structures", "Algorithms",
                         "Git", "System Design", "OOP", "SQL", "Problem Solving"],
    "software":         ["Python", "Java", "C++", "Data Structures", "Algorithms",
                         "Git", "OOP", "SQL"],
    "developer":        ["Python", "JavaScript", "Git", "REST APIs", "SQL", "Problem Solving"],
    "data scientist":   ["Python", "pandas", "scikit-learn", "Machine Learning", "SQL", "numpy"],
    "data science":     ["Python", "pandas", "scikit-learn", "Machine Learning", "SQL", "numpy"],
    "ml":               ["Python", "TensorFlow", "PyTorch", "Machine Learning", "Deep Learning", "numpy"],
    "machine learning": ["Python", "TensorFlow", "PyTorch", "Machine Learning", "Deep Learning"],
    "frontend":         ["React", "JavaScript", "HTML", "CSS", "TypeScript", "Git"],
    "backend":          ["Python", "Java", "Node.js", "REST APIs", "SQL", "Docker", "Git"],
    "fullstack":        ["React", "Node.js", "Python", "JavaScript", "SQL", "REST APIs", "Git"],
    "devops":           ["Docker", "Kubernetes", "CI/CD", "AWS", "Linux", "Git"],
    "intern":           ["Python", "Java", "C++", "Problem Solving", "Data Structures",
                         "Algorithms", "Git", "OOP", "SQL"],
}

COMPANY_SKILL_MAP = {
    "microsoft": ["C++", "C#", "Azure", "Python", "Java", "System Design",
                  "Algorithms", "Data Structures", "OOP", "Git", "SQL"],
    "google":    ["Python", "C++", "Java", "Algorithms", "System Design",
                  "Data Structures", "Git", "OOP", "SQL"],
    "amazon":    ["Java", "Python", "AWS", "System Design", "Data Structures",
                  "Algorithms", "SQL", "Git"],
    "meta":      ["Python", "C++", "React", "System Design", "Algorithms", "Git"],
    "apple":     ["Swift", "C++", "Algorithms", "System Design", "Git"],
    "netflix":   ["Java", "Python", "AWS", "System Design", "Git"],
    "flipkart":  ["Java", "Python", "System Design", "SQL", "Algorithms", "Git"],
    "infosys":   ["Java", "Python", "SQL", "Spring Boot", "REST APIs", "Git"],
    "tcs":       ["Java", "Python", "SQL", "Communication", "Git"],
    "wipro":     ["Java", "Python", "SQL", "REST APIs", "Communication", "Git"],
}


def _enrich_jd(job_description: str) -> str:
    jd = job_description.strip()
    if len(jd.split()) >= 25:
        return jd

    jd_lower = jd.lower()
    extra_skills = set()

    for keyword, skills in ROLE_SKILL_MAP.items():
        if keyword in jd_lower:
            extra_skills.update(skills)

    for company, skills in COMPANY_SKILL_MAP.items():
        if company in jd_lower:
            extra_skills.update(skills)

    if not extra_skills:
        extra_skills = set(ROLE_SKILL_MAP["software"])

    enriched = (
        f"{jd}\n\nTypical requirements: {', '.join(sorted(extra_skills))}. "
        f"Strong problem-solving, communication, and teamwork expected."
    )
    print(f"  📝 JD enriched with {len(extra_skills)} inferred skills")
    return enriched


def extract_jd_skills(job_description: str) -> list:
    prompt = f"""
Extract all required technical skills, tools, and technologies from this job description.
Include: programming languages, frameworks, databases, cloud platforms, CS fundamentals.
Return ONLY a JSON array like: ["Python", "C++", "SQL", "Git", "OOP", "Data Structures"]

Job Description:
{job_description[:2500]}
"""
    result = ask_llm(
        prompt,
        system="Return ONLY a valid JSON array of skills. No explanation, no markdown."
    )
    result = result.strip()
    result = re.sub(r'^```json\s*', '', result)
    result = re.sub(r'^```\s*',     '', result)
    result = re.sub(r'\s*```$',     '', result)
    result = result.strip()

    try:
        skills = json.loads(result)
        return [s for s in skills if isinstance(s, str)]
    except Exception:
        match = re.search(r'\[.*?\]', result, re.DOTALL)
        if match:
            try:
                return [s for s in json.loads(match.group()) if isinstance(s, str)]
            except Exception:
                pass
    return []


def calculate_match(resume_data: dict, job_description: str) -> dict:
    # Step 1: Enrich short JDs
    enriched_jd = _enrich_jd(job_description)

    # Step 2: Extract from ALL resume sections
    all_resume_skills = extract_resume_skills_fully(resume_data)
    resume_norm       = normalize_set(all_resume_skills)

    # Step 3: Extract + normalize JD skills
    raw_jd_skills = extract_jd_skills(enriched_jd)
    jd_norm       = normalize_set(raw_jd_skills)

    # Step 4: Compare using normalized keys
    resume_keys  = set(resume_norm.keys())
    jd_keys      = set(jd_norm.keys())
    matched_keys = resume_keys & jd_keys
    missing_keys = jd_keys - resume_keys

    # Step 5: Scores
    skill_score = len(matched_keys) / len(jd_keys) if jd_keys else 0.0

    resume_text = " ".join(str(s) for s in all_resume_skills)
    if not resume_text.strip():
        resume_text = resume_data.get("domain", "software engineering")

    # Lightweight semantic score — no heavy ML packages needed
    semantic_score = _simple_semantic_score(resume_text, enriched_jd[:1000])

    final_score = round((skill_score * 0.7 + semantic_score * 0.3) * 100, 1)
    final_score = min(final_score, 100.0)

    # Step 6: Display lists
    matched_display = sorted([
        resume_norm.get(k) or jd_norm.get(k, k.title())
        for k in matched_keys
    ])
    missing_display = sorted([
        jd_norm.get(k, k.title())
        for k in missing_keys
    ])

    print(f"  ✅ Matched ({len(matched_display)}): {matched_display}")
    print(f"  ❌ Missing ({len(missing_display)}): {missing_display}")

    return {
        "match_percentage": final_score,
        "skill_score":      round(skill_score    * 100, 1),
        "semantic_score":   round(semantic_score * 100, 1),
        "matched_skills":   matched_display,
        "missing_skills":   missing_display,
    }