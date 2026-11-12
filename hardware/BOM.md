# BOM — EcoCell universal node

Prices are rough 2026 spot prices — verify at order time. Every item is
commodity. For a manufactured run, `pcb/assembly/` has the Seeed BOMs
and `FIELD-KIT.md` is the complete sourcing matrix — use those two.
**EcoCell One** (`ecocell-node.kicad_pcb`) reflows the XIAO, E22 LoRa
module and the BME280/BH1750/AD7746 as bare ICs onto one board — the
integrated path supersedes the module/perfboard build below, which
stays the hand-build/prototype list.

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
| 9b | **PM2.5** | Sensirion SPS30 (I2C 0x69, 5 V via J9) | ~40 | `pm` — dust events; see `docs/ENV-HEADS.md` |
| 9c | H2S (optional) | SPEC 3SP_H2S_A4 electrochemical **or** MQ-136 + divider | 4–90 | `h2s` — indicative grade only; defer unless requested |
| 10 | Emit transducer | 40 kHz ultrasonic transducer + logic MOSFET (2N7000/AO3400) + resistor | 3 | `emit` — bio-write, consent-gated |
| | **Heads subtotal** | | **~17–21** (+~44 with PM, +H2S option) | |

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
| Range ext. | **E32-900T20D UART LoRa module** (µReticulum-native, D6/D7) | ~12–15 | km-range cells — single-MCU mesh, no companion board (`docs/RNODE-MESH.md`) |
| Range ext. (alt) | Wio-SX1262 SPI stack or SX1276 module ×2 | 15–25 ea | SPI path needs pin remap — see `docs/RNODE-MESH.md` pin budget |

## What's NOT in the BOM (by policy)

- No flash/IR illuminator — emitting light is a bio-write, not a
  sense head.
- No soil probes, no attachment hardware — nothing touches an organism.
- No seabed anchor hardware — moorings are deadweight or existing
  structure only.
