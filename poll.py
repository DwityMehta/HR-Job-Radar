"""
HR Job Radar poller — run on a schedule (GitHub Actions cron, cron, or by hand).

Each run:
  1. Fetches every posting from the configured Greenhouse/Lever/Ashby boards.
  2. Keeps only People/HR roles in the target location that were posted within
     MAX_AGE_HOURS (default 2).
  3. Compares against seen.json so you're only notified about NEW roles.
  4. Sends a phone push (one per role) + an email digest.
  5. Records what it saw so the same role never pings you twice.

Config via environment variables (all optional except where noted):
  LOCATION_MODE     "usa" or "bay_area"        (default: usa)
  INCLUDE_REMOTE    "true" / "false"           (default: true)
  MAX_AGE_HOURS     freshness ceiling in hours (default: 2)
  SEEN_FILE         path to state file         (default: seen.json)
  NOTIFY_ON_SEED    "true" to notify on the very first run (default: false)

Notification config lives in notify.py (NTFY_* and SMTP_* / EMAIL_TO).
"""

import json
import os
import time

import job_sources as js
import notify

SEEN_FILE = os.environ.get("SEEN_FILE", "seen.json")
RETENTION_DAYS = 30  # forget IDs older than this so seen.json stays small


def _load_seen():
    try:
        with open(SEEN_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(seen, f, indent=0, sort_keys=True)


def _prune(seen, now_ts):
    cutoff = now_ts - RETENTION_DAYS * 86400
    return {k: v for k, v in seen.items() if v >= cutoff}


def main():
    now_ts = int(time.time())
    mode = os.environ.get("LOCATION_MODE", "usa").strip().lower()
    include_remote = os.environ.get("INCLUDE_REMOTE", "true").lower() != "false"
    max_age_hours = float(os.environ.get("MAX_AGE_HOURS", "2"))
    notify_on_seed = os.environ.get("NOTIFY_ON_SEED", "false").lower() == "true"

    seen = _load_seen()
    first_run = len(seen) == 0

    jobs, errors = js.fetch_all_jobs()
    fresh = js.filter_jobs(
        jobs, mode=mode, include_remote=include_remote,
        max_age_hours=max_age_hours, now_ts=now_ts,
    )

    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] fetched {len(jobs)} postings; "
          f"{len(fresh)} match (mode={mode}, <= {max_age_hours}h old); "
          f"{len(errors)} boards skipped")

    new = [j for j in fresh if j["id"] not in seen]

    # Record everything fresh we saw (so future runs treat it as known),
    # even items we won't notify about.
    for j in fresh:
        seen.setdefault(j["id"], now_ts)

    should_notify = new and (not first_run or notify_on_seed)

    if should_notify:
        print(f"  -> {len(new)} NEW role(s); notifying")
        # Never let a notification error abort the run before we save state —
        # otherwise the same roles re-trigger every cycle (a failure loop).
        try:
            for j in new:
                ok = notify.send_push(j, now_ts)
                print(f"     {'push' if ok else 'log '} | {j['company']}: {j['title']}")
            if notify.send_email_digest(new, now_ts):
                print(f"     email digest sent ({len(new)} roles)")
        except Exception as e:
            print(f"  ! notification error (continuing): {type(e).__name__}: {e}")
    elif new and first_run:
        print(f"  -> first run: seeded {len(new)} existing role(s) silently "
              f"(set NOTIFY_ON_SEED=true to be pinged on the first run)")
    else:
        print("  -> no new roles this cycle")

    seen = _prune(seen, now_ts)
    _save_seen(seen)


if __name__ == "__main__":
    main()
