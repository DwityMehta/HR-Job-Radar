"""
HR Job Radar poller.

Runs in one of two modes:

  Single shot  (LOOP_FOR_MINUTES unset/0)  — one scan, then exit.
  Self-looping (LOOP_FOR_MINUTES > 0)      — scans every POLL_EVERY_SECONDS
                                             for that long, then exits.

The self-looping mode exists because GitHub Actions treats `cron` as a
suggestion: a `*/10` schedule was measured firing every 29 min on average, with
gaps up to 7 hours. Rather than trust their alarm clock, we ask for one
long-lived run and keep our own time inside it. Detection latency then comes
from POLL_EVERY_SECONDS (~2 min), not from GitHub's scheduler.

Each cycle:
  1. Fetches every posting from the configured boards.
  2. Keeps People/HR roles in the target location posted within LOOKBACK_HOURS.
  3. Compares against seen.json so you're only notified about NEW roles.
  4. Pushes to your phone, volume graded by age (see notify.push_tier), and
     emails a digest.
  5. Records what it saw so the same role never pings you twice.

Note on LOOKBACK_HOURS: this is deliberately generous (24h). It is NOT a
freshness gate — de-duplication by job ID is what prevents repeat pings. A
tight window here does not make you faster; it only decides whether you are
told at all, and a role that ages out is lost silently and permanently. Urgency
belongs in the notification volume, not in a filter.

Config via environment variables (all optional):
  LOCATION_MODE      "usa" or "bay_area"            (default: usa)
  INCLUDE_REMOTE     "true" / "false"               (default: true)
  LOOKBACK_HOURS     how far back to consider       (default: 24)
  POLL_EVERY_SECONDS seconds between scans in loop  (default: 120)
  LOOP_FOR_MINUTES   total loop duration, 0 = once  (default: 0)
  PUSH_BURST_CAP     max phone pushes per cycle     (default: 8)
  SEEN_FILE          path to state file             (default: seen.json)
  GIT_PERSIST        "true" to commit seen.json      (default: false)
  NOTIFY_ON_SEED     "true" to notify on first run  (default: false)

Notification config lives in notify.py (NTFY_* and SMTP_* / EMAIL_TO).
"""

import json
import os
import signal
import subprocess
import time

import job_sources as js
import notify

SEEN_FILE = os.environ.get("SEEN_FILE", "seen.json")
RETENTION_DAYS = 30  # forget IDs older than this so seen.json stays small

_stop = False


def _on_signal(signum, _frame):
    """GitHub sends SIGTERM when a job is cancelled or times out. Finish the
    current cycle and exit cleanly so state gets flushed."""
    global _stop
    _stop = True
    print(f"  (signal {signum} received — finishing up and exiting)")


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


def _git(*args, check=False):
    return subprocess.run(("git",) + args, capture_output=True, text=True, check=check)


def _git_persist():
    """Commit + push seen.json when it changed. Called from inside the loop, so
    it must tolerate the bot having pushed from a previous run: pull --rebase
    first, and never raise (a git failure must not kill the poller)."""
    try:
        if not _git("status", "--porcelain", SEEN_FILE).stdout.strip():
            return False
        _git("add", SEEN_FILE)
        _git("-c", "user.name=hr-job-radar[bot]",
             "-c", "user.email=actions@users.noreply.github.com",
             "commit", "-m", "chore: update seen roles [skip ci]")
        for attempt in (1, 2):
            if _git("push").returncode == 0:
                return True
            # Someone else (a previous run) pushed first — replay on top.
            r = _git("pull", "--rebase", "--autostash")
            if r.returncode != 0:
                print(f"  ! git pull --rebase failed: {r.stderr.strip()[:200]}")
                return False
        print("  ! git push failed twice; will retry next cycle")
        return False
    except Exception as e:
        print(f"  ! git persist error (continuing): {type(e).__name__}: {e}")
        return False


