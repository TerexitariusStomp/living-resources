# EcoCell Ocean — Production Test & Calibration Plan

Run order per serialized unit. Record every result on the unit traveler
(`UNIT-TRAVELER.md`); a unit that fails any step is quarantined, not
reworked past two attempts.

## 1. Incoming inspection

- Visual: soldermask, silkscreen, hole registration vs fab drawing.
- Continuity: 100% netlist compare (flying-probe or ICT fixture) against
  `electrical/ecocell-ocean.net` — no opens, no shorts.
- Unpowered impedance: VIN–GND ≥ 1 kΩ; +3V3–GND ≥ 200 Ω; VBAT–GND ≥ 100 Ω.

## 2. Bring-up

1. Feed VIN at 4.2 V limited to 50 mA. Expect < 20 mA quiescent before
   firmware load; a higher draw means stop and inspect.
2. Program `firmware/node/main.py` image; record image SHA-256 on the
   traveler.
3. Verify boot: serial banner, RTC/PPS lock, watchdog armed.

## 3. Functional test

| Test | Stimulus | Pass criterion |
|---|---|---|
| GPS/PPS | sky or simulator | PPS lock ≤ 120 s, NMEA sane |
| I2C bus | — | BME280 + expander respond at expected addresses |
| Light (BH1750/LDR) | covered/uncovered | lux delta > 10× |
| PM (SPS30) | ambient | pm2_5 in sane range, CRC clean |
| Air mic (I2S) | 1 kHz tone @ SPL ref | recorded level within ±3 dB of fixture ref |
| Hydrophone front end | bench transducer | AFE output present, gain step measurable |
| Ultrasonic emit | scope on EMIT_SIG | 40 kHz burst present ONLY with consent token; absent without (`ConsentRequired` path verified) |
| SD spool | — | AUD1 frames persist, ack-before-delete honored |
| LoRa uplink | fixture gateway | DET1 frame received, RSSI logged |
| Power gating | toggle EN_* rails | each peripheral rail switches and comes back; no required capability silently lost |

## 4. Calibration (per unit, stored on traveler)

- Battery divider: measure VBAT vs reported, store correction.
- Hydrophone channel gain: record AFE gain code used at fixture level.
- Mic SPL offset: store dB offset at 1 kHz ref.

## 5. Environmental (per serialized batch, sampled)

- Thermal soak −10…+50 °C: boot + uplink pass at endpoints.
- Pressure hull leak test: per mechanical spec — **spec not yet
  released; this step is blocked until the pressure spec lands.**

## 6. Emission duty audit

With a consent token present, drive the emit lane for 60 s and confirm
from the log that on-time never exceeds the declared duty cap and every
emission produced a receipt entry. Without a token, confirm refusal is
logged.
