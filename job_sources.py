"""
Fetch + filter People/HR roles from public Greenhouse, Lever, and Ashby boards.

Pure standard-library (urllib) so it runs anywhere with zero pip installs —
including free GitHub Actions runners. Returns normalized job dicts:

    {
        "id":        "greenhouse:stripe:1234567",   # stable, unique
        "source":    "greenhouse",
        "company":   "Stripe",
        "title":     "People Operations Manager",
        "location":  "San Francisco, CA",
        "url":       "https://...",
        "posted_ts": 1724800000,                     # epoch seconds or None
    }
"""

import concurrent.futures as cf
import json
import re
import urllib.request
from datetime import datetime, timezone

from companies import BOARDS

# --------------------------------------------------------------------------
# What counts as a People / HR role (matched against the job TITLE)
# --------------------------------------------------------------------------
HR_TITLE_PATTERNS = [
    "human resources", "people operations", "people ops", "people partner",
    "people & culture", "people and culture", "people generalist",
    "people coordinator", "people analytics", "people scientist",
    "head of people", "chief people", "vp people", "vp of people",
    "director of people", "people business partner", "people team",
    "hr business partner", "hrbp", "hr generalist", "hr manager",
    "hr director", "hr coordinator", "hr partner", "hr specialist",
    "hr operations", "hris",
    "talent acquisition", "talent partner", "talent management",
    "talent development", "recruiter", "recruiting", "sourcer", "talent sourc",
    "total rewards", "compensation", "benefits",
    "employee relations", "employee experience", "employee engagement",
    "learning and development", "learning & development", "l&d",
    "organizational development", "org development",
    "diversity", "inclusion", "dei", "deib",
    "workforce", "workplace experience", "onboarding specialist",
]

# --------------------------------------------------------------------------
# Location matching
# --------------------------------------------------------------------------
US_STATE_ABBR = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID",
    "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS",
    "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK",
    "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV",
    "WI", "WY", "DC",
}
US_STATE_NAMES = [
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana",
    "maine", "maryland", "massachusetts", "michigan", "minnesota",
    "mississippi", "missouri", "montana", "nebraska", "nevada",
    "new hampshire", "new jersey", "new mexico", "new york",
    "north carolina", "north dakota", "ohio", "oklahoma", "oregon",
    "pennsylvania", "rhode island", "south carolina", "south dakota",
    "tennessee", "texas", "utah", "vermont", "virginia", "washington",
    "west virginia", "wisconsin", "wyoming",
]
NON_US_HINTS = [
    "emea", "apac", "latam", "united kingdom", "uk", "london", "europe",
    "canada", "toronto", "vancouver", "india", "bangalore", "bengaluru",
    "germany", "berlin", "munich", "ireland", "dublin", "france", "paris",
    "amsterdam", "netherlands", "spain", "madrid", "barcelona", "australia",
    "sydney", "singapore", "japan", "tokyo", "brazil", "mexico", "poland",
    "portugal", "lisbon", "israel", "tel aviv", "philippines", "manila",
]
BAY_AREA_TERMS = [
    "san francisco", "sf bay", "bay area", "oakland", "berkeley", "emeryville",
    "san jose", "palo alto", "mountain view", "menlo park", "sunnyvale",
    "santa clara", "redwood city", "south san francisco", "cupertino",
    "san mateo", "foster city", "burlingame", "fremont", "marin",
    "silicon valley",
]

_ABBR_RE = re.compile(r",\s*([A-Z]{2})(?:\b|,|$)")


def _looks_us(loc: str) -> bool:
    low = loc.lower()
    if "united states" in low or "usa" in low or "u.s." in low or " us " in f" {low} ":
        return True
    for m in _ABBR_RE.finditer(loc):
        if m.group(1) in US_STATE_ABBR:
            return True
    return any(name in low for name in US_STATE_NAMES)


def _is_remote(loc: str) -> bool:
    return "remote" in loc.lower()


def _has_non_us_hint(loc: str) -> bool:
    low = loc.lower()
    return any(h in low for h in NON_US_HINTS)


def location_matches(loc: str, mode: str, include_remote: bool) -> bool:
    """mode is 'usa' or 'bay_area'."""
    if not loc:
        loc = ""
    low = loc.lower()
    if mode == "bay_area":
        if any(term in low for term in BAY_AREA_TERMS):
            return True
        if include_remote and _is_remote(loc) and not _has_non_us_hint(loc):
            return True
        return False
    # usa (nationwide)
    if _looks_us(loc):
        return True
    if _is_remote(loc):
        return include_remote and not _has_non_us_hint(loc)
    return False


