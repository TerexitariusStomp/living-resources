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
- **TCA9535DBT pinout corrected** — U_EXP's expander port map used a
  fictional pinout (I2C/GND on wrong physical pads; nets on pins
  25–27 of a 24-pin package). Netlist repinned to the verified
  DB-24 map, same scheme as the land node's U12 fix
  (`1=INT, 2=A1, 3=A2, 4–11=P00–P07, 12=GND, 13–20=P10–P17,
  21=A0, 22=SCL, 23=SDA, 24=VCC`; address pins grounded → 0x20,
  spare ports low): 1 = EXP_INT, 2/3 = A1/A2 → GND,
  4–11 = PIR_OUT/CHRG_ST/STDBY_ST/EN_CAM/EN_AMP/EN_ILLUM/EN_PLAY/
  CAM_RST, 13/14 = LORA_M0/LORA_M1, 15–21 spares+A0 → GND,
  22 = SCL, 23 = SDA, 24 = +3V3.
  Live board rewired: pad stubs re-escaped, multilayer weave rebuilt
  around U_EXP. Three GND pads on dense connectors/U_EXP set to
  solid zone connection (starved-thermal ECO). DRC: 0 unconnected,
  errors = declared fiducial-keepout deviations only. Same pinout fix
  applied to the land node (U12).
- **Microvias eliminated — standard-fab restored** — the rewire had
  briefly introduced seven blind/buried microvias (0.4/0.2 mm,
  HDI-class) in the U_EXP/FID3 pockets. All removed: four junctions
  now use ordinary 0.5/0.3 mm through-vias at re-probed sites, and the
  FID3-adjacent HYDRO_SIG junction threads the fiducial's 0.6 mm local
  pad clearance on a 1.35 mm center-distance rule (through-via at
  (61.1,67.05)); dead-end weave islands (ILLUM_5V, +5V, EXP_INT
  fragments) were deleted rather than bridged. Board is back to a
  through-via-only process: min via 0.5 mm OD / 0.3 mm drill
  (0.1 mm annular — at JLCPCB/Seeed standard-process limit),
  PTH+NPTH Excellon only, no blind-via drill files in the fab set.
  DRC: 0 unconnected, errors = declared fiducial-keepout
  deviations only.
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
