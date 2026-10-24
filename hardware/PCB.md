<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# EcoCell PCB fabrication packages

Two boards live here. Order **the node** for deployment; the carrier is
the earlier dev adapter, kept for bench work.

| Board | File | Role |
|---|---|---|
| **EcoCell One** (integrated node) | `ecocell-node.kicad_pcb` | the deployable product — one PCBA = the whole electronics |
| EcoCell carrier | `ecocell-carrier.kicad_pcb` | dev adapter: socketed XIAO + head headers |

Both are generated parametrically (`tools/pcb/gen_node.py`,
`gen_carrier.py`) and DRC-clean: **0 violations, 0 unconnected items**.

## EcoCell One — the one-order board

100 × 100 mm, 2-layer. Everything electronic is on the board; the only
off-board items are transducer heads, antenna, battery, enclosure.

### On-board

| Subsystem | Parts |
|---|---|
| MCU | U1 — **Seeed XIAO ESP32-S3**, reflowed as castellated SMD module (no sockets) |
| Radio | U5 — **EBYTE E22-400M22S** UART LoRa module + J14 edge-mount SMA |
| Sensors (bare ICs) | U2 BME280 (temp/RH/press), U3 BH1750 (lux), U4 AD7746 (capacitance → C4D electrodes) |
| Charge+power | U6 TP4056 Li-ion charger, U7 MT3608 boost, J12 JST-XH battery, J13 PWR-SEL jumper |
| Protection | F1 polyfuse 0.75 A, D3 SMAJ5.0A rail TVS, D2 SS14 reverse-polarity, D4–D6 PESD5V0 signal ESD |
| Emit driver | R1 → Q1 2N7002 → J10 transducer terminal — **populated but consent-gated** |
| Power LED | LED1/R2 (3V3 rail), LED2/R8 (charge status) |
| Expansion | J1 PIR, J2 hydrophone, J3 ultrasonic, J4 I2C expansion, J6 C4D electrodes, J7 UART, J8 SPI, J9 5V-AUX |
| Assembly | FID1–3 fiducials, 4× M3 mounts |

### Board spec (Seeed Fusion standard)

| Parameter | Value |
|---|---|
| Layers / size | 2 / 100 × 100 mm |
| Min trace / space | 0.35 mm / 0.2 mm (0.65 mm-pitch sensor cluster) |
| Min via | 0.6 mm pad / 0.3 mm drill |
| Thickness / copper / finish | 1.6 mm FR4 / 1 oz / HASL or ENIG |
| Special | castellated-module reflow (U1, U5), edge-mount SMA |

### Files for Seeed

```
hardware/pcb/
  ecocell-node.kicad_pcb            KiCad source (regen via tools/pcb/gen_node.py)
  ecocell-node.png                  3D render
  gerbers/ecocell-node-gerbers.zip  upload this to Fusion
  gerbers/ecocell-node/             raw Gerber + drill
  assembly/ecocell-node-bom.csv     manufacturing BOM (46 lines)
  assembly/ecocell-node-cpl.csv     pick-and-place (30 SMT placements)
```

### Ordering

1. **Fusion → PCB + Assembly**: upload the Gerber zip; 2-layer,
   100×100 mm, 1.6 mm, 1 oz, HASL, qty 5–10 first run.
2. **PCBA**: upload `ecocell-node-bom.csv` + `ecocell-node-cpl.csv`.
   Mark jellybean lines (R/C/diodes/fuse) "acceptable equivalent".
   **Modules need explicit sourcing** — ask Seeed to supply
   XIAO ESP32-S3 (they make it) and EBYTE E22-400M22S; both are
   castellated reflow parts. If Fusion won't source them, order the
   modules from the Seeed store / EBYTE and consign them.
3. **THT leftovers**: J1–J10 headers, J11 screw terminal, J12 JST-XH,
   J13 PWR-SEL, J14 SMA — ~15 min hand solder, or ask Fusion to place.
4. **Field kit**: heads, antenna, battery, enclosure → `FIELD-KIT.md`.
5. **Provision**: `PROVISIONING.md`.

## Honest flags before ordering

- **Region**: E22-400M22S is the 433 MHz variant. For EU868/US915 order
  E22-900M22S — same footprint, same UART, swap the BOM line.
- **XIAO reflow**: verify Fusion can place the castellated XIAO module
  (it's a tall, heavy part vs typical SMD). If not, the fallback is
  hand-soldering the module's castellated pads — doable but defeats
  the one-item goal; ask in the quote first.
- **BH1750 footprint is custom-drawn** (WSOF-6): verify against the
  ROHM datasheet land pattern before a second spin.
- **Pin map is provisional** — verify D0–D10 against the XIAO Sense
  board revision (same flag as the carrier).
- **PWR-SEL (J13)**: jumper selects protected-5V-in (J11/J9) vs
  battery-boost (J12+U7). Ship with a jumper or specify default.
- **Ultrasonic head** firmware caveat unchanged (decimation / ESP-IDF).
- **Emit lane** populated but consent-gated — inert until firmware +
  policy unlock it. That is the product, not a defect.
- **0/0 DRC ≠ production-proven**: no fabricated unit exists. The
  first-article checklist in `ASSEMBLY.md` + `FIELD-KIT.md` is what
  turns this into a field-proven product. Order 5–10, bench one.

## Carrier (dev board, kept for reference)

`ecocell-carrier.kicad_pcb`, 100 × 80 mm — socketed XIAO + header
breakout. Also DRC-clean with its own Gerbers/BOM/CPL under `gerbers/`
and `assembly/`. Useful for bring-up before committing to the
integrated spin.
