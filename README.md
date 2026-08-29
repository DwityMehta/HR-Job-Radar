# 📡 HR Job Radar

A personal app that watches **Greenhouse, Lever, Ashby, and Workday** job boards
and pings your **phone and email the moment a fresh Human Resources (HR) or
People Operations role is posted** — anywhere in the **USA** or the **SF Bay
Area**.

Freshness rules by source:
- **Greenhouse / Lever / Ashby** — only roles **posted within the last 2 hours**
  (they expose exact posting timestamps).
- **Workday** — only roles marked **"Posted Today"** (Workday exposes no
  hour-level date, so day-level is the finest possible).

Either way it de-duplicates by job ID, so it never pings you about the same
role twice.

> **Built to live entirely on your *personal* accounts** (personal GitHub +
> personal Gmail + the ntfy app on your phone). It does **not** touch Thumbtack
> systems, and it reaches you wherever you are — that's what makes it accessible
> "from outside Thumbtack."

---

## What's in the box

| Piece | File | What it does |
|-------|------|--------------|
| **Auto-poller** | `poll.py` + `.github/workflows/poll.yml` | Runs itself in the cloud every ~10 min, finds new roles, pushes to your phone + emails you. **This is the main app.** |
| **Browse dashboard** | `app.py` | Optional mobile web page to see everything at once. |
| Board list | `companies.py` | The ~64 company boards it scans. Edit to add/remove. |
| Matching logic | `job_sources.py` | Fetch + People/HR filter + location + freshness. |
| Notifications | `notify.py` | Phone push (ntfy) + email digest. |

---

## Try it locally first (2 minutes, no setup)

```bash
cd hr-job-radar
python3 poll.py                      # scans all boards, logs matches (no alerts sent yet)
LOCATION_MODE=bay_area MAX_AGE_HOURS=240 NOTIFY_ON_SEED=true python3 poll.py   # see it find roles
```

To see the dashboard locally:

```bash
python3 -m pip install -r requirements.txt
streamlit run app.py                 # opens http://localhost:8501
```

---

## Setup — do these in order

### Part A · Phone push (the "app on your phone"), ~2 min

The push app is **ntfy** — free, no account.

1. Install **ntfy** from the App Store / Google Play.
2. Pick a **secret topic name** — something nobody would guess, e.g.
   `dmehta-hr-radar-7Kq2p`. (Anyone who knows the topic can see your alerts,
   so make it random.)
3. In the ntfy app: **+ → Subscribe to topic →** type that exact name.
4. Remember the topic — you'll paste it into GitHub as `NTFY_TOPIC` below.

Tapping a notification opens the job posting directly.

### Part B · Email digest, ~3 min (optional but recommended)

Uses your **personal Gmail** to email yourself.

1. Turn on 2-Step Verification: <https://myaccount.google.com/security>
2. Create an **App Password**: <https://myaccount.google.com/apppasswords>
   (pick "Mail" → generate → copy the 16-character code).
3. You'll use these values as GitHub secrets below:
   `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`,
   `SMTP_USER=you@gmail.com`, `SMTP_PASS=<the 16-char app password>`,
   `EMAIL_TO=you@gmail.com`.

### Part C · Put it in the cloud so it runs 24/7 and reaches you anywhere

This is the step that makes it independent of Thumbtack.

1. Create a **personal GitHub account** (if you don't have one) at github.com —
   use your *personal* email, not your Thumbtack one.
2. Create a **new private repository** called `hr-job-radar`.
3. Upload this folder's contents to it. Easiest no-terminal way:
   on the repo page → **Add file → Upload files** → drag everything in →
   **Commit**. (Make sure the `.github/workflows/poll.yml` file comes along.)
4. In the repo, go to **Settings → Secrets and variables → Actions** and add:
   - Under **Secrets** (New repository secret): `NTFY_TOPIC`, and if using email:
     `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `EMAIL_TO`.
   - Under **Variables** (optional): `LOCATION_MODE` = `usa` or `bay_area`;
     `MAX_AGE_HOURS` = `2`.
5. Go to the **Actions** tab → enable workflows if prompted → click
   **HR Job Radar poll → Run workflow** to test it now.
   - The **first run seeds silently** (learns what's already posted) so you
     aren't flooded. After that, you're pinged only for genuinely new roles.
   - To get pinged even on that first run, temporarily add a variable
     `NOTIFY_ON_SEED=true`.

That's it. From now on it wakes up every ~10 minutes on GitHub's servers and
alerts your phone + inbox — no laptop needed, nothing running on Thumbtack's
network.

### Part D · Mobile browse dashboard (optional), ~3 min

If you also want a web page to scroll through matches:

1. Go to <https://share.streamlit.io> and sign in with your **personal GitHub**.
2. **Create app → pick your `hr-job-radar` repo → main file `app.py` → Deploy.**
3. You get a public URL like `https://your-app.streamlit.app`.
4. On your phone, open it in the browser and **Add to Home Screen** — it now
   behaves like an installed app icon.

---

## How you access it "from outside Thumbtack" — summary

- **Phone push:** the ntfy app on your personal phone. Works on cellular/any
  Wi-Fi, nothing to do with Thumbtack.
- **Email:** your personal Gmail, readable anywhere.
- **Dashboard:** a public `*.streamlit.app` link you can open on any device.
- **The engine:** runs on GitHub's cloud (your personal account), not your work
  laptop — so it keeps working even when your Thumbtack machine is off.

---

## Customizing

- **Add companies:** edit `companies.py`.
  - Greenhouse/Lever/Ashby: append the board token (the company slug in their
    `greenhouse.io` / `lever.co` / `ashbyhq.com` careers URL).
  - Workday: add an entry to `WORKDAY` with `tenant`, `dc` (e.g. `wd5`), and
    `site`, all read from the company's `…myworkdayjobs.com/…` URL.
  - Note: Workday "N Locations" multi-site postings are skipped (the list feed
    hides the actual cities), so some multi-location Workday roles won't match.
- **Change what counts as an HR role:** edit `HR_TITLE_PATTERNS` in `job_sources.py`.
- **USA vs Bay Area / remote:** set the `LOCATION_MODE` and `INCLUDE_REMOTE`
  GitHub *Variables*.
- **Freshness window:** `MAX_AGE_HOURS` (default `2`).
- **How often it checks:** the `cron` line in `.github/workflows/poll.yml`
  (`*/10` = every 10 min; GitHub's minimum is 5).

## Good to know

- **Not truly instant:** these boards have no public push feed, so the app polls
  every ~10 min. You'll hear about a new role within minutes of it going live.
- **2-hour rule is strict:** anything the boards can't timestamp as fresh is
  skipped, by design.
- **Free tiers:** GitHub Actions, ntfy, and Streamlit Community Cloud all cover
  this easily at personal scale.
