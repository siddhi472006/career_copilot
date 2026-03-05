"""
Skill-Gap Bridge Agent
For each missing skill, provides:
- Free learning resource (YouTube/docs/course)
- Estimated time to learn
- Estimated score boost after adding skill
- Difficulty level
"""

from utils.llm_client import ask_llm
import json
import re

# ── Static resource database (50+ skills) ─────────────────────────────────────
SKILL_RESOURCES = {
    # Frontend
    "react":        {"resource": "React Full Course", "url": "https://www.youtube.com/watch?v=bMknfKXIFA8", "platform": "freeCodeCamp", "hours": 10, "boost": 15},
    "reactjs":      {"resource": "React Full Course", "url": "https://www.youtube.com/watch?v=bMknfKXIFA8", "platform": "freeCodeCamp", "hours": 10, "boost": 15},
    "redux":        {"resource": "Redux Toolkit in 2 Hours", "url": "https://www.youtube.com/watch?v=bbkBuqC1rU4", "platform": "YouTube", "hours": 2, "boost": 12},
    "typescript":   {"resource": "TypeScript Full Course", "url": "https://www.youtube.com/watch?v=30LWjhZzg50", "platform": "freeCodeCamp", "hours": 5, "boost": 10},
    "nextjs":       {"resource": "Next.js Crash Course", "url": "https://www.youtube.com/watch?v=mTz0GXj8NN0", "platform": "Traversy Media", "hours": 3, "boost": 12},
    "vue":          {"resource": "Vue.js Full Course", "url": "https://www.youtube.com/watch?v=VeNfHj6MhgA", "platform": "freeCodeCamp", "hours": 4, "boost": 10},
    "angular":      {"resource": "Angular Crash Course", "url": "https://www.youtube.com/watch?v=3dHNOWTI7H8", "platform": "Traversy Media", "hours": 3, "boost": 10},
    "tailwind":     {"resource": "Tailwind CSS Full Course", "url": "https://www.youtube.com/watch?v=ft30zcMlFa8", "platform": "freeCodeCamp", "hours": 4, "boost": 8},
    "tailwindcss":  {"resource": "Tailwind CSS Full Course", "url": "https://www.youtube.com/watch?v=ft30zcMlFa8", "platform": "freeCodeCamp", "hours": 4, "boost": 8},

    # Backend
    "nodejs":       {"resource": "Node.js Full Course", "url": "https://www.youtube.com/watch?v=Oe421EPjeBE", "platform": "freeCodeCamp", "hours": 8, "boost": 14},
    "node.js":      {"resource": "Node.js Full Course", "url": "https://www.youtube.com/watch?v=Oe421EPjeBE", "platform": "freeCodeCamp", "hours": 8, "boost": 14},
    "express":      {"resource": "Express.js Crash Course", "url": "https://www.youtube.com/watch?v=SccSCuHhOw0", "platform": "Traversy Media", "hours": 2, "boost": 10},
    "django":       {"resource": "Django Full Course", "url": "https://www.youtube.com/watch?v=PtQiiknWUcI", "platform": "freeCodeCamp", "hours": 10, "boost": 14},
    "fastapi":      {"resource": "FastAPI Full Course", "url": "https://www.youtube.com/watch?v=0sOvCWFmrtA", "platform": "freeCodeCamp", "hours": 5, "boost": 12},
    "flask":        {"resource": "Flask Full Course", "url": "https://www.youtube.com/watch?v=Qr4QMBUPxWo", "platform": "freeCodeCamp", "hours": 4, "boost": 10},
    "spring boot":  {"resource": "Spring Boot Full Course", "url": "https://www.youtube.com/watch?v=9SGDpanrc8U", "platform": "Amigoscode", "hours": 8, "boost": 14},
    "springboot":   {"resource": "Spring Boot Full Course", "url": "https://www.youtube.com/watch?v=9SGDpanrc8U", "platform": "Amigoscode", "hours": 8, "boost": 14},

    # Databases
    "sql":          {"resource": "SQL Full Course", "url": "https://www.youtube.com/watch?v=HXV3zeQKqGY", "platform": "freeCodeCamp", "hours": 4, "boost": 10},
    "mysql":        {"resource": "MySQL Full Course", "url": "https://www.youtube.com/watch?v=ER8oKX5myE0", "platform": "freeCodeCamp", "hours": 5, "boost": 10},
    "postgresql":   {"resource": "PostgreSQL Full Course", "url": "https://www.youtube.com/watch?v=qw--VYLpxG4", "platform": "freeCodeCamp", "hours": 4, "boost": 10},
    "mongodb":      {"resource": "MongoDB Full Course", "url": "https://www.youtube.com/watch?v=ExcRbA7fy_A", "platform": "freeCodeCamp", "hours": 7, "boost": 10},
    "redis":        {"resource": "Redis Crash Course", "url": "https://www.youtube.com/watch?v=jgpVdJB2sKQ", "platform": "TechWorld", "hours": 2, "boost": 8},

    # DevOps / Cloud
    "docker":       {"resource": "Docker Full Course", "url": "https://www.youtube.com/watch?v=fqMOX6JJhGo", "platform": "freeCodeCamp", "hours": 3, "boost": 12},
    "kubernetes":   {"resource": "Kubernetes Full Course", "url": "https://www.youtube.com/watch?v=X48VuDVv0do", "platform": "TechWorld", "hours": 5, "boost": 14},
    "aws":          {"resource": "AWS Full Course", "url": "https://www.youtube.com/watch?v=ulprqHHWlng", "platform": "freeCodeCamp", "hours": 10, "boost": 15},
    "azure":        {"resource": "Azure Full Course", "url": "https://www.youtube.com/watch?v=NKEFWyqJ5XA", "platform": "freeCodeCamp", "hours": 8, "boost": 14},
    "gcp":          {"resource": "GCP Full Course", "url": "https://www.youtube.com/watch?v=IEEQznCZFxA", "platform": "freeCodeCamp", "hours": 8, "boost": 14},
    "ci/cd":        {"resource": "CI/CD Full Course", "url": "https://www.youtube.com/watch?v=R8_veQiYBjI", "platform": "TechWorld", "hours": 3, "boost": 10},
    "linux":        {"resource": "Linux Full Course", "url": "https://www.youtube.com/watch?v=sWbUDq4S6Y8", "platform": "freeCodeCamp", "hours": 6, "boost": 8},

    # ML/AI
    "machine learning": {"resource": "ML Full Course", "url": "https://www.youtube.com/watch?v=NWONeJKn6kc", "platform": "freeCodeCamp", "hours": 10, "boost": 18},
    "tensorflow":   {"resource": "TensorFlow 2.0 Full Course", "url": "https://www.youtube.com/watch?v=tPYj3fFJGjk", "platform": "freeCodeCamp", "hours": 7, "boost": 15},
    "pytorch":      {"resource": "PyTorch Full Course", "url": "https://www.youtube.com/watch?v=V_xro1bcAuA", "platform": "freeCodeCamp", "hours": 8, "boost": 15},
    "deep learning":{"resource": "Deep Learning Crash Course", "url": "https://www.youtube.com/watch?v=VyWAvY2CF9c", "platform": "freeCodeCamp", "hours": 6, "boost": 15},
    "nlp":          {"resource": "NLP with Python Full Course", "url": "https://www.youtube.com/watch?v=X2vAabgKiuM", "platform": "freeCodeCamp", "hours": 5, "boost": 14},
    "pandas":       {"resource": "Pandas Full Course", "url": "https://www.youtube.com/watch?v=gtjxAH8uaP0", "platform": "freeCodeCamp", "hours": 4, "boost": 10},
    "numpy":        {"resource": "NumPy Full Course", "url": "https://www.youtube.com/watch?v=QUT1VHiLmmI", "platform": "freeCodeCamp", "hours": 3, "boost": 8},
    "scikit-learn": {"resource": "Scikit-learn Crash Course", "url": "https://www.youtube.com/watch?v=0B5eIE_1vpU", "platform": "freeCodeCamp", "hours": 3, "boost": 10},
    "opencv":       {"resource": "OpenCV Full Course", "url": "https://www.youtube.com/watch?v=oXlwWbU8l2o", "platform": "freeCodeCamp", "hours": 5, "boost": 12},

    # Programming Languages
    "python":       {"resource": "Python Full Course", "url": "https://www.youtube.com/watch?v=rfscVS0vtbw", "platform": "freeCodeCamp", "hours": 4, "boost": 12},
    "javascript":   {"resource": "JavaScript Full Course", "url": "https://www.youtube.com/watch?v=PkZNo7MFNFg", "platform": "freeCodeCamp", "hours": 7, "boost": 12},
    "java":         {"resource": "Java Full Course", "url": "https://www.youtube.com/watch?v=GdzRzWymT4c", "platform": "freeCodeCamp", "hours": 9, "boost": 12},
    "c++":          {"resource": "C++ Full Course", "url": "https://www.youtube.com/watch?v=vLnPwxZdW4Y", "platform": "freeCodeCamp", "hours": 6, "boost": 10},
    "golang":       {"resource": "Go Full Course", "url": "https://www.youtube.com/watch?v=un6ZyFkqFKo", "platform": "freeCodeCamp", "hours": 7, "boost": 12},
    "rust":         {"resource": "Rust Full Course", "url": "https://www.youtube.com/watch?v=BpPEoZW5IiY", "platform": "freeCodeCamp", "hours": 8, "boost": 12},
    "kotlin":       {"resource": "Kotlin Full Course", "url": "https://www.youtube.com/watch?v=F9UC9DY-vIU", "platform": "freeCodeCamp", "hours": 6, "boost": 12},
    "swift":        {"resource": "Swift Full Course", "url": "https://www.youtube.com/watch?v=comQ1-x2a1Q", "platform": "freeCodeCamp", "hours": 6, "boost": 12},

    # CS Fundamentals
    "data structures": {"resource": "DSA Full Course", "url": "https://www.youtube.com/watch?v=pkYVOmU3MgA", "platform": "freeCodeCamp", "hours": 8, "boost": 15},
    "algorithms":   {"resource": "Algorithms Full Course", "url": "https://www.youtube.com/watch?v=8hly31xKli0", "platform": "freeCodeCamp", "hours": 8, "boost": 15},
    "system design":{"resource": "System Design Full Course", "url": "https://www.youtube.com/watch?v=m8Icp_Cid5o", "platform": "freeCodeCamp", "hours": 5, "boost": 18},
    "os":           {"resource": "Operating Systems Course", "url": "https://www.youtube.com/watch?v=vBURTt97EkA", "platform": "freeCodeCamp", "hours": 6, "boost": 10},
    "networking":   {"resource": "Computer Networking Full Course", "url": "https://www.youtube.com/watch?v=qiQR5rTSshw", "platform": "freeCodeCamp", "hours": 5, "boost": 10},

    # Tools
    "git":          {"resource": "Git & GitHub Full Course", "url": "https://www.youtube.com/watch?v=RGOj5yH7evk", "platform": "freeCodeCamp", "hours": 1, "boost": 6},
    "graphql":      {"resource": "GraphQL Full Course", "url": "https://www.youtube.com/watch?v=ed8SzALpx1Q", "platform": "freeCodeCamp", "hours": 4, "boost": 10},
    "rest apis":    {"resource": "REST API Full Course", "url": "https://www.youtube.com/watch?v=0sOvCWFmrtA", "platform": "freeCodeCamp", "hours": 3, "boost": 10},
    "rest api":     {"resource": "REST API Full Course", "url": "https://www.youtube.com/watch?v=0sOvCWFmrtA", "platform": "freeCodeCamp", "hours": 3, "boost": 10},
    "microservices":{"resource": "Microservices Full Course", "url": "https://www.youtube.com/watch?v=lTAcCNbJ7KE", "platform": "freeCodeCamp", "hours": 5, "boost": 14},
    "figma":        {"resource": "Figma Full Course", "url": "https://www.youtube.com/watch?v=FTFaQWZBqQ8", "platform": "freeCodeCamp", "hours": 3, "boost": 8},

    # Mobile
    "react native": {"resource": "React Native Full Course", "url": "https://www.youtube.com/watch?v=0-S5a0eXPoc", "platform": "freeCodeCamp", "hours": 8, "boost": 14},
    "flutter":      {"resource": "Flutter Full Course", "url": "https://www.youtube.com/watch?v=VPvVD8t02U8", "platform": "freeCodeCamp", "hours": 10, "boost": 14},
    "android":      {"resource": "Android Dev Full Course", "url": "https://www.youtube.com/watch?v=fis26HvvDII", "platform": "freeCodeCamp", "hours": 10, "boost": 12},
}

