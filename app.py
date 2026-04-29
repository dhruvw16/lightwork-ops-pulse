import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
from io import StringIO

st.set_page_config(page_title="LightWork Ops Pulse", page_icon="⚡", layout="wide")

# -----------------------------
# Helpers
# -----------------------------
TEAMS = ["Engineering", "Product", "Commercial", "Operations", "Other"]
CONFIDENCE_LEVELS = ["High", "Medium", "Low"]
MANUAL_STATUSES = ["Not started", "In progress", "Completed", "Blocked"]

SAMPLE_COMMITMENTS = [
    {
        "Team": "Engineering",
        "Owner": "Sarah",
        "Commitment": "Ship PMS integration beta",
        "Deadline": date.today() + timedelta(days=2),
        "Manual Status": "In progress",
        "Confidence": "Medium",
        "Blocked": False,
        "Last Update Date": date.today() - timedelta(days=6),
        "Latest Update": "Core API connection works; still resolving webhook reliability.",
        "Priority": "High",
    },
    {
        "Team": "Commercial",
        "Owner": "James",
        "Commitment": "Close Greenfield pilot",
        "Deadline": date.today() + timedelta(days=5),
        "Manual Status": "In progress",
        "Confidence": "Low",
        "Blocked": True,
        "Last Update Date": date.today() - timedelta(days=1),
        "Latest Update": "Procurement has asked for security documentation before signature.",
        "Priority": "High",
    },
    {
        "Team": "Product",
        "Owner": "Maya",
        "Commitment": "Release maintenance-notification redesign",
        "Deadline": date.today() - timedelta(days=1),
        "Manual Status": "In progress",
        "Confidence": "Medium",
        "Blocked": False,
        "Last Update Date": date.today() - timedelta(days=3),
        "Latest Update": "Design signed off; release missed due to QA queue.",
        "Priority": "Medium",
    },
    {
        "Team": "Operations",
        "Owner": "Alex",
        "Commitment": "Complete onboarding checklist v1",
        "Deadline": date.today() + timedelta(days=7),
        "Manual Status": "Completed",
        "Confidence": "High",
        "Blocked": False,
        "Last Update Date": date.today(),
        "Latest Update": "Checklist completed and shared with hiring managers.",
        "Priority": "Medium",
    },
    {
        "Team": "Engineering",
        "Owner": "Priya",
        "Commitment": "Reduce notification failure rate below 1%",
        "Deadline": date.today() + timedelta(days=12),
        "Manual Status": "In progress",
        "Confidence": "High",
        "Blocked": False,
        "Last Update Date": date.today() - timedelta(days=2),
        "Latest Update": "Retries and alerting added; monitoring results this week.",
        "Priority": "Medium",
    },
]


def normalise_record(record):
    record = dict(record)
    if isinstance(record.get("Deadline"), str):
        record["Deadline"] = datetime.strptime(record["Deadline"], "%Y-%m-%d").date()
    if isinstance(record.get("Last Update Date"), str):
        record["Last Update Date"] = datetime.strptime(record["Last Update Date"], "%Y-%m-%d").date()
    return record


def calculate_status(row):
    today = date.today()
    deadline = row["Deadline"]
    last_update = row["Last Update Date"]
    days_to_deadline = (deadline - today).days
    days_since_update = (today - last_update).days

    if row["Manual Status"] == "Completed":
        return "Completed"
    if deadline < today and row["Manual Status"] != "Completed":
        return "Missed"
    if row["Blocked"] or row["Manual Status"] == "Blocked" or row["Confidence"] == "Low":
        return "At risk"
    if days_to_deadline <= 3 and days_since_update >= 5:
        return "At risk"
    return "On track"


def risk_reason(row):
    today = date.today()
    deadline = row["Deadline"]
    last_update = row["Last Update Date"]
    days_to_deadline = (deadline - today).days
    days_since_update = (today - last_update).days

    if calculate_status(row) == "Completed":
        return "Completed"
    if deadline < today:
        return f"Deadline passed {abs(days_to_deadline)} day(s) ago"
    if row["Blocked"] or row["Manual Status"] == "Blocked":
        return "Marked as blocked"
    if row["Confidence"] == "Low":
        return "Owner confidence is low"
    if days_to_deadline <= 3 and days_since_update >= 5:
        return f"Deadline in {days_to_deadline} day(s), no update in {days_since_update} day(s)"
    return "No immediate risk signal"


def needs_attention(row):
    today = date.today()
    days_to_deadline = (row["Deadline"] - today).days
    days_since_update = (today - row["Last Update Date"]).days
    return (
        calculate_status(row) in ["At risk", "Missed"]
        or (0 <= days_to_deadline <= 3 and days_since_update >= 5)
    )


