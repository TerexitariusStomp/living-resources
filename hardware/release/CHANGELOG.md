# EcoCell Ocean — Release Changelog

## unreleased — R0 in progress

- Reconstructed `ecocell-ocean` electrical package after workspace loss:
  deterministic netlist emitter (`gen_ocean_sch.py`, 115 components /
  79 nets) and PCB generator (`gen_ocean_pcb.py`) rebuilt from session
  histories + remote salvage.
- Explicit keepout-aware placement: WROOM antenna keepout faces the top
  edge; connectors distributed across all four edges; passives under
  majors on the bottom side.
- U_CHG (TP4056): ESOP-8 footprint absent from stock KiCad libs —
  pin-compatible `SOIC-8-1EP_3.9x4.9mm` substituted pending MPN check.
- Router: signal nets + plane fanout stitched on a 0.5 mm raster with
  escape-via reservation, island post-attach, dead-copper cleanup.
- Release docs: README (levels, artifacts, ECO), TEST-PLAN,
  UNIT-TRAVELER, checksummed manifest.
- Generator self-heals to 0 unconnected / 0 DRC errors; Gerbers, drills,
  CPL exported and checksummed (fab/MANIFEST.sha256).
- **BMP390 fab-blocking defect fixed** — U_PRES was placed as
  `Bosch_LGA-8` (BME280 land pattern) with the BME280 pin convention;
  BMP390 is a 10-pin 2×2 mm LGA with a different pinout. ECO
  (`tools/pcb/eco_bmp390.py`, permanent record): correct project-local
  `EcoCell:BMP390_LGA-10_2x2mm` footprint, netlist repinned to
  `1/6/10=+3V3, 2=SCL, 3/5/8/9=GND (SDO low → addr 0x76), 4=SDA, 7=NC`,
  part relocated (102,59) → (109.5,58.5) into the open pocket east of
  the SCL/SDA/SD_CS stub field — the old site was unroutable without
  disturbing the U_ENV SCL bus-bridge via at (102.3,58.5). Fresh DRC:
  0 unconnected, 0 hard errors (declared fiducial deviations only).
- **Fiducials placed** (scope: assembly automation; reason: close the
  flagged R0 gap; risk: low — bare pads, no routing change). Three per
  populated side, `Fiducial_1mm_Mask2mm`. FID1/FID2 top + FID4/FID5
  bottom sit inside the U_MCU antenna-keepout far ends — declared
  deviation (no clean corner sites exist; ≥20 mm lateral from the
  antenna feed; RF-verify at bring-up). Third points FID3 (62,66) top,
  FID6 (100,66) bottom in copper pockets. DRC: 0 unconnected,
  0 errors; +8 keepout +2 courtyard findings, all expected/declared.
- **Mechanical package landed** (scope: pressure hull; reason: close the
  missing-CAD gate; risk: none to electrical artifacts). Parametric
  generator `tools/mech/gen_hull.py` → `mechanical/`: STEP (tube,
  endcap-dry/wet, assembly — quote-ready via cadquery), OpenSCAD
  source, STL previews, shared `dimensions.json`, MECHANICAL.md
  drawing. End cap: Ø118×12 flange / Ø103.7×20 plug, 2× AS568-244
  radial grooves, 6×M6 tie-rod retention, wet cap bores 1×M20 tether +
  3×M16 head glands. Flange set to 12 mm after the bending hand-calc
  showed 8 mm = ~1.5× POM-C margin at proof; 12 mm ≈ 3.5×.
- **DFM self-review** — `DFM-REVIEW.md`: board rules extracted from the
  PCB vs published Seeed/JLCPCB capabilities; all vanilla except
  0.15 mm annular ring (at-limit, called out) and the declared fiducial
  keepout deviation.
- **Quote bundle** — `electrical/ecocell-ocean-fab.zip` (Gerbers +
  drills + CPL + manifest).
- **Native schematic closed** — `ecocell-ocean.kicad_sch` regenerated
  from the shipped netlist by `tools/pcb/net2sch.py` (box symbols + net
  labels; netlist round-trip verifies 79/79 nets, 0 node diffs). Replaces
  the lost SKiDL source as the schematic artifact.
- **Assembly drawing** — `assembly/assy-top.svg` + `assy-bottom.svg`
  (F/B Fab+Silkscreen+courtyards) + `ASSEMBLY-NOTES.md`.
- **Mechanical, round 2** — `tray.step` chassis sled (board M3 pattern,
  96×200, slides in the Ø104 bore) and `float-ref.step` reference foam
  form; dome + tether gland called out as purchased parts.
- **BOM lifecycle check** — `BOM-LIFECYCLE.md`: **ICS-43434 + ICS-40730
  both EOL'd** (TDK PCN-000772, LTB 2026-06-15 NCNR); alternates are
  PDM-family → options documented. BME280 watch, BMP390 active/16-wk.
- **Land boards release rigor** — `hardware/pcb/`: fresh 0/0 DRC
  reports, MANIFEST.sha256 over the whole package, FAB-NOTES.md,
  node BOM enriched with MPNs, CPL convention documented.
- Open: supplier DFM sign-off + quote-backed BOM, CPL origin/rotation
  verify vs supplier pick file, mic-lane EOL decision (LTB buy vs PDM
  redesign), second-reviewer signoff, bring-up + environmental
  qualification.
