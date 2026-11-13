<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# Pressure / leak specification — ecocell-ocean submerged pod

Derived from the deployment envelope in `hardware/ENCLOSURE.md`
(Form E). Numbers here are engineering targets for the R0 prototype
qualification — not yet verified by test.

## Deployment envelope

| Parameter | Value | Basis |
|---|---|---|
| Max working depth | 30 m | reef/shore deployments; Salton Sea <5 m — 30 m gives headroom for open-coast sites |
| Design pressure | 0.4 MPa (4 bar) | 30 m water ≈ 0.3 MPa + 33 % margin |
| Proof pressure | 0.6 MPa (6 bar) | 1.5× design |
| Burst pressure | ≥0.9 MPa (9 bar) | ≥2.25× design |
| Temperature | −2 … +35 °C water, +60 °C surface float | polar exclusion not required |
| Salinity | 0–40 PSU + hypersaline (Salton Sea ~60 PSU) | brine-resistant materials |
| Service interval | 6 months between services | battery + fouling cadence |

## Hull concept (R0)

- **Body:** 110 mm OD clear-acrylic or PVC pressure tube, 3 mm wall,
  both ends closed by machined end-caps on double O-rings (radial,
  Buna-N 70). Buckling governs: hoop stress σ = p·r/t at 0.6 MPa,
  r=55 mm, t=3 mm → ~11 MPa ≪ acrylic ~70 MPa yield — acceptable with
  ≥6× margin for a first article; **verify tube wall from supplier
  datasheet before ordering** (cast acrylic preferred over extruded for
  pressure work).
- **Penetrators:** only wet-side heads penetrate — hydrophone puck,
  CTD cell, emit/playback transducer, camera dome, tether gland. Every
  penetration: through-wall cable gland (IP68 rated ≥5 bar) or epoxy
  potted feedthrough; no bare holes.
- **Interior:** board conformal-coated (acrylic or silicone) as the
  second barrier even though potted heads are primary.

## Leak qualification (per unit, recorded in `UNIT-TRAVELER.md`)

1. **Dry-pressure decay:** pressurize assembled hull to 0.6 MPa via the
   test gland; isolate; pressure drop <2 % over 10 min = pass.
2. **Wet submersion:** 24 h at 0.4 MPa-equivalent depth (tank or weighted
   field rig); pass = dry interior, no bubble trail >1 bubble/5 min.
3. **Penetrator check:** after 10× thermal cycles 5→35 °C, repeat the
   dry-pressure decay on the tether/head penetrators specifically.
4. **Vacuum alternative** (no pressure rig): pull −60 kPa inside the
   hull; hold ±3 % over 5 min — catches gross seal defects only; note
   method used in the traveler.

## Rejection / rework

- Any weep → disassemble, replace O-rings, re-lubricate with silicone
  grease, retest once. Second failure scraps the end-cap set.
- Acrylic craze/crack at penetrators → scrap hull, keep board if dry.

## Open items before production

- FEA or hand-calc verification of end-cap bending at proof pressure.
- O-ring groove dimensions per Parker guide for the chosen tube ID.
- Long-term salt-fog exposure data on gland bodies (nylon vs SS316).
