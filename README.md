# LightWork Ops Pulse

A lightweight operations layer for a Founder's Associate to track team
commitments, surface deadline risk, and produce the weekly founder brief.

Built for the LightWork AI assessment.

## What it does

- **This week** - commitment counts, who to chase today, who's gone silent.
- **Add commitment** - log a new team commitment with owner, deadline, confidence.
- **Log update** - record progress against an existing commitment.
- **Friday brief** - generates the weekly founder-ready summary. Deterministic
  by default; optional AI polish layer using Claude.
- **Export** - download all commitments as CSV.

## How status is calculated

Pure rules, no model in the loop:

- **Missed** - deadline passed, owner hasn't marked it done.
- **At risk** - blocked, low owner confidence, or due in ≤3 days with no
  update in ≥5 days.
- **On track** - anything else still open.
- **Done** - owner marked it done.

Stale items (no update in 7+ days) are surfaced separately on the dashboard,
because silence is its own signal.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Optional: enable AI polish on the Friday brief

The Friday brief works without any AI. The "Polish with AI" button on that
page is opt-in — it rewrites the structured brief in natural prose using
Claude. The deterministic version remains the source of truth.

To enable, set an Anthropic API key one of two ways:

**Streamlit Cloud:** add it to the app's secrets:

```toml
ANTHROPIC_API_KEY = "sk-ant-..."
```

**Local:** export it as an environment variable:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
streamlit run app.py
```

Without a key, the polish button shows a setup hint and the rest of the app
works normally.

## What's deliberately out of scope

- **No database.** State lives in Streamlit's session. Refreshing clears it.
  A real version uses Postgres or Airtable; the prototype does not.
- **No history / week-over-week deltas.** Would need persistence first.
- **No Slack / email integration.** Chase messages render as copy-paste blocks.
  Faking the integration would be worse than skipping it.
- **No auth.** Single-user prototype.
