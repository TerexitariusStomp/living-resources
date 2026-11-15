<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# BOM lifecycle check — 2026-11 (spot review, both boards)

Checked the risk-bearing line items against distributor/manufacturer
status. **Two real EOL findings** — the acoustic lanes are the exposure.

## ❌ Blocking: TDK InvenSense mic EOL (PCN-000772, issued 2026-01-15)

| Lane | Part | Status |
|---|---|---|
| Air mic (ocean board `U_MIC`) | ICS-43434 | **EOL** — LTB 2026-06-15 (NCNR), last ship 2027-01-15; ~53k stock at DigiKey today |
| Ultrasonic (`U_US` head spec) | ICS-40730 | **EOL** — same PCN |
| Land-node external mic | INMP441 module | legacy/EOL for years; survives on clone modules |

TDK's named alternates — **T5837 / T5838 / T5848** (MMICT583x) — are
PDM-output, not I2S. Consequences, in order of preference:

1. **LTB stock buy** for the prototype+pilot fleet: ~few hundred pcs of
   ICS-43434 + ICS-40730 covers all planned builds through 2027. Cheap
   ($1–3/ea), no design change. NCNR window closes 2026-06-15.
2. **Next board rev**: move both acoustic lanes to the T583x family —
   requires a PDM front end (the ESP32-S3 has a native PDM-capable I2S
   peripheral; footprint changes, 1.8 V rail or level handling). The
   XIAO land node already uses its onboard PDM mic successfully, so the
   firmware seam exists (`main.py` PDM path) — the node board's change
   is smaller than it looks.
3. Do nothing → lane dies with stock. Not a plan.

## ⚠ Watch

| Part | Status | Action |
|---|---|---|
| BME280 (land `U2`, ocean `U_ENV`) | Active, but chronically supply-fragile since 2021 | keep alternate: BME688 (drop-in bus-compatible, adds gas) — note on BOM |
| BMP390 (`U_PRES`) | Active; 16-week standard lead | order early in any build window; no design action |
| ESP32-S3-WROOM-1 | Active | — |
| XIAO ESP32-S3 | Active | consignment path already planned |

## ✅ Clear (checked)

ADS1220, ADS8681, OPA333, PCM5102A, TCA9535DBT, TPS27081A, AMS1117,
TP4056, MT3608, 2N7002, AD7746, GL5528 — all mainstream-active at
distributor of record; no PTN/EOL found.

## What this check did NOT cover (still gating)

- Full quote-backed BOM: pricing/MOQ/lead-time per line from the
  assembler's sourcing desk — needed before a production PO.
- Second-source mapping for connectors/crystals/passives.
