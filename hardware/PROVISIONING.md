<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# Provisioning — from parcel to live node

The steps between "boards arrive" and "node reporting in the field".
~20 minutes per unit once the gear is set up.

## 1 — Assemble (if not PCBA'd)

Solder the THT strip per `ASSEMBLY.md`: U1A/U1B sockets, J1–J10
headers, J11 screw terminal. Socket the XIAO — USB port toward the
silk "XIAO-S3 USB-up" mark.

## 2 — Flash MicroPython

1. Hold BOOT, plug USB — the XIAO enumerates as a flash device.
2. Flash the latest MicroPython ESP32-S3 build:
   `esptool.py --chip esp32s3 write_flash 0 firmware.bin`
3. Copy `firmware/node/main.py` to the filesystem (mpremote/Thonny/ampy):
   `mpremote cp firmware/node/main.py :main.py`

## 3 — Configure identity

In `firmware/node/main.py`, set before flashing (or edit on-device):

| Constant | Set to |
|---|---|
| `NODE_ID` | unique id, e.g. `node-garden-01` — lands in every frame |
| `LANES` | enable the lanes matching attached heads |
| uplink block | UDP host:port of the edge, or LoRa UART pins |

Insert the microSD — the spool and `lanes/` dir are created on first
boot.

## 4 — Consent defaults

- All read lanes enabled by their config flags.
- `emit` ships `enabled: False` — unlocking it takes a consent SAID
  issued by guardian + operator through the edge's lane gate
  (`deploy/policies/living/`). The node re-verifies the token; the
  ≤5% duty cap is firmware-hard and cannot be loosened by the token.
- No lane emits into a living system without that joint consent.

## 5 — Edge pairing

- UDP path: point the node at the edge listener
  (`adapters/reticulum.scm` demux or `tools/edge/rns_edge.py` for
  real RNS/LXMF).
- RNS path: the node's LXMF frames discover the edge by announce —
  both sides need a shared transport interface.

## 6 — Bench check

Power J11 at 5.5 V → LED1 on → serial log shows capture → spool →
uplink frames. Confirm a detection lands in the edge ledger.

## 7 — Field commissioning

Mount per `ENCLOSURE.md`, heads through glands, power on. First
receipt in the ledger = commissioned. Record node id, site, guardian
and consent scope in the cell's subject registry.
