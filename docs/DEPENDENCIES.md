<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# Dependencies — the adopted OSS behind every capability

Rule 3 of the commons: before a module is written, name the OSS that
covers it. Custom code stays under 5% — adapters are thin seams that
parse and delegate, never classify. Copyleft is acceptable.

| capability | adopted OSS / API | license | status |
|---|---|---|---|
| seismograph reads (Raspberry Shake) | ObsPy | LGPL | adapter seam shipped; edge binding pending |
| iNaturalist reads | pyinaturalist | MIT | seam shipped; binding pending |
| GBIF bulk (research-grade iNat) | pygbif | BSD | seam shipped; binding pending |
| river gauges (USGS/EA) | dataretrieval | CC0 | seam shipped; binding pending |
| ocean floats + ERDDAP sources (Argo, CDIP, IOOS) | erddapy | BSD | seam shipped; binding pending |
| eBird reads | ebird-api | MIT | seam shipped; needs free Cornell key |
| PurpleAir reads | pypurpleair | — | seam shipped; needs free key |
| Motus telemetry | motus API | — | seam shipped; registration required |
| Sensor.Community / BirdWeather / Safecast / MetWOW reads | plain REST/GraphQL | — | seam shipped; public endpoints verified |
| FarmBot writes (demo + opt-in) | farmbot-py | MIT | seam shipped; demo account is open-invitation |
| Husqvarna Automower/Gardena writes | husqvarna-automower | MIT | seam shipped; owner OAuth required |
| OpenSprinkler / reef-pi / Tasmota writes | plain REST | — | seam shipped; owner-token only |
| LoRaWAN uplink/downlink (TTN, Helium) | paho-mqtt | EPL | seam shipped; app credentials bind per deployment |
| node-side LoRaWAN | MCCI arduino-lmic / uLoRaWAN-class | mixed (copyleft ok) | TtnLane shipped; radio object injected |
| mesh/off-grid backhaul | meshtastic, aprslib, RNode/Reticulum | GPLv3 / mixed | documented; Reticulum seam exists |
| on-device browser inference | TensorFlow.js + YAMNet | Apache / CC-BY | WebNode ships energy-gate; models pending — BirdNET-TFLite model terms to verify before bundling |
| KERI/SAID signing | keripy | Apache | guardian-verify seam; binds when SAD signing lands |
| Scheme-side HTTP | Guile `(web client)` | LGPL | stdlib — the default binding for fetch seams |

## The honesty rule for this table

A seam with an unbound fetch parameter answers `'no-source` — it never
invents data. `live-now` in the federation catalogue means the upstream
endpoint was verified public and working; `key-required` and
`gated-partnership` mean the code is ready but the credential or the
relationship is not.
