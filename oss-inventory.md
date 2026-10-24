# OSS inventory — adopted dependencies

License policy: commercially usable open source; copyleft acceptable where
compatible with our AGPL-3.0-or-later distribution. ⚠ = verify before the
use listed.

| Dependency | License | Role | Status |
|---|---|---|---|
| OpenSoundscape | MIT | edge bioacoustic ML | ✅ OK |
| BirdNET-Analyzer | custom — free non-commercial | species classifier | ⚠ verify commercial terms; else train on xeno-canto CC |
| xeno-canto data | CC (per-recording, varies) | training/reference audio | ⚠ per-recording terms |
| Reticulum / LXMF | **Reticulum License (custom)** | field transport | ⚠ verified: MIT-like + two restrictions — **no AI/ML training-dataset use** (our detection traffic passes through, never retained for training — documented in adapters/reticulum.scm) and no harm-to-humans systems. Commercial use OK; custom license, review before shipping |
| MicroReticulum | Apache-2.0 | Reticulum on ESP32 | ✅ verified — **but C++/PlatformIO, not MicroPython**: full RNS binding means an ESP-IDF/C++ firmware variant; MicroPython path runs the DET1/AUD1 frame contract without full RNS |
| RNode firmware | GPL-3.0 | LoRa interface | ✅ acceptable for firmware image |
| MicroPython | MIT | node firmware runtime | ✅ OK |
| ESP-IDF | Apache-2.0 | base SDK under MicroPython | ✅ OK |
| SciPy | BSD-3 | edge DSP | ✅ OK |
| SoX | GPL-2.0 | audio tooling | ⚠ copyleft — tooling only, not linked |
| Open-Meteo | AGPL-3.0 (code), CC-BY-4.0 (data) | weather/env context | ✅ verified — same-family license; data attribution required |
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
