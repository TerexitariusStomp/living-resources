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
- Open: DRC to 0 errors/0 unconnected, Gerber/drill/CPL export, stack-up
  drawing, harness drawings, mechanical CAD + pressure spec, DFM review.
