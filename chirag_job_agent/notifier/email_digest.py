"""
notifier/email_digest.py — Send daily job digest via Gmail SMTP (FREE)
Uses Python's built-in smtplib — no email API needed.
"""
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_TO, CANDIDATE


def _score_badge_html(score: int) -> str:
    score = int(score or 0)
    if score >= 9:
        return f'<span style="background:#D1FAE5;color:#065F46;padding:4px 12px;border-radius:20px;font-weight:700;font-size:13px;">🔥 {score}/10 Excellent</span>'
    elif score >= 7:
        return f'<span style="background:#DBEAFE;color:#1E40AF;padding:4px 12px;border-radius:20px;font-weight:700;font-size:13px;">⭐ {score}/10 Strong</span>'
    else:
        return f'<span style="background:#FEF3C7;color:#92400E;padding:4px 12px;border-radius:20px;font-weight:700;font-size:13px;">✅ {score}/10 Good</span>'


def _platform_color(platform: str) -> str:
    colors = {"LinkedIn": "#0A66C2", "Indeed": "#2164F4", "Naukri": "#FF6F61"}
    return colors.get(platform, "#6B7280")


def _build_job_card(job: dict) -> str:
    title    = job.get("title", "")
    company  = job.get("company", "")
    location = job.get("location", "")
    platform = job.get("platform", "")
    url      = job.get("url", "#")
    score    = int(job.get("fit_score", 0))
    summary  = job.get("ai_summary", "")
    matching = job.get("matching_skills", "")
    missing  = job.get("missing_skills", "")
    category = job.get("role_category", "")
    key_req  = job.get("key_requirement", "")

    match_pills = ""
    if matching:
        for skill in matching.split(", ")[:4]:
            match_pills += f'<span style="background:#EFF6FF;color:#1D4ED8;padding:3px 10px;border-radius:20px;font-size:12px;margin:2px;display:inline-block;">✅ {skill}</span>'

    missing_pills = ""
    if missing:
        for skill in missing.split(", ")[:3]:
            missing_pills += f'<span style="background:#FFFBEB;color:#B45309;padding:3px 10px;border-radius:20px;font-size:12px;margin:2px;display:inline-block;">⚠️ {skill}</span>'

    key_req_html = f'<p style="margin:6px 0;font-size:12px;color:#9CA3AF;font-style:italic;">📌 {key_req}</p>' if key_req else ""

    plat_color = _platform_color(platform)

    return f"""
    <div style="border:1px solid #E5E7EB;border-radius:12px;padding:18px 20px;margin:14px 0;background:#FFFFFF;">
      <table width="100%" cellpadding="0" cellspacing="0"><tr>
        <td style="vertical-align:top;">
          <h3 style="margin:0 0 4px;font-size:17px;color:#111827;font-weight:700;">{title}</h3>
          <p style="margin:0;font-size:13px;color:#6B7280;">
            {company}
            &nbsp;·&nbsp; {location}
            &nbsp;·&nbsp; <span style="color:{plat_color};font-weight:600;">{platform}</span>
            &nbsp;·&nbsp; <span style="color:#6B7280;">{category}</span>
          </p>
        </td>
        <td style="vertical-align:top;text-align:right;white-space:nowrap;">
          {_score_badge_html(score)}
        </td>
      </tr></table>
      <p style="margin:10px 0 6px;font-size:14px;color:#374151;line-height:1.6;">{summary}</p>
      {key_req_html}
      <div style="margin:8px 0;">{match_pills}{missing_pills}</div>
      <a href="{url}" style="display:inline-block;margin-top:10px;background:#1E40AF;color:#ffffff;
         padding:8px 20px;border-radius:6px;text-decoration:none;font-size:14px;font-weight:600;">
        View &amp; Apply →
      </a>
    </div>"""


def build_html_digest(jobs: list[dict]) -> str:
    today = datetime.now().strftime("%A, %d %B %Y")
    count = len(jobs)

    job_cards_html = ""
    for job in jobs:
        job_cards_html += _build_job_card(job)

    if not job_cards_html:
        job_cards_html = '<p style="color:#6B7280;text-align:center;padding:20px;">No new jobs found today.</p>'

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;
             background:#F3F4F6;margin:0;padding:0;">
