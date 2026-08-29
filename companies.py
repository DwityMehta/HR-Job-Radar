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
        "affirm", "airbnb", "airtable", "amplitude", "anthropic", "asana",
        "betterment", "brex", "calendly", "carta", "chime", "cloudflare",
        "coinbase", "cultureamp", "databricks", "datadog", "discord",
        "dropbox", "elastic", "faire", "figma", "flexport", "gitlab",
        "gusto", "instacart", "lattice", "lyft", "mixpanel", "mongodb",
        "nuro", "pinterest", "reddit", "robinhood", "samsara", "scaleai",
        "sofi", "stripe", "twitch", "verkada", "waymo", "webflow",
    ],
    "lever": [
        "spotify",
    ],
    "ashby": [
        "abridge", "browserbase", "cursor", "decagon", "elevenlabs",
        "harvey", "hex", "linear", "mercor", "notion", "openai",
        "openevidence", "perplexity", "posthog", "ramp", "replit",
        "runway", "sierra", "suno", "vanta", "watershed", "writer",
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
    {"tenant": "paypal",     "dc": "wd1",  "site": "jobs",                     "name": "PayPal"},
    {"tenant": "ebay",       "dc": "wd5",  "site": "apply",                    "name": "eBay"},
    {"tenant": "mastercard", "dc": "wd1",  "site": "CorporateCareers",         "name": "Mastercard"},
    {"tenant": "target",     "dc": "wd5",  "site": "targetcareers",            "name": "Target"},
    {"tenant": "hp",         "dc": "wd5",  "site": "ExternalCareerSite",       "name": "HP"},
    {"tenant": "hpe",        "dc": "wd5",  "site": "Jobsathpe",                "name": "HPE"},
    {"tenant": "kla",        "dc": "wd1",  "site": "Search",                   "name": "KLA"},
    {"tenant": "gilead",     "dc": "wd1",  "site": "gileadcareers",            "name": "Gilead"},
    {"tenant": "workday",    "dc": "wd5",  "site": "Workday",                  "name": "Workday"},
]
