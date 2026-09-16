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


def age_minutes(job, now_ts):
    """Minutes since posting, or None when the board gives no real timestamp
    (Workday only reports day-level dates)."""
    ts = job.get("posted_ts")
    if not ts:
        return None
    return max(0, (now_ts - ts) / 60.0)


# How loud a push is, by how fresh the role is. The goal is to apply inside the
# first hour, so urgency is graded rather than used to suppress: a stale role
# still arrives, just quietly, instead of vanishing silently.
#
#   < 15 min   urgent  -> pierces Do Not Disturb; drop everything and apply
#   15-60 min  high    -> still inside the golden hour, normal loud push
#   > 60 min   low     -> no sound; "you missed the window, apply anyway"
#   unknown    default -> Workday-style day-level date, can't grade it
def push_tier(job, now_ts):
    """-> (tier, ntfy_priority, ntfy_tag)"""
    mins = age_minutes(job, now_ts)
    if mins is None:
        return ("unknown", "default", "briefcase")
    if mins < 15:
        return ("hot", "urgent", "rotating_light")
    if mins < 60:
        return ("fresh", "high", "briefcase")
    return ("stale", "low", "hourglass")


def send_push(job, now_ts):
    # Note: GitHub Actions passes *undefined* secrets as "" (not unset), so use
    # `or` fallbacks rather than dict defaults. Wrap everything so a bad config
    # can never crash the poller (which would otherwise loop on the same role).
    try:
        topic = (os.environ.get("NTFY_TOPIC") or "").strip()
        if not topic:
            return False
        server = (os.environ.get("NTFY_SERVER") or "https://ntfy.sh").strip().rstrip("/")
        if not server.startswith("http"):
            server = "https://ntfy.sh"
        age = job.get("posted_label") or _age_str(job["posted_ts"], now_ts)
        tier, priority, tag = push_tier(job, now_ts)
        body = f"{job['company']} · {job['location'] or 'location n/a'} · {age}"
        req = urllib.request.Request(
            f"{server}/{topic}",
            data=body.encode("utf-8"),
            headers={
                "Title": _header_safe(job["title"])[:120],
                "Click": job["url"],      # tap the notification -> opens the posting
                "Tags": tag,
                "Priority": priority,
                "User-Agent": "hr-job-radar/1.0",
            },
            method="POST",
        )
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

    _MARK = {
        "hot":     ("[APPLY NOW]", "#b00020"),
        "fresh":   ("[golden hour]", "#a06000"),
        "stale":   ("[older]", "#666666"),
        "unknown": ("[posted today]", "#666666"),
    }

    lines_txt = []
    lines_html = ['<h2>New People/HR roles</h2><ul>']
    for j in jobs:
        age = j.get("posted_label") or _age_str(j["posted_ts"], now_ts)
        tier, _, _ = push_tier(j, now_ts)
        mark, color = _MARK[tier]
        lines_txt.append(
            f"• {mark} {j['title']} — {j['company']} ({j['location']}) · {age}\n  {j['url']}")
        lines_html.append(
            f'<li><span style="color:{color};font-weight:bold">{mark}</span> '
            f'<a href="{j["url"]}"><b>{j["title"]}</b></a> — '
            f'{j["company"]} <i>({j["location"]})</i> · {age}</li>'
        )
    lines_html.append("</ul>")

    msg = EmailMessage()
    n = len(jobs)
    hot = sum(1 for j in jobs if push_tier(j, now_ts)[0] in ("hot", "fresh"))
    urgency = f" — {hot} inside the golden hour" if hot else ""
    msg["Subject"] = f"[HR Job Radar] {n} new role{'s' if n != 1 else ''}{urgency}"
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
