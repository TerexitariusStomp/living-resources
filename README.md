# living-resources

A living sensing commons: cheap, passive, **universal** field nodes relay
multimodal ecological detections over Reticulum to a Playnet edge, where
readings become witnessed receipts and receipts become credit for the
ecology that produced them.

License: AGPL-3.0-or-later.

## The node

One board, every lane's electronics populated (~$35–45 BOM):

camera (OV2640) · air mic (INMP441, 48 kHz/16-bit) · env
(BME280/BH1750/PIR) · hydrophone front-end · ultrasonic MEMS (20–100 kHz)
· C4D contactless front-end · 40 kHz emit transducer · microSD · Reticulum
(WiFi/LoRa/satellite)

A node's role is software + which head is in the environment — never a
different product. See `spec/living-resources.md`.

## The rules that make it a commons

- Every ecological subject is an agent with a human guardian and
  **voice 0** — it earns, it never speaks.
- `sense`/`fleet` lanes admit on **evidence** (a SAID on the lane's gate).
- `emit`/`cast`/`store` admit on **joint guardian+operator consent** —
  bio-write and cloud-write are decisions, not defaults.
- `hop`/`compute`/`engineered` refuse outright — consent is not evidence.
- Every refusal is a structured value; every emission is logged and
  receipted.

## Quickstart

```bash
make test                  # e2e under guile; static checks without it
make check-custom-budget   # the ≤5% first-party rule
```

E0 field validation (see `docs/EXPERIMENTS.md`): flash
`firmware/node/main.py` to a XIAO ESP32-S3 Sense, run the edge adapters
against the node's detection stream, score detections blinded.

## Layout

```
module/living/   specs · agents · sense-subject · attest · settlement · offers
adapters/        mic · camera · reticulum · weather   (thin seams; ML stays
                 Python-side)
firmware/node/   MicroPython universal node (incl. consent-gated EmitLane)
deploy/policies/ OPA: lane-gate.rego · consent.rego
spec/            the system spec
docs/            SCIENCE (claim table) · EXPERIMENTS (E-gates) · ROADMAP
                 · CONNECTOME · EFFICIENCY · FUNDING (+ funding/ app drafts)
tests/e2e/       sensing-cell · refused-lanes · write-lanes
tools/edge/      classify.py (edge ML seam) · rns_edge.py (LXMF daemon)
tools/e0/        score.py (blinded field-validation scorer)
```

## Non-interference

Passive by default: nothing attaches to an organism, nothing enters soil,
no anchor moorings, no flash or IR. Emission exists — it is a lane the
commons can ride — and it rides only on recorded joint consent, at
duty-cycled minimum power, with every burst on the ledger.
