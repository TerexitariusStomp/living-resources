<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# RNODE-MESH — single-MCU LoRa mesh for the EcoCell node

Status: **implemented, awaiting hardware validation** — the node-side
µReticulum client and central durable-receipt edge are built. This doc is
the design of record for mesh hops without a companion board.

## The decision: one MCU, not two

A companion RNode per node doubles radio cost and adds a second firmware
to flash, provision and debug. Rejected. Instead the **same XIAO
ESP32-S3 that runs `firmware/node/main.py` also runs the Reticulum
stack** — via [µReticulum](https://github.com/varna9000/micropython-reticulum),
a pure-MicroPython, wire-compatible RNS/LXMF port (MIT license — clean
to vendor into this AGPL tree). Mesh hops, store-and-forward, path
discovery and duty-cycled retransmission are then handled *inside* the
transport layer, exactly as `spec/living-resources.md` §3 T3 intends —
no app-layer relay code needed on the node.

µReticulum is explicitly tested against the **Seeed XIAO ESP32-S3 +
Wio-SX1262** combination and ships C-accelerated crypto modules
(`ed25519_fast_xtensawin.mpy`, `bz2_fast_xtensawin.mpy`) for the S3's
Xtensa core. ESP32-S3 has 8 MB flash / 512 kB SRAM + 8 MB PSRAM — the
stack fits alongside our capture/spool code.

## Radio choices (pick per build)

| Radio | Bus | µReticulum support | ~$ | Verdict |
|---|---|---|---:|---|
| **E32-900T20D/SX1276** | UART | native `interfaces/e32.py` (transparent serial, M0/M1 config) | 12–15 | **Recommended for hand-builds** — rides free pins D6/D7, zero conflicts |
| Wio-SX1262 stack | SPI | native `interfaces/lora.py` + `lora_boards.py` has `xiao_esp32s3_sx1262` | 15–20 | Works, but see pin-conflict warning below |
| E22-900M22S (on integrated PCB) | UART | **no driver** — E22 ≠ E32 command set | (on board) | Needs an `e22.py` port or a respin to E22-900M30S (SPI) |
| E22-900M30S (SPI variant) | SPI | needs `lora.py` board entry — same SX1262 core | — | Cleanest integrated-PCB path if respinning |

### Pin budget — read before wiring LoRa

EcoCell already spends the XIAO header (`hardware/PINOUT.md`):

- **D6/D7 (GPIO43/44)** — free UART → **E32 module lands here.** This is
  the conflict-free choice.
- **D8–D10 (GPIO7/9/10)** — SPI bus, marked "spare/expansion". The
  µReticulum XIAO board def uses SCK=7, MOSI=9, MISO=8 — note GPIO8 is
  **not on our D-pin map** and GPIO10-vs-9 MOSI/MISO ordering differs;
  verify against the XIAO schematic before committing.
- **Wio-SX1262 kit variant** wants CS=41, BUSY=40, DIO1=39, RESET=42 —
  on ESP32-S3 those are internal flash/PSRAM-adjacent pins, likely
  unavailable on the XIAO header. The **header variant** wants
  CS=5, BUSY=4, DIO1=2, RESET=3 — GPIO2/3/4/5 collide with our
  hydro/ultra/emit/I2C heads. Either way the stock pinout does **not**
  fit the universal node; control lines must be remapped to free pins
  (D6/D7 UART can't carry SPI — a remap needs ≥4 free GPIOs we don't
  currently have spare).

**Consequence:** for v1 mesh nodes, spec the **E32 UART module on D6/D7**.
It is transparent-serial, needs only TX/RX/GND plus M0/M1 mode straps,
and µReticulum configures it over the same UART. Reserve the SPI bus
for the integrated-PCB respin (E22-900M30S or pin-remapped SX1262).

## The uplink path (what changes in firmware)

```
[node main.py]                    [µReticulum urns/]
 capture → SD spool → flush ──▶  LXMessage(dest=edge_hash,
                                    content=RES1/DET1/ENV1/GAP1/AUC1)
                      ...[4504 chars truncated]...Mesh behavior & duty cycle (honest notes)
     ...[3350 chars truncated]...retries on





















































### Central WiFi audio receipt

`tools/edge/udp_edge.py` is the central WiFi ingest service. Firmware
splits each `.pcm` into `AUD1` datagrams:

```text
AUD1 | name-len u8 | name | idx u16be | total u16be | sha256(blob) |
payload≤1200 B
```

The edge durably records every received index under `incoming/`,
reassembles the item, verifies the embedded SHA-256, commits the PCM by
content hash under `committed/`, fsyncs ledger + receipt, and returns a
`TSK1` JSON ACK `{ "op":"ack","name":…,"sha":… }`. The node compares
that SHA to the local PCM and only then deletes the spool file. A lost
ACK is safe: retransmitted chunks receive the same durable ACK.

### Central annotation

After ingest, `tools/edge/classify.py` watches the ingest's `committed/`
directory — `.pcm` is wrapped as 48 kHz WAV, while `AUC1` commits already
contain a decoded 8 kHz `.wav` beside the source `.auc` (the WAV is the
canonical input; the `.auc` is provenance and is not double-classified).
Run it beside `udp_edge.py`/`rns_edge.py`:

```sh
PYTHONPATH=tools/edge python3 tools/edge/classify.py \
  --spool .edge_ingest/committed \
  --out detections.jsonl --review-out review.jsonl \
  --backend birdnet --lat 33.35 --lon -115.72 --habitat playa
```

BirdNET-Analyzer supplies species labels plus optional lat/lon/week
filtering; an OpenSoundscape model file is used with
`--backend opensoundscape --opso-model <path>` for broader sound classes.
Raw acoustic scores and context-adjusted scores are recorded separately —
context never silently becomes the detection. Scores below `--threshold`,
backend failures and unsupported audio emit `needs_review` records to the
review queue with model/version/provenance, never an invented species.

### Identity & provisioning

- Node identity: µReticulum provisions an RNS identity per device —
  generate on first boot, persist to flash/SD; record the node's
  Reticulum **destination hash** in the cell registry (replaces the
  plaintext `NODE_ID` for transport; keep `NODE_ID` inside the JSON for
  ledger readability).
- Edge: `rns_edge.py --identity .edge_id` announces `ecocell-edge` every
  60 s. Nodes learn the edge's **LXMF destination hash** from a config
  block on SD (`/sd/lxmf.json`: `{"edge_dest": "<hex>", "iface": "lora"}`)
  — written at provisioning time (`PROVISIONING.md` gains a step).
- Downlinks: admitted `TSK1`/`LANE` intents arrive as LXMF messages to
  the node's own destination; `poll_task()` decodes `content` as the
  same JSON `handle_task` already consumes. Consent tokens still gate
  `emit`/`store`/`lane-install` — transport adds no authority.

## Mesh behavior & duty cycle (honest notes)

- **Hops are automatic** — RNS path discovery + store-and-forward mean a
  shore node 15 km from the edge relays through any intermediate RNS
  node (another EcoCell, a fixed gateway, an RNode on a mast). We do not
  implement relay ourselves; the `relay` lane in the gate vocabulary is
  for *content-addressed bundle forwarding at the edge*, a different
  thing.
- **Sleep vs. reachability:** our `WAKE_WINDOWS` deep-sleep the ESP32.
  During sleep the node is off-mesh — uplinks spool, LXMF retries on
  wake, downlinks wait in the mesh's store. For the Salton Sea
  deployment this is acceptable (detections are delay-tolerant);
  consent-gated writes already tolerate scheduling. Do **not** promise
  real-time downlink tasking to sleeping nodes.
- **Antenna:** 915 MHz quarter-wave whip (~8 cm) through a gland;
  elevation beats transmit power in flat desert. Gateway/edge placement
  on the playa's west rise gives LOS to the whole north shore.
- **Range budget (915 MHz, SF7–SF10, desert LOS):** ~1–5 km reliable per
  hop at node TX power; multi-hop extends to ~15–30 km with 2–3
   contract seam. Untested on hardware — E0 owns that.
3. E32 wiring on D6/D7 (TXD→GPIO44, RXD→GPIO43; M0/M1 strapped or
   jumpered to D8/D9; AUX optional) + antenna — **field task**.
   ⚠ If M0/M1 are GPIO-driven rather than strapped, check
   `urns/interfaces/e32.py`'s GPIO drive-strength poke
   (`machine.mem32[0x4001C000 + ...]`) — that base address is not the
   ESP32-S3 GPIO register range (0x60004000); strap M0/M1 on the module
   or fix the address at bring-up. Strapping is the default.
**Continuous is the default:** the node reads, writes and mesh-polls
24/7 including night — the battery carries dark hours, solar refills by
day. `wake_windows` in `/sd/lxmf.json` (or a downlink `windows` task)
opts a power-limited site down to scheduled windows; leaf nodes then
lightsleep between them (CPU ~mA, RAM/RNS state survives). **Relay nodes
(`"transport": true`) must stay awake regardless** — an asleep relay
is a broken hop; give them `"wake_windows": [[0,24]]` or mains/solar-rich
sites.

**Remote-E32 variant (submerged pod):** the E32 need not sit on the
node board — `ENCLOSURE.md` Form F puts it on the shore pole or the
surface float, with UART (TX/RX/GND/VCC) running the tether to the
pod's D6/D7. Firmware is unchanged: `lxmf_node.py` sees a UART either
way. This is what lets the entire sensor stack live underwater —
only the radio and its antenna stay in air. Cable runs ≤ ~30 m at
9600 baud are fine with twisted-pair marine cable; longer runs want a
lower baud or a repeater pole.

