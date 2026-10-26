<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# FUNDING — live tracker

Status key: `drafted` | `submitted` | `awarded` | `declined` | `watching`
(= waiting for the next window). Update the status + date as things move.
All application drafts live in `docs/funding/applications/`; the shared
two-page concept note is `docs/funding/concept-note.md`.

Entity: **Treetable LLC** — US entity confirmed, SAM.gov registered.
SBIR and federal lanes unblocked today. LLC → C-corp conversion is
routine if an equity raise requires it.

## Lane A — earned revenue, $0 capital (now)

| Program | Est. | Status | Next action |
|---|---|---|---|
| Wetware verification audits — Cortical Labs | $5–25k/engagement | **SENT** | Email sent → logged as helpdesk ticket **#03733**, under review by their Info team |
| Wetware verification audits — FinalSpark | $5–25k/engagement | SUBMITTED | Researchers form on finalspark.com/contact submitted 2026-10-25 — portal confirmed "request received, ~3-day reply window". Watch terexmaps@gmail.com |
| Bench certification reports (edge-AI / neuromorphic / MRV vendors) | $2–10k/report | drafted | `applications/lane-a-bench-cert.md` — attach to follow-up emails once targets named |
| Replay-verified compute API | MRR | **LIVE** | `workers/compute-api/` deployed 2026-10-25: `connectome-compute-api.terexmaps.workers.dev` — TS port bit-identical to lif.py (930/930), /task /verdict /verify all live. Free tier; API keys + landing page before paid tiers |
| Evidence-layer re-analysis of existing datasets | $5–20k/project | drafted | Fold into audit pitch as the "your data, receipted" offer |

## Lane B — small fast grants

| Program | Amount | Window | Status | Next action |
|---|---|---|---|---|
| WILDLABS Awards | $10k / $50k | Annual (Feb — 2025 closed) | watching | `applications/wildlabs-awards.md` ready — submit at next cycle open |
| The Boring Fund | up to $12.5k | ~Aug, annual (2024 closed) | watching | `applications/boring-fund.md` ready — receipt plumbing is squarely "boring but essential" |
| Con X Tech prizes | varies | Rolling challenges | watching | Monitor challenge board, apply when sensing/MRV challenge posts |
| GBIF BID (via fiscal host) | €30–60k | Regional calls | drafted | `applications/gbif-bid.md` + partner-outreach email `applications/gbif-fiscal-host-email.md` (also in Gmail Drafts) — send to chosen lab |
| ~~Schmidt Futures AI-in-Science~~ | — | — | **NOT ELIGIBLE** | Postdoc-only + faculty-mentor required; AI2050 is closed-nomination. No non-academic Schmidt program exists |

## Lane C — ReFi / community (parallel)

| Program | Amount | Cycle | Status | Next action |
|---|---|---|---|---|
| Gitcoin Regen Coordination round | $1–5k realistic | Quarterly-ish rounds | watching | `applications/gitcoin-regen.md` ready — needs wallet connect + an open round |
| Regen Network grants | 50/50 cash/REGEN | Waves (old program dormant) | watching | `applications/regen-network.md` ready — verify current grant program status |
| Greenpill / Ma Earth local rounds | $1–10k | Opportunistic | watching | Attach to the Gitcoin submission |

## Lane D — hardware capital (fleet without buying it)

| Program | Amount | Timing | Status | Next action |
|---|---|---|---|---|
| Crowd Supply campaign (EcoCell) | $30–100k typical | — | **SUBMITTED** | Submitted as Treetable LLC — welcome email → account setup → SoW (~5 days review) |
| Lab pre-orders | $150–300/unit | Anytime | drafted | `applications/lab-preorder-email.md` — needs named lab contacts |

## Lane E — equity + big non-dilutive

| Program | Amount | Timing | Status | Next action |
|---|---|---|---|---|
| Superorganism (pre-seed) | $250–500k | Rolling | **SENT** | Email sent to hello@superorganism.com — await reply |
| NSF SBIR Phase I — Project Pitch | first gate | Rolling | **SUBMITTED** | Pitch #00131003 (ET topic, Phase I) — NSF reviews within ~1 month; invite → full proposal |
| NSF SBIR Phase I — full proposal | $275k | ~3 windows/yr | drafted | `applications/nsf-sbir.md` — only after pitch invite |
| DOE V-MRV adjacent calls | varies | Periodic | watching | Match when a digital-MRV call opens |
| Elemental Impact — Project Track | $500k ask | Rolling | **SUBMITTED** | Intake form submitted 2026-10-25 (portal confirmed) — full app + deck; awaits screening |
| SOSV HAX (Newark) | up to $550k | Rolling | **SUBMITTED** | Confirmation email received 2026-10-25 — review ~2 weeks; silence by month-end = pass |
| Carbon13 Venture Accelerator | €150–250k | Cohort (open) | **READY TO SUBMIT** | Email confirmed; all 7 sections complete; deck + cap table + tech one-pager uploaded — **user: record+upload founder intro video (required), then submit** (tab open) |
| Canadian Space Agency AO | up to $250k | Periodic | watching | Needs Canadian partner — consortium option |

## Staging

```
Now ──────────► Lane A outreaches + SBIR draft + Lane B/C submissions
Month 1–3 ────► First-article: 5 boards funded by first audit
Month 3–6 ────► Crowd Supply campaign (real photos, real units)
Month 6–12 ───► WILDLABS + SBIR window → E0 pilot
Month 12+ ────► Superorganism once receipt volume proves the model
```

## Rules for every application

- Lead with the evidence model — tiered measured/estimated/cited is the
  differentiator, not a caveat
- Include a replayable artifact wherever allowed (a live `replay-ok`
  URL beats a paragraph of claims)
- Never claim living compute; the compute lane is simulation over
  preserved wiring, gated separately — say it before reviewers find it
- The mutual-credit architecture is a feature for funders (subjects earn
  through guardians) — but phrase it as "per-contribution receipts," not
  crypto, in conventional applications
