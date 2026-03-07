"""
OTP Service — AI Career Copilot
Handles work-email OTP generation, hashing, sending and verification.
Uses SendGrid (already configured) to send OTP emails.
"""

import os
import random
import string
from datetime import datetime, timedelta
from passlib.context import CryptContext
from utils.email_service import send_email

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

OTP_EXPIRY_MINUTES = 10


# ── Known Indian tech company domains → display names ────────────────────────
KNOWN_COMPANIES = {
    # Indian unicorns & startups
    "razorpay.com":      "Razorpay",
    "zepto.com":         "Zepto",
    "swiggy.com":        "Swiggy",
    "zomato.com":        "Zomato",
    "meesho.com":        "Meesho",
    "cred.club":         "CRED",
    "phonepe.com":       "PhonePe",
    "paytm.com":         "Paytm",
    "freshworks.com":    "Freshworks",
    "zoho.com":          "Zoho",
    "ola.com":           "Ola",
    "olaelectric.com":   "Ola Electric",
    "myntra.com":        "Myntra",
    "nykaa.com":         "Nykaa",
    "sharechat.com":     "ShareChat",
    "dream11.com":       "Dream11",
    "udaan.com":         "Udaan",
    "lenskart.com":      "Lenskart",
    "groww.com":         "Groww",
    "zerodha.com":       "Zerodha",
    "upstox.com":        "Upstox",
    "slice.is":          "Slice",
    "postman.com":       "Postman",
    "browserstack.com":  "BrowserStack",
    "chargebee.com":     "Chargebee",
    "hasura.io":         "Hasura",
    "setu.co":           "Setu",
    "niyo.co":           "Niyo",
    "jupiter.money":     "Jupiter",
    "fi.money":          "Fi Money",
    "simpl.is":          "Simpl",
    "recko.com":         "Recko",
    "juspay.in":         "Juspay",
    "cashfree.com":      "Cashfree",
    "instamojo.com":     "Instamojo",
    "shiprocket.in":     "Shiprocket",
    "delhivery.com":     "Delhivery",
    "dunzo.com":         "Dunzo",
    "blinkit.com":       "Blinkit",
    "bigbasket.com":     "BigBasket",
    "1mg.com":           "1mg",
    "practo.com":        "Practo",
    "healthifyme.com":   "HealthifyMe",
    "cult.fit":          "Cult.fit",
    "unacademy.com":     "Unacademy",
    "byjus.com":         "BYJU'S",
    "vedantu.com":       "Vedantu",
    "toppr.com":         "Toppr",
    "classplus.co":      "Classplus",
    "scaler.com":        "Scaler",
    "interviewbit.com":  "InterviewBit",
    "hackerrank.com":    "HackerRank",
    "hackerearth.com":   "HackerEarth",
    "unstop.com":        "Unstop",
    "internshala.com":   "Internshala",
    "naukri.com":        "Naukri",
    "linkedin.com":      "LinkedIn",
    # Global MNCs with India presence
    "google.com":        "Google",
    "microsoft.com":     "Microsoft",
    "amazon.com":        "Amazon",
    "apple.com":         "Apple",
    "meta.com":          "Meta",
    "netflix.com":       "Netflix",
    "uber.com":          "Uber",
    "adobe.com":         "Adobe",
    "salesforce.com":    "Salesforce",
    "oracle.com":        "Oracle",
    "sap.com":           "SAP",
    "ibm.com":           "IBM",
    "accenture.com":     "Accenture",
    "wipro.com":         "Wipro",
    "infosys.com":       "Infosys",
    "tcs.com":           "TCS",
    "hcltech.com":       "HCL Technologies",
    "techmahindra.com":  "Tech Mahindra",
    "cognizant.com":     "Cognizant",
    "capgemini.com":     "Capgemini",
}

# Domains that are NOT work emails
PERSONAL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "rediffmail.com", "icloud.com", "protonmail.com",
    "ymail.com", "live.com", "msn.com",
}


def extract_domain(email: str) -> str:
    return email.strip().lower().split("@")[-1]


def is_work_email(email: str) -> bool:
    domain = extract_domain(email)
    return domain not in PERSONAL_DOMAINS


def detect_company(email: str) -> str:
    """
    Returns company name from email domain.
    Known domains → exact name.
    Unknown domains → title-case the domain (e.g. mycompany.com → Mycompany).
    """
    domain = extract_domain(email)
    if domain in KNOWN_COMPANIES:
        return KNOWN_COMPANIES[domain]
    # Fallback: strip TLD and title-case
    name_part = domain.split(".")[0]
    return name_part.replace("-", " ").replace("_", " ").title()


def generate_otp() -> str:
    """Returns a 6-digit numeric OTP."""
    return "".join(random.choices(string.digits, k=6))


def hash_otp(otp: str) -> str:
    return pwd_context.hash(otp)


def verify_otp_hash(plain_otp: str, hashed_otp: str) -> bool:
    try:
        return pwd_context.verify(plain_otp, hashed_otp)
    except Exception:
        return False


def otp_expiry() -> datetime:
    return datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)


def send_otp_email(to_email: str, to_name: str, otp: str, company: str) -> bool:
    subject = f"🔐 Your AI Career Copilot verification code: {otp}"
    html = f"""
<!DOCTYPE html>
<html>
<body style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto;padding:20px;color:#333;">
  <div style="background:linear-gradient(135deg,#667eea,#764ba2);
       padding:28px 32px;border-radius:12px 12px 0 0;text-align:center;">
    <h2 style="color:white;margin:0;">🔐 Recruiter Verification</h2>
    <p style="color:rgba(255,255,255,0.85);margin:8px 0 0;font-size:14px;">
      AI Career Copilot · Talent Discovery Portal
    </p>
  </div>

  <div style="background:#f8f9fa;padding:32px;border-radius:0 0 12px 12px;
       border:1px solid #e5e7eb;border-top:none;">
    <p style="margin:0 0 8px;">Hi <b>{to_name or "there"}</b>,</p>
    <p style="color:#374151;">
      You're registering as a recruiter from <b>{company}</b>.
      Use the code below to verify your work email:
    </p>

    <div style="background:white;border:2px dashed #667eea;border-radius:12px;
         padding:24px;text-align:center;margin:24px 0;">
      <div style="font-size:42px;font-weight:900;letter-spacing:10px;color:#4f46e5;">
        {otp}
      </div>
      <div style="font-size:13px;color:#9ca3af;margin-top:8px;">
        Valid for <b>{OTP_EXPIRY_MINUTES} minutes</b>
      </div>
    </div>

    <p style="font-size:13px;color:#6b7280;margin:0;">
      If you didn't request this, you can safely ignore this email.<br>
      Never share this code with anyone.
    </p>
  </div>
</body>
</html>"""
    return send_email(to_email, to_name or "", subject, html)