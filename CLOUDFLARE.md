# Porting HR Job Radar to Cloudflare Workers

**Status: not built yet — this is the plan.** The GitHub Actions self-loop
(shipped) already gets detection latency to ~2 min. This port buys *reliability
and legitimacy*, not more speed.

## Why bother

| | GitHub Actions self-loop (current) | Cloudflare Workers |
|---|---|---|
| Cadence | ~2 min, but only while a run is alive | ~1 min, guaranteed by the platform |
| Scheduler trust | cron is best-effort; watchdog gaps possible | Cron Triggers are a real scheduler |
| Coverage gaps | small window between run exit and next cron tick | none |
| Terms of service | grey area — Actions is for building software | squarely intended use |
| Cost | free | free *with sharding*, or ~$5/mo |
| Work to get there | done | ~1 day; requires a Python → JS rewrite |

The honest summary: the current setup is fine and probably won't ever be
noticed. Do this port if you want it to be unambiguously above board, or if you
start seeing watchdog gaps in the Actions logs.

---

## Architecture

```
Cron Trigger (* * * * *)  ──>  Worker (scheduled handler)
                                 │
                                 ├─ fetch board APIs (shard of the board list)
                                 ├─ filter: HR title + location + lookback
                                 ├─ read/write KV: "seen" job IDs
                                 ├─ POST ntfy  (phone push, graded priority)
                                 └─ POST email HTTP API (digest)
```

State lives in **Workers KV** instead of `seen.json`-in-git. Same idea, minus
the commit churn — and KV's eventual consistency is harmless here because
de-duplication only needs to be *eventually* right.

---

## The two constraints that shape the design

These are the reason this isn't a copy-paste job. **Verify both against current
Cloudflare docs before starting** — limits move.

### 1. Subrequests per invocation

Each board is one `fetch()` = one subrequest. The app currently makes well over
100 per scan (≈115 board tokens, plus Workday and Eightfold which each fire one
request *per search term*).

My understanding is the free plan caps this around **50 subrequests** per
invocation, and the paid plan far higher. Either way, ~120 in one invocation is
likely too many for free.

**Fix: shard the board list across minutes.** With the cron firing every minute
and 3 shards, every board gets checked every 3 minutes — still far better than
today. Pick the shard from the current minute:

```js
const SHARDS = 3
const shard = Math.floor(Date.now() / 60000) % SHARDS
const myBoards = ALL_BOARDS.filter((_, i) => i % SHARDS === shard)
```

Bonus: this also cuts per-invocation CPU.

### 2. CPU time per invocation

A scan currently parses ~14,000 postings. Awaiting network I/O does *not* count
against CPU time, but `JSON.parse` and the title/location filtering do. The free
plan's CPU allowance is small (my understanding: ~10ms), which ~14k postings
would likely blow; the paid plan allows far more (tens of seconds).

**Fix:** sharding (above) cuts this ~3×, and filtering titles *before* building
full objects cuts it further. If it still doesn't fit, the $5/mo Workers Paid
plan removes the question entirely.

---

## Work breakdown

### 1. `job_sources.py` → `src/sources.js` — the bulk of the effort

Mechanical but not trivial. Port, per ATS:

| Function | Notes |
|---|---|
| `fetch_greenhouse` | trivial — plain GET + JSON |
| `fetch_lever` | trivial |
| `fetch_ashby` | trivial |
| `fetch_workday` | POST with JSON body, one request **per search term** — main subrequest consumer |
| `fetch_teamtailor` | trivial |
| `fetch_eightfold` | GET per search term |

Also port the pure logic, which is straightforward: `is_hr_title`,
`location_matches`, `_looks_us`, `HR_TITLE_PATTERNS`, `US_STATE_*`,
`BAY_AREA_TERMS`, `NON_US_HINTS`.

⚠️ **Regex gotcha:** `_HR_WORD_RE` is `(?<!\d\s)(?<!\d)\bHR\b`. JS supports
lookbehind in modern V8, so this ports as-is — but test it, because getting it
wrong reintroduces the "12 hr Day Shift" false positive.

Replace `concurrent.futures` with `Promise.allSettled` — and keep the
per-board error isolation, so one dead board never kills a scan:

