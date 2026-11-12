# PINOUT — EcoCell universal node

XIAO ESP32-S3 Sense exposes 11 pins on the expansion headers (D0–D10).
Onboard camera, PDM mic, and SD slot are internal — they occupy their
own pins and are **not** on this map. The map below uses only free
header pins.

⚠ **Verify against your board revision's schematic** — Seeed has
revised the Sense expansion board; the free-pin set below is the
published D0–D10 map. If a head conflicts, reassign in firmware
(`firmware/node/main.py` pin constants) — the software is built for it.

## The pin map

| XIAO pin | GPIO | Function | Head | Notes |
|---|---|---|---|---|
| **D0** | GPIO1 | **PIR wake** | AM312/HC-SR501 OUT | RTC-capable — wakes the MCU from deep sleep |
| **D1** | GPIO2 | **ADC1_CH1** | hydrophone preamp out | analog in, hydro lane |
| **D2** | GPIO3 | **ADC1_CH2** | ICS-40730 ultrasonic out | analog in, ultra lane (see caveat) |
| **D3** | GPIO4 | **PWM / LEDC** | emit transducer MOSFET gate | consent-gated emit lane |
| **D4** | GPIO5 | **I2C SDA** | BME280 + BH1750 + AD7746 | shared bus |
| **D5** | GPIO6 | **I2C SCL** | same | shared bus |
| **D6** | GPIO43 | **UART TX** | LoRa RNode / sat modem / serial gateway | backhaul |
| **D7** | GPIO44 | **UART RX** | same | backhaul |
| **D8** | GPIO7 | **SPI SCK** | spare/expansion | second SD, GPS, display |
| **D9** | GPIO9 | **SPI MISO** | spare | |
| **D10** | GPIO10 | **SPI MOSI** | spare | |
| 3V3 | — | power | all head VCC | heads are 3.3 V parts |
| GND | — | ground | all heads | common |

## I2C bus (D4/D5)

| Device | Address | Lane |
|---|---|---|
| BME280 | 0x76 | `env` — temp/humidity/pressure |
| BH1750 | 0x23 | `env` — light |
| AD7746 (C4D) | 0x48 | `c4d` — capacitance → biofilm waves |

All three share one bus — no address conflicts.

## Head wiring notes

**Hydrophone:** piezo disc → 1 MΩ bias resistor → preamp (MAX9814 module
or JFET 2N5459) → D1. Preamp gain set for the quiet band — reef work
wants the shrimp crackle band ~2–15 kHz.

**Ultrasonic (ICS-40730):** analog out → D2. ⚠ Caveat: its 20–100 kHz
band exceeds comfortable ESP32 ADC sampling; plan the firmware capture
path (decimated alias sampling or the C++/ESP-IDF firmware variant) —
the head and pin are correct either way.

**Emit transducer:** 40 kHz transducer across 3V3↔MOSFET drain, MOSFET
gate ← D3 via ~100 Ω, source → GND. Firmware ceilings are hard-coded
(`EmitLane.MAX_ON_MS = 50`, `MIN_OFF_MS = 950`) — the *software* caps
duty at 5%; hardware adds no cap of its own.

**PIR:** OUT → D0. Module set to repeatable trigger, shortest delay —
it's a wake source, not a recording sensor.

**UART heads:** LoRa RNode (SX1276 flashed with RNode firmware) or
LTE-M/satellite modem — TX/RX cross-wired, shared GND, 3.3 V logic.

## Second microphone (optional stereo)

The onboard PDM mic is the primary air mic. If a second INMP441 is
added for stereo/direction: wire it to the **same I2S bus as the
onboard mic with L/R tied opposite** — check the expansion schematic
for the onboard mic's I2S pins and mirror them; do not allocate new
header pins.

## Ocean heads — the map above is the terrestrial baseline

The ocean-capable unit adds hardware the current carrier does not
route: an external high-rate SPI ADC + anti-alias front-end for the
hydrophone, an inductive CTD interface, an underwater camera head with
gated illumination, a GPS/PPS path, a playback DAC/amp/projector chain,
and solar/battery power-gating rails. Those additions exceed the free
D0–D10 map on this XIAO revision — the ocean board is a respin, not a
jumper change. The controlled pin map for the ocean release lives in
`hardware/release/`; do not reuse this table for an ocean build.

## Environmental heads (Salton Sea build)

| Head | Connects to | Notes |
|---|---|---|
| **SPS30 PM** | I2C bus D4/D5, addr 0x69; **5 V power via J9** | shares bus with BME280/BH1750/AD7746 — no address conflict; verify 3.3 V I2C level tolerance (docs/ENV-HEADS.md) |
| **H2S (MQ-136 / SPEC)** | **D10 (GPIO10, ADC1_CH9)** analog, or UART for electrochemical | MQ-136 0–4 V out needs ~2:1 divider to ≤3.1 V; conflicts only if SPI expansion (D8–D10) is populated — remap to D8/D9 then |
| **LoRa radio (v1)** | **D6/D7 UART** — E32-900T20D/SX1276 | conflict-free; µReticulum `e32.py` drives it (docs/RNODE-MESH.md) |
| LoRa (integrated PCB) | SPI bus D8–D10 + CS/BUSY/DIO1/RESET | needs 4 control GPIOs we don't have spare on this pin map — respin decision pending |
