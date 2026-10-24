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

Well inside Fusion's cheapest tier — no HDI, no impedance control,
no castellated edges.

## What's on the board

- **U1A/U1B**: two 1×7 pin-socket rows for Seeed XIAO ESP32-S3 Sense
  (17.78 mm row spacing; headers, so the XIAO stays socketed/removable)
- **J1–J3** (left): PIR / hydrophone / ultrasonic heads — SIG, 3V3, GND
- **J4–J6** (right): I2C sensors — 3V3, GND, SDA, SCL
- **J7** (bottom): UART backhaul — RX, TX, GND, 5V
- **J8** (bottom-left): SPI/expansion — 3V3, GND, MOSI, MISO, SCK
- **J9**: 5V input
- **J10**: emit transducer terminal (EMIT_SW + 3V3, consent-gated lane)
- **Emit driver**: R1 100R → Q1 2N7000 gate; D1 1N4148W flyback; C1 decoupling
- GND plane on B.Cu + explicit GND backbone; M3 mounting holes with
  copper keepouts

## Files for Seeed

```
hardware/pcb/
  ecocell-carrier.kicad_pcb          KiCad source (regenerate via tools/pcb/gen_carrier.py)
  gerbers/ecocell-carrier-gerbers.zip  upload this to Fusion
  gerbers/ecocell-carrier/           raw Gerber + drill files
  assembly/ecocell-carrier-bom.csv   manufacturing BOM
  assembly/ecocell-carrier-cpl.csv   pick-and-place (4 SMT parts)
  render-top.svg                     copper/mask/edge plot
  render.png                         3D render
```

## Ordering

1. PCB order: upload `ecocell-carrier-gerbers.zip`, spec as above.
2. PCBA (optional): the only SMT parts are R1, C1, Q1, D1 — use the
   BOM + CPL in `assembly/`, or hand-solder them (all are easy packages:
   0805, SOD-123, SOT-23). Everything else is through-hole and hand-soldered.
3. XIAO, sensor modules and heads are NOT part of the PCBA BOM — they
   plug into the sockets/headers per `BOM.md` and `ASSEMBLY.md`.

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
- This is a **v1 carrier**: cheap enough to iterate. Order a small run
  (5–10 boards), bench-test one, then scale.