```js
const results = await Promise.allSettled(myBoards.map(fetchBoard))
const jobs = results.filter(r => r.status === 'fulfilled').flatMap(r => r.value)
```

### 2. `notify.py` → `src/notify.js`

- **ntfy push:** direct port. `fetch(url, {method:'POST', headers:{Title, Click, Tags, Priority}})`. Keep `push_tier` exactly as-is — the age grading is the useful part.
- **Email: needs replacing, not porting.** ⚠️ Workers cannot open raw TCP sockets, so **SMTP is impossible** — `smtplib` has no equivalent. You must switch to an HTTP email API. [Resend](https://resend.com) has a free tier that covers this comfortably; Brevo and SendGrid also work. Note MailChannels (the old go-to for Workers) ended its free Workers tier, so don't follow older tutorials.
- Drop `_header_safe` — JS strings are UTF-16 and `fetch` handles header encoding, though you should still strip non-latin-1 characters since ntfy sends the title as an HTTP header.

### 3. `poll.py` → `src/index.js`

The self-looping machinery all **disappears** — that existed only to work
around GitHub's unreliable cron. No loop, no signal handlers, no git persistence.

```js
export default {
  async scheduled(event, env, ctx) {
    const seen = JSON.parse(await env.RADAR.get('seen') || '{}')
    const jobs = await fetchShard(env)
    const fresh = filterJobs(jobs, { lookbackHours: 24, mode: env.LOCATION_MODE })
    const isNew = fresh.filter(j => !(j.id in seen))
    const now = Math.floor(Date.now() / 1000)

    for (const j of isNew.slice(0, 8)) await sendPush(j, now, env)
    if (isNew.length) await sendDigest(isNew, now, env)

    for (const j of fresh) seen[j.id] ??= now
    await env.RADAR.put('seen', JSON.stringify(prune(seen, now)))
  }
}
```

Keep `PUSH_BURST_CAP` and the 30-day `prune` — both still matter.

### 4. `wrangler.toml`

```toml
name = "hr-job-radar"
main = "src/index.js"
compatibility_date = "2026-09-16"

[triggers]
crons = ["* * * * *"]

[[kv_namespaces]]
binding = "RADAR"
id = "<from: wrangler kv namespace create RADAR>"

[vars]
LOCATION_MODE = "usa"
INCLUDE_REMOTE = "true"
LOOKBACK_HOURS = "24"
PUSH_BURST_CAP = "8"
SHARDS = "3"
```

### 5. Deploy

```bash
npm install -g wrangler
wrangler login
wrangler kv namespace create RADAR          # paste the id into wrangler.toml
wrangler secret put NTFY_TOPIC
wrangler secret put RESEND_API_KEY
wrangler secret put EMAIL_TO
wrangler deploy
wrangler tail                               # watch live logs
```

### 6. Seed and cut over

1. Copy the current `seen.json` into KV so you don't get a flood of
   already-known roles on first run:
   ```bash
   wrangler kv key put --binding=RADAR seen "$(cat seen.json)"
   ```
2. Let both run in parallel for a day and compare — you should get duplicate
   pings for the same roles, which confirms the port is finding what Actions
   finds.
3. Once they agree, disable the Actions workflow (Actions tab → **⋯ → Disable
   workflow**). Keep the Python version in the repo; it's a useful reference
   and a fallback.

---

## What does *not* need to change

- `companies.py` — port to a JS array/object literal verbatim; no logic in it.
- `app.py` (Streamlit dashboard) — leave on Streamlit Cloud, it's unrelated to
  polling and works fine as-is.
- The age-grading tiers, lookback-window reasoning, and burst cap — these are
  design decisions, not GitHub workarounds. Carry them over unchanged.

## Rough effort

| Task | Estimate |
|---|---|
| Port sources + filters, with tests against live boards | 3–4 h |
| Port notify (incl. new email provider) | 1–2 h |
| Worker entrypoint, KV, sharding | 1–2 h |
| Deploy, seed, parallel-run verification | 1–2 h |

**Total ≈ 1 day.** The risk concentrates in the sources port — that's where a
silent mistranslation of the filters would cause quiet misses, which is exactly
the failure mode this whole exercise was about. Test the filters against known
postings (the Webflow job is a good fixture) before cutting over.
