<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# Field node kit — complete sourcing matrix

The EcoCell carrier is the interconnect. A deployable node = assembled
carrier + XIAO + heads + radio + power + enclosure. This file is the
full buy list — concrete part numbers wherever a fab or distributor
needs one — plus the first-article test plan.

## A — Seeed PCBA (on the carrier, 12 SMT parts)

| Ref | Value | Suggested MPN (any equivalent OK) | Role |
|---|---|---|---|
| R1 | 100 Ω | Yageo RC0805FR-07100RL | emit gate series |
| R2 | 1 kΩ | Yageo RC0805FR-071KL | power LED |
| C1 | 100 nF / 50 V | Samsung CL21B104KBCNNNC | 3V3 decoupling |
| Q1 | 2N7002 | onsemi 2N7002LT1G | emit driver (consent-gated) |
| D1 | 1N4148W | 1N4148W-7-F | emit flyback |
| D2 | SS14 | SS14 / 1N5819 SMA-equiv | reverse-polarity |
| D3 | SMAJ5.0A | Littelfuse SMAJ5.0A | rail transient clamp |
| D4–D6 | PESD5V0 | Nexperia PESD5V0S1BA | head-signal ESD clamps |
| F1 | 0.75 A hold | Bourns MF-MSMF075-2 | input polyfuse |
| LED1 | green | Lite-On LTST-C170GKT | power indicator |

All are jellybean parts — mark "acceptable equivalent" on the Fusion
BOM line and Seeed will substitute their stock.

## B — Seeed store, plug-in (no solder)

| Item | Part | ~USD |
|---|---|---|
| XIAO ESP32-S3 Sense | Seeed 113991115 — camera + mic + SD onboard | 14 |
| microSD card | 32 GB, class A1 | 5 |

## C — THT on the board (hand-solder or ask Fusion to place)

| Ref | Part | Notes |
|---|---|---|
| U1A/U1B | 2.54 mm socket strips, 1×7 ×2 | XIAO stays removable |
| J1–J8 | 2.54 mm pin headers | cut from a 40-pin strip |
| J9, J10 | 2.54 mm pin headers | 5V-AUX tap + emit terminal |
| J11 | Phoenix MKDS 1.5/2-5.0 screw terminal | field 5V input |

## D — Sensor heads (per deployment; nothing attaches to an organism)

| Lane | Connector | Typical part | ~USD |
|---|---|---|---|
| PIR | J1 | HC-SR501 / AM312 module | 1 |
| Hydrophone | J2 | piezo disc + MAX9814 preamp module | 5–10 |
| Ultrasonic | J3 | MEMS ultrasonic mic breakout | 4 |
| Temp/RH/press | J4 (I2C) | BME280 module (3.3 V) | 2 |
| Light | J5 (I2C) | BH1750 module | 1 |
| C4D | J6 (I2C) | AD7746 breakout | 4 |
| Emit 40 kHz | J10 | piezo T/R pair | 2 |

## E — Backhaul (J7: RX, TX, GND, 5V)

| Option | Part | ~USD |
|---|---|---|
| LoRa RNode | Heltec WiFi LoRa 32 V3 / RNode kit | 8–20 |
| Wi-Fi/UART bridge | any ESP UART→Wi-Fi | 5 |
| Satellite | Swarm M138 modem | 60–150 |

## F — Power (J11)

Recommended: **off-shelf certified power module, not on-board** —
cheaper, safer, already tested. Any of:

| Item | Part | ~USD |
|---|---|---|
| Solar+battery kit | 5 V solar power bank (ruggedized) | 15–25 |
| DIY chain | TP4056 charger module + 18650 + MT3608 boost (set 5.5–6 V out) | 8–15 |
| Mains/site | 5.5–6 V 1 A wall adapter + gland | 5 |

Feed J11 with 5.5–6 V → rail lands ~5 V after the SS14 drop. Reverse
polarity, transients and overcurrent are handled on-board.

## G — Enclosure & mounting

| Item | Spec | ~USD |
|---|---|---|
| Enclosure | IP65+ ABS/polycarbonate box | 5–15 |
| Cable glands | M12/M16 IP68, one per head lead | 1–2 ea |
| Mount | stake / pole clamp / moored-float bracket | 2–10 |
| Conformal coat | acrylic spray — shore/marine units | 5 |

Forms and gland positions: `ENCLOSURE.md`.

## After the parcel arrives — deploy in this order

1. Solder the THT strip (U1A/U1B sockets, headers, J11) — ~10 min.
2. Flash + provision: `PROVISIONING.md` — firmware, device identity,
   consent defaults.
3. Bench checklist (below).
4. Mount enclosure, route heads through glands, attach heads.
5. Commission: power at J11 → LED1 on → frames on uplink → receipts
   in the ledger.

## First-article test plan (before any fleet order)

1. **Bench power-up**: J11 at 5.5 V → LED1 on; +5V at J9 p2 ≈ 5.1 V,
   3V3 at J1 p2 ≈ 3.3 V.
2. **Fault checks**: reversed J11 → no damage; brief rail short → F1
   trips and recovers.
3. **Function**: XIAO flashed → I2S capture → SD spool → frames on
   J7 TX / uplink.
4. **Heads**: each attached head produces readings; cable wiggle →
   no resets.
5. **48-h soak**: closed enclosure, continuous power — temperature
   and dropouts.
6. **Field pilot**: 1–2 nodes through E0 (`tools/e0/score.py`).
7. **Compliance**: ESP32-S3 radio carries FCC/CE on the module;
   assembled product still needs a regional conformity check before
   commercial sale.

## Status honesty

- **Now**: fab-ready v2 — orderable today.
- **After first-article + E0**: pilot-ready.
- **Production**: pilot + compliance + locked suppliers. Not assumed.
