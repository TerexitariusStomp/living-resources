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
| µReticulum (`varna9000/micropython-reticulum`) | MIT | single-MCU RNS/LXMF on the node — vendored `third_party/uret/` + C-accel `.mpy` crypto | ✅ verified MIT; wire-compatible RNS/LXMF, ESP32-S3 tested (XIAO+Wio-SX1262). **Supersedes the frame-contract-only MicroPython path for mesh nodes** — see `docs/RNODE-MESH.md`. Inherits Reticulum License terms (no AI-training retention — same posture as `adapters/reticulum.scm`) |
| robert-hh/BME280 `bme280_float.py` | MIT-style (header) | BME280 temp/RH/pressure compensation on the node — vendored `third_party/bme280/` | ✅ verified; Bosch datasheet-derived, derived from Adafruit (MIT). Float variant — env readings are 1-per-window |
| EBYTE E32-900T20D | hardware module | 915 MHz UART LoRa for µReticulum `e32.py` interface | ✅ commodity; ~12–15 USD |
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
| ESP-ADF (Espressif Audio Dev Framework) | Espressif MIT | playback pipeline — WAV decode, I2S, amp control | ⚠ verify branch/version; commercial OK on Espressif parts |
| ESP-IDF `adc_continuous` DMA | Apache-2.0 (via ESP-IDF) | high-rate hydrophone baseline capture | ✅ OK — external SPI ADC is the primary path for useful band |
| OpenCTD (Rev 8 schematic/firmware) | MIT | CTD sensor stack + calibration protocol | ✅ adopted as reference, not forked |
| Atlas EZO-EC (vendor example) | vendor (verify) | conductivity command wrapper | ⚠ verify license at selection |
| `bluerobotics/ms5837-python` | MIT | pressure/depth (MS5837-30BA) | ✅ OK |
| MicroPython `onewire`/`ds18x20` | MIT (MicroPython) | water temperature (DS18B20) | ✅ OK |
| Adafruit `CircuitPython_MAX31865` | MIT | PT1000 path (if adopted) | ⚠ MicroPython shim only |
| `micropyGPS` / NMEA parser | MIT | GPS parse; PPS interrupt timestamping is custom glue | ✅ OK |
| esp32-camera / OV5640 driver | Apache-2.0/MIT (verify) | underwater camera head | ⚠ verify license at selection |
| libFLAC (ESP-ADF component) | Xiph BSD | audio compression for hydro payloads | ✅ OK |
| NumPy/SciPy | BSD-3 | edge DSP, particle-motion estimate, TDOA math | ✅ OK |
| FishSounds / Watkins-MBARI / xeno-canto aquatic | CC per-recording | playback source assets | ⚠ per-recording terms; manifest records license + checksum |

## Adoption rule

First-party code (module/, adapters/, firmware/, deploy/, tests/) stays
under the `CUSTOM_BUDGET` line-count in the Makefile; `make
check-custom-budget` enforces. Detection/ML is never reimplemented —
adapters parse, they never classify.
