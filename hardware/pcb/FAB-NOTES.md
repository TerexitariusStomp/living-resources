<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# Fab notes — EcoCell land boards (ecocell-node, ecocell-carrier)

## Stack-up / spec

- `ecocell-node` (the deployable board): 100 × 100 mm, **2-layer**,
  1.6 mm FR-4, green mask, white silk. Both Gerber sets include
  adhesive/courtyard/fab layers — Seeed-standard naming.
- `ecocell-carrier` (dev adapter): same recipe.
- Both DRC-clean: **0 violations, 0 unconnected** (fresh
  `*-drc.rpt` in this dir, regenerated per release).
- **Fiducials: 6 per board, already placed** (3 top + 3 bottom pattern).
- SMT one side; THT headers/JST/SMA hand-soldered or ask Fusion to place.

## Assembly notes

- `assembly/ecocell-node-bom.csv` — MPN column populated; rows marked
  "acceptable equivalent" are jellybean 0805s.
- `assembly/*-cpl.csv` — KiCad CSV centroid, mm; KiCad convention
  (rotation 0 = library orientation, CCW positive; `side` column is
  top/bottom). Assembler to spot-check rotation on the first article —
  convention unverified against a supplier pick file.
- Consignment: XIAO ESP32-S3 (Seeed-made), EBYTE E22 — ask Seeed Fusion
  to source; everything else is "acceptable equivalent".

## Compliance / order caveats

- E22 module band must match deployment region (400M22S vs 900M22S) —
  the BOM lists both; pick one at quote time.
- ESP32-S3 + E22 carry module certs; assembled-product conformity
  check required before any commercial sale (see FIELD-KIT.md §status).
