# OSS inventory — adopted dependencies

License policy: commercially usable open source; copyleft acceptable where
compatible with our AGPL-3.0-or-later distribution. ⚠ = verify before the
use listed.

| Dependency | License | Role | Status |
|---|---|---|---|
| OpenSoundscape | MIT | edge bioacoustic ML | ✅ OK |
| BirdNET-Analyzer | custom — free non-commercial | species classifier | ⚠ verify commercial terms; else train on xeno-canto CC |
| xeno-canto data | CC (per-recording, varies) | training/reference audio | ⚠ per-recording terms |
| Reticulum / LXMF | MIT | field transport | ⚠ verify |
| MicroReticulum | MIT | Reticulum on ESP32 | ⚠ verify |
| RNode firmware | GPL-3.0 | LoRa interface | ⚠ copyleft — acceptable for firmware image |
| MicroPython | MIT | node firmware runtime | ✅ OK |
| ESP-IDF | Apache-2.0 | base SDK under MicroPython | ✅ OK |
| SciPy | BSD-3 | edge DSP | ✅ OK |
| SoX | GPL-2.0 | audio tooling | ⚠ copyleft — tooling only, not linked |
| Open-Meteo | AGPL-3.0 | weather/env context | ⚠ same-license as us; verify API ToS |
| mosquitto | EPL-2.0/EDL | edge message bus (optional) | ✅ OK |
| SQLite | public domain | detection ledger | ✅ OK |
| Temporal | MIT | workflow edge (optional) | ✅ OK |
| OPA | Apache-2.0 | policy engine (lane-gate, consent) | ✅ OK |
| hREA / ValueFlows | Apache-2.0 | accounting vocabulary | ✅ OK |
| helia | Apache-2.0/MIT | content-addressed evidence store | ✅ OK |

## Adoption rule

First-party code (module/, adapters/, firmware/, deploy/, tests/) stays
under the `CUSTOM_BUDGET` line-count in the Makefile; `make
check-custom-budget` enforces. Detection/ML is never reimplemented —
adapters parse, they never classify.