DIFFICULTY_MAP = {
    range(1, 3):  "⚡ Quick Win",
    range(3, 6):  "📚 Medium",
    range(6, 15): "🏋️ Intensive",
}

def get_difficulty(hours: int) -> str:
    if hours <= 2:   return "⚡ Quick Win (1-2 hrs)"
    if hours <= 5:   return "📚 Medium (3-5 hrs)"
    if hours <= 10:  return "🏋️ Intensive (6-10 hrs)"
    return "🎓 Deep Dive (10+ hrs)"


def get_skill_resources(missing_skills: list, match_percentage: float) -> list:
    """For each missing skill, find a free learning resource and score boost."""
    bridges = []

    for skill in missing_skills:
        skill_lower = skill.lower().strip()

        # Look up in static database first
        resource_data = SKILL_RESOURCES.get(skill_lower)

        # Try partial match if exact not found
        if not resource_data:
            for key in SKILL_RESOURCES:
                if key in skill_lower or skill_lower in key:
                    resource_data = SKILL_RESOURCES[key]
                    break

        if resource_data:
            boost = resource_data["boost"]
            new_score = min(100, round(match_percentage + boost))
            bridges.append({
                "skill":       skill,
                "resource":    resource_data["resource"],
                "url":         resource_data["url"],
                "platform":    resource_data["platform"],
                "hours":       resource_data["hours"],
                "difficulty":  get_difficulty(resource_data["hours"]),
                "score_boost": boost,
                "new_score":   new_score,
                "free":        True,
            })
        else:
            # Fallback: AI-generated resource suggestion
            bridges.append({
                "skill":       skill,
                "resource":    f"Search '{skill} tutorial' on YouTube",
                "url":         f"https://www.youtube.com/results?search_query={skill.replace(' ', '+')}+tutorial+free",
                "platform":    "YouTube",
                "hours":       3,
                "difficulty":  "📚 Medium (3-5 hrs)",
                "score_boost": 8,
                "new_score":   min(100, round(match_percentage + 8)),
                "free":        True,
            })

    # Sort by score boost descending (highest impact first)
    bridges.sort(key=lambda x: x["score_boost"], reverse=True)
    return bridges


def generate_skill_gap_bridge(missing_skills: list, match_percentage: float, job_title: str = "") -> dict:
    """Main function — returns skill gap bridge data."""
    if not missing_skills:
        return {
            "bridges": [],
            "total_boost": 0,
            "potential_score": match_percentage,
            "message": "Great! No critical skill gaps found.",
        }

    bridges = get_skill_resources(missing_skills, match_percentage)

    # Calculate total potential boost (capped at 100)
    total_boost = sum(b["score_boost"] for b in bridges[:5])
    potential_score = min(100, round(match_percentage + total_boost))

    # Quick wins (under 3 hours)
    quick_wins = [b for b in bridges if b["hours"] <= 2]

    return {
        "bridges":         bridges,
        "total_boost":     total_boost,
        "potential_score": potential_score,
        "quick_wins":      quick_wins,
        "message": (
            f"Learn these {len(bridges)} skills to boost your match from "
            f"{match_percentage}% to {potential_score}%"
        ),
    }