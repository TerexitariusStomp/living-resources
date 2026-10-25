<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# Bench certification — offering draft

Target: edge-AI hardware vendors, neuromorphic chip companies,
MRV platform vendors, anyone publishing efficiency claims.

## The gap

Every compute vendor claims efficiency. Almost none publish joules, and
none publish joules a third party can reproduce. Marketing slides are
not evidence — and buyers, journalists, and regulators increasingly
know it.

## The product: a certified efficiency receipt

We run your workload (or a reference workload on your hardware) through
our measurement harness — the same one we run on ourselves — and emit:

- ops/decision (exact op-model counts, not FLOP marketing)
- bytes/decision (real format footprints)
- wall/CPU/RSS (pinned-core measured)
- joules/decision (RAPL counter deltas, wraparound-safe,
  ≥100ms windows so sub-ms workloads don't resolve to zero)
- every cell tiered: **measured** | **estimated** | **cited**
- a SAIDed bundle any third party can replay and verify

## Proof artifact (already published)

Our own benchmark: 15 real-organism connectome workloads vs dense and
sparse fp32 baselines on x86 — including the result where we *lose*
(small wiring is ~20× more joules than SIMD numpy) and the degree-
matched control proving the efficiency is sparsity, not biology. A
certification methodology that publishes its own unfavorable results is
the only kind worth buying.

## Pricing

| Report | Scope | Price |
|---|---|---|
| Single-workload cert | One workload, one receipt bundle, public-verifiable | $2,500 |
| Comparative cert | Your hardware vs named baselines | $7,500 |
| Standing cert | Per-release re-certification | $10k/quarter |

## Outreach line

"You claim efficiency. We'll make it provable — or tell you honestly
that it isn't, which is worth more."
