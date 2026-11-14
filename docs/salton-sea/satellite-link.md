# Satellite link at Mars College — Starlink Mini siting & procurement

Status: planning doc, Nov 2026. Companion to `tools/edge/phone_edge.md`
(the cheap-edge variant) and `adapters/backhaul.scm` (the seam this
link binds to).

## Why a dish at all

The LoRa mesh stays authoritative — it needs no subscription and works
in every dead zone. The Starlink Mini is **augmentation**: near-real-time
uplink during the semester so the public dashboard reflects the playa
live instead of on store-and-forward cadence. LPWAN-satellite
competitors carry ~46-byte detections on an hourly→daily schedule;
this path carries full audio snippets in seconds. That delta is the
publishable benchmark.

## Hardware

- **Starlink Mini** (~$600 kit, Gen 3 router + dish). ~25–40 W
  typical, peaks higher during storms/heavy rain — budget the power.
- Router provides WiFi AP + one Ethernet port. Field nodes join its
  WiFi like any site LAN (`Uplink` UDP path, `EDGE_PORT` 5055); the
  phone/Pi edge (`tools/edge/phone_edge.sh`) sits on the same LAN and
  runs `udp_edge.py --via starlink-sat`.
- Cable: router→dish is captive; plan the dish-to-router run (dish is
  outdoor-rated, router indoor). ~45 m cable may need the longer kit.

## Siting

- **Clear sky view is the only hard requirement.** The playa is flat —
  excellent. Mount the dish on a stake/tripod at least ~1 m up, away
  from the plywood structures and metal framing (multipath hurts
  throughput, not correctness).
- Keep the router + edge device indoors or in a sealed box: dust is
  the Salton Sea's real enemy (PM events will show up in our own air
  data — that's the point, but the gear still needs protection).
- Obstructions to avoid: kitchen steam vents, metal sheds, dense tree
  lines to the east (the Chocolate Mountains are west — fine).

## Power budget

- Dish+router: ~30 W average → ~0.7 kWh/day.
- Campus solar exists but is allocated; confirm headroom with DPW
  before install. A dedicated 100 W panel + small battery for the
  terminal is cheap insurance against campus power decisions.
- The edge device (phone/Pi) adds <5 W — negligible.

## Data path

```
nodes ──WiFi/UDP──▶ edge (udp_edge.py --via starlink-sat)
                        │  committed, hash-verified, content-addressed
                        ▼
                  onward uplink → Playnet / compute-api
                  (records carry "via": "starlink-sat" —
                   third-party transport → federated provenance)
```

- `adapters/backhaul.scm` maps `starlink-sat` → channel `satellite`,
  cap `full` — audio snippets and scheduled media, not just
  detections. `cat1-sat` (CAT-1 modem + carrier DTC) is the no-dish
  fallback at `snippets` cap.
- Records arriving via this path are **imports** (federated lane):
  labeled `starlink`, never counted as local-node quorum evidence on
  their own — the mesh remains the evidence spine.

## Benchmark plan (the surpass artifact)

During the semester, measure and publish:

1. **Detection→receipt latency**: timestamp at node capture vs.
   `edge_ts` at commit, starlink path vs. LoRa store-forward windows.
2. **Payload capability**: bytes/hour sustained (detections +
   snippets) vs. published LPWAN-sat limits (~46 B/msg, hourly).
3. **Uptime**: dish availability through wind/dust/rain events —
   the playa is a legitimately harsh RF environment; honest numbers
   are worth more than marketing ones.

## Procurement checklist

- [ ] Starlink Mini kit (hardware ~$600) — sponsor ask
- [ ] 100 W panel + charge controller + battery (backup power)
- [ ] USB-C/mains for router; outdoor-rated cable for dish run
- [ ] Sealed enclosure for router + edge device
- [ ] Confirm campus power headroom with DPW crew (Nov build season)
- [ ] Clear-sky sightline survey (photograph the horizon from mount point)
