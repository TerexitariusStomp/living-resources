<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# Field node kit — EcoCell One sourcing matrix

With the integrated board, the deployable unit is: **one Seeed PCBA
order + antenna + battery + heads + enclosure**. This file is the buy
list — concrete part numbers wherever a fab or distributor needs one —
plus the first-article test plan.

## A — Seeed Fusion PCBA (the one order)

Upload `gerbers/ecocell-node-gerbers.zip` + `assembly/ecocell-node-bom.csv`
+ `assembly/ecocell-node-cpl.csv`.

### Modules (ask Seeed to source, or consign)

| Ref | Part | Source |
|---|---|---|
| U1 | XIAO ESP32-S3 | Seeed — they make it; ask in quote |
| U5 | EBYTE E22-400M22S (433 MHz) or E22-900M22S (868/915) | EBYTE / distributor |
| U2 | BME280 | Bosch — any distri |
| U3 | BH1750FVI | ROHM |
| U4 | AD7746ARUZ | Analog Devices |
| U6 | TP4056 | generic — "acceptable equivalent" |
| U7 | MT3608 | generic |

### Jellybean SMT (mark "acceptable equivalent")

| Ref | Value | Suggested MPN | Role |
|---|---|---|---|
| R1 | 100 Ω | Yageo RC0805FR-07100RL | emit gate series |
| R2, R8 | 1 kΩ | RC0805FR-071KL | LED1, LED2 |
| R3 | 1.2 kΩ | RC0805FR-071K2L | TP4056 PROG (~1 A charge) |
| R4 | 75 kΩ | RC0805FR-0775KL | MT3608 FB top |
| R5 | 10 kΩ | RC0805FR-0710KL | MT3608 FB bottom |
| R6, R7 | 4.7 kΩ | RC0805FR-074K7L | I2C pull-ups |
| C1–C4 | 100 nF | Samsung CL21B104KBCNNNC | decoupling |
| C5, C6 | 22 µF | CL21A226MQQNNNE | charger/boost bulk |
| L1 | 22 µH ≥1 A | Murata LQH2HPZ220MJR | boost inductor |
| Q1 | 2N7002 | onsemi 2N7002LT1G | emit driver (consent-gated) |
| D1 | 1N4148W | 1N4148W-7-F | emit flyback |
| D2, D7 | SS14 | SS14 / 1N5819 SMA | reverse-polarity + boost diode |
| D3 | SMAJ5.0A | Littelfuse SMAJ5.0A | rail transient clamp |
| D4–D6 | PESD5V0 | Nexperia PESD5V0S1BA | head-signal ESD |
| F1 | 0.75 A | Bourns MF-MSMF075-2 | input polyfuse |
| LED1 | green 0805 | Lite-On LTST-C170GKT | power |
| LED2 | red 0805 | Lite-On LTST-C170KRKT | charge |

### THT (hand-solder ~15 min, or ask Fusion to place)

| Ref | Part |
|---|---|
| J1–J8, J10, J13 | 2.54 mm pin headers (cut from 40-pin strip) |
| J9 | 2.54 mm header — 5V-AUX tap |
| J11 | Phoenix MKDS 1.5/2-5.0 screw terminal |
| J12 | JST B2B-XH-A battery connector |
| J14 | SMA edge-launch jack + 433/868/915 whip antenna |

## B — Antenna (match the E22 band)

| Band | Item |
|---|---|
| 433 MHz | SMA whip, ~17 cm, 2–3 dBi |
| 868/915 | SMA whip, ~8 cm |

## C — Battery (J12 JST-XH)

Any 3.7 V Li-ion/LiPo pack with a 2.54 mm JST-XH lead — 18650 cell +
holder (~$4) or a flat LiPo pouch. TP4056 charges it from the 5V input;
PWR-SEL (J13) chooses rail source: jumper toward J11 = external 5V,
toward J12 = boosted battery.

## D — Sensor heads (per deployment; nothing attaches to an organism)

| Lane | Connector | Typical part | ~USD |
|---|---|---|---|
| PIR | J1 | HC-SR501 / AM312 module | 1 |
| Hydrophone | J2 | piezo disc + MAX9814 preamp module | 5–10 |
| Ultrasonic | J3 | MEMS ultrasonic mic breakout | 4 |
| Extra I2C | J4 | any 3.3 V I2C module — bus is on-board | 1–4 |
| C4D electrodes | J6 | two-pin stainless/carbon electrode pair — **non-contact, near-substrate placement** | 2 |
| Emit 40 kHz | J10 | piezo T/R pair | 2 |

BME280 + BH1750 + AD7746 are already on the board as bare ICs — no
modules needed for those lanes.

## E — Power input (J11)

| Scenario | Item |
|---|---|
| Solar field | 5–6 V solar power bank or panel + buck, feeds J11 |
| Battery only | J12 pack, PWR-SEL set to battery |
| Mains/site | 5.5–6 V 1 A wall adapter + gland |

Feed J11 with 5.5–6 V → rail lands ~5 V after the SS14 drop. Reverse
polarity, transients and overcurrent are handled on-board.

## F — Enclosure & mounting

| Item | Spec | ~USD |
|---|---|---|
| Enclosure | IP65+ ABS/polycarbonate, ≥120×120 mm inside | 5–15 |
| Cable glands | M12/M16 IP68, one per head lead | 1–2 ea |
| Antenna | hole for SMA jack + drip loop | — |
| Mount | stake / pole clamp / moored-float bracket | 2–10 |
| Conformal coat | acrylic spray — shore/marine units | 5 |

Forms and gland positions: `ENCLOSURE.md`.

## After the parcel arrives — deploy in this order

1. Solder THT strip (headers, J11, J12, SMA) — ~15 min.
2. Set PWR-SEL jumper; attach antenna + battery.
3. Flash + provision: `PROVISIONING.md`.
4. Bench checklist (below).
5. Mount enclosure, route heads through glands.
6. Commission: power J11 → LED1 on → LoRa frames on uplink → receipts
   in the ledger.

## First-article test plan (before any fleet order)

1. **Bench power-up**: J11 at 5.5 V → LED1 on; +5V ≈ 5.1 V, 3V3 ≈ 3.3 V.
2. **Fault checks**: reversed J11 → no damage; rail short → F1 trips,
   recovers.
3. **Charge path**: battery on J12, 5 V on J11 → LED2 charge indicator;
   unplug 5 V → boosted rail holds.
4. **Radio**: flashed node → Reticulum announces via E22; edge sees
   frames (see `tools/edge/rns_edge.py`).
5. **Sensors**: BME280/BH1750/AD7746 read over I2C; attached heads
   produce readings; cable wiggle → no resets.
6. **48-h soak**: closed enclosure, continuous power.
7. **Field pilot**: 1–2 nodes through E0 (`tools/e0/score.py`).
8. **Compliance**: ESP32-S3 + E22 modules carry regional certs; the
   assembled product needs a conformity check before commercial sale.

## Status honesty

- **Now**: fab-ready integrated design — DRC 0/0, orderable today.
- **After first-article + E0**: pilot-ready.
- **Production**: pilot + compliance + locked suppliers. Not assumed.
