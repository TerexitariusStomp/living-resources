<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# Wetware verification audit — outreach draft

Target: Cortical Labs, FinalSpark, organoid-computing research groups
(Bristol Ward-Cherrier lab, Johns Hopkins organoid-intelligence program),
and their *buyers* (the audit works both directions).

## Cold email

Subject: Your customers will soon ask "prove the neurons computed that"

Hi [name] —

Wetware computing has a credibility gap hiding in plain sight: when a
CL1 or Neuroplatform task reports a result, the buyer has no way to
verify the biological substrate actually performed that computation —
they trust the vendor's word. That works at research scale. It will not
survive the first enterprise procurement or regulatory review.

We run an open-source evidence layer that makes computation
replay-verifiable: input → deterministic transform → content-addressed
trace digest → independent replay that reproduces the result bit-for-bit.
We're already using it on preserved real-organism connectomes (15 wiring
diagrams, C. elegans through a 40,000-neuron fly medulla), measured end
to end — op counts, bytes, and RAPL joule deltas, published with honesty
tiers including the unfavorable numbers.

We'd like to offer a verification audit: you run a task, we wrap it in
the evidence layer and produce a signed, replay-verifiable receipt of
what was computed. First audit is scoped small — one task, one receipt
chain, a report your customers can check themselves. $7,500, delivered
in two weeks.

The companies that prove their compute will own the claim. Happy to show
the replay machinery on a 20-minute call — you can verify one of our
benchmarks yourself during it.

[signature]

## The offer in one line

"We make wetware claims checkable — a receipt a skeptic can replay."

## Pricing ladder

| Tier | Scope | Price |
|---|---|---|
| Single-task audit | One task → receipt chain + report | $7,500 |
| Pipeline integration | Evidence layer wraps your inference path | $25k + retainer |
| Certification standard | Ongoing verified-task registry, co-branded | negotiation |
