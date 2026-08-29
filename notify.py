"""
Notification channels: ntfy phone push (one per role) + email digest.
Standard library only. All config comes from environment variables.

  NTFY_TOPIC        ntfy.sh topic to publish to (e.g. "dmehta-hr-9f3k2")
  NTFY_SERVER       optional, defaults to https://ntfy.sh

  SMTP_HOST         e.g. smtp.gmail.com
  SMTP_PORT         e.g. 587
  SMTP_USER         sending address (your personal Gmail)
  SMTP_PASS         Gmail App Password (NOT your normal password)
  EMAIL_TO          where the digest lands (can equal SMTP_USER)

Any channel with missing config is simply skipped.
"""

import os
import smtplib
import urllib.request
from email.message import EmailMessage


def _header_safe(s: str) -> str:
    """HTTP headers must be latin-1. Normalize common unicode punctuation to
    ASCII, then replace anything still unencodable so a push never crashes."""
    for bad, good in (
        ("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'),
        ("–", "-"), ("—", "-"), ("…", "..."), (" ", " "),
    ):
        s = s.replace(bad, good)
    return s.encode("latin-1", "replace").decode("latin-1")


def _age_str(posted_ts, now_ts):
    if not posted_ts:
        return "just now"
    mins = max(0, int((now_ts - posted_ts) / 60))
    if mins < 60:
        return f"{mins} min ago"
    return f"{mins // 60}h {mins % 60}m ago"


def send_push(job, now_ts):
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        return False
    server = os.environ.get("NTFY_SERVER", "https://ntfy.sh").rstrip("/")
    age = job.get("posted_label") or _age_str(job["posted_ts"], now_ts)
    body = f"{job['company']} · {job['location'] or 'location n/a'} · {age}"
    req = urllib.request.Request(
        f"{server}/{topic}",
        data=body.encode("utf-8"),
        headers={
            "Title": _header_safe(job["title"])[:120],
            "Click": job["url"],          # tap the notification -> opens the posting
            "Tags": "briefcase",
            "Priority": "high",
            "User-Agent": "hr-job-radar/1.0",
        },
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=15)
        return True
    except Exception as e:
        print(f"  ! push failed: {type(e).__name__}: {e}")
        return False


def send_email_digest(jobs, now_ts):
    host = os.environ.get("SMTP_HOST")
    user = os.environ.get("SMTP_USER")
    pw = os.environ.get("SMTP_PASS")
    to = os.environ.get("EMAIL_TO") or user
    if not (host and user and pw and to):
        return False
    port = int(os.environ.get("SMTP_PORT", "587"))

    lines_txt = []
    lines_html = ['<h2>New People/HR roles</h2><ul>']
    for j in jobs:
        age = j.get("posted_label") or _age_str(j["posted_ts"], now_ts)
        lines_txt.append(f"• {j['title']} — {j['company']} ({j['location']}) · {age}\n  {j['url']}")
        lines_html.append(
            f'<li><a href="{j["url"]}"><b>{j["title"]}</b></a> — '
            f'{j["company"]} <i>({j["location"]})</i> · {age}</li>'
        )
    lines_html.append("</ul>")

    msg = EmailMessage()
    n = len(jobs)
    msg["Subject"] = f"[HR Job Radar] {n} new role{'s' if n != 1 else ''}"
    msg["From"] = user
    msg["To"] = to
    msg.set_content("\n\n".join(lines_txt))
    msg.add_alternative("\n".join(lines_html), subtype="html")

    try:
        with smtplib.SMTP(host, port, timeout=30) as s:
            s.starttls()
            s.login(user, pw)
            s.send_message(msg)
        return True
    except Exception as e:
        print(f"  ! email failed: {type(e).__name__}: {e}")
        return False