def run_cycle(seen, cfg, first_run):
    """One scan. Mutates `seen`. Returns the list of newly-notified jobs."""
    now_ts = int(time.time())

    jobs, errors = js.fetch_all_jobs()
    fresh = js.filter_jobs(
        jobs, mode=cfg["mode"], include_remote=cfg["include_remote"],
        max_age_hours=cfg["lookback_hours"], now_ts=now_ts,
    )

    new = [j for j in fresh if j["id"] not in seen]

    print(f"[{time.strftime('%H:%M:%S')}] {len(jobs)} postings; {len(fresh)} match "
          f"(<= {cfg['lookback_hours']}h); {len(new)} new; {len(errors)} boards skipped")

    # Record everything we saw, including items we won't notify about, so a
    # later cycle never re-surfaces them.
    for j in fresh:
        seen.setdefault(j["id"], now_ts)

    if not new:
        return []

    if first_run and not cfg["notify_on_seed"]:
        print(f"  -> first run: seeded {len(new)} existing role(s) silently "
              f"(set NOTIFY_ON_SEED=true to be pinged on the first run)")
        return []

    # `fresh` is sorted newest-first, so the cap keeps the most urgent roles on
    # the phone and lets the rest land in the email digest. Without this, the
    # first run after widening LOOKBACK_HOURS would fire a wall of pushes.
    cap = cfg["push_burst_cap"]
    push_list, digest_only = new[:cap], new[cap:]

    print(f"  -> {len(new)} NEW role(s); notifying")
    # Never let a notification error abort the cycle before state is saved —
    # otherwise the same roles re-trigger forever (a failure loop).
    try:
        for j in push_list:
            tier = notify.push_tier(j, now_ts)[0]
            ok = notify.send_push(j, now_ts)
            print(f"     {'push' if ok else 'log '} [{tier:7}] | {j['company']}: {j['title']}")
        if digest_only:
            print(f"     {len(digest_only)} more over the burst cap -> email only")
        if notify.send_email_digest(new, now_ts):
            print(f"     email digest sent ({len(new)} roles)")
    except Exception as e:
        print(f"  ! notification error (continuing): {type(e).__name__}: {e}")

    return new


def main():
    cfg = {
        "mode": os.environ.get("LOCATION_MODE", "usa").strip().lower(),
        "include_remote": os.environ.get("INCLUDE_REMOTE", "true").lower() != "false",
        "lookback_hours": float(os.environ.get("LOOKBACK_HOURS", "24")),
        "notify_on_seed": os.environ.get("NOTIFY_ON_SEED", "false").lower() == "true",
        "push_burst_cap": int(os.environ.get("PUSH_BURST_CAP", "8")),
    }
    every = float(os.environ.get("POLL_EVERY_SECONDS", "120"))
    loop_for = float(os.environ.get("LOOP_FOR_MINUTES", "0")) * 60
    git_persist = os.environ.get("GIT_PERSIST", "false").lower() == "true"

    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)

    seen = _load_seen()
    first_run = len(seen) == 0
    deadline = time.time() + loop_for

    if loop_for > 0:
        print(f"self-looping: scanning every {every:.0f}s for {loop_for / 60:.0f} min "
              f"(mode={cfg['mode']}, lookback={cfg['lookback_hours']}h)")

    cycle = 0
    while True:
        cycle += 1
        started = time.time()
        try:
            run_cycle(seen, cfg, first_run)
        except Exception as e:
            # One bad cycle must not end a multi-hour run.
            print(f"  ! cycle {cycle} failed (continuing): {type(e).__name__}: {e}")
        first_run = False

        seen = _prune(seen, int(time.time()))
        _save_seen(seen)
        if git_persist and _git_persist():
            print("     seen.json committed")

        if _stop or time.time() >= deadline:
            break
        # Align to the interval so slow cycles don't accumulate drift.
        time.sleep(max(1.0, every - (time.time() - started)))

    if loop_for > 0:
        print(f"exiting after {cycle} cycle(s)")


if __name__ == "__main__":
    main()
