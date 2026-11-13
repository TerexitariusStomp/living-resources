<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# Harness drawings — ecocell-ocean

Board-side connector pinouts generated from
`electrical/ecocell-ocean.net` (single source of truth). Field-side
wiring uses pre-crimped JST XH leads or soldered pigtails; every run
leaving the enclosure passes a cable gland and gets a service loop.

Wire spec unless noted: 26 AWG stranded, tinned ends for headers,
JST XH crimps for board sockets. Signals to the submerged heads run in
shielded twisted pair where marked **STP**.

## Connector pinouts

| Conn | Type | Pin → net (1-based) | Harness note |
|---|---|---|---|
| J_BAT | JST XH-2 | 1 VBAT · 2 GND | 20 AWG red/black to 18650 holder; 30 mm max |
| J_PWR | JST XH-2 | 1 VIN · 2 GND | 20 AWG to solar/DC input; fuse 1 A inline |
| J_CAM | 1×5 hdr 2.54 | 1 CAM_3V3 · 2 GND · 3 UART3_RX · 4 UART3_TX · 5 CAM_RST | flat ribbon to camera flex; keep <15 cm, shield if longer |
| J_GPS | 1×5 hdr 2.54 | 1 +3V3 · 2 GND · 3 UART2_RX · 4 UART2_TX · 5 PPS | GPS module on float tether head; PPS is the array timing edge — do not daisy-chain |
| J_LORA | 1×6 hdr 2.54 | 1 +3V3 · 2 GND · 3 UART1_RX · 4 UART1_TX · 5 LORA_M0 · 6 LORA_M1 | E22 module plugs direct or on 10 cm ribbon; M0/M1 are mode selects |
| J_DEBUG | 1×4 hdr 2.54 | 1 +3V3 · 2 GND · 3 DEBUG_TX · 4 DEBUG_RX | USB-UART service dongle; not fitted at sea |
| J_PIR | JST XH-3 | 1 +3V3 · 2 GND · 3 PIR_OUT | PIR behind enclosure dome; 20 cm lead |
| J_CTD | JST XH-4 | 1 CTD_S_P · 2 CTD_S_N · 3 CTD_EXC_P · 4 CTD_EXC_N | **STP** to conductivity cell; excite pair twisted together |
| J_HYDRO | JST XH-2 | 1 HYDRO_SIG · 2 GND | **STP** to potted hydrophone puck, 1–2 m; sleeve the piezo lead |
| J_EMIT | JST XH-2 | 1 EMIT_SIG · 2 GND | to emit transducer via Q_EMIT gate; consent-gated lane |
| J_SPK | JST XH-2 | 1 SPK_P · 2 SPK_N | twisted pair to playback transducer, <50 cm |
| J_KILL | JST XH-2 | 1 EN_AMP · 2 GND | amp enable jumper — short to energise playback path |
| J_SD | microSD socket | on-board | card: 2 CS · 3 MOSI · 4 +3V3 · 5 SCK · 6 GND · 7 MISO |

## Float tether (ocean pod link)

Submerged pod to surface float: 4-conductor polyurethane tether,
Kevlar strain member — **not** a data cable; the pod reads locally and
the float carries GPS/antenna/solar. Conductors: +3V3, GND, UART2_RX,
UART2_TX, PPS. Terminate both ends in IP68 glands; pot the pod-side
penetrator per `ENCLOSURE.md` Form C.

## Harness checks (production)

1. Continuity pin-for-pin against this table — a swapped XH pair is a
   dead head, not a software bug.
2. Hipot/insulation check on the tether at 2× working voltage.
3. Log harness serial + wire lengths in `UNIT-TRAVELER.md` for each unit.
