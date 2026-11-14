# Phone-class edge — the $35 smart half

Any Linux-capable phone or SBC becomes a Playnet edge: durable UDP
ingest, optional classification, onward uplink over whatever link the
device has — site WiFi, cellular, or a CAT-1 modem riding carrier
direct-to-cell (DTC). The node stays dumb; the edge is where SAIDs,
gates, and receipts live.

## Why this exists

Satellite-IoT backhaul competitors (Kineis, Lacuna, Myriota) sell
proprietary terminals at $399+ and carry ~46-byte packets on an
hourly→daily cadence. A used phone + our AGPL stack carries full audio
snippets over carrier DTC **today** — data+IoT on Starlink DTC has been
live since 2025 via partners, compatible with off-the-shelf CAT-1/4
modems. Starlink Mini remains the high-bandwidth path (~$600 dish).

## Two variants

| Variant | Hardware | Link | When |
|---|---|---|---|
| Phone edge | Android phone, Termux or chroot Linux | cellular data, or WiFi→site terminal | field kit, rapid deployment |
| Pi edge | Pi Zero/3 + CAT-1 HAT (SIM7600-class) | DTC or local carrier | fixed remote site, no phone in the loop |

Both run the same three processes; nothing about the edge assumes the
transport — `adapters/backhaul.scm` labels which path carried each
record (`via` field on committed records).

## Setup

```sh
tools/edge/phone_edge.sh            # installs python3, prints next steps
python3 tools/edge/udp_edge.py --port 5055 \
    --out ledger.jsonl --store store/ --via wifi
python3 tools/edge/uplink.py --ledger ledger.jsonl \
    --target https://<receiver>/ingest      # onward HTTPS forwarder
python3 tools/edge/classify.py --spool <audio-dir> \
    --out detections.jsonl --backend none
```

`uplink.py` is the onward path: it tails the committed ledger and
POSTs `{"records":[...]}` batches to any HTTPS receiver, persisting a
byte offset so restarts resend nothing and retries are idempotent on
the receiver's content-hash dedupe. Point `--target` at whatever
ingest endpoint exists for the deployment — until a public route
lands, a receiver you control is the honest answer.

- `--via` must match the `adapters/backhaul.scm` vocabulary
  (`lora wifi cat1-sat starlink-sat`) so receipts can say which path
  carried the reading — that label is itself evidence.
- Nodes reach the edge over UDP 5055 on the shared LAN (or a tunnel
  the phone provides); frame contract is DET1/ENV1/AUD1/RES1/GAP1,
  content-hash ACKed, idempotent under retry.

## CAT-1 / DTC notes

- Modem control rides **ModemManager + libqmi/qmicli** (GPL tooling,
  not linked) — `mmcli -m any --simple-connect="apn carrier.apn"`.
- Verify carrier DTC coverage at the site before depending on it;
  treat as a bound seam with LoRa/WiFi fallbacks, never the only path.
- Power: phone edge sips; Pi+modem ~2–4W — trivial on a solar budget.

## What this is not

Not a sensor node — no heads, no consent surface. Not a replacement
for the mesh: LoRa stays authoritative for off-grid clusters; this is
the augmentation path for sites with (or soon-to-have) broadband.
