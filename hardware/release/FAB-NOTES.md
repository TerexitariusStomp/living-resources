<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# Fabrication notes — ecocell-ocean

Stack-up, drill, and process notes for the ocean node PCB. This is the
document a fab's CAM engineer reads first; pair it with the Gerber/drill
package once exported.

## Board

| Item | Spec |
|---|---|
| Dimensions | 120 mm × 90 mm rectangular |
| Layer count | 4 |
| Copper stack | F.Cu signal · In1.Cu = GND pour · In2.Cu = +3V3 pour · B.Cu signal+GND pour |
| Min track | 0.25 mm routes (0.15 mm rule floor) |
| Min clearance | 0.2 mm copper-to-copper |
| Vias | 0.6 mm pad / 0.3 mm drill, through; blind/buried only if emitted by the stitcher (check drill table) |
| Copper-to-edge | ≥0.5 mm |
| Min drilled hole | 0.2 mm (WROOM-1 thermal PTHs — confirm fab supports 0.2 mech or laser) |
| Hole-to-hole edge | ≥0.2 mm |
| Solder mask web | ≥0.1 mm |
| Mounting holes | 4 × M3, corners, plated=no, keep-out annulus |

## Material call-out (prototype default)

- FR-4 Tg150, 1.6 mm finished thickness, ±10 %
- Copper: 1 oz outer, 0.5 oz inner (35/17 µm) — the inner pours are
  DC-power rails, not RF return planes; 0.5 oz is fine
- Solder mask: green, LPI
- Silkscreen: white, both sides
- Surface finish: HASL lead-free (prototype); ENIG preferred for the
  LGA-8 environmental sensors at production
- Impedance: none controlled — LoRa antenna feed is a short 50 Ω
  reference trace; keep ground under it uninterrupted

## Special notes for CAM

- **ESP32-S3-WROOM-1 antenna keepout** (all-layer keepout under the
  module's PCB antenna, front-left area): no copper of any net on any
  layer. Verify the keepout zone survived Gerber conversion — the board
  will not certify if copper leaks under the antenna.
- **Test points** are bare 1.5 mm pads — include in testpoint report for
  the bed-of-nails fixture (see `TEST-PLAN.md`).
- **Panelization**: none for R0; ship as singletons.
- **Fiducials**: not placed in R0 — flagged as a known gap; add global
  + local fiducials before any automated-assembly run.

## Assembly-side notes

- Two-sided SMD: all ICs/connectors top; 0603 passives + LDR bottom.
- PTH: JST XH and 2.54 mm headers, wave or hand solder.
- The microSD connector (J_SD, Molex 104031-0811) wants paste-in-hole or
  careful hand reflow — flag for the assembler.
- LGA-8 sensors (BME280/BMP390) are humidity-sensitive: MSL-3 handling,
  bake if floor life exceeded.
