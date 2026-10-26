<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# Cloudflare for Startups — field answers ($10k credits, BOOTSTRAPPED)

Apply: cloudflare.com/startups — promo code **BOOTSTRAPPED tier is now "Tier 3" (bootstrapped, under $1M raised) — note for future reference:
bootstrapped/self-funded tier (<$1M raised → $10k credits).
Why: the Startup Plan credits/upgrade directly addresses our one
infrastructure limit — the Free tier's ~10ms CPU/invocation caps the two
largest connectome verdicts and the `/verdict all` fan-out. Credits
also cover KV/Durable Objects if receipt volume outgrows free quotas.

## Form fields

**Company / project name**
Temple Earth (legal entity: Treetable LLC)

**Website**
https://templeearth.cc

**LinkedIn** — [user fills]

**Contact email**
hello@templeearth.cc

**Funding raised to date**
$0 — bootstrapped/self-funded

**What are you building? (short)**

Temple Earth is a living cloud: small open-hardware listeners sit near
forests, reefs and soil (never touching anything), and every field
reading becomes a content-addressed, quorum-witnessed receipt anyone
can replay. Built on Workers: the compute API runs deterministic LIF
simulations over 15 real organism connectome wirings with
replay-verifiable receipts; KV holds the public ledger and waitlist;
static assets serve the whole site. Federation layer pipes in 20+ allied
ecological sensor networks with provenance intact.

**Why Cloudflare?**

Already deployed: `connectome-compute-api` Worker serving templeearth.cc
+ www via custom domains, Workers Static Assets, two KV namespaces
(RECEIPTS ledger, WAITLIST), and a live public API (task/verdict/
verify/receipts/federation/presence). Scaling needs = paid-tier CPU for
the largest compute substrates + KV/Durable Objects for fleet-scale
receipt persistence.

**GitHub / product links**
- https://github.com/TerexitariusStomp/living-resources (AGPL-3.0)
- https://templeearth.cc/developers (live API docs)
- https://templeearth.cc/temple-earth-deck.pdf

## Notes

- If asked about revenue model: API access tiers + verification services
  + node hardware — all real, not speculative (Lane A in FUNDING.md).
- The worker is already live on the free plan — the application shows a
  working system, not a promise.
