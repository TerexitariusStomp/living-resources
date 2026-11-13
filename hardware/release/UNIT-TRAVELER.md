# EcoCell Ocean — Unit Traveler

One traveler per serialized unit travels with the hardware through
assembly, test, and deployment. Nothing ships without it.

## Identity

| Field | Value |
|---|---|
| Unit serial | `ECO-____-____` |
| Board rev / PCB date code | |
| BOM revision | |
| Firmware image SHA-256 | |
| Radio variant (433 / 868 / 915 MHz) | |
| Enclosure revision | |
| Deployment role flags | |

## Build record

| Date | Station | Operator | Operation | Notes |
|---|---|---|---|---|
| | fab | | bare board received, incoming inspection | |
| | SMT | | top-side population | |
| | SMT | | bottom-side population | |
| | assy | | connectors, THT, harness | |
| | flash | | firmware image + provisioning | |
| | seal | | pressure hull + potting | |

## Test results (from TEST-PLAN)

| Test | Result | Date | Operator |
|---|---|---|---|
| Incoming continuity | | | |
| Unpowered impedance | | | |
| Bring-up quiescent | | | |
| GPS/PPS lock | | | |
| I2C bus | | | |
| Light | | | |
| PM (SPS30) | | | |
| Air mic | | | |
| Hydrophone AFE | | | |
| Emit (with consent) | | | |
| Emit refusal (no token) | | | |
| SD spool / ack-delete | | | |
| LoRa uplink | | | |
| Power gating | | | |
| Emission duty audit | | | |

## Calibration values

| Channel | Correction stored | Date |
|---|---|---|
| Battery divider | | |
| Hydrophone gain | | |
| Mic SPL offset | | |

## Deployment record

| Field | Value |
|---|---|
| Site | |
| Coordinates | |
| Guardian of record | |
| Consent token id (if emit enabled) | |
| Date deployed / recovered | |
| Condition on recovery | |