def enrich_df(records):
    rows = [normalise_record(r) for r in records]
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["Calculated Status"] = df.apply(calculate_status, axis=1)
    df["Risk Reason"] = df.apply(risk_reason, axis=1)
    df["Needs Attention"] = df.apply(needs_attention, axis=1)
    df["Days to Deadline"] = df["Deadline"].apply(lambda d: (d - date.today()).days)
    df["Days Since Update"] = df["Last Update Date"].apply(lambda d: (date.today() - d).days)
    return df


def make_follow_up(row):
    deadline_text = row["Deadline"].strftime("%d %b")
    return (
        f"Hi {row['Owner']} — quick check on '{row['Commitment']}', due {deadline_text}. "
        f"It is currently showing as {row['Calculated Status'].lower()} because: {row['Risk Reason'].lower()}. "
        "Are we still on track, and is there anything blocking delivery?"
    )


def generate_weekly_summary(df):
    if df.empty:
        return "No commitments logged yet."

    status_counts = df["Calculated Status"].value_counts().to_dict()
    completed = status_counts.get("Completed", 0)
    at_risk = status_counts.get("At risk", 0)
    missed = status_counts.get("Missed", 0)
    on_track = status_counts.get("On track", 0)

    summary = []
    summary.append("Weekly Cross-Functional Summary")
    summary.append("")
    summary.append(f"Overall: {completed} completed, {on_track} on track, {at_risk} at risk, {missed} missed.")
    summary.append("")

    completed_df = df[df["Calculated Status"] == "Completed"]
    if not completed_df.empty:
        summary.append("Completed")
        for _, row in completed_df.iterrows():
            summary.append(f"- {row['Team']}: {row['Commitment']} ({row['Owner']})")
        summary.append("")

    risk_df = df[df["Calculated Status"].isin(["At risk", "Missed"])].sort_values("Days to Deadline")
    if not risk_df.empty:
        summary.append("At Risk / Missed")
        for _, row in risk_df.iterrows():
            summary.append(
                f"- {row['Team']}: {row['Commitment']} ({row['Owner']}) — {row['Calculated Status']}; {row['Risk Reason']}"
            )
        summary.append("")

    attention_df = df[df["Needs Attention"]].sort_values("Days to Deadline")
    if not attention_df.empty:
        summary.append("Recommended Founder’s Associate Actions")
        for _, row in attention_df.iterrows():
            if row["Calculated Status"] == "Missed":
                action = "confirm revised delivery date and escalation path"
            elif row["Blocked"] or row["Manual Status"] == "Blocked":
                action = "identify blocker owner and unblock path"
            else:
                action = "request a same-day status update"
            summary.append(f"- {row['Team']} / {row['Owner']}: {action} for '{row['Commitment']}'.")

    return "\n".join(summary)


# -----------------------------
# Session State
# -----------------------------
if "commitments" not in st.session_state:
    st.session_state.commitments = SAMPLE_COMMITMENTS.copy()

# -----------------------------
# App Header
# -----------------------------
st.title("⚡ LightWork Ops Pulse")
st.caption("A lightweight operations orchestration agent for team commitments, deadline risk, and weekly founder updates.")

with st.sidebar:
    st.header("Navigation")
    page = st.radio(
        "Go to",
        ["Dashboard", "Add Commitment", "Log Update", "Weekly Summary", "Export"],
        label_visibility="collapsed",
    )
    st.divider()
    st.write("**Status logic**")
    st.caption(
        "Completed if marked completed. Missed if deadline passed. At risk if blocked, low confidence, or deadline is close with no recent update."
    )

# -----------------------------
# Dashboard
# -----------------------------
df = enrich_df(st.session_state.commitments)

if page == "Dashboard":
    st.subheader("Founder View")

    if df.empty:
        st.info("No commitments yet. Add one from the sidebar.")
    else:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("On track", int((df["Calculated Status"] == "On track").sum()))
        col2.metric("At risk", int((df["Calculated Status"] == "At risk").sum()))
        col3.metric("Missed", int((df["Calculated Status"] == "Missed").sum()))
        col4.metric("Completed", int((df["Calculated Status"] == "Completed").sum()))

        st.divider()
        st.subheader("Needs Attention Today")
        attention = df[df["Needs Attention"]].sort_values("Days to Deadline")
        if attention.empty:
            st.success("No urgent risks flagged today.")
        else:
            for _, row in attention.iterrows():
                with st.container(border=True):
                    st.markdown(f"**{row['Team']} — {row['Commitment']}**")
                    st.write(f"Owner: {row['Owner']} | Deadline: {row['Deadline'].strftime('%d %b %Y')} | Status: {row['Calculated Status']}")
                    st.warning(row["Risk Reason"])
                    with st.expander("Suggested follow-up message"):
                        st.write(make_follow_up(row))

        st.divider()
        st.subheader("All Commitments")
        display_cols = [
            "Team",
            "Owner",
            "Commitment",
            "Deadline",
            "Priority",
            "Manual Status",
            "Confidence",
            "Calculated Status",
            "Risk Reason",
            "Latest Update",
        ]
        st.dataframe(df[display_cols], use_container_width=True, hide_index=True)

