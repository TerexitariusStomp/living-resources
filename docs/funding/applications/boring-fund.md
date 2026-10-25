<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# The Boring Fund — application draft (up to $12.5k)

Window ~August, annual. Perfect-fit framing: we are the "essential but
overlooked" plumbing.

## Project title

Receipt plumbing: the unglamorous infrastructure conservation data needs

## Why this is "boring to fund"

Not a new sensor. Not a model. The integrity layer *between* them —
SAIDs, quorum merge, witnessed receipts, replay verification — the part
every monitoring pipeline needs and nobody funds because it isn't a
demo-able gadget.

## What we build with $12,500

- Receipt format finalized + versioned (the interoperable part)
- Adapter that lets *existing* deployments (AudioMoth-class) emit
  receipts — adoption without new hardware
- Replay verifier: any third party recomputes a claim's evidence chain
- Catalogue: public browsable receipt graph

## Budget

| Item | $ |
|---|---|
| Receipt format + adapters | 6,000 |
| Replay verifier + catalogue | 4,000 |
| Field validation with pilot nodes | 2,500 |
| **Total** | **12,500** |

## Sustainability

AGPL; evidence layer is hardware-agnostic. Adoption path is "emit
receipts from whatever you already run."
