"""
HR Job Radar — mobile-friendly browse dashboard.

Run locally:      streamlit run app.py
Or deploy free:   share.streamlit.io  (see README)

This is the "see everything at once" companion to the push/email poller.
"""

import time

import streamlit as st

import job_sources as js

st.set_page_config(page_title="HR Job Radar", page_icon="📡", layout="centered")


@st.cache_data(ttl=300, show_spinner=False)
def load_jobs():
    return js.fetch_all_jobs()


def age_str(posted_ts, now_ts):
    if not posted_ts:
        return "—"
    mins = max(0, int((now_ts - posted_ts) / 60))
    if mins < 60:
        return f"{mins}m ago"
    if mins < 1440:
        return f"{mins // 60}h {mins % 60}m ago"
    return f"{mins // 1440}d ago"


st.title("📡 HR Job Radar")
st.caption("Fresh Human Resources (HR) & People Operations roles "
           "from Greenhouse, Lever & Ashby boards.")

with st.sidebar:
    st.header("Filters")
    mode_label = st.radio("Location", ["USA (nationwide)", "SF Bay Area"], index=0)
    mode = "usa" if mode_label.startswith("USA") else "bay_area"
    include_remote = st.checkbox("Include remote roles", value=True)
    hours = st.slider("Posted within (hours)", 1, 168, 2,
                      help="Your notifier uses 2h. Widen here just to browse.")
    if st.button("🔄 Refresh now"):
        load_jobs.clear()
    st.divider()
    st.caption("Tip: add this page to your phone's home screen for an app-like icon.")

now_ts = int(time.time())
with st.spinner("Scanning boards…"):
    jobs, errors = load_jobs()

matched = js.filter_jobs(jobs, mode=mode, include_remote=include_remote,
                         max_age_hours=hours, now_ts=now_ts)

c1, c2, c3 = st.columns(3)
c1.metric("Postings scanned", f"{len(jobs):,}")
c2.metric("Matching roles", len(matched))
c3.metric("Window", f"≤ {hours}h")

if errors:
    st.caption(f"{len(errors)} board(s) temporarily unavailable.")

st.divider()

if not matched:
    st.info("No People/HR roles in this window right now. "
            "Widen the hours in the sidebar, or check back soon — "
            "your phone/email alerts will catch new ones automatically.")
else:
    for j in matched:
        st.markdown(
            f"**[{j['title']}]({j['url']})**  \n"
            f"{j['company']} · {j['location'] or 'location n/a'} · "
            f"_{j.get('posted_label') or age_str(j['posted_ts'], now_ts)}_  \n"
            f"<span style='color:gray;font-size:0.8em'>{j['source']}</span>",
            unsafe_allow_html=True,
        )
        st.divider()