def is_hr_title(title: str) -> bool:
    t = (title or "").lower()
    return any(p in t for p in HR_TITLE_PATTERNS)


# --------------------------------------------------------------------------
# HTTP helper
# --------------------------------------------------------------------------
def _get_json(url: str, timeout: int = 15):
    req = urllib.request.Request(url, headers={"User-Agent": "hr-job-radar/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def _parse_iso(s):
    if not s:
        return None
    try:
        s = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except Exception:
        return None


# --------------------------------------------------------------------------
# Per-ATS fetchers -> list of normalized jobs
# --------------------------------------------------------------------------
def _title(company_token: str) -> str:
    return company_token.replace("-", " ").title()


def fetch_greenhouse(token):
    url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
    out = []
    for j in _get_json(url).get("jobs", []):
        out.append({
            "id": f"greenhouse:{token}:{j.get('id')}",
            "source": "greenhouse",
            "company": _title(token),
            "title": j.get("title", ""),
            "location": (j.get("location") or {}).get("name", ""),
            "url": j.get("absolute_url", ""),
            # first_published = true posting time; fall back to updated_at
            "posted_ts": _parse_iso(j.get("first_published") or j.get("updated_at")),
        })
    return out


def fetch_lever(token):
    url = f"https://api.lever.co/v0/postings/{token}?mode=json"
    out = []
    for j in _get_json(url):
        cats = j.get("categories") or {}
        created = j.get("createdAt")
        ts = int(created / 1000) if isinstance(created, (int, float)) else None
        out.append({
            "id": f"lever:{token}:{j.get('id')}",
            "source": "lever",
            "company": _title(token),
            "title": j.get("text", ""),
            "location": cats.get("location", ""),
            "url": j.get("hostedUrl", ""),
            "posted_ts": ts,
        })
    return out


def fetch_ashby(token):
    url = f"https://api.ashbyhq.com/posting-api/job-board/{token}"
    out = []
    for j in _get_json(url).get("jobs", []):
        out.append({
            "id": f"ashby:{token}:{j.get('id')}",
            "source": "ashby",
            "company": _title(token),
            "title": j.get("title", ""),
            "location": j.get("location", ""),
            "url": j.get("jobUrl") or j.get("applyUrl", ""),
            "posted_ts": _parse_iso(j.get("publishedAt")),
        })
    return out


_FETCHERS = {
    "greenhouse": fetch_greenhouse,
    "lever": fetch_lever,
    "ashby": fetch_ashby,
}


# --------------------------------------------------------------------------
# Top-level: fetch everything, then filter
# --------------------------------------------------------------------------
def fetch_all_jobs(max_workers: int = 16):
    """Fetch every posting from every configured board. Returns (jobs, errors)."""
    tasks = []
    for source, tokens in BOARDS.items():
        for token in tokens:
            tasks.append((source, token))

    jobs, errors = [], []

    def run(task):
        source, token = task
        try:
            return (_FETCHERS[source](token), None)
        except Exception as e:  # skip a board that 404s / hiccups; keep going
            return ([], f"{source}:{token} -> {type(e).__name__}")

    with cf.ThreadPoolExecutor(max_workers=max_workers) as ex:
        for got, err in ex.map(run, tasks):
            jobs.extend(got)
            if err:
                errors.append(err)
    return jobs, errors


def filter_jobs(jobs, mode="usa", include_remote=True, max_age_hours=None, now_ts=None):
    """Keep People/HR roles in the target location.

    If max_age_hours is set, only postings whose true posting time is within
    that window are kept. Postings with no reliable timestamp are DROPPED when
    a freshness window is requested (we can't prove they're fresh enough).
    """
    import time
    now_ts = now_ts or int(time.time())
    out = []
    for j in jobs:
        if not is_hr_title(j["title"]):
            continue
        if not location_matches(j["location"], mode, include_remote):
            continue
        if max_age_hours is not None:
            if not j["posted_ts"]:
                continue
            age_hours = (now_ts - j["posted_ts"]) / 3600.0
            if age_hours > max_age_hours:
                continue
        out.append(j)
    # newest first (jobs without a timestamp sink to the bottom)
    out.sort(key=lambda x: x["posted_ts"] or 0, reverse=True)
    return out
