import os
import streamlit as st
import pandas as pd
from datetime import date, timedelta

st.set_page_config(page_title="LightWork Ops Pulse", page_icon="⚡", layout="wide")

# config
TEAMS = ["Engineering", "Product", "Commercial", "Operations", "Other"]
CONFIDENCE_LEVELS = ["High", "Medium", "Low"]
STATUSES = ["Not started", "In progress", "Done", "Blocked"]
PRIORITIES = ["P0", "P1", "P2"]

STATUS_EMOJI = {
    "Missed": "🔴",
    "At risk": "🟠",
    "On track": "🟢",
    "Done": "✅",
}

# sample data so the app is useful on first open
SAMPLE_COMMITMENTS = [
    {
        "Team": "Engineering", "Owner": "Sarah",
        "Commitment": "Ship PMS integration beta",
        "Deadline": date.today() + timedelta(days=2),
        "Status": "In progress", "Confidence": "Medium", "Blocked": False,
        "Last Update Date": date.today() - timedelta(days=6),
        "Latest Update": "Core API connection works. Webhook reliability still flaky.",
        "Priority": "P0",
    },
    {
        "Team": "Commercial", "Owner": "James",
        "Commitment": "Close Greenfield pilot",
        "Deadline": date.today() + timedelta(days=5),
        "Status": "In progress", "Confidence": "Low", "Blocked": True,
        "Last Update Date": date.today() - timedelta(days=1),
        "Latest Update": "Procurement wants security docs before signature.",
        "Priority": "P0",
    },
    {
        "Team": "Product", "Owner": "Maya",
        "Commitment": "Release maintenance notification redesign",
        "Deadline": date.today() - timedelta(days=1),
        "Status": "In progress", "Confidence": "Medium", "Blocked": False,
        "Last Update Date": date.today() - timedelta(days=3),
        "Latest Update": "Design signed off. Missed release window, stuck in QA.",
        "Priority": "P1",
    },
    {
        "Team": "Operations", "Owner": "Alex",
        "Commitment": "Onboarding checklist v1",
        "Deadline": date.today() + timedelta(days=7),
        "Status": "Done", "Confidence": "High", "Blocked": False,
        "Last Update Date": date.today(),
        "Latest Update": "Done. Shared with hiring managers Monday.",
        "Priority": "P1",
    },
    {
        "Team": "Engineering", "Owner": "Priya",
        "Commitment": "Notification failure rate < 1%",
        "Deadline": date.today() + timedelta(days=12),
        "Status": "In progress", "Confidence": "High", "Blocked": False,
        "Last Update Date": date.today() - timedelta(days=2),
        "Latest Update": "Retries and alerting live. Watching this week's numbers.",
        "Priority": "P1",
    },
]


def calc_status(row):
    today = date.today()
    days_to_deadline = (row["Deadline"] - today).days
    days_since_update = (today - row["Last Update Date"]).days
    if row["Status"] == "Done":
        return "Done"
    if row["Deadline"] < today:
        return "Missed"
    if row["Blocked"] or row["Status"] == "Blocked" or row["Confidence"] == "Low":
        return "At risk"
    if days_to_deadline <= 3 and days_since_update >= 5:
        return "At risk"
    return "On track"


def risk_reason(row):
    today = date.today()
    days_to_deadline = (row["Deadline"] - today).days
    days_since_update = (today - row["Last Update Date"]).days
    status = calc_status(row)
    if status == "Done":
        return ""
    if row["Deadline"] < today:
        return f"Deadline slipped {abs(days_to_deadline)}d ago"
    if row["Blocked"] or row["Status"] == "Blocked":
        return "Blocked"
    if row["Confidence"] == "Low":
        return "Owner confidence: low"
    if days_to_deadline <= 3 and days_since_update >= 5:
        return f"Due in {days_to_deadline}d, no update in {days_since_update}d"
    return ""


def needs_attention(row):
    today = date.today()
    days_to_deadline = (row["Deadline"] - today).days
    days_since_update = (today - row["Last Update Date"]).days
    return (
        calc_status(row) in ["At risk", "Missed"]
        or (0 <= days_to_deadline <= 3 and days_since_update >= 5)
    )


def enrich(records):
    df = pd.DataFrame([dict(r) for r in records])
    if df.empty:
        return df
    df["Calculated Status"] = df.apply(calc_status, axis=1)
    df["Risk Reason"] = df.apply(risk_reason, axis=1)
    df["Needs Attention"] = df.apply(needs_attention, axis=1)
    df["Days to Deadline"] = df["Deadline"].apply(lambda d: (d - date.today()).days)
    df["Days Since Update"] = df["Last Update Date"].apply(lambda d: (date.today() - d).days)
    return df


