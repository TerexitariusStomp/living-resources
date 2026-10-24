<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# EcoCell carrier PCB — fabrication package

`ecocell-carrier.kicad_pcb` is a manufacturable 2-layer carrier board
(100 × 80 mm) generated parametrically by `tools/pcb/gen_carrier.py`.
KiCad DRC: **0 violations, 0 unconnected items** (`kicad-cli pcb drc`).
Gerbers, drill, BOM and pick-and-place are exported and ready to upload.

## Board spec (Seeed Fusion standard capabilities)

| Parameter | Value |
|---|---|
| Layers | 2 (F.Cu, B.Cu) |
| Dimensions | 100 × 80 mm |
| Min trace / space | 0.5 mm / 0.2 mm (signal), 0.8 mm (power) |
| Min drill | 0.4 mm (vias), 1.0 mm (headers), 3.2 mm (M3 mounts) |
| Thickness | 1.6 mm FR4 |
| Copper | 1 oz |
| Finish | HASL or ENIG — no special requirements |
| Vias | through-hole only, no blind/buried |
| Assembly marks | 3 fiducials (FID1–3), mask-margin type |

Well inside Fusion's cheapest tier — no HDI, no impedance control,
no castellated edges.

## What's on the board

### Sensing / expansion

- **U1A/U1B**: two 1×7 pin-socket rows for Seeed XIAO ESP32-S3 Sense
  (17.78 mm row spacing; headers, so the XIAO stays socketed/removable)
- **J1–J3** (left): PIR / hydrophone / ultrasonic heads — SIG, 3V3, GND
- **J4–J6** (right): I2C sensors — 3V3, GND, SDA, SCL
- **J7** (bottom): UART backhaul — RX, TX, GND, 5V
- **J8** (bottom-left): SPI/expansion — 3V3, GND, MOSI, MISO, SCK
- **J9**: 5V-AUX tap (protected side — feeds a 5V peripheral such as a
  LoRa/RNode module)
- **J10**: emit transducer terminal (EMIT_SW + 3V3, consent-gated lane)
- **Emit driver**: R1 100R → Q1 2N7000 gate; D1 1N4148W flyback;
  C1 decoupling

### Field protection (v2 additions)

- **J11**: Phoenix MKDS 2-pole screw terminal — rugged 5V input
  (6–12 V tolerant wiring practice; the Schottky drop makes the rail
  ≈ VIN − 0.4 V, so feed 5.5–6 V for a full 5 V rail, or feed 5 V and
  accept ~4.6 V — ESP32-S3 regulates from its own 5V pin down to 3V3
  either way)
- **F1**: 1206 resettable polyfuse, 0.75 A hold
- **D3**: SMAJ5.0A unidirectional TVS across the rail (clamps transients)
- **D2**: SS14 Schottky in series — reverse-polarity protection
- **D4–D6**: PESD5V0 SOD-323 ESD/TVS clamps on the J1–J3 signal pins
  (the exposed head inputs that get handled/walked in the field)
- **LED1 + R2**: green 0805 power indicator on the 3V3 rail
- Power order: J11 → F1 → [D3 to GND] → D2 → +5V net (trunk on B.Cu)

### Plane

- GND plane on B.Cu + explicit GND backbone (spine + top bus + stubs);
  M3 mounting holes with copper keepouts

## Files for Seeed

```
hardware/pcb/
  ecocell-carrier.kicad_pcb          KiCad source (regenerate via tools/pcb/gen_carrier.py)
  gerbers/ecocell-carrier-gerbers.zip  upload this to Fusion
  gerbers/ecocell-carrier/           raw Gerber + drill files
  assembly/ecocell-carrier-bom.csv   manufacturing BOM (25 line items)
  assembly/ecocell-carrier-cpl.csv   pick-and-place (12 SMT parts)
  render-top.svg                     copper/mask/edge plot
  render.png                         3D render
```

## Ordering

1. **PCB order**: upload `ecocell-carrier-gerbers.zip`, spec as above.
2. **PCBA (recommended now)**: 12 SMT parts — R1, R2, C1, Q1, D1–D6,
   F1, LED1 — all common values/packages Seeed stocks or sources
   cheaply. Hand-soldering is also fine (0805, SOD-323, SOT-23, SMA,
   1206 are all iron-friendly).
3. **THT**: headers, sockets and the J11 terminal are marked
   `THT - hand solder` in the BOM. Seeed can place THT for extra cost —
   ask in the PCBA quote — or solder them in minutes.
4. **Not on this BOM**: XIAO module, sensor heads, radio, power system,
   enclosure — see `FIELD-KIT.md` for the complete sourcing matrix.

## Honest flags before ordering

- **Pin mapping is provisional** — verify D0–D10 assignments against the
  exact XIAO ESP32-S3 Sense board revision before committing to a run.
- **Ultrasonic head** (D2): 20–100 kHz exceeds easy ESP32 ADC capture;
  header is wired but firmware needs decimation or the ESP-IDF path.
- **Emit lane**: populated but consent-gated — the J10 path is inert
  until firmware + policy unlock it. That is the product, not a defect.
- The emit MOSFET/diode sizes are chosen for a small piezo transducer;
  a higher-power actuator needs a bigger Q1 + diode and a review of
  trace widths on EMIT_SW.
- **D4–D6 are ESD clamps, not surge arrestors** — they protect the
  signal pins against handling/static; a direct lightning-induced
  surge on a long head cable still needs the cable kept short or an
  inline GDT at the enclosure gland (noted in FIELD-KIT.md).
- This is **fab-ready, not yet production-proven**: no unit has been
  fabricated or bench-tested. Order a small run (5–10 boards), run the
  first-article checklist in `ASSEMBLY.md`, then scale.
