# hardware/ — EcoCell universal node

One board design. Every lane's electronics on every unit. Role =
firmware config + which head sits in the environment — never a variant,
never an upgrade purchase.

## What to read in what order

| File | For |
|---|---|
| `BOM.md` | What to buy — core board + every head + per-deployment kits |
| `FIELD-KIT.md` | **Complete sourcing matrix** — Seeed-assembled vs plug-in vs field kit, first-article test plan |
| `PINOUT.md` | How it wires — the pin map the firmware and heads share |
| `ASSEMBLY.md` | How to build — solder points, flash steps, bench test |
| `ENCLOSURE.md` | How to deploy — garden / shore-dock / reef-float / submerged forms |
| `DATASHEET.md` | The tender-attachable product sheet (prospective — v1 target) |
| `PCB.md` | **Manufacturable carrier** — KiCad source, DRC-clean Gerbers, Seeed ordering |
| `diagrams/wiring.svg` | **Visual: full wiring diagram** — every pin→head wire, net colors |
| `diagrams/layout.svg` | **Visual: carrier top-view** — component placement on perfboard |
| `diagrams/enclosure-forms.svg` | **Visual: 4 cross-sections** — garden/shore/float/pod |

## The build in one picture

```
        ┌──────────────────── XIAO ESP32-S3 Sense ───────────────────┐
        │  onboard: OV2640 camera · PDM mic · microSD · ESP32-S3     │
        │                                                           │
  D0 PIR wake ──┐            ┌── D4/D5  I2C bus ──────────────────┐  │
  D1 hydro ADC  │            │  BME280 · BH1750 · AD7746 (C4D)    │  │
  D2 ultra ADC  │            └────────────────────────────────────┘  │
  D3 emit PWM ──┼──▶ 40 kHz transducer driver (consent-gated)        │
  D6/D7 UART ───┼──▶ LoRa RNode / satellite modem / serial gateway   │
  D8–D10 SPI ───┴──▶ spare (expansion: second SD, display, GPS)      │
        └───────────────────────────────────────────────────────────┘
```

## Two build paths

1. **Hand build (v1, now):** XIAO ESP32-S3 Sense + breakout modules on
   headers — no PCB fab needed, ~1–2 h per unit, ~$35–45.
2. **Carrier board (v2, tender path):** `pcb/` holds a **DRC-clean,
   fab-ready KiCad design** — upload `gerbers/ecocell-carrier-gerbers.zip`
   to Seeed Fusion (2-layer, 100×80, standard spec). v2 adds the field
   layer: screw-terminal 5V input, fuse, reverse-polarity Schottky, rail
   TVS, ESD clamps on the head inputs, power LED, fiducials. See `PCB.md`
   for the package and `FIELD-KIT.md` for everything else a deployable
   node still needs (XIAO, heads, radio, power, enclosure).

## Honest flags

- Pin assignments in `PINOUT.md` are the recommended map — **verify the
  free-GPIO set against your board revision's schematic** (XIAO Sense
  expansion board occupies internal pins for camera/mic/SD).
- The ultrasonic lane's 20–100 kHz band exceeds what the ESP32 ADC path
  samples comfortably — the head and wiring are ready; firmware capture
  may need decimation tricks or the C++ firmware variant. Noted in
  `PINOUT.md`, not hidden.
- Emit lane: hardware is live on every board; activation is purely a
  consent flag — see `deploy/policies/living/` and `firmware/node/main.py`.
