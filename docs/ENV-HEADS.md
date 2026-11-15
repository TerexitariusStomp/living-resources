<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# ENV-HEADS.md — Salton Sea environmental heads

Per-head wiring, siting, and evidence-grade notes for the sensor lanes
beyond the core env trio (BME280/BH1750/PIR). Every head is optional
hardware — absent or faulted heads yield nothing, never invented
values. Conversion/calibration happens at the edge; node readings ship
raw or first-unit fields.

## PM — SPS30

| Lane | `pm` — evidence-gated, same class as `env` |

**I2C level caveat (verify before committing):** the SPS30 runs on 5 V
and its module pull-ups reference VDD. The ESP32-S3's I2C pins are
3.3 V — powering the sensor at 5 V while pulling SDA/SCL to 3.3 V is
the standard field workaround and generally works, but confirm against
the datasheet/rev at order time. If it doesn't, a $1 BSS138 level-
shifter on SDA/SCL is the fallback. Do **not** pull the bus to 5 V —
that kills the XIAO.

**Placement:** connector J4 ("any 3.3 V I2C module") — repurpose as the
dedicated PM head; keep one J4 channel free for expansion by moving
SPS30 to a two-channel I2C mux only if a second I2C head appears.
Siting rule stays: nothing in the airstream disturbance of the sampler
intake — offset ≥ 0.5 m, same height band.

## H2S — two honest options

| Lane | `h2s` — indicative screening, not compliance grade |

MQ-136 analog module on GPIO10 (ADC1_CH9) or a SPEC electrochemical on
UART. Node ships `raw`/`mv`; ppm conversion + temperature compensation
is the edge's job with the head's calibration sheet. Lagoon-adjacent
siting per Centeno 2025 exposure pathways — downwind of the playa.

## Water-chemistry EZO heads (pH / ORP / DO)

| Lanes | `ph` 0x63 · `orp` 0x62 · `do` 0x61 — measured grade |

Atlas EZO carrier circuits on the shared I2C bus (SDA GPIO5, SCL
GPIO6, 100 kHz) with lab-grade wet probes. Firmware sends `R`, waits
1 s, reads status byte + ASCII; first CSV field only — temperature
compensation uses the edge's reading of the node's own water temp
channel. Calibration (2-point pH, zero/saturated DO, ORP quinhydrone)
is a **service-interval bench procedure**, logged per probe serial in
the unit traveler — never field-fudged. These are the measured-grade
parameters; everything below is a proxy or screening lane.

## Turbidity

| Lane | `turb` — proxy grade |

Analog IR nephelometer on GPIO7 (ADC1_CH6, XIAO D8 — free-pool pin).
Node ships `raw`/`mv`; edge converts to NTU with the
head's curve. Wipers/fouling drift dominate over weeks — readings are
storm-load *event* evidence, not a calibrated TSS record.

## Wind

| Lane | `wind` — indicative grade |

Cup/reed-switch anemometer on GPIO8 (XIAO D9 — free-pool pin, digital
input + pull-up). Firmware counts closures over a 5 s sample per env poll —
duty-cycled, so this is *characteristic* wind at poll time, not a
continuous gust record. Edge converts delta-Hz to m/s with the head's
calibration constant. Required for dust-source attribution paired with
`pm` — a PM event only indicts the upwind fetch if `wind` says it
blew that way.

## Honest limits — what is NOT onboard

Nutrients (nitrate/phosphate/ammonia), trace metals, selenium,
pesticides/organics: no node-cost in-situ sensor exists or is
evidence-grade. These lanes are automated **collection** (SPE cassettes,
swapped on the service interval) plus optional co-located instrument-tier
analyzers (RS-232/485 seam) — never dressed as node measurements.
See `hardware/BOM.md` water-evidence section and
`docs/salton-sea/monitoring-fit.md` for the full tier table.
