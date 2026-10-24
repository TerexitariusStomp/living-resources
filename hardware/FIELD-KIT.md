<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# Field node kit — complete sourcing matrix

The EcoCell carrier is the interconnect. A deployable node = assembled
carrier + XIAO + heads + radio + power + enclosure. This file is the
full buy list, split by who supplies what, with the first-article test
plan that turns "fab-ready" into "field-ready".

## A — Seeed assembles (on the carrier)

| Part | On-board ref | Package | Notes |
|---|---|---|---|
| 100 Ω resistor | R1 | 0805 | emit gate series |
| 1 kΩ resistor | R2 | 0805 | power LED |
| 100 nF cap | C1 | 0805 | 3V3 decoupling |
| 2N7000 MOSFET | Q1 | SOT-23 | emit driver (consent-gated) |
| 1N4148W diode | D1 | SOD-123 | emit flyback |
| SS14 Schottky | D2 | SMA | reverse-polarity protection |
| SMAJ5.0A TVS | D3 | SMA | rail transient clamp |
| PESD5V0 ESD ×3 | D4–D6 | SOD-323 | J1/J2/J3 signal clamps |
| Polyfuse 0.75 A | F1 | 1206 | input fuse |
| Green LED | LED1 | 0805 | power indicator |

Any generic equivalents are fine — mark them "acceptable substitute" on
the Fusion BOM line rather than locking a brand.

## B — Seeed stocks but you buy separately (plug-in, no solder)

| Item | Typical part | ~USD |
|---|---|---|
| XIAO ESP32-S3 Sense | Seeed 113991115 (camera+mic+SD onboard) | 14 |
| MicroSD card | 32 GB A1 | 5 |

## C — Sensor heads (buy per deployment)

| Lane | Connector | Typical part | ~USD |
|---|---|---|---|
| PIR | J1 | HC-SR501 or AM312 module | 1 |
| Hydrophone | J2 | electret/piezo hydrophone + preamp module | 5–10 |
| Ultrasonic | J3 | MEMS ultrasonic mic board (e.g. SPH0641-class breakout) | 4 |
| Temp/RH/pressure | J4 (I2C) | BME280 module | 2 |
| Light | J5 (I2C) | BH1750 module | 1 |
| C4D / capacitive | J6 (I2C) | AD7746 breakout | 4 |
| Emit transducer | J10 | 40 kHz piezo pair (T/R) | 2 |

Every lane is on the board; attach only the heads the deployment needs.
Nothing attaches to an organism — heads mount on the enclosure or a
free-standing stake (zero-disruption rule).

## D — Backhaul radio (J7: RX, TX, GND, 5V)

| Option | Use when | ~USD |
|---|---|---|
| LoRa RNode/Heltec V3 | mesh within km of a gateway | 8–20 |
| Wi-Fi/UART bridge | node near infrastructure | 5 |
| Satellite modem (Swarm-class) | open ocean / remote | 60–150 |

Reticulum runs over whatever serial the radio offers; firmware picks
the uplink at config time.

## E — Power (J11 screw terminal)

| Item | Spec | ~USD |
|---|---|---|
| Battery | 18650 pack + holder, or 6 V SLA | 5–15 |
| Charge controller | TP4056/CN3791 module (solar-in) | 2–4 |
| Solar panel | 5–10 W, 6 V | 8–15 |
| DC-DC (optional) | buck to 5.5–6 V if panel/battery ≠ 5–6 V | 2 |

Feed J11 with 5.5–6 V so the rail lands at ~5 V after the SS14 drop;
5 V in still works (~4.6 V rail — the XIAO's onboard regulator covers it).
Reverse polarity and transients are handled on-board (D2/D3/F1).

## F — Enclosure & mounting

| Item | Spec | ~USD |
|---|---|---|
| Enclosure | IP65+ box, UV-stable ABS/polycarbonate | 5–15 |
| Cable glands | M12/M16 IP68, one per head cable | 1–2 ea |
| Mount | stake / pole clamp / moored-float bracket | 2–10 |
| Conformal coat (optional) | acrylic spray for shore/marine units | 5 |

Enclosure forms and mounting notes: `ENCLOSURE.md` (garden, shore-dock,
moored float, submerged pod).

## First-article test plan (do this before calling it production)

1. **Bench power-up**: J11 at 5.5 V → LED1 lights; measure +5V net at
   J9 pin 2 (expect ~5.1 V) and 3V3 at J1 pin 2 (expect ~3.3 V).
2. **Protection check**: apply reversed polarity at J11 → no damage,
   no LED; restore correct polarity → normal power-up.
3. **Socket the XIAO**, flash `firmware/node/main.py`, confirm I2S
   capture → SD spool → uplink frames on J7 TX.
4. **Head smoke test**: each attached head produces readings;
   wiggle cables — no resets (TVS/filter sanity).
5. **48-h soak**: one unit powered continuously, enclosure closed;
   check temperature rise and dropouts.
6. **Field pilot**: 1–2 nodes through the E0 protocol
   (`tools/e0/score.py` for scoring) before any fleet order.
7. **Compliance review**: ESP32-S3 module carries FCC/CE on the radio
   side; the assembled product still needs a regional conformity
   check before commercial sale.

## What "production-ready" means here

- **Now**: fab-ready v2 — DRC-clean files, complete BOM, protected
  I/O, assembly marks. Orderable today.
- **After first-article + E0**: pilot-ready.
- **Production**: additionally needs the compliance check, finalized
  suppliers for every line above, and a documented flashing/config
  procedure (device identity, consent defaults) — tracked on the
  roadmap, not assumed done.
