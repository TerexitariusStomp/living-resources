<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# WILDLABS Awards — application draft ($50k tier)

Cycle: annual (Feb window; 2025 closed — prep for next).
Adapt into their form fields; word limits vary per question.

## Project title

Witnessed receipts for ecological sensing: making every field reading
verifiable

## Elevator summary

Conservation sensing produces data buyers must trust. We produce data
they can *check*: every field reading is content-addressed, witnessed by
a quorum of independent nodes, and issued as a replayable receipt — plus
the first universal ~$40 multimodal node anyone can build and deploy.

## Conservation need

Field teams deploying bioacoustics, camera, and environmental monitors
generate readings whose provenance dies at the CSV export. Downstream
users — protected-area managers, MRV buyers, researchers — can't tell a
calibrated reading from a fabrication. The integrity problem that hit
carbon markets is coming for biodiversity data.

## The technology

- EcoCell One: all-electronics-on-one-PCB field node (~$35–45 BOM):
  air mic, ultrasonic MEMS, hydrophone/C4D front-end, env sensors,
  camera; Reticulum/LXMF store-and-forward mesh; solar/battery.
  DRC-clean, orderable from Seeed — truly buildable by practitioners.
- Evidence layer (AGPL): readings → SAIDs → quorum merge → witnessed
  receipts → per-contribution credit. Consent-gated emission lanes;
  minimum-disruption defaults — passive listen only, nothing attaches
  to organisms or soil.
- Replay-verified compute over real organism wiring diagrams — a
  research differentiator that also serves as the integrity testbed.

## What the award funds (12 months)

- Fab + first-article: 10 EcoCell One boards, enclosure, provisioning
- E0 field pilot: 5-node deployment with a conservation partner,
  blinded-validation scoring (scorer already exists — tools/e0)
- Public catalogue: receipt graph browsable à la connectome catalogue
- Documentation so any WILDLABS member can build/deploy/receive receipts

## Budget sketch

| Item | $ |
|---|---|
| 10 nodes fab+parts+enclosures | 2,500 |
| Field pilot costs (partner travel, solar kits) | 7,500 |
| Edge infrastructure + catalogue | 5,000 |
| Development time (12 mo part-time) | 35,000 |
| **Total** | **50,000** |

## Accessibility angle (Arm-aligned)

$40 BOM vs £640 incumbents; solder-free assembly path; opens the
receipts format so existing AudioMoth-class deployments can adopt the
evidence layer without replacing hardware.
