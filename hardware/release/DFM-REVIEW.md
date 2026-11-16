<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# DFM self-review — ecocell-ocean R0

Board rules extracted from `ecocell-ocean.kicad_pcb` and checked against
published capabilities of the two candidate fabs (Seeed Fusion 4-layer
standard; JLCPCB JLC04161H-7628 class). **Self-review only** — the fab
must still confirm against their current spec; that is the remaining
production gate, not a checklist item here.

## Board parameters vs fab capability

| Parameter | Board | Seeed Fusion std | JLCPCB std 4L | Verdict |
|---|---|---|---|---|
| Layers / stack-up | 4 (F.Cu/GND/+3V3/B.Cu) | 1–16 | 4 | OK |
| Board size | 120 × 90 mm | ≤450×500 | ≤400×500 | OK |
| Min track width | 0.25 mm | ≥0.10 mm | ≥0.09 mm | OK |
| Min clearance | ~0.2 mm (netclass) | ≥0.10 mm | ≥0.09 mm | OK — confirm in Gerber |
| Min via | 0.5 mm OD / 0.3 mm drill (0.6/0.3 typical; all through — no blind/buried) | 0.45/0.25 | 0.45/0.15 | OK |
| Min PTH drill | 0.3 mm | ≥0.2 mm | ≥0.2 mm | OK |
| Max PTH drill | 3.2 mm (mounts) | ≤6.3 | ≤6.3 | OK |
| Min annular ring (PTH) | 0.15 mm | ≥0.15 mm | ≥0.13 mm | at limit — call out on order |
| Aspect ratio | ~5.3 (1.6 mm / 0.3 mm) | ≤8:1 | ≤10:1 | OK |
| Surface finish | TBD — spec ENIG or lead-free HASL | ENIG/HASL | ENIG/HASL | decide at PO (ENIG for LGA) |
| Soldermask/silk | green/white assumed | any | any | OK |
| Fiducials | 6× 1 mm/2 mm mask (see FAB-NOTES) | standard | standard | declared keepout deviation |

## Assembly-side flags for the assembler

- Two-sided reflow: ICs/connectors top, 0603 passives + LDR bottom.
- Fine-pitch: ADS8681 QFN-16 (0.65), ESP32-S3-WROOM module pads,
  BME280/BMP390 LGA-8 — local fiducial coverage is FID3/FID6 region;
  assembler should confirm vision against their machine.
- Molex 104031-0811 microSD wants paste-in-hole or hand reflow.
- BME280/BMP390 are MSL-3 — bake control per J-STD-020.
- TP4056 is in a substituted SOIC-8-1EP footprint (ESOP-8 MPN check
  pending — see CHANGELOG) — assembler to verify pad fit on first
  article.
- CPL contains FID* rows — fiducials are bare pads, not components;
  exclude from placement if the machine does not auto-filter.

## Not yet verified (production gates)

- Supplier DFM sign-off on actual Gerbers (this review is self-serve).
- BOM lifecycle/stock at distributor of record.
- CPL origin/rotation convention vs assembler pick file.
- Second-reviewer signoff per ECO procedure.