# -----------------------------
# Add Commitment
# -----------------------------
elif page == "Add Commitment":
    st.subheader("Add a Team Commitment")
    with st.form("add_commitment"):
        col1, col2 = st.columns(2)
        team = col1.selectbox("Team", TEAMS)
        owner = col2.text_input("Owner", placeholder="e.g. Sarah")
        commitment = st.text_input("Commitment", placeholder="e.g. Ship integration by 14 April")
        col3, col4, col5 = st.columns(3)
        deadline = col3.date_input("Deadline", value=date.today() + timedelta(days=7))
        priority = col4.selectbox("Priority", ["High", "Medium", "Low"])
        confidence = col5.selectbox("Confidence", CONFIDENCE_LEVELS, index=1)
        manual_status = st.selectbox("Manual Status", MANUAL_STATUSES, index=1)
        blocked = st.checkbox("Blocked?")
        latest_update = st.text_area("Latest Update", placeholder="What is the latest known progress or blocker?")
        submitted = st.form_submit_button("Add commitment")

    if submitted:
        if not owner or not commitment:
            st.error("Please add at least an owner and commitment.")
        else:
            st.session_state.commitments.append(
                {
                    "Team": team,
                    "Owner": owner,
                    "Commitment": commitment,
                    "Deadline": deadline,
                    "Manual Status": manual_status,
                    "Confidence": confidence,
                    "Blocked": blocked,
                    "Last Update Date": date.today(),
                    "Latest Update": latest_update or "No update provided yet.",
                    "Priority": priority,
                }
            )
            st.success("Commitment added. Check the Dashboard to see its calculated status.")

# -----------------------------
# Log Update
# -----------------------------
elif page == "Log Update":
    st.subheader("Log an Update")
    if df.empty:
        st.info("No commitments available to update.")
    else:
        options = [f"{i}: {row['Team']} — {row['Commitment']} ({row['Owner']})" for i, row in df.iterrows()]
        selected = st.selectbox("Select commitment", options)
        idx = int(selected.split(":")[0])
        current = st.session_state.commitments[idx]

        with st.form("log_update"):
            col1, col2, col3 = st.columns(3)
            manual_status = col1.selectbox("Manual Status", MANUAL_STATUSES, index=MANUAL_STATUSES.index(current["Manual Status"]))
            confidence = col2.selectbox("Confidence", CONFIDENCE_LEVELS, index=CONFIDENCE_LEVELS.index(current["Confidence"]))
            blocked = col3.checkbox("Blocked?", value=current["Blocked"])
            latest_update = st.text_area("Update", value=current["Latest Update"])
            submitted = st.form_submit_button("Save update")

        if submitted:
            st.session_state.commitments[idx]["Manual Status"] = manual_status
            st.session_state.commitments[idx]["Confidence"] = confidence
            st.session_state.commitments[idx]["Blocked"] = blocked
            st.session_state.commitments[idx]["Latest Update"] = latest_update
            st.session_state.commitments[idx]["Last Update Date"] = date.today()
            st.success("Update logged.")

# -----------------------------
# Weekly Summary
# -----------------------------
elif page == "Weekly Summary":
    st.subheader("Weekly Summary Generator")
    st.write("Generate a concise founder-ready weekly summary from current commitments.")

    summary = generate_weekly_summary(df)
    st.text_area("Generated summary", summary, height=360)

    st.download_button(
        "Download summary as .txt",
        data=summary,
        file_name=f"lightwork_weekly_summary_{date.today().isoformat()}.txt",
        mime="text/plain",
    )

    st.info(
        "In a fuller version, this summary could be passed to ChatGPT or Claude to make the tone sharper, but the core risk logic remains deterministic and testable."
    )

# -----------------------------
# Export
# -----------------------------
elif page == "Export":
    st.subheader("Export Current Commitments")
    if df.empty:
        st.info("No commitments to export.")
    else:
        export_df = df.copy()
        csv = export_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download commitments CSV",
            data=csv,
            file_name="lightwork_ops_pulse_commitments.csv",
            mime="text/csv",
        )
        st.dataframe(export_df, use_container_width=True, hide_index=True)
