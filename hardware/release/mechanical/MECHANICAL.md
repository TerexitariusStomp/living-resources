<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# Mechanical package — ecocell-ocean submerged pod

Source of truth: `tools/mech/gen_hull.py` → `dimensions.json` (the single
number set; `.scad` and `.stl` are generated views of it). Pressure and
leak requirements live in `../PRESSURE-SPEC.md` — this file is the
machining/assembly drawing in text form.

## Status

| Part | Artifact | State |
|---|---|---|
| Pressure tube | `hull-tube.step` / `.scad` / `.stl` | cut-to-length purchase; cast acrylic preferred (see PRESSURE-SPEC) |
| End cap ×2 | `endcap-dry.step` / `endcap-wet.step` (+ `.scad` source) | **machined** — POM-C/acetal or 316L; STEP is quote-ready |
| Assembly | `assembly.step` | tube + both caps, verifies fit |
| Tie rods ×6 | — | off-the-shelf M6 × L(TBD by stack-up) SS316, per `dimensions.json` PCD |
| O-rings ×4 | — | AS568-244 Buna-N 70 (98.02 × 3.53 mm), silicone grease |
| Camera dome | not modeled | flat-port alternative documented in ENCLOSURE; dome port TBD |
| Surface float / tether | not modeled | encapsulation, not machining — float is shaped closed-cell foam |

## End-cap dimension callouts (mm, see dimensions.json)

| Feature | Value | Note |
|---|---|---|
| Flange | Ø118 × 12 | covers Ø110 tube OD + witness land; 12 mm set by bending calc below |
| Plug | Ø103.7 × 20 engagement | 0.15 mm radial clearance to 104 mm bore |
| O-ring groove ×2 | root Ø98.1, width 4.6 | Parker radial static, 3.53 CS; land 2.0 between grooves |
| Plug nose | 1.0 chamfer + ~4.8 land | lead-in protects O-rings on assembly |
| Tie rods | 6 × Ø6 on Ø114 PCD, through flange | cap-to-cap clamping; seals loaded by tie-rod preload |
| Wet-cap glands | 1 × Ø20.5 (M20 tether) + 3 × Ø16.5 (M16) on Ø60 PCD | thread or glue per gland vendor |

## Machining notes

- Groove surface finish ≤0.8 µm Ra on root and both flanks; no spiral
  marks across the seal path.
- Tube ends faced square ±0.1 mm over Ø110; deburr, no chamfer on the
  sealing land (plug provides the lead-in).
- Plug/bore fit: H11/g10 class; plug must not rock in the bore.
- Proof-test each cap set per PRESSURE-SPEC leak qualification before
  any electronics go in.

## Bending check (hand-calc, closed)

Conservative model: cap face as simply-supported disc retained at the
tie-rod PCD (Ø114), uniform 0.6 MPa proof load, Roark
σ = 3(3+ν)·p·a² / 8t². At t = 12 mm, σ ≈ 17 MPa → **~3.5× margin on
POM-C (~60 MPa yield), ~12× on 316L**. Tie rods see ~850 N each vs
~10 kN proof. 8 mm flanges gave only ~1.5× on POM-C — rejected.
The real section is stiffer (solid plug reinforces the bore face), so
the margin is understated — FEA optional for R1 refinement, not a
production gate.

## Known gaps before production
- **Camera dome / float / tether** not modeled; float is an
  encapsulation job (closed-cell foam), dome is a purchased port.
- Internal stack-up tray (board + battery mounting inside the tube) —
  needed before tube_len is frozen; 240 mm is the R0 allowance.
