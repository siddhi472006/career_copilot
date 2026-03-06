"""
Email Service
Sends real emails via SendGrid free tier (100 emails/day free)
Falls back to console log if no API key set.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
FROM_EMAIL       = os.getenv("FROM_EMAIL", "noreply@aicareercopilot.com")
FROM_NAME        = "AI Career Copilot"


def send_email(to_email: str, to_name: str, subject: str, html_body: str) -> bool:
    if not SENDGRID_API_KEY:
        print(f"[EMAIL - no key] To: {to_email} | Subject: {subject}")
        return False
    try:
        response = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={
                "Authorization": f"Bearer {SENDGRID_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "personalizations": [{"to": [{"email": to_email, "name": to_name}]}],
                "from": {"email": FROM_EMAIL, "name": FROM_NAME},
                "subject": subject,
                "content": [{"type": "text/html", "value": html_body}],
            },
            timeout=10,
        )
        return response.status_code == 202
    except Exception as e:
        print(f"Email error: {e}")
        return False


def send_interest_notification(
    candidate_name: str, candidate_email: str, project_title: str,
    recruiter_name: str, recruiter_email: str, company_name: str, message: str = ""
) -> bool:
    subject = f"🎉 {recruiter_name} from {company_name} is interested in your project!"
    html_body = f"""
<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;color:#333;">
  <div style="background:linear-gradient(135deg,#667eea,#764ba2);padding:30px;border-radius:12px 12px 0 0;text-align:center;">
    <h1 style="color:white;margin:0;">🎉 Someone is Interested!</h1>
    <p style="color:rgba(255,255,255,0.9);margin:8px 0 0;">Your project caught a recruiter's eye</p>
  </div>
  <div style="background:#f8f9fa;padding:30px;border-radius:0 0 12px 12px;border:1px solid #e5e7eb;">
    <p>Hi <b>{candidate_name}</b>,</p>
    <p><b>{recruiter_name}</b> from <b>{company_name}</b> is interested in your project <b>{project_title}</b>.</p>
    {"<div style='background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:16px;margin:16px 0;'><b>💬 Message:</b><br><i>" + message + "</i></div>" if message else ""}
    <div style="background:white;border:1px solid #e5e7eb;border-radius:8px;padding:16px;margin:16px 0;">
      👤 {recruiter_name} &nbsp;·&nbsp; 🏢 {company_name} &nbsp;·&nbsp;
      📧 <a href="mailto:{recruiter_email}">{recruiter_email}</a>
    </div>
    <div style="text-align:center;margin-top:24px;">
      <a href="mailto:{recruiter_email}?subject=Re: Interest in {project_title}"
         style="background:linear-gradient(135deg,#667eea,#764ba2);color:white;padding:12px 28px;
                border-radius:8px;text-decoration:none;font-weight:700;">
        📧 Reply to {recruiter_name}
      </a>
    </div>
  </div>
</body></html>"""
    return send_email(candidate_email, candidate_name, subject, html_body)


def send_interest_confirmation(
    recruiter_name: str, recruiter_email: str,
    project_title: str, candidate_name: str, candidate_email: str
) -> bool:
    subject = f"✅ Your interest in '{project_title}' has been sent"
    html_body = f"""
<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
  <div style="background:linear-gradient(135deg,#667eea,#764ba2);padding:30px;border-radius:12px 12px 0 0;text-align:center;">
    <h1 style="color:white;margin:0;">✅ Interest Sent!</h1>
  </div>
  <div style="background:#f8f9fa;padding:30px;border-radius:0 0 12px 12px;border:1px solid #e5e7eb;">
    <p>Hi <b>{recruiter_name}</b>,</p>
    <p>Your interest in <b>{project_title}</b> by <b>{candidate_name}</b> has been sent successfully.</p>
    <p>If they're interested, they'll reply to you at <b>{recruiter_email}</b> directly.</p>
  </div>
</body></html>"""
    return send_email(recruiter_email, recruiter_name, subject, html_body)