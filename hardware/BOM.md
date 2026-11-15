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

## Water-evidence heads (wet-side probe additions — no respin)

Per the Salton Sea evidence review (`docs/salton-sea/monitoring-fit.md`):
spare ADS8681 channels, the I2C bus, and the penetrator architecture
absorb these as additional wet-side glands. Evidence tier is declared
per head — never sold as more than it is.

| Head | Part | Interface | ~$ | Evidence tier |
|---|---|---|---|---|
| pH | Atlas EZO-pH (or glass electrode → spare ADS8681 AIN) | I2C / AIN | 60 | measured |
| Dissolved O₂ | Atlas EZO-DO | I2C | 70 | measured — fish-kill lane |
| Turbidity | analog nephelometer (DFRobot TSW-class) | spare ADS8681 AIN | 25–40 | measured — TSS/metals *proxy*, corroborates Sentinel-2 screening |
| ORP (optional) | Atlas EZO-ORP | I2C | 60 | measured — redox/Se-speciation context |
| Wind (land nodes) | reed/hall anemometer + vane | pulse/ADC → MCU | 25–45 | measured — dust-source attribution |
| Nutrient ISE (optional trigger) | nitrate/ammonium ISE or EZO-ISE | I2C | 100 | **event-detection only** — flags lab grabs, never an evidentiary concentration |

**Instrument tier (co-located, not node BOM):** submersible wet-chem
nutrient analyzer (Systea WIZ/NPA, or Kekan KK-750-class ~$2,750 —
NH₃/NO₂/NO₃/PO₄, real concentrations, RS-232/485 seam) at top-priority
river-terminus sites. Rent or 1–2 purchases; nodes flank them for
cheap physical context.

**Automated collection (no sensor):** passive SPE/sorbent cassettes —
organics/metals/Se collected in-situ, swapped on the 6-month service
interval, lab elutes + runs the panel. Serial, install/pull dates, and
chain-of-custody ride the record manifest.

**Honest limits (verified 2026-11-15):** no deployable in-situ sensor
for selenium (ICP-MS only) or organics/PFAS/pesticides (fluorescence
"risk index" products are screening-grade); in-situ voltammetric metal
probes read the bioavailable fraction, not DMR-comparable totals.

## What's NOT in the BOM (by policy)

- No flash/IR illuminator — emitting light is a bio-write, not a
  sense head.
- No soil probes, no attachment hardware — nothing touches an organism.
- No seabed anchor hardware — moorings are deadweight or existing
  structure only.
