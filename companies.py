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
