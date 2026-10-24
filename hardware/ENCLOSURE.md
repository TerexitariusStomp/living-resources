# ENCLOSURE — deployment forms

One chassis, four forms. All share the rule set: nothing attaches to an
organism, nothing in soil, no anchor moorings, no flash/IR.

## Form A — Garden (terrestrial)

- **Housing:** weatherproof ABS box (~IP65) or a wide-mouth jar +
  desiccant. Mic and camera face out through a PTFE membrane vent
  (acoustically transparent, weatherproof) and a flat glass/acrylic port.
- **Heads exposed:** mic (membrane vent), camera (window), BME280
  (vented cavity, not sealed), BH1750 (window), PIR (behind a small
  dome or Fresnel window).
- **Mount:** strap or stake — no fasteners into trees' living tissue;
  strap bands, not screws, where bark is involved.
- **Power:** power bank inside, or solar on top.

## Form B — Shore-dock (primary ocean deployment)

- **Housing:** same box, dock/piling/breakwater mounted. The node stays
  *above* the waterline; only the hydrophone goes in the water.
- **Hydrophone:** piezo in a potted puck (epoxy potting + short 1–2 m
  lead through a cable gland). Hangs in the water column — never
  touches the bottom.
- **Zero-disruption:** nothing laid on the seabed, nothing emitted,
  no buoy required.

## Form C — Reef float (moored, stationary)

- **Housing:** the node lives *inside* a small closed-cell float —
  solar + antenna above the waterline, hydrophone dangling below on a
  1–5 m lead.
- **Station-keeping:** deadweight anchor (a placed weight — no driving,
  no dragging) OR clipped to an existing mooring/nav structure.
- **Backhaul:** LoRa to shore gateway (≤ ~10 km) or satellite modem.

## Form D — Submerged pod (shore-cabled)

- **Housing:** pressure-rated tube + full epoxy potting of the board;
  hydrophone is integral.
- **Cable:** shore-to-pod pair carries power + serial (D6/D7) — lays on
  the bottom but is the *only* tolerated cable form; prefer Form B
  where a dock exists.

## The emit-head rule

The 40 kHz transducer is mounted on every unit (inside the enclosure,
facing the medium) — it's part of the universal build. Activation is
the consent flag, not the hardware: firmware `EmitLane` + the joint
guardian+operator SAID. A unit that never gets consent simply never
drives it.

## Marine notes (honest)

- Salt water corrodes: conformal-coat the board or pot it — an unpotted
  box in a marine splash zone fails in months.
- Biofouling covers hydrophone faces over weeks — schedule cleaning or
  use anti-foul sleeves on the lead section.
- Mooring legality varies — existing-structure piggyback is the safest
  permit path; deadweight in public water may need notice.