def chase_message(row):
    """Slack DM style. Short, direct, no system log explanations."""
    deadline = row["Deadline"].strftime("%a %d %b")
    if row["Calculated Status"] == "Missed":
        return (f"Hi {row['Owner']}, '{row['Commitment']}' was due {deadline}. "
                f"Can you share a revised date and what we need to unblock it? "
                f"Founder syncs Friday.")
    if row["Blocked"] or row["Status"] == "Blocked":
        return (f"Hi {row['Owner']}, '{row['Commitment']}' is flagged blocked. "
                f"What's the blocker, and who needs to act? Happy to help escalate.")
    if row["Confidence"] == "Low":
        return (f"Hi {row['Owner']}, you've marked '{row['Commitment']}' as low confidence. "
                f"What would move it back to medium? Anything worth flagging to the founder?")
    return (f"Hi {row['Owner']}, quick check on '{row['Commitment']}', due {deadline}. "
            f"Any update? Haven't heard since {row['Last Update Date'].strftime('%a %d %b')}.")


def weekly_brief(df):
    """Founder ready brief. Opens with asks, not inventory."""
    if df.empty:
        return "No commitments tracked."

    today = date.today()
    week_end = today + timedelta(days=(4 - today.weekday()) % 7)
    lines = []
    lines.append(f"WEEKLY OPS BRIEF, week ending {week_end.strftime('%a %d %b %Y')}")
    lines.append("")

    missed = df[df["Calculated Status"] == "Missed"].sort_values("Days to Deadline")
    blocked = df[(df["Calculated Status"] == "At risk") &
                 ((df["Blocked"]) | (df["Status"] == "Blocked"))]
    asks = pd.concat([missed, blocked]).drop_duplicates(subset=["Commitment"])

    lines.append("NEEDS YOU")
    if asks.empty:
        lines.append("  Nothing requires founder input this week.")
    else:
        for _, r in asks.iterrows():
            lines.append(f"  - {r['Commitment']} ({r['Owner']}, {r['Team']}): {r['Risk Reason']}")
    lines.append("")

    soft_risk = df[(df["Calculated Status"] == "At risk") & (~df.index.isin(asks.index))]
    if not soft_risk.empty:
        lines.append("WATCHING")
        for _, r in soft_risk.iterrows():
            lines.append(f"  - {r['Commitment']} ({r['Owner']}): {r['Risk Reason']}")
        lines.append("")

    done = df[df["Calculated Status"] == "Done"]
    if not done.empty:
        lines.append("SHIPPED")
        for _, r in done.iterrows():
            lines.append(f"  - {r['Commitment']} ({r['Owner']}, {r['Team']})")
        lines.append("")

    on_track = df[df["Calculated Status"] == "On track"]
    if not on_track.empty:
        by_team = on_track.groupby("Team").size().to_dict()
        breakdown = ", ".join(f"{t} {n}" for t, n in by_team.items())
        lines.append(f"ON TRACK: {len(on_track)} commitments ({breakdown})")
        lines.append("")

    stale = df[(df["Days Since Update"] >= 7) & (df["Calculated Status"] != "Done")]
    if not stale.empty:
        lines.append("STALE (no update in 7+ days)")
        for _, r in stale.iterrows():
            lines.append(f"  - {r['Owner']} on '{r['Commitment']}', last update {r['Days Since Update']}d ago")

    return "\n".join(lines)


# optional AI polish layer
def get_anthropic_key():
    try:
        return st.secrets["ANTHROPIC_API_KEY"]
    except (KeyError, FileNotFoundError):
        return os.environ.get("ANTHROPIC_API_KEY")


def polish_brief_with_ai(deterministic_brief: str) -> str:
    api_key = get_anthropic_key()
    if not api_key:
        raise RuntimeError("No ANTHROPIC_API_KEY found.")

    try:
        from anthropic import Anthropic
    except ImportError:
        raise RuntimeError("anthropic package not installed. Run: pip install anthropic")

    system_prompt = (
        "You are a Founder's Associate at an early stage startup, rewriting the weekly "
        "ops brief for the co-founders. You have been given a structured status report. "
        "Rewrite it in short, scannable prose. Strict rules:\n"
        "1. Only include sections that appear in the input. If the input has no STALE "
        "section, do not invent one. Same for ON TRACK, SHIPPED, WATCHING.\n"
        "2. Keep section headers in CAPS, on their own line. Plain text only. No "
        "markdown bold, no horizontal rules, no separators between sections.\n"
        "3. Section order must match the input.\n"
        "4. Convert each bullet into one short sentence. Sound like a competent human, "
        "not a system log.\n"
        "5. Do not invent facts, names, dates, or context. Only use what is in the input.\n"
        "6. The phrase 'Nothing requires founder input' belongs only in the NEEDS YOU "
        "section, and only if the input says so. Do not put it in any other section.\n"
        "7. ON TRACK should be one short sentence summarising the count and team mix, "
        "matching whatever the input says.\n"
        "8. No em dashes. Use commas, full stops, colons, or parentheses instead.\n"
        "9. No emojis, no marketing voice, no hedging.\n"
        "10. Under 250 words total."
    )
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        system=system_prompt,
        messages=[{"role": "user", "content": deterministic_brief}],
    )
    polished = message.content[0].text.strip()
    # post-process: strip any em dashes the model slipped in
    polished = polished.replace("—", ",").replace("–", ",")
    return polished

