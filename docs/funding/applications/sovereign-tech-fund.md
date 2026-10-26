<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# Sovereign Tech Fund — application answers

Portal: apply.sovereign.tech (account: hello@templeearth.cc).
Scope discipline: this asks to fund the **open infrastructure layer** —
the receipt/verification/federation commons — not field deployment.
Minimum eligible project size: **>€50k** of work.

## Project name
Temple Earth evidence commons (Treetable LLC)

## Describe your project in a sentence (~100 words)

The commons is an open, content-addressed evidence layer for
ecological and sensor data: every field reading is hashed to a
self-certifying SAID, witnessed by a quorum of independent nodes,
merged into a replayable receipt, and settled as per-contribution
credit. Anyone can replay-verify a computation or reading without
trusting the operator — the same trust model a full node gives a
blockchain, applied to real-world sensor evidence.

## In-depth description (~300 words)

Ecological data infrastructure is fragmenting across hundreds of
incompatible networks — acoustic monitors, camera traps, water gauges,
citizen-science apps — while the buyers of that data (MRV markets,
protected-area management, research) cannot verify what they receive.
Each platform is a silo whose exports lose provenance at the boundary.

This project maintains and hardens the open commons that solves the
integrity half: a lane-gated protocol (`sense`/`fleet` evidence-gated,
`emit`/`store` consent-gated, `hop`/`compute` refused outright,
`federated` provenance-labeled), a witnessed-receipt format
(SAID-addressed canonical JSON + BLAKE2s + quorum merge rules), a
federation adapter registry for 20+ allied networks, and a
replay-verified compute layer running deterministic simulations over
real connectome wiring where every task ships its own checkable proof.

The funded work: hardening the protocol and reference implementation —
spec documentation, conformance test vectors, security review of the
consent/quorum gates, interoperable receipt schema for federation
partners, and maintainer time for review. Deliverables are the spec,
the test corpus, the audited gates, and the reference tooling — all
AGPL/CC, reusable by any sensor network, MRV platform, or research
group that needs evidence they don't have to take on trust.

## Links
- Repo: https://github.com/TerexitariusStomp/living-resources
- Site/API: https://templeearth.cc (+ /developers, /receipts live)

## Estimated costs
€75,000 — ~15 person-months: spec + conformance suite (€30k),
consent/quorum security review (€15k), federation adapter hardening +
interop schema (€20k), maintainer/community (€10k).

## Dependencies / who depends on it
Built on: Reticulum/LXMF, BLAKE2s, OPA Rego, Guile/Goblins-style
actors, Astro. Depends-on-us candidates: allied sensor networks
importing via the federated lane, MRV platforms consuming receipts,
the Filecoin evidence-store adapter (devgrants #2233, separate scope).

## Funding acknowledgment
No other public funding covers these same activities (SBIR/Crowd
Supply/etc. fund hardware + field deployment, a different scope).
