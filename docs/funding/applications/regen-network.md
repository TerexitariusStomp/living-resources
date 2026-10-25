<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# Regen Network grants — submission draft

Categories that map directly: Science, Natural Asset Development,
Regen Ledger & Interfaces. Payment 50% cash / 50% REGEN.

## Category: Science + Natural Asset Development

### Title

Per-reading receipts for ecological MRV: a witnessed-evidence layer
for natural assets

### Objective

Ship an evidence layer that makes ecological monitoring receipted at
the reading level — SAIDs, quorum witnessing, replay verification —
compatible with Regen Registry methodology requirements. Natural assets
backed by receipted data are defensible assets; ours is the first layer
that receipts the *reading*, not just the report.

### Scoped measurable outcomes

- Receipt format + open verifier (replay any claim's evidence chain)
- Adapter emitting receipts over existing monitoring datasets
- One methodology note: how witnessed receipts map to Regen Registry
  evidence requirements
- Reference implementation: universal ~$40 field node + MicroPython
  firmware emitting receipts

### Why Regen specifically

Regen's ontology already treats ecological state as ledger-native.
Our receipts are the *input integrity* layer that ledger is missing —
claims enter the registry with their evidence chain attached. And our
guardian-custody subject-credit model is a mutual-credit complement to
credit issuance, not competition.

### Budget sketch

| Item | |
|---|---|
| Receipt format + verifier | 40% |
| Dataset adapters + registry methodology note | 35% |
| Reference node + field validation | 25% |
