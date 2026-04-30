# Task 1, Written Brief

## What I built

LightWork Ops Pulse is a single page Streamlit app for a Founder's
Associate to track team commitments, surface deadline risk, and produce
the weekly founder brief. Five views in the sidebar: a Monday morning
dashboard called This Week, forms for adding commitments and logging
updates, a Friday brief generator, and CSV export.

The dashboard opens with what is broken and who needs chasing, not with
metrics. A separate "Silent" panel surfaces commitments where the owner
has not logged an update in seven or more days, so silent failure has
its own surface area on the page. The Friday brief is structured so the
founder reads what needs their input first, not a status inventory.

## Tools and why

Streamlit and pandas for the app. A non-technical user can run it in
the browser, and I can iterate on logic in 50 lines instead of 500. No
frontend build step, no auth layer, no database. This is a prototype,
not a product.

Status logic is fully rule based. Whether something is missed, at risk,
or on track is determined by deterministic rules over deadline, owner
confidence, blocker flag, and time since last update. An LLM has no
business deciding this. The founder needs the same answer every Monday
or they lose trust in the tool.

The Anthropic API (Claude Sonnet 4.6) is wired in for one specific job:
rewriting the structured Friday brief in natural prose. The structured
version stays the source of truth. The AI rewrite is opt-in, behind a
button, and the prompt restricts the model to using only facts in the
input. I also strip em dashes in post processing, because the model
inserts them despite instructions not to. If the API key is not set,
the polish button shows a setup hint and the rest of the app works
normally.

The split is the point: rules where reliability matters, AI where tone
matters.

## Day to day usage

Monday morning, open This Week. Scan the four counts, work down the
Chase Today list, click Draft Chase Message on each, paste into Slack.
Five minutes total.

Through the week, when an owner replies, log it under Log Update. The
list is pre-sorted so the most overdue items are at the top.

Adding new commitments takes 20 seconds per item. Any time the
co-founders commit a team to something in a meeting, log it.

Friday morning, open the Friday Brief, optionally press Polish With AI
for friendlier wording, paste into the founder's Slack DM or email.

## What I would improve with more time

1. Persistence. Currently session state only, refresh and you lose
your work. Move to Postgres or Airtable as the system of record.
2. Week over week deltas. "Newly at risk this week," "moved from
blocked to in progress." This is what a founder actually wants. Needs
persistence first.
3. Slack integration. Drop chase messages straight into a DM, ingest
replies as updates. Right now it is copy and paste.
4. Calendar awareness. Cross reference deadlines against PTO, public
holidays, and known launches.
5. Owner self service. A read only link per owner so they can update
their own commitments without bothering the FA.

## Limitations to flag

Single user, no auth. Fine for a prototype, not for a real team.

The status thresholds (3 days to deadline, 5 days no update) are the
rules I would start with, not the rules I would ship with. A real FA
would tune these against actual missed deadlines over a quarter.

No history. I can tell you the state today. I cannot tell you what
changed since last week. The weekly delta is the next feature, but it
requires persistence first, and faking it without storage would be
worse than not having it.

The AI polish layer occasionally tries to fabricate content (during
testing it invented "Nothing requires founder input" in sections where
that phrase did not belong, and slipped in em dashes despite explicit
instructions). I caught both during testing and constrained them
through prompt rules and post processing. A production version would
add an automated check that verifies every named entity and number in
the polished output appears in the structured input.

## Approach note

I built this in Python with Streamlit because I wanted something I could
deploy in 60 seconds and iterate on quickly. I used Claude (the chat
interface and the API) to pressure test the structure of the weekly
brief. The first draft opened with status counts, which is the wrong
lede for a founder. The current order (Needs You, Watching, Shipped,
On Track, Stale) was a result of asking what the founder would actually
scan first on a Friday morning, not what the data looks easiest to
summarise.
