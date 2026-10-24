# BOM — EcoCell universal node

Prices are rough 2026 spot prices — verify at order time. Every item is
commodity; nothing custom until the v1.5 carrier board.

## Core (on every unit)

| # | Part | Example source | ~$ | Notes |
|---|------|----------------|---:|---|
| 1 | **XIAO ESP32-S3 Sense** | Seeed, Mouser, AliExpress | 14 | MCU + OV2640 camera + onboard PDM mic + microSD slot in one board — the whole multimodal core |
| 2 | microSD card, 16–32 GB | any | 4 | store-and-forward spool |
| 3 | BME280 module (3.3 V) | AliExpress | 2 | temp/humidity/pressure — I2C addr 0x76/0x77 |
| 4 | BH1750 module | AliExpress | 1 | ambient light — I2C 0x23 |
| 5 | PIR sensor (HC-SR501 or AM312 mini) | AliExpress | 1 | wake-on-wildlife; AM312 is smaller/3.3 V-native |
| 6 | Headers + hookup wire + perf/veroboard | any | 2 | XIAO ships with headers unsoldered |
| | **Core subtotal** | | **~24** | |

## Heads (electronics populated on every board)

| # | Head | Parts | ~$ | Lane |
|---|------|-------|---:|---|
| 7 | Hydrophone | piezo disc (27–35 mm) + preamp (MAX9814 module or JFET) | 5–8 | `hydro` — reef/fish/shrimp |
| 8 | Ultrasonic MEMS | ICS-40730 breakout (20–100 kHz) | 4–5 | `ultra` — plant clicks, bats |
| 9 | C4D front-end | AD7746 capacitance eval module + electrode pair (copper tape/rings) | 5 | `c4d` — biofilm readout |
| 10 | Emit transducer | 40 kHz ultrasonic transducer + logic MOSFET (2N7000/AO3400) + resistor | 3 | `emit` — bio-write, consent-gated |
| | **Heads subtotal** | | **~17–21** | |

## Enclosure & power (per deployment)

| Item | ~$ | Notes |
|---|---|---:|---|
| Weatherproof box/jar + cable gland | 3–5 | garden/shore form |
| USB power bank (existing) or 18650 + holder | 0–10 | duty-cycled → weeks |
| Solar panel 2 W + TP4056/CN3791 charge board | 10–15 | permanent deploys |
| Potting epoxy + pressure tube (submerged pod) | 10–15 | reef variant only |
| **Universal node total** | | **~$35–45** typical |

## Deployment kits (add per site)

| Kit | Extra parts | ~$ | Deployment |
|---|---|---:|---|
| Garden | stake/strap mount, rain hood | 2 | garden |
| Shore-dock | dock clamp, 1–2 m hydrophone lead, strain relief | 5 | shore/dock reef |
| Reef float | closed-cell float, deadweight (~2 kg lead/stone), tether line | 10 | near-shore reef |
| Offshore | + SWARM satellite modem OR LTE-M module (SIM7000) | 80–120 | far offshore |
| Range ext. | SX1276 LoRa module ×2 (node + gateway dongle) | 8–10 ea | km-range cells |

## What's NOT in the BOM (by policy)

- No flash/IR illuminator — emitting light is a bio-write, not a
  sense head.
- No soil probes, no attachment hardware — nothing touches an organism.
- No seabed anchor hardware — moorings are deadweight or existing
  structure only.