# session state
if "commitments" not in st.session_state:
    st.session_state.commitments = [dict(r) for r in SAMPLE_COMMITMENTS]
if "polished_brief" not in st.session_state:
    st.session_state.polished_brief = None


# header
st.title("⚡ LightWork Ops Pulse")
st.caption("What's breaking this week, who needs chasing, and what to put in the founder's brief.")


# sidebar
with st.sidebar:
    page = st.radio(
        "View",
        ["This week", "Add commitment", "Log update", "Friday brief", "Export"],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption(
        "**How status is calculated**\n\n"
        "🔴 **Missed**: deadline passed, not done.\n\n"
        "🟠 **At risk**: blocked, low confidence, or due in 3 days or less with no "
        "update in 5+ days.\n\n"
        "🟢 **On track**: everything else open.\n\n"
        "✅ **Done**: owner marked it done."
    )

df = enrich(st.session_state.commitments)


# this week
if page == "This week":
    if df.empty:
        st.info("No commitments yet. Add one from the sidebar.")
        st.stop()

    missed_n = int((df["Calculated Status"] == "Missed").sum())
    risk_n = int((df["Calculated Status"] == "At risk").sum())
    on_track_n = int((df["Calculated Status"] == "On track").sum())
    done_n = int((df["Calculated Status"] == "Done").sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🔴 Missed", missed_n)
    c2.metric("🟠 At risk", risk_n)
    c3.metric("🟢 On track", on_track_n)
    c4.metric("✅ Done", done_n)

    st.divider()

    st.subheader("Chase today")
    attention = df[df["Needs Attention"]].sort_values(
        ["Calculated Status", "Days to Deadline"],
        key=lambda s: s.map({"Missed": 0, "At risk": 1}).fillna(s) if s.name == "Calculated Status" else s,
    )
    if attention.empty:
        st.success("Clean week. Nothing needs chasing today.")
    else:
        for _, row in attention.iterrows():
            emoji = STATUS_EMOJI.get(row["Calculated Status"], "")
            with st.container(border=True):
                top = st.columns([5, 1])
                top[0].markdown(
                    f"**{emoji} {row['Commitment']}**  \n"
                    f"{row['Owner']} · {row['Team']} · due "
                    f"{row['Deadline'].strftime('%a %d %b')} · {row['Priority']}"
                )
                top[1].markdown(
                    f"<div style='text-align:right; color:#b45309; font-weight:600;'>"
                    f"{row['Risk Reason']}</div>",
                    unsafe_allow_html=True,
                )
                if row["Latest Update"]:
                    st.caption(
                        f"Last update ({row['Days Since Update']}d ago): "
                        f"{row['Latest Update']}"
                    )
                with st.expander("Draft chase message"):
                    st.code(chase_message(row), language=None)

    # silent panel
    stale = df[(df["Days Since Update"] >= 7) & (df["Calculated Status"] != "Done")]
    if not stale.empty:
        st.divider()
        st.subheader("Silent: no update in 7+ days")
        st.caption("Even if not at risk on paper, no news is its own signal.")
        for _, row in stale.iterrows():
            with st.container(border=True):
                st.markdown(
                    f"**{row['Commitment']}**: {row['Owner']} ({row['Team']})  \n"
                    f"Last update {row['Days Since Update']} days ago: _{row['Latest Update']}_"
                )

    st.divider()
    with st.expander(f"All commitments ({len(df)})", expanded=False):
        team_filter = st.multiselect("Filter by team", TEAMS, default=[])
        status_filter = st.multiselect(
            "Filter by status",
            ["Missed", "At risk", "On track", "Done"],
            default=[],
        )
        view = df.copy()
        if team_filter:
            view = view[view["Team"].isin(team_filter)]
        if status_filter:
            view = view[view["Calculated Status"].isin(status_filter)]

        display_cols = ["Calculated Status", "Priority", "Team", "Owner",
                        "Commitment", "Deadline", "Days Since Update",
                        "Confidence", "Latest Update"]
        st.dataframe(
            view[display_cols].rename(columns={"Calculated Status": "Status"}),
            use_container_width=True,
            hide_index=True,
        )


# add commitment
elif page == "Add commitment":
    st.subheader("Add a commitment")
    with st.form("add"):
        c1, c2 = st.columns(2)
        team = c1.selectbox("Team", TEAMS)
        owner = c2.text_input("Owner", placeholder="First name is fine")

        commitment = st.text_input(
            "What did they commit to?",
            placeholder="One sentence, verb first. e.g. 'Ship integration beta'",
        )

        c3, c4, c5 = st.columns(3)
        deadline = c3.date_input("Deadline", value=date.today() + timedelta(days=7))
        priority = c4.selectbox("Priority", PRIORITIES, index=1)
        confidence = c5.selectbox("Owner confidence", CONFIDENCE_LEVELS, index=1)

        c6, c7 = st.columns([3, 1])
        status = c6.selectbox("Status", STATUSES, index=1)
        blocked = c7.checkbox("Blocked", value=False)

        latest = st.text_area(
            "Latest update",
            placeholder="What did the owner last say? Leave blank if no update yet.",
        )

        submit = st.form_submit_button("Add", type="primary")
        if submit:
            if not owner or not commitment:
                st.error("Need at least an owner and the commitment.")
            else:
                st.session_state.commitments.append({
                    "Team": team, "Owner": owner.strip(),
                    "Commitment": commitment.strip(),
                    "Deadline": deadline, "Status": status,
                    "Confidence": confidence, "Blocked": blocked,
                    "Last Update Date": date.today(),
                    "Latest Update": latest.strip() or "",
                    "Priority": priority,
                })
                st.success("Added. Switch to **This week** to see where it lands.")


# log update
elif page == "Log update":
    st.subheader("Log an update")
    if df.empty:
        st.info("Nothing to update.")
    else:
        sort_df = df.sort_values(
            ["Needs Attention", "Days Since Update"],
            ascending=[False, False],
        )
        options = [
            f"{i}: {STATUS_EMOJI.get(row['Calculated Status'], '')} "
            f"{row['Commitment']} ({row['Owner']}, last update {row['Days Since Update']}d ago)"
            for i, row in sort_df.iterrows()
        ]
        selected = st.selectbox("Pick a commitment", options)
        idx = int(selected.split(":")[0])
        current = st.session_state.commitments[idx]

        with st.form("update"):
            c1, c2, c3 = st.columns(3)
            status = c1.selectbox("Status", STATUSES, index=STATUSES.index(current["Status"]))
            confidence = c2.selectbox(
                "Confidence", CONFIDENCE_LEVELS,
                index=CONFIDENCE_LEVELS.index(current["Confidence"]),
            )
            blocked = c3.checkbox("Blocked", value=current["Blocked"])

            latest = st.text_area("What's the update?", value=current["Latest Update"])
            submit = st.form_submit_button("Save", type="primary")
            if submit:
                st.session_state.commitments[idx].update({
                    "Status": status,
                    "Confidence": confidence,
                    "Blocked": blocked,
                    "Latest Update": latest.strip() or "",
                    "Last Update Date": date.today(),
                })
                st.success("Saved.")


# friday brief
elif page == "Friday brief":
    st.subheader("Friday brief")
    st.caption("The summary to send the founder on Friday.")

    brief = weekly_brief(df)
    st.code(brief, language=None)

    st.download_button(
        "Download .txt",
        data=brief,
        file_name=f"lightwork_brief_{date.today().isoformat()}.txt",
        mime="text/plain",
    )

    st.divider()

    st.markdown("**Polish with AI** _(optional)_")
    st.caption("Rewrites the brief above in plain English. Same facts, friendlier wording.")

    if not get_anthropic_key():
        st.info(
            "To enable, add ANTHROPIC_API_KEY to Streamlit secrets or set it as an "
            "environment variable. The brief above works without it."
        )
    else:
        if st.button("Polish brief"):
            with st.spinner("Rewriting..."):
                try:
                    st.session_state.polished_brief = polish_brief_with_ai(brief)
                except Exception as e:
                    st.error(f"AI polish failed: {e}. Use the brief above.")

    if st.session_state.polished_brief:
        st.markdown("**Polished version**")
        st.code(st.session_state.polished_brief, language=None)
        st.download_button(
            "Download polished .txt",
            data=st.session_state.polished_brief,
            file_name=f"lightwork_brief_polished_{date.today().isoformat()}.txt",
            mime="text/plain",
            key="dl_polished",
        )


# export
elif page == "Export":
    st.subheader("Export")
    if df.empty:
        st.info("Nothing to export.")
    else:
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download CSV",
            data=csv,
            file_name=f"lightwork_ops_pulse_{date.today().isoformat()}.csv",
            mime="text/csv",
            type="primary",
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
