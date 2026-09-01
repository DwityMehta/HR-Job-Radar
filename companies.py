# List of company job boards to scan, grouped by ATS (applicant tracking system).
# These were verified to have live, public postings. Add or remove freely —
# just append the company's board "token" (the slug in their careers URL).
#
#   Greenhouse -> boards-api.greenhouse.io/v1/boards/<TOKEN>/jobs
#   Lever      -> api.lever.co/v0/postings/<TOKEN>?mode=json
#   Ashby      -> api.ashbyhq.com/posting-api/job-board/<TOKEN>
#
# Tip: open a company's careers page. If the URL contains "greenhouse.io",
# "lever.co", or "ashbyhq.com", the token is the company slug in that URL.

BOARDS = {
    "greenhouse": [
        "affirm", "airbnb", "airtable", "alloy", "amplitude", "anthropic",
        "asana", "assemblyai", "atoms", "betterment", "brex", "calendly", "calyxo",
        "carta", "checkr", "chime", "cloudflare", "coinbase", "cresta",
        "cultureamp", "customerio", "databricks", "datadog", "discord",
        "dropbox", "elastic", "faire", "figma", "five9", "flexport", "gitlab",
        "groww", "gusto", "instacart", "intercom", "knock", "lattice",
        "launchdarkly", "lyft", "mattermost", "mercury", "mixpanel", "mongodb",
        "netlify", "nuro", "pinterest", "planetscale", "reddit", "remote",
        "robinhood", "samsara", "scaleai", "sofi", "stripe", "twitch",
        "unchainedlabs", "vercel", "verkada", "waymo", "webflow",
    ],
    "lever": [
        "cred", "humata", "meesho", "neon", "spotify", "veeva",
        "verygoodsecurity",
    ],
    "ashby": [
        "abridge", "airbyte", "applied", "baseten", "benchling", "browserbase",
        "clerk", "column", "crisp", "cursor", "decagon", "docker", "elevenlabs",
        "harvey", "hex", "linear", "mercor", "middesk", "modal", "notion",
        "openai", "openevidence", "oyster", "perplexity", "posthog", "pylon",
        "railway", "ramp", "render", "replit", "resend", "runway", "sentry",
        "sierra", "skymavis", "suno", "supabase", "temporal", "thumbtack",
        "uforce", "unit", "vanta", "watershed", "workos", "writer", "zapier",
        "zip",
    ],
}

# Workday boards need three pieces each (tenant + data-center + site path),
# verified to return live postings. Workday only reports day-level dates, so
# these are filtered to "Posted Today" only (see job_sources.fetch_workday).
#
# To add one: open a company's Workday careers page. The URL looks like
#   https://<TENANT>.<DC>.myworkdayjobs.com/<SITE>
# e.g. https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite
WORKDAY = [
    {"tenant": "nvidia",     "dc": "wd5",  "site": "NVIDIAExternalCareerSite", "name": "NVIDIA"},
    {"tenant": "salesforce", "dc": "wd12", "site": "External_Career_Site",     "name": "Salesforce"},
    {"tenant": "autodesk",   "dc": "wd1",  "site": "Ext",                      "name": "Autodesk"},
    {"tenant": "mastercard", "dc": "wd1",  "site": "CorporateCareers",         "name": "Mastercard"},
    {"tenant": "hp",         "dc": "wd5",  "site": "ExternalCareerSite",       "name": "HP"},
    {"tenant": "hpe",        "dc": "wd5",  "site": "Jobsathpe",                "name": "HPE"},
    {"tenant": "gilead",     "dc": "wd1",  "site": "gileadcareers",            "name": "Gilead"},
    {"tenant": "workday",    "dc": "wd5",  "site": "Workday",                  "name": "Workday"},
    {"tenant": "thermofisher","dc": "wd5", "site": "ThermoFisherCareers",      "name": "Thermo Fisher"},
    {"tenant": "chevron",    "dc": "wd5",  "site": "jobs",                     "name": "Chevron"},
]

# Teamtailor boards expose a public JSON Feed at <base>/jobs.json (no key, with
# real posting timestamps, so these keep the strict 2-hour freshness rule).
# To add one: use the careers-site base URL (the part before /jobs).
TEAMTAILOR = [
    {"base": "https://careers.cove.is", "name": "Cove"},
]

# Eightfold AI career sites expose a public JSON API with real posting
# timestamps (so these keep the strict 2-hour rule). Each entry needs the
# Eightfold host and the company's domain.
# To add one: a company's careers page powered by Eightfold hits
#   https://<HOST>/api/apply/v2/jobs?domain=<DOMAIN>&...
EIGHTFOLD = [
    {"host": "explore.jobs.netflix.net", "domain": "netflix.com", "name": "Netflix"},
]
