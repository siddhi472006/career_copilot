import streamlit as st
import requests
import requests as http_requests

API_URL = "http://localhost:8000/api"

st.set_page_config(
    page_title="AI Career Copilot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.job-row {
    display:flex; align-items:center; justify-content:space-between;
    background:#f8f9fa; border:1px solid #e0e0e0;
    border-left:5px solid #4f8ef7; border-radius:10px;
    padding:14px 18px; margin-bottom:10px; gap:16px;
}
.job-row:hover { border-left-color:#1a56db; background:#f0f4ff; }
.badge-strong  { background:#d1fae5; color:#065f46; font-weight:700; border-radius:20px; padding:4px 12px; font-size:12px; white-space:nowrap; }
.badge-good    { background:#dbeafe; color:#1e40af; font-weight:700; border-radius:20px; padding:4px 12px; font-size:12px; white-space:nowrap; }
.badge-partial { background:#fef3c7; color:#92400e; font-weight:700; border-radius:20px; padding:4px 12px; font-size:12px; white-space:nowrap; }
.badge-stretch { background:#fee2e2; color:#991b1b; font-weight:700; border-radius:20px; padding:4px 12px; font-size:12px; white-space:nowrap; }
.intern-badge  { background:#ede9fe; color:#5b21b6; font-weight:600; border-radius:10px; padding:2px 8px; font-size:11px; }
.job-badge     { background:#e0f2fe; color:#0369a1; font-weight:600; border-radius:10px; padding:2px 8px; font-size:11px; }
.source-tag    { background:#f3f4f6; color:#6b7280; border-radius:8px; padding:2px 8px; font-size:11px; }
.chip-matched  { background:#d1fae5; color:#065f46; border-radius:6px; padding:2px 8px; font-size:12px; display:inline-block; margin:2px; }
.chip-missing  { background:#fee2e2; color:#991b1b; border-radius:6px; padding:2px 8px; font-size:12px; display:inline-block; margin:2px; font-weight:600; }
.chip-keyword  { background:#ede9fe; color:#5b21b6; border-radius:6px; padding:2px 8px; font-size:12px; display:inline-block; margin:2px; font-weight:600; }
.salary-period-tag {
    background:#dcfce7; color:#15803d; font-weight:700;
    border-radius:20px; padding:5px 16px; font-size:13px;
    display:inline-block; margin-bottom:10px;
}
.web-badge {
    background:#fef9c3; color:#854d0e; font-weight:600;
    border-radius:20px; padding:4px 12px; font-size:12px;
    display:inline-block; margin-left:8px;
}
.company-insight {
    background:#f0f9ff; border:1px solid #bae6fd;
    border-radius:8px; padding:10px 16px;
    margin:10px 0; font-size:14px; color:#0369a1;
}
.monthly-inhand {
    background:#eff6ff; border:1px solid #bfdbfe;
    border-radius:8px; padding:10px 16px;
    margin-top:8px; font-size:14px; color:#1e40af;
}
.auth-container {
    max-width:420px; margin:60px auto 0 auto;
    background:#ffffff; border:1px solid #e5e7eb;
    border-radius:16px; padding:36px 32px;
    box-shadow:0 4px 24px rgba(0,0,0,0.07);
}
.auth-title {
    text-align:center; font-size:28px; font-weight:800;
    color:#1a1a2e; margin-bottom:4px;
}
.auth-sub {
    text-align:center; color:#6b7280; font-size:14px; margin-bottom:24px;
}
.history-card {
    background:#f8f9fa; border:1px solid #e5e7eb;
    border-radius:10px; padding:12px 16px; margin-bottom:8px;
    display:flex; justify-content:space-between; align-items:center;
}
</style>
""", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────
for k, v in [
    ("analysis_data", None),
    ("resume_data", None),
    ("recommended_jobs", None),
    ("selected_job_analysis", {}),
    ("token", None),
    ("user", None),
]:
    if k not in st.session_state:
        st.session_state[k] = v


# ── Auth helpers ──────────────────────────────────────────────────────────────
def auth_headers():
    return {"Authorization": f"Bearer {st.session_state.token}"}


# ══════════════════════════════════════════════════════════════════════════════
# AUTH GATE
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state.token:
    st.markdown("""
    <div class="auth-container">
        <div class="auth-title">🚀 AI Career Copilot</div>
        <div class="auth-sub">Your personal AI-powered career assistant</div>
    </div>
    """, unsafe_allow_html=True)

    _, center, _ = st.columns([1, 2, 1])
    with center:
        tab_login, tab_signup = st.tabs(["🔑 Login", "✨ Sign Up"])

        with tab_login:
            st.markdown("#### Welcome back!")
            login_email = st.text_input("Email", key="login_email", placeholder="you@example.com")
            login_pass  = st.text_input("Password", type="password", key="login_pass", placeholder="Your password")
            st.markdown("")
            if st.button("Login →", use_container_width=True, type="primary", key="login_btn"):
                if not login_email or not login_pass:
                    st.error("Please fill in all fields.")
                else:
                    try:
                        res = http_requests.post(
                            f"{API_URL}/login",
                            json={"email": login_email, "password": login_pass},
                            timeout=10,
                        )
                        if res.status_code == 200:
                            data = res.json()
                            st.session_state.token = data["token"]
                            st.session_state.user  = data["user"]
                            st.success(f"Welcome back, {data['user']['name']}! 🎉")
                            st.rerun()
                        else:
                            st.error(res.json().get("detail", "Login failed."))
                    except Exception as e:
                        st.error(f"Could not connect to server: {e}")

        with tab_signup:
            st.markdown("#### Create your account")
            signup_name  = st.text_input("Full Name",  key="signup_name",  placeholder="Siddhi Suryavanshi")
            signup_email = st.text_input("Email",      key="signup_email", placeholder="you@example.com")
            signup_pass  = st.text_input("Password",   type="password", key="signup_pass", placeholder="Min 6 characters")
            st.markdown("")
            if st.button("Create Account →", use_container_width=True, type="primary", key="signup_btn"):
                if not signup_name or not signup_email or not signup_pass:
                    st.error("Please fill in all fields.")
                elif len(signup_pass) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    try:
                        res = http_requests.post(
                            f"{API_URL}/signup",
                            json={"full_name": signup_name, "email": signup_email, "password": signup_pass},
                            timeout=10,
                        )
                        if res.status_code == 200:
                            data = res.json()
                            st.session_state.token = data["token"]
                            st.session_state.user  = data["user"]
                            st.success(f"Account created! Welcome, {data['user']['name']}! 🎉")
                            st.rerun()
                        else:
                            st.error(res.json().get("detail", "Signup failed."))
                    except Exception as e:
                        st.error(f"Could not connect to server: {e}")

    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# LOGGED IN
# ══════════════════════════════════════════════════════════════════════════════
user = st.session_state.user


# ── Helpers ───────────────────────────────────────────────────────────────────
def badge_html(level, score):
    ll  = (level or "").lower()
    cls = ("badge-strong"  if "strong"  in ll else
           "badge-good"    if "good"    in ll else
           "badge-partial" if "partial" in ll else "badge-stretch")
    return f'<span class="{cls}">{score}% · {level}</span>'

def score_color(s):
    return "#16a34a" if s >= 70 else "#d97706" if s >= 45 else "#dc2626"

def render_salary(sal: dict, key_suffix: str = ""):
    if not sal:
        st.info("Salary data unavailable.")
        return
    period   = sal.get("salary_period", "annual")
    is_ann   = period == "annual"
    p_label  = "per year (Annual CTC)" if is_ann else "per month"
    p_emoji  = "📅" if is_ann else "🗓️"
    display  = sal.get("salary_display", "")
    bd       = sal.get("salary_breakdown", {})
    monthly  = bd.get("monthly_in_hand", 0)
    web_used = sal.get("_web_data_used", False)
    sources  = sal.get("data_sources", [])
    insight  = sal.get("company_specific_insight", "")

    web_badge_html = '<span class="web-badge">🌐 Web-researched</span>' if web_used else ""
    st.markdown(
        f'<span class="salary-period-tag">{p_emoji} Figures are {p_label}</span>'
        f'{web_badge_html}',
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    if is_ann:
        c1.metric("Min CTC",    f"₹{sal.get('min_salary',    0):,} / yr")
        c2.metric("Median CTC", f"₹{sal.get('median_salary', 0):,} / yr")
        c3.metric("Max CTC",    f"₹{sal.get('max_salary',    0):,} / yr")
    else:
        c1.metric("Min Stipend",    f"₹{sal.get('min_salary',    0):,} / mo")
        c2.metric("Median Stipend", f"₹{sal.get('median_salary', 0):,} / mo")
        c3.metric("Max Stipend",    f"₹{sal.get('max_salary',    0):,} / mo")
    if display:
        st.markdown(f"**Range:** {display}")
    if is_ann and monthly:
        st.markdown(
            f'<div class="monthly-inhand">💵 Estimated monthly in-hand after tax: '
            f'<b>₹{monthly:,} / month</b></div>',
            unsafe_allow_html=True,
        )
    if insight and insight.strip().lower() not in ("n/a", "n/a — could not retrieve company data", ""):
        st.markdown(
            f'<div class="company-insight">🏢 <b>Company insight:</b> {insight}</div>',
            unsafe_allow_html=True,
        )
    if sources:
        st.caption("📚 Sources used: " + " · ".join(sources))
    if bd:
        with st.expander("📊 Full Salary Breakdown"):
            b1, b2, b3 = st.columns(3)
            b1.metric("Base Annual",  f"₹{bd.get('base_annual',      0):,}")
            b2.metric("Bonus Annual", f"₹{bd.get('bonus_annual',     0):,}")
            b3.metric("Total CTC",    f"₹{bd.get('total_ctc_annual', 0):,}")
            if monthly:
                st.caption(f"Monthly in-hand ≈ ₹{monthly:,} (estimated after ~25% tax)")
    st.write("**Experience Level:**", sal.get("experience_level", ""))
    comparables = sal.get("comparable_roles", [])
    if comparables:
        st.subheader("📊 Comparable Roles")
        for r in comparables:
            rp = r.get("period", period)
            rl = "/yr" if rp == "annual" else "/mo"
            st.write(f"• **{r.get('role','')}** — ₹{r.get('avg_salary', 0):,} {rl}")
    insights_list = sal.get("market_insights", [])
    if insights_list:
        st.subheader("💡 Market Insights")
        for i in insights_list:
            st.write(f"• {i}")
    tips = sal.get("negotiation_tips", [])
    if tips:
        st.subheader("🤝 Negotiation Tips")
        for t in tips:
            st.write(f"• {t}")


def render_skill_bridge(bridge_data: dict, current_score: float):
    """Render Skill-Gap Bridge inside Match & Gaps tab."""
    if not bridge_data:
        return
    bridges    = bridge_data.get("bridges", [])
    potential  = bridge_data.get("potential_score", current_score)
    quick_wins = bridge_data.get("quick_wins", [])
    if not bridges:
        st.success("🎉 No skill gaps! You're a strong match.")
        return

    st.markdown("---")
    st.markdown("## 🌉 Skill-Gap Bridge")
    st.caption("Free resources to close your skill gaps and boost your match score")

    c1, c2, c3 = st.columns(3)
    c1.metric("Current Score",   f"{current_score}%")
    c2.metric("Potential Score", f"{potential}%", delta=f"+{round(potential - current_score)}%")
    c3.metric("Skills to Learn", len(bridges))

    if quick_wins:
        qw = ", ".join(f"**{q['skill']}**" for q in quick_wins[:3])
        st.info(f"⚡ **Quick Wins (under 2 hrs):** {qw} — learn these first for fastest score boost!")

    st.markdown("### 📚 Your Learning Roadmap")

    for b in bridges:
        skill       = b.get("skill", "")
        resource    = b.get("resource", "")
        url         = b.get("url", "#")
        platform    = b.get("platform", "YouTube")
        difficulty  = b.get("difficulty", "📚 Medium")
        boost       = b.get("score_boost", 8)
        new_score   = b.get("new_score", current_score + boost)
        boost_color = "#16a34a" if boost >= 14 else "#d97706" if boost >= 10 else "#6b7280"

        st.markdown(f"""
<div style="background:#f8f9fa; border:1px solid #e5e7eb;
     border-left:4px solid {boost_color}; border-radius:10px;
     padding:14px 18px; margin-bottom:10px;">
  <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:8px;">
    <div style="flex:1; min-width:200px;">
      <div style="font-size:16px; font-weight:700; color:#1a1a2e; margin-bottom:4px;">
        ❌ Missing: <span style="color:#dc2626;">{skill}</span>
      </div>
      <div style="font-size:14px; color:#374151; margin-bottom:6px;">
        📖 <b>{resource}</b>
        <span style="background:#e0f2fe; color:#0369a1; border-radius:6px;
              padding:2px 8px; font-size:11px; margin-left:6px;">{platform}</span>
        <span style="background:#dcfce7; color:#15803d; border-radius:6px;
              padding:2px 8px; font-size:11px; margin-left:4px;">🆓 Free</span>
      </div>
      <div style="font-size:13px; color:#6b7280;">
        ⏱ {difficulty} &nbsp;·&nbsp;
        📈 Score after learning: <b style="color:{boost_color};">{new_score}%</b> (+{boost}%)
      </div>
    </div>
    <div style="text-align:center; min-width:80px;">
      <div style="font-size:22px; font-weight:800; color:{boost_color};">+{boost}%</div>
      <div style="font-size:11px; color:#9ca3af;">score boost</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)
        st.link_button(f"▶ Start Learning: {skill}", url)
        st.markdown("")

    total_hours = sum(b.get("hours", 3) for b in bridges)
    st.markdown(f"""
<div style="background:linear-gradient(135deg, #667eea 0%, #764ba2 100%);
     border-radius:12px; padding:16px 20px; margin-top:16px; color:white;">
  <div style="font-size:18px; font-weight:700; margin-bottom:4px;">
    🎯 Complete all {len(bridges)} resources
  </div>
  <div style="font-size:14px; opacity:0.9;">
    ⏱ Total time: ~{total_hours} hours &nbsp;·&nbsp;
    📈 Potential score: <b>{potential}%</b> &nbsp;·&nbsp;
    💰 All completely free
  </div>
</div>
""", unsafe_allow_html=True)


def save_analysis_to_history(company_name, job_description, match_score, result_data, analysis_type="resume_jd"):
    try:
        http_requests.post(
            f"{API_URL}/history/save",
            json={
                "company_name":    company_name,
                "job_description": job_description,
                "match_score":     int(match_score),
                "result_data":     result_data,
                "analysis_type":   analysis_type,
            },
            headers=auth_headers(),
            timeout=10,
        )
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🤖 AI Career Copilot")
    st.markdown(f"👋 **{user['name']}**  \n📧 {user['email']}")
    if st.button("Logout", use_container_width=True):
        for k in ["token", "user", "analysis_data", "resume_data", "recommended_jobs"]:
            st.session_state[k] = None
        st.session_state.selected_job_analysis = {}
        st.rerun()

    st.markdown("---")
    mode = st.radio("Mode", ["📄 Resume + Job Description", "🔍 Job Recommendations", "📚 My History"],
                    label_visibility="collapsed")
    st.markdown("---")

    if mode != "📚 My History":
        st.subheader("📋 Upload Resume")
        resume_file = st.file_uploader("PDF or DOCX", type=["pdf", "docx"])
    else:
        resume_file = None

    if mode == "📄 Resume + Job Description":
        st.subheader("📝 Job Description")
        job_description = st.text_area("Paste JD", height=180, placeholder="Paste the full job description here…")
        company_name  = st.text_input("Company Name", placeholder="e.g. Google")
        location      = st.text_input("Location", value="India")
        analyze_btn   = st.button("🚀 Analyze Resume", use_container_width=True, type="primary")
        find_jobs_btn = False
    elif mode == "🔍 Job Recommendations":
        st.subheader("⚙️ Settings")
        adzuna_id  = st.text_input("Adzuna App ID (optional)", placeholder="Free at adzuna.com/api")
        adzuna_key = st.text_input("Adzuna App Key (optional)", type="password")
        max_jobs   = st.slider("Max results", 5, 20, 12)
        st.markdown("<small>🌐 Remotive · 🌍 Arbeitnow · 🔍 Adzuna (optional)</small>", unsafe_allow_html=True)
        find_jobs_btn = st.button("🔍 Find Recommended Jobs", use_container_width=True, type="primary")
        analyze_btn   = False
    else:
        analyze_btn   = False
        find_jobs_btn = False

    st.markdown("---")
    st.caption("Powered by Groq + Llama3 · Salary data from web")


# ══════════════════════════════════════════════════════════════════════════════
# MODE 1 — Resume + Job Description
# ══════════════════════════════════════════════════════════════════════════════
if mode == "📄 Resume + Job Description":
    st.title("🤖 AI Career Copilot")

    if analyze_btn:
        if not resume_file or not job_description:
            st.error("Please upload a resume and enter a job description.")
        else:
            with st.spinner("🔍 Running all AI agents… (30–60 sec)"):
                resp = requests.post(
                    f"{API_URL}/analyze",
                    files={"resume": (resume_file.name, resume_file.getvalue(), "application/octet-stream")},
                    data={"job_description": job_description,
                          "company_name": company_name or "the company",
                          "location": location or "India"},
                    headers=auth_headers(),
                )
            if resp.status_code == 200:
                st.session_state.analysis_data = resp.json()
                st.success("✅ Analysis complete!")
                d = st.session_state.analysis_data
                save_analysis_to_history(
                    company_name=company_name or "Unknown",
                    job_description=job_description[:500],
                    match_score=d.get("match", {}).get("match_percentage", 0),
                    result_data=d,
                    analysis_type="resume_jd",
                )
            else:
                st.error(f"Error: {resp.text}")

    data = st.session_state.analysis_data
    if data:
        tabs = st.tabs(["👤 Resume", "🎯 Match & 🌉 Bridge", "📝 ATS", "🗺️ Roadmap",
                         "🎤 Interview", "✉️ Cover Letter", "💰 Salary"])

        with tabs[0]:
            r = data["resume"]
            st.subheader(r.get("name", "Candidate"))
            c1, c2 = st.columns(2)
            with c1:
                st.write("📧", r.get("email", ""))
                st.write("📱", r.get("phone", ""))
                edu = r.get("education", [])
                st.write("🎓", edu[0].get("degree", "") if edu else "")
            with c2:
                st.write("🏷️ Domain:", r.get("domain", ""))
                st.write("⏱️ Experience:", f"{r.get('experience_years', 0)} years")
            st.write("**Skills:**", ", ".join(r.get("skills", [])))
            st.write("**Tools:**",  ", ".join(r.get("tools",  [])))

        with tabs[1]:
            m = data["match"]
            c1, c2, c3 = st.columns(3)
            c1.metric("Overall Match", f"{m['match_percentage']}%")
            c2.metric("Skill Score",   f"{m['skill_score']}%")
            c3.metric("Semantic",      f"{m['semantic_score']}%")
            st.progress(m["match_percentage"] / 100)
            ca, cb = st.columns(2)
            with ca:
                st.success("✅ Matched Skills")
                for s in m.get("matched_skills", []): st.write(f"• {s}")
            with cb:
                st.error("❌ Missing Skills")
                for s in m.get("missing_skills", []): st.write(f"• {s}")
            # ── Skill-Gap Bridge ──────────────────────────────────────────
            render_skill_bridge(data.get("skill_bridge", {}), m["match_percentage"])

        with tabs[2]:
            a = data["ats"]
            st.subheader("Optimized Summary"); st.info(a.get("optimized_summary", ""))
            st.subheader("Improved Bullet Points")
            for b in a.get("improved_bullets", []): st.write(b)
            st.subheader("Formatting Tips")
            for t in a.get("formatting_tips", []): st.write(f"• {t}")

        with tabs[3]:
            rd = data["roadmap"]
            st.subheader(f"🎯 {rd.get('goal', '')}")
            st.caption(f"Duration: {rd.get('total_weeks', 0)} weeks")
            for w in rd.get("weeks", [])[:6]:
                with st.expander(f"Week {w['week']}: {w['focus']}"):
                    for t in w.get("tasks", []): st.write(f"• {t}")
                    st.success(f"🏁 {w.get('milestone', '')}")

        with tabs[4]:
            iv = data["interview"]
            st.subheader("Technical Questions")
            for q in iv.get("technical_questions", []):
                with st.expander(f"[{q['difficulty']}] {q['question']}"):
                    st.write("Topic:", q.get("topic", ""))
            st.subheader("Behavioral Questions")
            for q in iv.get("behavioral_questions", []): st.write(f"• {q}")

        with tabs[5]:
            cl = data["cover_letter"]
            st.subheader(cl.get("subject_line", ""))
            st.text_area("Cover Letter", cl.get("cover_letter", ""), height=300)

        with tabs[6]:
            render_salary(data.get("salary", {}), key_suffix="mode1")

    else:
        st.info("⬅️ Upload your resume and paste a job description, then click **Analyze Resume**.")


# ══════════════════════════════════════════════════════════════════════════════
# MODE 2 — Job Recommendations
# ══════════════════════════════════════════════════════════════════════════════
elif mode == "🔍 Job Recommendations":
    st.title("🔍 Recommended Jobs & Internships")
    st.caption("Ranked by AI match score · Software/Tech + Data Science/ML · Global + India")

    if find_jobs_btn:
        if not resume_file:
            st.error("Please upload your resume first.")
            st.stop()

        with st.spinner("📄 Reading your resume…"):
            res = requests.post(
                f"{API_URL}/analyze",
                files={"resume": (resume_file.name, resume_file.getvalue(), "application/octet-stream")},
                data={"job_description": "General software engineering and data science role",
                      "company_name": "any", "location": "Global"},
                headers=auth_headers(),
            )
        if res.status_code != 200:
            st.error(f"Could not read resume: {res.text}")
            st.stop()

        st.session_state.resume_data = res.json()["resume"]

        with st.spinner("🌐 Fetching jobs from 3 portals + AI ranking… (30–60 sec)"):
            job_res = requests.post(
                f"{API_URL}/recommend-jobs",
                json={"resume_data": st.session_state.resume_data,
                      "adzuna_app_id":  adzuna_id  or "",
                      "adzuna_app_key": adzuna_key or "",
                      "max_results":    max_jobs},
                headers=auth_headers(),
                timeout=120,
            )
        if job_res.status_code == 200:
            st.session_state.recommended_jobs      = job_res.json()["jobs"]
            st.session_state.selected_job_analysis = {}
            st.success(f"✅ {len(st.session_state.recommended_jobs)} jobs found and ranked!")
        else:
            st.error(f"Error: {job_res.text}")

    jobs        = st.session_state.recommended_jobs
    resume_data = st.session_state.resume_data

    if jobs:
        col_f1, col_f2, col_f3 = st.columns([2, 2, 2])
        with col_f1: type_filter   = st.selectbox("Type",   ["All", "Full-time", "Internship"])
        with col_f2: source_filter = st.selectbox("Source", ["All", "Remotive 🌐", "Arbeitnow 🌍", "Adzuna 🔍"])
        with col_f3: min_score     = st.slider("Min match %", 0, 90, 0, step=10)

        filtered = [
            j for j in jobs
            if (type_filter   == "All" or type_filter.lower() in j.get("job_type", "").lower())
            and (source_filter == "All" or source_filter.split()[0] in j.get("source", ""))
            and j.get("match_score", 0) >= min_score
        ]

        st.markdown(f"**Showing {len(filtered)} of {len(jobs)} jobs** — sorted best → least match")
        st.markdown("---")

        for idx, job in enumerate(filtered):
            score     = job.get("match_score", 0)
            level     = job.get("match_level",  "Partial Match")
            reason    = job.get("reason", "")
            is_intern = job.get("is_intern", False)

            type_badge = ('<span class="intern-badge">🎓 Internship</span>' if is_intern
                          else '<span class="job-badge">💼 Full-time</span>')
            source_tag = f'<span class="source-tag">{job.get("source","")}</span>'

            st.markdown(f"""
<div class="job-row">
  <div style="flex:1;min-width:0">
    <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:4px">
      <span style="font-size:16px;font-weight:700;color:#1a1a2e">{job['title']}</span>
      {type_badge} {source_tag}
    </div>
    <div style="font-size:13px;color:#555;margin-bottom:2px">
      🏢 <b>{job['company']}</b> &nbsp;·&nbsp; 📍 {job['location']}
      {"&nbsp;·&nbsp; 💰 " + job['salary'] if job.get('salary') and job['salary'] != 'Not specified' else ""}
    </div>
    <div style="font-size:12px;color:#888;font-style:italic">"{reason}"</div>
  </div>
  <div style="text-align:center;min-width:90px">
    <div style="font-size:26px;font-weight:800;color:{score_color(score)};line-height:1">{score}%</div>
    {badge_html(level, score)}
    <div style="font-size:10px;color:#aaa;margin-top:2px">📅 {job.get('posted_date','')}</div>
  </div>
</div>
""", unsafe_allow_html=True)

            b1, b2, _ = st.columns([2, 2, 4])
            with b1:
                do_analyze = st.button("🔬 Full Analysis", key=f"analyze_{idx}",
                                        use_container_width=True, type="primary")
            with b2:
                if job.get("url"):
                    st.link_button("🔗 View Job", job["url"], use_container_width=True)

            job_key = f"{job['title']}|{job['company']}"

            if do_analyze and job_key not in st.session_state.selected_job_analysis:
                with st.spinner(f"🤖 Analyzing {job['title']} at {job['company']}…"):
                    try:
                        r = requests.post(
                            f"{API_URL}/analyze-job",
                            json={"resume_data": resume_data,
                                  "job_title":       job["title"],
                                  "job_description": job["description"],
                                  "company_name":    job["company"]},
                            headers=auth_headers(),
                            timeout=90,
                        )
                        result = r.json() if r.status_code == 200 else {"error": r.text}
                        st.session_state.selected_job_analysis[job_key] = result
                        if r.status_code == 200:
                            save_analysis_to_history(
                                company_name=job["company"],
                                job_description=job.get("description", "")[:500],
                                match_score=result.get("match", {}).get("match_percentage", score),
                                result_data=result,
                                analysis_type="job_recommendation",
                            )
                    except Exception as e:
                        st.session_state.selected_job_analysis[job_key] = {"error": str(e)}

            if job_key in st.session_state.selected_job_analysis:
                analysis = st.session_state.selected_job_analysis[job_key]
                with st.expander(f"📊 Full Analysis — {job['title']} @ {job['company']}", expanded=True):
                    if "error" in analysis:
                        st.error(analysis["error"])
                    else:
                        atabs = st.tabs(["🎯 Match & 🌉 Bridge", "📝 ATS Tips", "🗺️ Roadmap",
                                          "🎤 Interview", "✉️ Cover Letter", "💰 Salary"])

                        with atabs[0]:
                            m = analysis.get("match", {})
                            c1, c2, c3 = st.columns(3)
                            c1.metric("Overall Match", f"{m.get('match_percentage', score)}%")
                            c2.metric("Skill Score",   f"{m.get('skill_score', 0)}%")
                            c3.metric("Semantic",      f"{m.get('semantic_score', 0)}%")
                            st.progress(m.get("match_percentage", score) / 100)
                            cg1, cg2 = st.columns(2)
                            with cg1:
                                st.markdown("**✅ Matched Skills**")
                                st.markdown(" ".join(f'<span class="chip-matched">{s}</span>'
                                            for s in m.get("matched_skills", [])) or "_None_",
                                            unsafe_allow_html=True)
                            with cg2:
                                st.markdown("**🔑 Keywords to Add**")
                                kws = analysis.get("ats", {}).get("keywords_to_add", [])
                                st.markdown(" ".join(f'<span class="chip-keyword">{k}</span>'
                                            for k in kws[:12]) or "_Already optimized_",
                                            unsafe_allow_html=True)
                            # ── Skill-Gap Bridge ──────────────────────────
                            render_skill_bridge(
                                analysis.get("skill_bridge", {}),
                                m.get("match_percentage", score)
                            )

                        with atabs[1]:
                            a = analysis.get("ats", {})
                            st.subheader("Optimized Summary"); st.info(a.get("optimized_summary", ""))
                            st.subheader("Improved Bullet Points")
                            for b in a.get("improved_bullets", []): st.write(b)
                            st.subheader("Formatting Tips")
                            for t in a.get("formatting_tips", []): st.write(f"• {t}")

                        with atabs[2]:
                            rd = analysis.get("roadmap", {})
                            st.subheader(f"🎯 {rd.get('goal', '')}")
                            st.caption(f"{rd.get('total_weeks', 0)} weeks")
                            for w in rd.get("weeks", [])[:6]:
                                with st.expander(f"Week {w['week']}: {w['focus']}"):
                                    for t in w.get("tasks", []): st.write(f"• {t}")
                                    st.success(f"🏁 {w.get('milestone', '')}")

                        with atabs[3]:
                            iv = analysis.get("interview", {})
                            st.subheader("Technical Questions")
                            for q in iv.get("technical_questions", []):
                                with st.expander(f"[{q['difficulty']}] {q['question']}"):
                                    st.write("Topic:", q.get("topic", ""))
                            st.subheader("Behavioral Questions")
                            for q in iv.get("behavioral_questions", []): st.write(f"• {q}")
                            st.subheader("Tips")
                            for t in iv.get("tips", []): st.write(f"💡 {t}")

                        with atabs[4]:
                            cl = analysis.get("cover_letter", {})
                            st.subheader(cl.get("subject_line", ""))
                            st.text_area("Cover Letter", cl.get("cover_letter", ""),
                                          height=280, key=f"cl_{idx}_{job_key[:20]}")

                        with atabs[5]:
                            render_salary(analysis.get("salary", {}), key_suffix=f"job_{idx}")

            st.markdown("---")

    else:
        st.markdown("""
### How it works
1. **Upload your resume** in the sidebar
2. Click **Find Recommended Jobs**
3. Jobs fetched from **3 live portals**, ranked by AI match score
4. Click **🔬 Full Analysis** on any job for deep analysis + Skill-Gap Bridge

> 💡 Get free Adzuna keys at [developer.adzuna.com](https://developer.adzuna.com)
        """)


# ══════════════════════════════════════════════════════════════════════════════
# MODE 3 — History
# ══════════════════════════════════════════════════════════════════════════════
elif mode == "📚 My History":
    st.title("📚 My Analysis History")
    st.caption("All your past resume analyses saved automatically")

    try:
        res = http_requests.get(f"{API_URL}/history", headers=auth_headers(), timeout=10)
        if res.status_code == 200:
            history = res.json().get("history", [])
            if not history:
                st.info("No analyses saved yet. Run your first analysis to see it here!")
            else:
                st.markdown(f"**{len(history)} analyses found**")
                st.markdown("---")
                for item in history:
                    score      = item.get("match_score", 0)
                    company    = item.get("company", "Unknown")
                    atype      = item.get("analysis_type", "resume_jd")
                    created_at = item.get("created_at", "")[:10]
                    type_label = "📄 Resume + JD" if atype == "resume_jd" else "🔍 Job Recommendation"
                    color      = score_color(score)
                    st.markdown(f"""
<div class="history-card">
  <div>
    <div style="font-weight:700;font-size:15px;color:#1a1a2e">{company}</div>
    <div style="font-size:12px;color:#6b7280">{type_label} &nbsp;·&nbsp; 📅 {created_at}</div>
  </div>
  <div style="font-size:22px;font-weight:800;color:{color}">{score}%</div>
</div>
""", unsafe_allow_html=True)
        else:
            st.error("Could not load history. Please try again.")
    except Exception as e:
        st.error(f"Error loading history: {e}")