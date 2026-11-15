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
- Open: supplier DFM sign-off + BOM lifecycle, CPL origin/rotation
  verify, second-reviewer signoff, assembly drawing, float/dome/tether
  models, bring-up + environmental qualification.
