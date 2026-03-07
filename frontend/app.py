import streamlit as st
import requests
import requests as http_requests

API_URL = "https://career-copilot-otjj.onrender.com/api"

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
.recruiter-card {
    background:linear-gradient(135deg,#f0f9ff,#e0f2fe);
    border:1px solid #bae6fd; border-radius:12px;
    padding:16px 20px; margin-bottom:12px;
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
    ("recruiter_token", None),
    ("recruiter", None),
    ("rec_email_checked", False),
    ("rec_has_password", False),
    ("rec_email", ""),
    ("rec_company", ""),
    ("rec_otp_sent", False),
    ("rec_forgot_password", False),
    ("views_tracked", False),
    # Candidate forgot password states
    ("cand_forgot_mode", False),
    ("cand_otp_sent", False),
    ("cand_reset_email", ""),
]:
    if k not in st.session_state:
        st.session_state[k] = v


# ── Auth helpers ──────────────────────────────────────────────────────────────
def auth_headers():
    return {"Authorization": f"Bearer {st.session_state.token}"}

def recruiter_auth_headers():
    return {"Authorization": f"Bearer {st.session_state.recruiter_token}"}

def reset_recruiter_auth_state():
    for k in ["rec_email_checked", "rec_has_password", "rec_email",
              "rec_company", "rec_otp_sent", "rec_forgot_password"]:
        st.session_state[k] = False if isinstance(st.session_state[k], bool) else ""

def reset_candidate_forgot_state():
    st.session_state.cand_forgot_mode  = False
    st.session_state.cand_otp_sent     = False
    st.session_state.cand_reset_email  = ""


# ══════════════════════════════════════════════════════════════════════════════
# AUTH GATE — Candidate Login
# ══════════════════════════════════════════════════════════════════════════════
query_params      = st.query_params
is_recruiter_mode = query_params.get("portal", "") == "recruiter"

if not st.session_state.token and not is_recruiter_mode:
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
            # ── Forgot Password Flow ──────────────────────────────────────────
            if st.session_state.cand_forgot_mode:
                st.markdown("#### 🔄 Reset Your Password")

                if not st.session_state.cand_otp_sent:
                    st.caption("Enter your registered email to receive a reset code.")
                    fp_email = st.text_input("Email", key="fp_email_input", placeholder="you@example.com")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("📧 Send Reset Code", type="primary", use_container_width=True):
                            if not fp_email:
                                st.error("Please enter your email.")
                            else:
                                with st.spinner("Sending code..."):
                                    try:
                                        r = http_requests.post(
                                            f"{API_URL}/auth/forgot-password",
                                            json={"email": fp_email}, timeout=15,
                                        )
                                        if r.status_code == 200:
                                            st.session_state.cand_reset_email = fp_email
                                            st.session_state.cand_otp_sent    = True
                                            st.rerun()
                                        else:
                                            st.error(r.json().get("detail", "Failed to send code."))
                                    except Exception as e:
                                        st.error(f"Could not connect: {e}")
                    with c2:
                        if st.button("← Back to Login", use_container_width=True):
                            reset_candidate_forgot_state()
                            st.rerun()

                else:
                    email = st.session_state.cand_reset_email
                    st.success(f"✅ Code sent to **{email}**")
                    fp_otp  = st.text_input("6-digit Code", max_chars=6, placeholder="123456", key="fp_otp")
                    fp_new  = st.text_input("New Password", type="password", placeholder="Min 6 characters", key="fp_new_pass")
                    fp_conf = st.text_input("Confirm Password", type="password", placeholder="Repeat password", key="fp_conf_pass")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✅ Reset Password", type="primary", use_container_width=True):
                            if not fp_otp:
                                st.error("Please enter the verification code.")
                            elif not fp_new or len(fp_new) < 6:
                                st.error("Password must be at least 6 characters.")
                            elif fp_new != fp_conf:
                                st.error("Passwords do not match.")
                            else:
                                with st.spinner("Resetting..."):
                                    try:
                                        r = http_requests.post(
                                            f"{API_URL}/auth/reset-password",
                                            json={"email": email, "otp": fp_otp, "password": fp_new},
                                            timeout=15,
                                        )
                                        if r.status_code == 200:
                                            data = r.json()
                                            st.session_state.token = data["token"]
                                            st.session_state.user  = data["user"]
                                            reset_candidate_forgot_state()
                                            st.success(f"✅ Password reset! Welcome back, {data['user']['name']}!")
                                            st.rerun()
                                        else:
                                            st.error(r.json().get("detail", "Reset failed."))
                                    except Exception as e:
                                        st.error(f"Could not connect: {e}")
                    with c2:
                        if st.button("🔄 Resend Code", use_container_width=True):
                            st.session_state.cand_otp_sent = False
                            st.rerun()
                    st.markdown("---")
                    if st.button("← Back to Login"):
                        reset_candidate_forgot_state()
                        st.rerun()

            # ── Normal Login ──────────────────────────────────────────────────
            else:
                st.markdown("#### Welcome back!")
                login_email = st.text_input("Email", key="login_email", placeholder="you@example.com")
                login_pass  = st.text_input("Password", type="password", key="login_pass", placeholder="Your password")
                st.markdown("")
                c1, c2 = st.columns([3, 2])
                with c1:
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
                with c2:
                    if st.button("Forgot password?", use_container_width=True, key="cand_forgot_btn"):
                        st.session_state.cand_forgot_mode = True
                        st.rerun()

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

        st.markdown("---")
        st.markdown(
            "<div style='text-align:center;font-size:13px;color:#6b7280;'>"
            "Are you a recruiter? "
            "<a href='?portal=recruiter' target='_self'>Access Recruiter Portal →</a>"
            "</div>",
            unsafe_allow_html=True
        )

    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# RECRUITER PORTAL
# ══════════════════════════════════════════════════════════════════════════════
if is_recruiter_mode:
    st.markdown("""
    <div style="background:linear-gradient(135deg,#1a1a2e,#16213e);border-radius:16px;
         padding:28px 32px;margin-bottom:24px;color:white;">
      <div style="font-size:28px;font-weight:800;margin-bottom:4px;">🏢 Recruiter Portal</div>
      <div style="font-size:14px;opacity:0.8;">Discover top talent by their actual work — not just resumes</div>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.recruiter_token:

        if not st.session_state.rec_email_checked:
            st.markdown("### 👋 Welcome to the Recruiter Portal")
            st.caption("Enter your work email to get started. Personal emails (Gmail, Yahoo, Hotmail) are not accepted.")
            col1, _ = st.columns([2, 1])
            with col1:
                rec_email_input = st.text_input(
                    "Work Email", placeholder="you@razorpay.com / you@infosys.com",
                    key="rec_email_input_step1"
                )
            if st.button("Continue →", type="primary"):
                if not rec_email_input:
                    st.error("Please enter your work email.")
                else:
                    with st.spinner("Checking..."):
                        try:
                            r = http_requests.post(
                                f"{API_URL}/recruiter/check-email",
                                json={"email": rec_email_input}, timeout=10,
                            )
                            if r.status_code == 200:
                                data = r.json()
                                st.session_state.rec_email         = rec_email_input
                                st.session_state.rec_has_password  = data["has_password"]
                                st.session_state.rec_company       = data["company"]
                                st.session_state.rec_email_checked = True
                                st.rerun()
                            else:
                                st.error(r.json().get("detail", "Invalid email."))
                        except Exception as e:
                            st.error(f"Could not connect: {e}")

        elif st.session_state.rec_has_password and not st.session_state.rec_forgot_password:
            company = st.session_state.rec_company
            email   = st.session_state.rec_email
            st.markdown("### 🔑 Welcome back!")
            st.success(f"✅ Account found — **{company}** · {email}")
            col1, _ = st.columns([2, 1])
            with col1:
                rec_password = st.text_input("Password", type="password", key="rec_password_input", placeholder="Your password")
            c1, c2 = st.columns([2, 2])
            with c1:
                if st.button("Sign In →", type="primary", use_container_width=True):
                    if not rec_password:
                        st.error("Please enter your password.")
                    else:
                        with st.spinner("Signing in..."):
                            try:
                                r = http_requests.post(
                                    f"{API_URL}/recruiter/login",
                                    json={"email": email, "password": rec_password}, timeout=10,
                                )
                                if r.status_code == 200:
                                    data = r.json()
                                    st.session_state.recruiter_token = data["token"]
                                    st.session_state.recruiter       = data["recruiter"]
                                    st.session_state.views_tracked   = False
                                    reset_recruiter_auth_state()
                                    st.rerun()
                                else:
                                    st.error(r.json().get("detail", "Sign in failed."))
                            except Exception as e:
                                st.error(f"Could not connect: {e}")
            with c2:
                if st.button("Forgot password?", use_container_width=True):
                    st.session_state.rec_forgot_password = True
                    st.session_state.rec_otp_sent        = False
                    st.rerun()
            st.markdown("---")
            if st.button("← Use a different email"):
                reset_recruiter_auth_state()
                st.rerun()

        else:
            email    = st.session_state.rec_email
            company  = st.session_state.rec_company
            is_reset = st.session_state.rec_forgot_password
            if is_reset:
                st.markdown("### 🔄 Reset Your Password")
                st.caption(f"We'll send a one-time code to **{email}**.")
            else:
                st.markdown("### ✨ Create Your Recruiter Account")
                st.info(f"🏢 Company detected: **{company}** · {email}")

            if not st.session_state.rec_otp_sent:
                if st.button("📧 Send Verification Code", type="primary"):
                    with st.spinner("Sending code..."):
                        try:
                            r = http_requests.post(
                                f"{API_URL}/recruiter/send-otp",
                                json={"email": email}, timeout=15,
                            )
                            if r.status_code == 200:
                                st.session_state.rec_otp_sent = True
                                st.rerun()
                            else:
                                st.error(r.json().get("detail", "Failed to send code."))
                        except Exception as e:
                            st.error(f"Could not send code: {e}")
            else:
                st.success(f"✅ Code sent to **{email}**")
                col1, col2 = st.columns([1, 1])
                with col1:
                    entered_otp = st.text_input("6-digit Code", max_chars=6, placeholder="123456", key="rec_otp_input")
                with col2:
                    rec_full_name = st.text_input("Your Full Name", placeholder="Priya Sharma", key="rec_name_input")
                col3, col4 = st.columns([1, 1])
                with col3:
                    new_password = st.text_input("Set a Password" if not is_reset else "New Password",
                                                  type="password", placeholder="Min 6 characters", key="rec_new_pass")
                with col4:
                    confirm_password = st.text_input("Confirm Password", type="password",
                                                      placeholder="Repeat password", key="rec_confirm_pass")
                cv1, cv2 = st.columns([2, 1])
                with cv1:
                    if st.button("✅ Verify & Sign In", type="primary", use_container_width=True):
                        if not entered_otp:
                            st.error("Please enter the verification code.")
                        elif not rec_full_name:
                            st.error("Please enter your full name.")
                        elif not new_password or len(new_password) < 6:
                            st.error("Password must be at least 6 characters.")
                        elif new_password != confirm_password:
                            st.error("Passwords do not match.")
                        else:
                            with st.spinner("Verifying..."):
                                try:
                                    r = http_requests.post(
                                        f"{API_URL}/recruiter/verify-otp",
                                        json={"email": email, "otp": entered_otp,
                                              "full_name": rec_full_name, "password": new_password},
                                        timeout=15,
                                    )
                                    if r.status_code == 200:
                                        data = r.json()
                                        st.session_state.recruiter_token = data["token"]
                                        st.session_state.recruiter       = data["recruiter"]
                                        st.session_state.views_tracked   = False
                                        reset_recruiter_auth_state()
                                        st.rerun()
                                    else:
                                        st.error(r.json().get("detail", "Verification failed."))
                                except Exception as e:
                                    st.error(f"Verification failed: {e}")
                with cv2:
                    if st.button("🔄 Resend Code", use_container_width=True):
                        st.session_state.rec_otp_sent = False
                        st.rerun()

            st.markdown("---")
            if st.button("← Use a different email"):
                reset_recruiter_auth_state()
                st.rerun()

        st.markdown(
            "<div style='text-align:center;font-size:13px;color:#6b7280;margin-top:16px;'>"
            "<a href='/' target='_self'>← Back to Candidate Portal</a></div>",
            unsafe_allow_html=True
        )
        st.stop()

    # ── Recruiter logged in ───────────────────────────────────────────────────
    rec = st.session_state.recruiter

    with st.sidebar:
        st.markdown("## 🏢 Recruiter Portal")
        st.markdown(f"👋 **{rec['full_name']}**")
        st.markdown(f"🏢 {rec['company_name']}")
        st.markdown(f"📧 {rec['email']}")
        st.markdown("---")
        if st.button("Logout", use_container_width=True):
            st.session_state.recruiter_token = None
            st.session_state.recruiter       = None
            st.session_state.views_tracked   = False
            st.rerun()
        st.markdown("---")
        st.markdown("<a href='/' target='_self'>← Candidate Portal</a>", unsafe_allow_html=True)

    tab_discover, tab_saved, tab_activity = st.tabs(["🔍 Discover Talent", "🔖 Saved Projects", "📋 My Activity"])

    with tab_discover:
        st.markdown("### 🔍 Discover Talent")
        st.caption("Browse projects submitted by candidates. Use filters to find exactly who you need.")

        sf1, sf2, sf3 = st.columns([3, 2, 2])
        with sf1:
            st.markdown("**🔎 Search by skill, role, or tech**")
            search_query = st.text_input(
                "Search", placeholder="e.g. React developer, Python ML, Docker...",
                label_visibility="collapsed", key="rec_search"
            )
        with sf2:
            st.markdown("**📊 Sort projects by**")
            sort_by = st.selectbox(
                "Sort by",
                ["relevance", "recent", "interest"],
                format_func=lambda x: {
                    "relevance": "⭐ Best Quality First (AI Score)",
                    "recent":    "🕐 Newest Submissions First",
                    "interest":  "🔥 Most Recruiter Interest First",
                }[x],
                label_visibility="collapsed", key="rec_sort"
            )
        with sf3:
            st.markdown("**🏷️ Filter by role**")
            role_filter = st.selectbox(
                "Role",
                ["All Roles", "Frontend", "Backend", "Full Stack", "ML/AI", "Data Science", "DevOps", "Mobile"],
                label_visibility="collapsed", key="rec_role"
            )

        # Only track views once per session
        if not st.session_state.views_tracked:
            params = {"sort_by": sort_by, "recruiter_id": rec["id"], "track_views": "true"}
            st.session_state.views_tracked = True
        else:
            params = {"sort_by": sort_by, "recruiter_id": rec["id"]}

        if search_query:
            params["search"] = search_query
        if role_filter != "All Roles":
            params["role_filter"] = role_filter

        try:
            feed_res = http_requests.get(f"{API_URL}/projects", params=params, timeout=15)
            if feed_res.status_code == 200:
                projects = feed_res.json().get("projects", [])
                st.markdown(f"**{len(projects)} projects found**")
                st.markdown("---")

                if not projects:
                    st.info("No projects match your search. Try different keywords or clear filters.")
                else:
                    for proj in projects:
                        score         = proj.get("relevance_score", 0)
                        is_bookmarked = proj.get("is_bookmarked", False)

                        tags_html = " ".join(
                            f'<span style="background:#ede9fe;color:#5b21b6;border-radius:6px;padding:2px 8px;font-size:11px;margin:2px;display:inline-block;">{t}</span>'
                            for t in proj.get("ai_tags", [])
                        )
                        stack_html = " ".join(
                            f'<span style="background:#f3f4f6;color:#374151;border-radius:6px;padding:2px 8px;font-size:11px;margin:2px;display:inline-block;">{s}</span>'
                            for s in (proj.get("tech_stack") or [])[:8]
                        )
                        github_btn = f'<a href="{proj["github_url"]}" target="_blank" style="background:#1a1a2e;color:white;border-radius:6px;padding:4px 12px;font-size:12px;text-decoration:none;margin-right:6px;">⚡ GitHub</a>' if proj.get("github_url") else ""
                        demo_btn   = f'<a href="{proj["demo_url"]}" target="_blank" style="background:#0369a1;color:white;border-radius:6px;padding:4px 12px;font-size:12px;text-decoration:none;">🌐 Live Demo</a>' if proj.get("demo_url") else ""

                        pc1, pc2 = st.columns([1, 6])
                        with pc1:
                            st.markdown(f"""
<div style="background:linear-gradient(135deg,#667eea,#764ba2);border-radius:12px;
     padding:14px 8px;text-align:center;color:white;">
  <div style="font-size:10px;opacity:0.8;margin-bottom:2px;">AI Score</div>
  <div style="font-size:22px;font-weight:800;">{int(score)}</div>
  <div style="font-size:10px;opacity:0.8;">/100</div>
  <div style="margin-top:8px;font-size:18px;">{"🔖" if is_bookmarked else "📌"}</div>
</div>
""", unsafe_allow_html=True)

                        with pc2:
                            st.markdown(f"""
<div style="background:#f8f9fa;border:1px solid #e5e7eb;border-left:4px solid #667eea;
     border-radius:10px;padding:16px 18px;margin-bottom:4px;">
  <div style="font-size:18px;font-weight:800;color:#1a1a2e;margin-bottom:4px;">📂 {proj['title']}</div>
  <div style="font-size:13px;color:#6b7280;margin-bottom:8px;">
    👤 <b>{proj['submitter_name']}</b> &nbsp;·&nbsp; 📅 {proj.get('created_at','')[:10]}
    &nbsp;·&nbsp; 💼 {proj.get('interest_count', 0)} recruiter(s) interested
    &nbsp;·&nbsp; 👁️ {proj.get('views', 0)} views
  </div>
  <div style="font-size:14px;color:#374151;margin-bottom:10px;font-style:italic;">
    "{proj.get('ai_summary', proj.get('description','')[:100])}"
  </div>
  <div style="margin-bottom:8px;">{tags_html}</div>
  <div style="margin-bottom:10px;">{stack_html}</div>
  <div>{github_btn}{demo_btn}</div>
</div>
""", unsafe_allow_html=True)

                        ab1, ab2, _ = st.columns([2, 2, 4])
                        with ab1:
                            bm_label = "🔖 Unsave" if is_bookmarked else "📌 Save Project"
                            if st.button(bm_label, key=f"bm_{proj['id']}", use_container_width=True):
                                try:
                                    br = http_requests.post(
                                        f"{API_URL}/projects/{proj['id']}/bookmark",
                                        headers=recruiter_auth_headers(), timeout=10,
                                    )
                                    if br.status_code == 200:
                                        action = br.json().get("action", "saved")
                                        st.success("Saved! 🔖" if action == "saved" else "Removed from saved")
                                        st.rerun()
                                    else:
                                        st.error(f"Error {br.status_code}: {br.text}")
                                except Exception as e:
                                    st.error(str(e))

                        with ab2:
                            if st.button("💼 I'm Interested", key=f"int_{proj['id']}", type="primary", use_container_width=True):
                                st.session_state[f"show_interest_{proj['id']}"] = True

                        if st.session_state.get(f"show_interest_{proj['id']}", False):
                            with st.expander(f"✉️ Send Interest — {proj['title']}", expanded=True):
                                i_msg = st.text_area(
                                    "Message to candidate (optional)",
                                    key=f"imsg_{proj['id']}",
                                    placeholder="Tell them why you're interested in their work...",
                                    height=80
                                )
                                ic1, ic2 = st.columns(2)
                                with ic1:
                                    if st.button("📩 Send", key=f"isend_{proj['id']}", type="primary", use_container_width=True):
                                        try:
                                            ir = http_requests.post(
                                                f"{API_URL}/projects/{proj['id']}/interest",
                                                json={
                                                    "recruiter_id":    rec["id"],
                                                    "recruiter_name":  rec["full_name"],
                                                    "recruiter_email": rec["email"],
                                                    "company_name":    rec["company_name"],
                                                    "message":         i_msg,
                                                },
                                                headers=recruiter_auth_headers(), timeout=15,
                                            )
                                            if ir.status_code == 200:
                                                st.success(f"✅ Interest sent! {proj['submitter_name']} has been notified.")
                                                st.session_state[f"show_interest_{proj['id']}"] = False
                                                st.rerun()
                                            else:
                                                st.error(ir.json().get("detail", ir.text))
                                        except Exception as e:
                                            st.error(str(e))
                                with ic2:
                                    if st.button("Cancel", key=f"icancel_{proj['id']}", use_container_width=True):
                                        st.session_state[f"show_interest_{proj['id']}"] = False
                                        st.rerun()

                        st.markdown("---")
            else:
                st.error(f"Could not load projects. Error {feed_res.status_code}: {feed_res.text}")
        except Exception as e:
            st.error(f"Error loading projects: {e}")

    with tab_saved:
        st.markdown("### 🔖 Your Saved Projects")
        st.caption("Projects you've bookmarked for later review.")
        try:
            saved_res = http_requests.get(
                f"{API_URL}/recruiter/bookmarks",
                headers=recruiter_auth_headers(), timeout=15,
            )
            if saved_res.status_code == 200:
                saved = saved_res.json().get("bookmarks", [])
                if not saved:
                    st.info("📭 No saved projects yet. Browse the **Discover Talent** tab and click **📌 Save Project**.")
                else:
                    st.markdown(f"**{len(saved)} saved projects**")
                    for proj in saved:
                        st.markdown(f"""
<div class="recruiter-card">
  <div style="font-size:16px;font-weight:700;color:#1a1a2e;margin-bottom:4px;">📂 {proj['title']}</div>
  <div style="font-size:13px;color:#6b7280;margin-bottom:6px;">
    👤 {proj['submitter_name']} &nbsp;·&nbsp; 📅 {proj.get('created_at','')[:10]}
  </div>
  <div style="font-size:13px;color:#374151;font-style:italic;">"{proj.get('ai_summary', proj.get('description','')[:80])}"</div>
</div>
""", unsafe_allow_html=True)
                        sc1, sc2 = st.columns([2, 2])
                        with sc1:
                            if proj.get("github_url"):
                                st.link_button("⚡ GitHub", proj["github_url"], use_container_width=True)
                        with sc2:
                            if st.button("🗑 Remove", key=f"unsave_{proj['id']}", use_container_width=True):
                                try:
                                    http_requests.post(
                                        f"{API_URL}/projects/{proj['id']}/bookmark",
                                        headers=recruiter_auth_headers(), timeout=10,
                                    )
                                    st.rerun()
                                except Exception:
                                    pass
            else:
                try:
                    detail = saved_res.json().get("detail", saved_res.text)
                except Exception:
                    detail = saved_res.text
                st.warning(f"⚠️ Could not load saved projects (Error {saved_res.status_code}): {detail}")
        except Exception as e:
            st.error(f"Connection error: {e}")

    with tab_activity:
        st.markdown("### 📋 Candidates You've Reached Out To")
        st.caption("Full history of all interest messages you've sent.")
        try:
            act_res = http_requests.get(
                f"{API_URL}/recruiter/activity",
                headers=recruiter_auth_headers(), timeout=15,
            )
            if act_res.status_code == 200:
                activities = act_res.json().get("activities", [])
                if not activities:
                    st.info("📭 You haven't expressed interest in any projects yet. Head to **Discover Talent** to get started!")
                else:
                    st.markdown(f"**{len(activities)} candidates reached out to**")
                    for act in activities:
                        st.markdown(f"""
<div style="background:#f8f9fa;border:1px solid #e5e7eb;border-left:4px solid #16a34a;
     border-radius:10px;padding:14px 16px;margin-bottom:10px;">
  <div style="font-size:15px;font-weight:700;">📂 {act.get('project_title','')}</div>
  <div style="font-size:12px;color:#6b7280;">
    👤 {act.get('candidate_name','')} &nbsp;·&nbsp; 📅 {act.get('created_at','')[:10]}
  </div>
  {f'<div style="font-size:13px;color:#374151;margin-top:4px;font-style:italic;">"{act.get("message","")}"</div>' if act.get('message') else ''}
</div>
""", unsafe_allow_html=True)
            else:
                try:
                    detail = act_res.json().get("detail", act_res.text)
                except Exception:
                    detail = act_res.text
                st.warning(f"⚠️ Could not load activity (Error {act_res.status_code}): {detail}")
        except Exception as e:
            st.error(f"Connection error: {e}")

    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# CANDIDATE PORTAL
# ══════════════════════════════════════════════════════════════════════════════
user = st.session_state.user


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
        f'<span class="salary-period-tag">{p_emoji} Figures are {p_label}</span>{web_badge_html}',
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
            f'<div class="monthly-inhand">💵 Estimated monthly in-hand after tax: <b>₹{monthly:,} / month</b></div>',
            unsafe_allow_html=True,
        )
    if insight and insight.strip().lower() not in ("n/a", "n/a — could not retrieve company data", ""):
        st.markdown(f'<div class="company-insight">🏢 <b>Company insight:</b> {insight}</div>', unsafe_allow_html=True)
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
    for r in sal.get("comparable_roles", []):
        rp = r.get("period", period)
        st.write(f"• **{r.get('role','')}** — ₹{r.get('avg_salary', 0):,} {'/ yr' if rp == 'annual' else '/ mo'}")
    for i in sal.get("market_insights", []):
        st.write(f"• {i}")
    for t in sal.get("negotiation_tips", []):
        st.write(f"• {t}")


def render_skill_bridge(bridge_data: dict, current_score: float):
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
<div style="background:#f8f9fa;border:1px solid #e5e7eb;border-left:4px solid {boost_color};
     border-radius:10px;padding:14px 18px;margin-bottom:10px;">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;">
    <div style="flex:1;min-width:200px;">
      <div style="font-size:16px;font-weight:700;color:#1a1a2e;margin-bottom:4px;">
        ❌ Missing: <span style="color:#dc2626;">{skill}</span>
      </div>
      <div style="font-size:14px;color:#374151;margin-bottom:6px;">
        📖 <b>{resource}</b>
        <span style="background:#e0f2fe;color:#0369a1;border-radius:6px;padding:2px 8px;font-size:11px;margin-left:6px;">{platform}</span>
        <span style="background:#dcfce7;color:#15803d;border-radius:6px;padding:2px 8px;font-size:11px;margin-left:4px;">🆓 Free</span>
      </div>
      <div style="font-size:13px;color:#6b7280;">
        ⏱ {difficulty} &nbsp;·&nbsp; 📈 Score after learning: <b style="color:{boost_color};">{new_score}%</b> (+{boost}%)
      </div>
    </div>
    <div style="text-align:center;min-width:80px;">
      <div style="font-size:22px;font-weight:800;color:{boost_color};">+{boost}%</div>
      <div style="font-size:11px;color:#9ca3af;">score boost</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)
        st.link_button(f"▶ Start Learning: {skill}", url)

    total_hours = sum(b.get("hours", 3) for b in bridges)
    st.markdown(f"""
<div style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);
     border-radius:12px;padding:16px 20px;margin-top:16px;color:white;">
  <div style="font-size:18px;font-weight:700;margin-bottom:4px;">🎯 Complete all {len(bridges)} resources</div>
  <div style="font-size:14px;opacity:0.9;">⏱ ~{total_hours} hours &nbsp;·&nbsp; 📈 Potential: <b>{potential}%</b> &nbsp;·&nbsp; 💰 All free</div>
</div>
""", unsafe_allow_html=True)


def save_analysis_to_history(company_name, job_description, match_score, result_data, analysis_type="resume_jd"):
    try:
        http_requests.post(
            f"{API_URL}/history/save",
            json={"company_name": company_name, "job_description": job_description,
                  "match_score": int(match_score), "result_data": result_data, "analysis_type": analysis_type},
            headers=auth_headers(), timeout=10,
        )
    except Exception:
        pass


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🤖 AI Career Copilot")
    st.markdown(f"👋 **{user['name']}**  \n📧 {user['email']}")
    if st.button("Logout", use_container_width=True):
        for k in ["token", "user", "analysis_data", "resume_data", "recommended_jobs"]:
            st.session_state[k] = None
        st.session_state.selected_job_analysis = {}
        st.rerun()

    st.markdown("---")
    mode = st.radio("Mode", [
        "📄 Resume + Job Description",
        "🔍 Job Recommendations",
        "🚀 Reverse Pitch",
        "📚 My History",
    ], label_visibility="collapsed")

    st.markdown("---")
    st.markdown(
        "<div style='text-align:center;font-size:12px;color:#6b7280;'>"
        "Are you a recruiter?<br>"
        "<a href='?portal=recruiter' target='_self'>🏢 Recruiter Portal →</a>"
        "</div>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    if mode not in ("📚 My History", "🚀 Reverse Pitch"):
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
    elif mode == "🚀 Reverse Pitch":
        analyze_btn   = False
        find_jobs_btn = False
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
                    result_data=d, analysis_type="resume_jd",
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
            st.error(f"Could not read resume: {res.text}"); st.stop()
        st.session_state.resume_data = res.json()["resume"]
        with st.spinner("🌐 Fetching jobs from 3 portals + AI ranking… (30–60 sec)"):
            job_res = requests.post(
                f"{API_URL}/recommend-jobs",
                json={"resume_data": st.session_state.resume_data,
                      "adzuna_app_id": adzuna_id or "", "adzuna_app_key": adzuna_key or "",
                      "max_results": max_jobs},
                headers=auth_headers(), timeout=120,
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
            if (type_filter == "All" or type_filter.lower() in j.get("job_type", "").lower())
            and (source_filter == "All" or source_filter.split()[0] in j.get("source", ""))
            and j.get("match_score", 0) >= min_score
        ]
        st.markdown(f"**Showing {len(filtered)} of {len(jobs)} jobs** — sorted best → least match")
        st.markdown("---")

        for idx, job in enumerate(filtered):
            score     = job.get("match_score", 0)
            level     = job.get("match_level", "Partial Match")
            reason    = job.get("reason", "")
            is_intern = job.get("is_intern", False)
            type_badge = '<span class="intern-badge">🎓 Internship</span>' if is_intern else '<span class="job-badge">💼 Full-time</span>'
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
                do_analyze = st.button("🔬 Full Analysis", key=f"analyze_{idx}", use_container_width=True, type="primary")
            with b2:
                if job.get("url"):
                    st.link_button("🔗 View Job", job["url"], use_container_width=True)

            job_key = f"{job['title']}|{job['company']}"
            if do_analyze and job_key not in st.session_state.selected_job_analysis:
                with st.spinner(f"🤖 Analyzing {job['title']} at {job['company']}…"):
                    try:
                        r = requests.post(
                            f"{API_URL}/analyze-job",
                            json={"resume_data": resume_data, "job_title": job["title"],
                                  "job_description": job["description"], "company_name": job["company"]},
                            headers=auth_headers(), timeout=90,
                        )
                        result = r.json() if r.status_code == 200 else {"error": r.text}
                        st.session_state.selected_job_analysis[job_key] = result
                        if r.status_code == 200:
                            save_analysis_to_history(
                                company_name=job["company"],
                                job_description=job.get("description", "")[:500],
                                match_score=result.get("match", {}).get("match_percentage", score),
                                result_data=result, analysis_type="job_recommendation",
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
                                st.markdown(" ".join(f'<span class="chip-matched">{s}</span>' for s in m.get("matched_skills", [])) or "_None_", unsafe_allow_html=True)
                            with cg2:
                                st.markdown("**🔑 Keywords to Add**")
                                kws = analysis.get("ats", {}).get("keywords_to_add", [])
                                st.markdown(" ".join(f'<span class="chip-keyword">{k}</span>' for k in kws[:12]) or "_Already optimized_", unsafe_allow_html=True)
                            render_skill_bridge(analysis.get("skill_bridge", {}), m.get("match_percentage", score))
                        with atabs[1]:
                            a = analysis.get("ats", {})
                            st.subheader("Optimized Summary"); st.info(a.get("optimized_summary", ""))
                            for b in a.get("improved_bullets", []): st.write(b)
                            for t in a.get("formatting_tips", []): st.write(f"• {t}")
                        with atabs[2]:
                            rd = analysis.get("roadmap", {})
                            st.subheader(f"🎯 {rd.get('goal', '')}")
                            for w in rd.get("weeks", [])[:6]:
                                with st.expander(f"Week {w['week']}: {w['focus']}"):
                                    for t in w.get("tasks", []): st.write(f"• {t}")
                                    st.success(f"🏁 {w.get('milestone', '')}")
                        with atabs[3]:
                            iv = analysis.get("interview", {})
                            for q in iv.get("technical_questions", []):
                                with st.expander(f"[{q['difficulty']}] {q['question']}"): st.write("Topic:", q.get("topic", ""))
                            for q in iv.get("behavioral_questions", []): st.write(f"• {q}")
                            for t in iv.get("tips", []): st.write(f"💡 {t}")
                        with atabs[4]:
                            cl = analysis.get("cover_letter", {})
                            st.subheader(cl.get("subject_line", ""))
                            st.text_area("Cover Letter", cl.get("cover_letter", ""), height=280, key=f"cl_{idx}_{job_key[:20]}")
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
# MODE 3 — Reverse Pitch
# ══════════════════════════════════════════════════════════════════════════════
elif mode == "🚀 Reverse Pitch":
    st.title("🚀 Reverse Pitch — Let Recruiters Find You")
    st.caption("Showcase your project · Recruiters browse · Get discovered")

    rp_tab1, rp_tab2 = st.tabs(["🌍 Discovery Feed", "📤 Submit Your Project"])

    with rp_tab1:
        st.markdown("### 🔍 Browse Candidate Projects")
        try:
            feed_res = http_requests.get(f"{API_URL}/projects", timeout=15)
            if feed_res.status_code == 200:
                projects = feed_res.json().get("projects", [])
                if not projects:
                    st.info("🌱 No projects yet — be the first to submit yours in the **Submit Your Project** tab!")
                else:
                    st.markdown(f"**{len(projects)} projects** in the discovery feed")
                    st.markdown("---")
                    for proj in projects:
                        score_col, info_col = st.columns([1, 5])
                        with score_col:
                            st.markdown(f"""
<div style="background:linear-gradient(135deg,#667eea,#764ba2);border-radius:12px;
     padding:14px 8px;text-align:center;color:white;">
  <div style="font-size:22px;">👁️</div>
  <div style="font-size:18px;font-weight:800;">{proj.get('views', 0)}</div>
  <div style="font-size:10px;opacity:0.8;">views</div>
  <div style="font-size:18px;font-weight:800;margin-top:8px;">{proj.get('interest_count', 0)}</div>
  <div style="font-size:10px;opacity:0.8;">interested</div>
</div>
""", unsafe_allow_html=True)
                        with info_col:
                            tags_html  = " ".join(f'<span style="background:#ede9fe;color:#5b21b6;border-radius:6px;padding:2px 8px;font-size:11px;margin:2px;display:inline-block;">{t}</span>' for t in proj.get("ai_tags", []))
                            stack_html = " ".join(f'<span style="background:#f3f4f6;color:#374151;border-radius:6px;padding:2px 8px;font-size:11px;margin:2px;display:inline-block;">{s}</span>' for s in proj.get("tech_stack", [])[:8])
                            github_btn = f'<a href="{proj["github_url"]}" target="_blank" style="background:#1a1a2e;color:white;border-radius:6px;padding:4px 12px;font-size:12px;text-decoration:none;margin-right:6px;">⚡ GitHub</a>' if proj.get("github_url") else ""
                            demo_btn   = f'<a href="{proj["demo_url"]}" target="_blank" style="background:#0369a1;color:white;border-radius:6px;padding:4px 12px;font-size:12px;text-decoration:none;">🌐 Live Demo</a>' if proj.get("demo_url") else ""
                            st.markdown(f"""
<div style="background:#f8f9fa;border:1px solid #e5e7eb;border-left:4px solid #667eea;
     border-radius:10px;padding:16px 18px;margin-bottom:4px;">
  <div style="font-size:18px;font-weight:800;color:#1a1a2e;margin-bottom:4px;">📂 {proj['title']}</div>
  <div style="font-size:13px;color:#6b7280;margin-bottom:8px;">
    👤 <b>{proj['submitter_name']}</b> &nbsp;·&nbsp; 📅 {proj['created_at'][:10]}
  </div>
  <div style="font-size:14px;color:#374151;margin-bottom:10px;font-style:italic;">"{proj.get('ai_summary', proj['description'][:100])}"</div>
  <div style="margin-bottom:8px;">{tags_html}</div>
  <div style="margin-bottom:10px;">{stack_html}</div>
  <div>{github_btn}{demo_btn}</div>
</div>
""", unsafe_allow_html=True)
                        with st.expander(f"💼 I'm Interested — {proj['title']}", expanded=False):
                            i_name    = st.text_input("Your Name",    key=f"iname_{proj['id']}", placeholder="Jane Smith")
                            i_email   = st.text_input("Your Email",   key=f"iemail_{proj['id']}", placeholder="jane@company.com")
                            i_company = st.text_input("Company Name", key=f"icomp_{proj['id']}", placeholder="Google...")
                            i_msg     = st.text_area("Message (optional)", key=f"imsg_{proj['id']}", height=80)
                            if st.button("📩 Send Interest", key=f"ibtn_{proj['id']}", type="primary"):
                                if not i_name or not i_email or not i_company:
                                    st.error("Please fill in your name, email and company.")
                                else:
                                    try:
                                        ir = http_requests.post(
                                            f"{API_URL}/projects/{proj['id']}/interest",
                                            json={"recruiter_name": i_name, "recruiter_email": i_email,
                                                  "company_name": i_company, "message": i_msg},
                                            timeout=15,
                                        )
                                        if ir.status_code == 200:
                                            st.success(f"✅ Interest sent! {proj['submitter_name']} will be notified.")
                                        else:
                                            st.error(f"Error: {ir.text}")
                                    except Exception as e:
                                        st.error(f"Could not send: {e}")
                        st.markdown("---")
            else:
                st.error("Could not load projects feed.")
        except Exception as e:
            st.error(f"Error: {e}")

    with rp_tab2:
        st.markdown("### 📤 Showcase Your Project")
        default_name  = user.get("name",  "") if user else ""
        default_email = user.get("email", "") if user else ""

        with st.form("submit_project_form"):
            fc1, fc2 = st.columns(2)
            with fc1: sub_name  = st.text_input("Your Name*",  value=default_name)
            with fc2: sub_email = st.text_input("Your Email*", value=default_email)
            proj_title = st.text_input("Project Title*", placeholder="e.g. AI Resume Analyzer")
            proj_desc  = st.text_area("Project Description*", height=120)
            fp1, fp2 = st.columns(2)
            with fp1: github_url = st.text_input("GitHub URL*", placeholder="https://github.com/you/project")
            with fp2: demo_url   = st.text_input("Live Demo URL (optional)", placeholder="https://yourproject.com")
            tech_input = st.text_input("Tech Stack*", placeholder="Python, React, FastAPI...")
            submitted  = st.form_submit_button("🚀 Submit to Discovery Feed", type="primary", use_container_width=True)

        if submitted:
            if not sub_name or not sub_email or not proj_title or not proj_desc or not tech_input or not github_url:
                st.error("Please fill in all required fields including GitHub URL.")
            else:
                with st.spinner("🤖 AI analyzing your project…"):
                    try:
                        sr = http_requests.post(
                            f"{API_URL}/projects/submit",
                            json={"submitter_name": sub_name, "submitter_email": sub_email,
                                  "title": proj_title, "description": proj_desc,
                                  "github_url": github_url or "", "demo_url": demo_url or "",
                                  "tech_stack": [t.strip() for t in tech_input.split(",") if t.strip()]},
                            headers=auth_headers(), timeout=60,
                        )
                        if sr.status_code == 200:
                            result = sr.json()
                            st.success("🎉 Your project is now LIVE!")
                            st.markdown(f"""
<div style="background:linear-gradient(135deg,#667eea,#764ba2);border-radius:12px;padding:20px;color:white;">
  <div style="font-size:20px;font-weight:800;">✅ {proj_title}</div>
  <div style="font-size:14px;opacity:0.9;">"{result.get('ai_summary','')}"</div>
  <div style="font-size:13px;margin-top:8px;">🎯 Tags: {", ".join(result.get('ai_tags', []))}</div>
</div>
""", unsafe_allow_html=True)
                        else:
                            st.error(f"Submission failed: {sr.text}")
                    except Exception as e:
                        st.error(f"Could not submit: {e}")

    if user and st.session_state.token:
        try:
            nr = http_requests.get(f"{API_URL}/notifications", headers=auth_headers(), timeout=10)
            if nr.status_code == 200:
                unread = [n for n in nr.json().get("notifications", []) if not n.get("is_read")]
                if unread:
                    st.markdown("---")
                    st.markdown(f"### 🔔 Notifications ({len(unread)} new)")
                    for n in unread:
                        st.success(f"**{n['title']}**  \n{n['message']}")
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# MODE 4 — History
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