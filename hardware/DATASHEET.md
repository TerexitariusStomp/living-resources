# EcoCell — universal living-sensing node (prospective datasheet)

*Product datasheet for procurement/tender submission. Status: v1 target
spec — E0 field validation pending; figures marked † are targets to be
confirmed by test.*

## Summary

EcoCell is an open-hardware passive ecological monitoring node with
bio-write capability under policy. One board carries every sensing
lane — audio, camera, environmental, hydroacoustic, ultrasonic, and
contactless capacitance — plus a consent-gated emit path. Data returns
autonomously over Reticulum mesh (WiFi/LoRa/satellite) with
store-and-forward; every record is content-addressed and attested.

## Sensing

| Lane | Sensor | Coverage |
|---|---|---|
| Audible bioacoustics | onboard PDM mic + INMP441 | 0–24 kHz (48 kHz/16-bit) |
| Camera | OV2640 | phenology, pollinators, wildlife passage |
| Environmental | BME280 + BH1750 | T/RH/P, lux |
| Hydroacoustic | piezo + preamp | 0–24 kHz (core reef band) |
| Ultrasonic | ICS-40730 | 20–100 kHz † |
| Biofilm | AD7746 C4D | contactless capacitance |
| Emit (consent-gated) | 40 kHz transducer | ≤5% duty, hard firmware ceiling |

## Transport & data

- Reticulum-native: WiFi (full lossless FLAC audio), LoRa/RNode
  (detections, km range), LTE-M/satellite (remote), serial (pods)
- Store-and-forward: microSD spool, days-weeks offline tolerance
- Bidirectional: downlink tasking + OTA lane modules
- Every record: timestamp, calibration SAID, gain, node identity,
  content hash; quorum-witnessed receipts at the edge

## Physical

- ~90 g, weatherproof enclosure ~IP65 (land); potted pressure form
  (submerged); moored-float form (offshore)
- Duty-cycled power: weeks on a commodity power bank †; solar option
- No attachment to organisms; no soil insertion; no anchor mooring

## Compliance & licensing

- Radio: ESP32-S3 module carries pre-existing radio cert; product-level
  CE/UKCA EMC test required before commercial supply †
- Firmware/software: AGPL-3.0-or-later; hardware docs: CERN-OHL-S
  (intended)
- Reticulum (custom license — no AI-training use, commercial OK),
  MicroReticulum Apache-2.0 — see `oss-inventory.md`

## Pricing basis

- BOM ≈ $35–45 (hand-built); ~$8–12/unit fabricated carrier at 100+
- Incumbent comparables: AudioMoth ~$100/unit; tender pricing to
  ~£640/unit; Reef Pulse $9,900/site service

## Deployment forms

Garden stake · shore-dock (hydrophone lead) · moored reef float ·
submerged shore-cabled pod. One board serves all four.
