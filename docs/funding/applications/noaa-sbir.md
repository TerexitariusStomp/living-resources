<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# NOAA SBIR Phase I — draft for FY27 NOFO (~$175k)

Status: FY27 Notice of Funding Opportunity targeted for **Nov 1 2026**
release — this draft is ready to finalize against the actual topic
list when it posts. Apply via grants.gov. Entity (Treetable LLC) is
SAM.gov-registered; NSF SBIR pitch already in review proves the
machinery works.

## Topic fit (FY25 topics — re-map on NOFO release)

- **The Changing Ocean** — reef + coastal acoustic sensing, Argo-adjacent
- **Coastal Resilience** — non-invasive shoreline/estuary monitoring
- **Monitoring & Modeling for Climate Change Mitigation** — MRV
  provenance (the integrity layer is the product)
- Cross-cutting: **Uncrewed Systems**, **AI**, **Citizen Science** —
  all three are literal components

## Project title

Receipted Ocean & Coastal Sensing: Content-Addressed Evidence Chains
for Marine Monitoring Data

## Technical abstract [adapt to NOFO page limit]

Passive acoustic and environmental sensors are proliferating in ocean
and coastal monitoring, but every reading leaves its provenance behind
at export — a record says *what* was detected, not *how the detection
was evidenced*. We have built and open-sourced an evidence layer where
each field reading is content-addressed (SAID), witnessed by a quorum
of independent low-cost nodes, and issued as a replayable receipt.
Phase I hardens this for marine deployment: salt/fouling-tolerant
packaging for the ~$40 universal node (air mic, hydrophone front-end,
environmental sensing, Reticulum store-and-forward mesh), quorum
integrity under sparse offshore connectivity, and a receipt→data-portal
pipeline so mobilized records carry their evidence chain end-to-end.

## Innovation (for reviewers)

- Evidence travels *with* the reading — verification is a property of
  the artifact, not the vendor
- ~$40 universal node vs $600+ incumbents → denser arrays at the same
  budget (citizen-science + observing-system economics)
- Replay-verified compute receipts — the same integrity primitive the
  sensing data carries
- Non-invasive by design: passive listen-only defaults, consent-gated
  emission lanes, logged duty-cycle ceilings — clean fit for protected-
  area and marine-mammal-sensitive deployments

## Phase I technical risks

- Quorum merge under intermittent offshore links (store-and-forward
  delays ≠ missing data — the spool ordering is already implemented)
- Hydrophone front-end calibration binding to the receipt SAID
- Power/duty cycling on solar under real coastal conditions

## Commercialization

Buyers: coastal MRV developers, protected-area management, fisheries
observers, offshore-wind marine-mammal monitoring (see Spoor's
traction in exactly this space), aquaculture compliance. Model: node
hardware + hosted receipt catalogue + verification services. NOAA is
itself a downstream user of provenance-bound observation data.

## Work plan sketch (6–12 mo, ~$175k)

| WP | $ |
|---|---|
| Marine packaging + calibration binding | 60k |
| Offshore mesh + quorum hardening | 45k |
| Field pilot: coastal site deployment + blinded validation | 50k |
| Commercialization + Phase II prep | 20k |

## Before submitting

- [ ] Re-map to actual FY27 topic codes when NOFO posts (~Nov 1)
- [ ] Pull letter of support from a marine/coastal partner
- [ ] Update entity naming: "Temple Earth (Treetable LLC)"
- [ ] Attach concept-note.md export