<div style="max-width:680px;margin:24px auto;font-size:15px;">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#1E3A8A 0%,#2563EB 100%);
              color:#fff;padding:28px 32px;border-radius:16px 16px 0 0;">
    <h1 style="margin:0 0 6px;font-size:22px;font-weight:700;">🤖 Your Daily Job Digest</h1>
    <p style="margin:0;font-size:14px;opacity:0.85;">
      {today} &nbsp;·&nbsp; <strong>{count} new match{"es" if count!=1 else ""}</strong> found today
    </p>
    <p style="margin:8px 0 0;font-size:13px;opacity:0.7;">
      Only roles scored 6+/10 shown · Sorted by fit score
    </p>
  </div>

  <!-- Body -->
  <div style="background:#fff;padding:24px 28px;
              border-radius:0 0 16px 16px;border:1px solid #E5E7EB;border-top:none;">
    {job_cards_html}
    <hr style="margin:24px 0;border:none;border-top:1px solid #E5E7EB;">
    <p style="text-align:center;color:#9CA3AF;font-size:12px;margin:0;">
      Generated by your AI Job Agent · Running daily at 8:30 AM<br>
      Built for {CANDIDATE["name"]} · Zero cost · Open source
    </p>
  </div>
</div>
</body>
</html>"""


def build_no_jobs_html() -> str:
    today = datetime.now().strftime("%A, %d %B %Y")
    return f"""<!DOCTYPE html>
<html><body style="font-family:Arial;padding:24px;max-width:500px;margin:auto;">
  <div style="background:#1E3A8A;color:#fff;padding:20px;border-radius:10px;text-align:center;">
    <h2>🤖 AI Job Agent</h2>
    <p>{today}</p>
  </div>
  <div style="padding:20px;border:1px solid #E5E7EB;border-top:none;border-radius:0 0 10px 10px;">
    <h3>No new matching jobs today</h3>
    <p style="color:#6B7280;">The agent ran successfully but didn't find any roles scoring 6+/10.
    It will run again tomorrow at 8:30 AM.</p>
  </div>
</body></html>"""


def send_digest(jobs: list[dict]) -> bool:
    """
    Send the daily digest email via Gmail SMTP.
    Returns True on success.

    To use Gmail SMTP:
    1. Enable 2FA on your Google account
    2. Go to myaccount.google.com → Security → App Passwords
    3. Create an app password for "Mail"
    4. Paste that 16-char password as EMAIL_PASSWORD in config.py
    """
    if EMAIL_PASSWORD == "YOUR_GMAIL_APP_PASSWORD":
        print("[Email] ⚠️  Gmail App Password not set in config.py — printing digest to console instead.")
        _print_console_digest(jobs)
        return False

    today     = datetime.now().strftime("%A, %d %B %Y")
    count     = len(jobs)
    subject   = f"🤖 {count} Job Match{'es' if count!=1 else ''} For You — {today}" if jobs else f"🤖 No New Jobs Today — {today}"
    html_body = build_html_digest(jobs) if jobs else build_no_jobs_html()

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = EMAIL_SENDER
    msg["To"]      = EMAIL_TO
    msg.attach(MIMEText(html_body, "html"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_TO, msg.as_string())
        print(f"[Email] ✅ Digest sent to {EMAIL_TO} — {count} jobs")
        return True
    except smtplib.SMTPAuthenticationError:
        print("[Email] ❌ Gmail auth failed. Check your App Password in config.py")
        print("[Email]    Guide: myaccount.google.com → Security → App Passwords")
        return False
    except Exception as e:
        print(f"[Email] ❌ Error: {e}")
        return False


def _print_console_digest(jobs: list[dict]):
    """Fallback: pretty print to terminal when email is not configured."""
    print("\n" + "═"*60)
    print(f"  📋 DAILY JOB DIGEST — {datetime.now().strftime('%d %b %Y')}")
    print(f"  {len(jobs)} job{'s' if len(jobs)!=1 else ''} found")
    print("═"*60)
    for j in jobs:
        score = j.get("fit_score", 0)
        emoji = "🔥" if score >= 9 else "⭐" if score >= 7 else "✅"
        print(f"\n{emoji} {j['title']} @ {j['company']}")
        print(f"   📍 {j['location']} · {j['platform']} · Score: {score}/10")
        print(f"   💬 {j.get('ai_summary','')}")
        print(f"   ✅ Matches: {j.get('matching_skills','N/A')}")
        if j.get("missing_skills"):
            print(f"   ⚠️  Missing: {j.get('missing_skills','')}")
        print(f"   🔗 {j.get('url','')}")
    print("\n" + "═"*60)


if __name__ == "__main__":
    # Test with mock data
    test_jobs = [
        {
            "title": "Business Analyst", "company": "Deloitte India",
            "location": "Gurugram", "platform": "LinkedIn", "url": "https://linkedin.com/jobs/test",
            "fit_score": 9, "role_category": "Business Analyst", "role_match": "High",
            "matching_skills": "BRD Writing, Agile, Stakeholder Management",
            "missing_skills": "MBA",
            "ai_summary": "Strong match — BRD and stakeholder management align perfectly.",
            "key_requirement": "2+ years in business consulting"
        }
    ]
    _print_console_digest(test_jobs)
    html = build_html_digest(test_jobs)
    with open("/tmp/digest_preview.html", "w") as f:
        f.write(html)
    print("\n[Test] Preview saved to /tmp/digest_preview.html")
