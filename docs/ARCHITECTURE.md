<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# ARCHITECTURE — component-level map

The megaplan's backend, file by file. Every source file in the repo
appears here exactly once, mapped to its lane and its status. When a
file is added, this table is the diff-of-record.

## Lane vocabulary (the closed set)

Enforced identically in `module/living/offers.scm` (code) and
`deploy/policies/living/lane-gate.rego` (OPA mirror). Anything not
named is denied as `unknown-lane`. A refusal is a value, never silence.

| Lane | Gate | Requirement | Graduation path |
|---|---|---|---|
| `sense` | evidence | lane gate carries an evidence SAID + duty-cycle declared + reference-tone calibration | E0 |
| `fleet` | evidence | lane gate carries an evidence SAID | E0 |
| `emit` | consent | joint guardian + operator approval + consent credential SAID | consent, always |
| `cast` | consent | same joint consent | consent, always |
| `store` | consent | same joint consent | consent, always |
| `hop` | refused | none — refused outright; consent is not evidence | E5 is the research path |
| `compute` | refused | none — refused outright | E4/E6 run outside the organism lane (witness simulation) |
| `engineered` | refused | none — refused outright | none |
| `relay` | transport | the intent must name the `packet-said` it forwards — only content-addressed bundles move | built (rns_edge.py) |

## Status legend

`stub` → `built` → `e2e-tested` → `deployed` → `field-validated`.

Built or tested is not field-validated; *live* means a deployed
endpoint answers today. No cell in this doc or on the landing page may
claim a tier the artifact hasn't earned.

## Actor layer — `module/living/`

| File | Role | Status | Tests |
|---|---|---|---|
| `specs.scm` | record types + the Goblins/shim contract (`define-actor`, `bcom`, portraits) | built | all e2e suites |
| `agents.scm` | `^eco-agent` — the subject as an agent; guardian custody, voice-0; `*guardian-verify*` seam | built | sensing-cell |
| `sense-subject.scm` | `^sense-node` — one sense node per subject | built | sensing-cell |
| `attest.scm` | quorum of readings → one witnessed receipt | built | sensing-cell |
| `settlement.scm` | mutual credit for witnessed sensing — subjects earn through guardians | built | sensing-cell |
| `offers.scm` | the evidence gate + closed refusal vocabulary (`lane-refused`, `unknown-lane`, `evidence-required`, `consent-required`, `incomplete-declaration`, `subject-required`) | built | refused-lanes, write-lanes |
| `connectome.scm` | witness class — connectome verdicts as an *additive* third evidence leg; never manufactures detections | built | connectome-witness |

E2E suites: `tests/e2e/sensing-cell.scm` (full pipeline),
`refused-lanes.scm`, `write-lanes.scm` (consent-gated writes),
`connectome-witness.scm`. 63/63 pass under bare Guile via the
`specs.scm` shim; real Goblins when `(goblins)` resolves.

## Adapters — `adapters/`

Thin parse-only seams — they never classify (the ≤5% custom rule).

| File | Seam | Head/lane |
|---|---|---|
| `mic.scm` | detection streams → readings | `sense` audio |
| `camera.scm` | photo detections → readings | `sense` visual |
| `sonar.scm` | Doppler canopy-motion frames → readings | `sense` canopy |
| `c4d.scm` | contactless biofilm conductivity frames → readings | `sense` biofilm (E3) |
| `weather.scm` | Open-Meteo context → readings | context on all heads |
| `reticulum.scm` | UDP socket + LXMF seam → edge | transport for `sense`/`fleet` |
| `connectome.scm` | LIF verdict JSONL → connectome-verdicts | witness leg |

## Firmware — `firmware/node/main.py`

EcoCell universal node (MicroPython, XIAO ESP32-S3 class). Implemented:
I2S 48 kHz/16-bit capture → SD spool → LXMF uplink → duty-cycle sleep;
every lane's electronics populated incl. consent-gated `EmitLane`
(`ConsentRequired` without a token). LXMF uplink is a stub at the seam.

## Policy mirrors — `deploy/policies/living/`

| File | Mirrors |
|---|---|
| `lane-gate.rego` | `offers.scm` — same closed vocabulary, same refusal reasons, auditable by OPA |
| `consent.rego` | emit consent: requires `emit_consent_said` |

## Edge tools — `tools/`

| File | Role |
|---|---|
| `edge/classify.py` | edge classifier loop — OpenSoundscape seam + energy-gate fallback |
| `edge/rns_edge.py` | real RNS/LXMF edge daemon |
| `e0/score.py` | blinded E0 validation scorer — never shows which chunk was which during capture |
| `e5/relay_check.py` | E5 graduation harness — relays an encoded observation through every packed connectome, checks replay determinism (local + optional deployed-verifier legs) and input→output provenance digests, emits a SAIDed bundle. Honest bound: preserved wiring only; the refused `hop` lane is untouched |
| `connectome/lif.py` | deterministic Q24 LIF inference over packed int4 CSR connectomes; canonical input SAIDs |
| `connectome/bench.py` | evidenced efficiency vs dense/sparse machine baselines (measured, incl. unfavorable cells) |

## Worker API — `workers/compute-api/`

Deployed: `connectome-compute-api.terexmaps.workers.dev`.

| File | Role |
|---|---|
| `src/lif.ts` | TypeScript port of `lif.py` — same packed int4 blobs, same Q24 fixed point, same digests. 930/930 bit-identical vs the Python runner (`test/diff.mjs`) |
| `src/blake2s.ts` | vendored unkeyed BLAKE2s-256 (RFC 7693) |
| `src/index.ts` | routes: `GET /` (the site) · `GET /info` · `GET /connectomes` · `POST /task` · `POST /verdict` (incl. `"all"`) · `POST /verify` · `GET /receipts` + `/receipts/{said}` (RECEIPTS KV ledger) · `POST /join` (WAITLIST KV waitlist) |

## Frontend — `site/`

AstroWind (MIT) vendored at a pinned commit — `site/UPSTREAM` records
provenance. Custom code budget: **<5% of everything shipped**
(`tools/site/budget.py`); adopted dependencies do the rest.

| Path | Role |
|---|---|
| `src/data/lanes.json` | single source of truth for lane portrayal; `tools/site/lane_drift.py` fails CI if it diverges from `specs.scm`/`lane-gate.rego` |
| `src/data/tiers.json` + `src/utils/tiers.ts` | single source of truth for plain-language claim tiers ("Works today" · "Built — field test next" · …); `tierChip` emits chip markup |
| `src/data/cloud.json` | living-cloud-vs-conventional comparison rows, trajectory items, per-axis evidence, AI-organism anatomy/evolution copy (content, not code) |
| `src/components/living/` | the custom seam: `LaneTable` `TierLink` `PlantListen` `Board3D` `Globe` `ValueLoop` `OrganismMap` `JoinForm` `Console` |
| `src/pages/` | `/` story homepage · `/how-it-works` signal journey + plain-English glossary · `/science` claim tiers · `/developers` API + live console · `/privacy` · `/credits` |
| `tools/site/readability.py` | Flesch-Kincaid gate: `/` and `/how-it-works` must stay ≤ grade 7 (`make check-readability`) |
| `public/packed/` `public/audio/` `public/img/` | connectome blobs · CC0 plant-sound clips (Dryad 10.5061/dryad.jwstqjqf7 via `tools/site/plant_audio.py`) · PD/CC0 imagery |

## Hardware tooling — `tools/pcb/`

| File | Role |
|---|---|
| `gen_carrier.py` | generates `hardware/pcb/ecocell-carrier.kicad_pcb` (100×80 mm) via pcbnew |
| `gen_node.py` | generates `hardware/pcb/ecocell-node.kicad_pcb` (100×100 mm integrated node) |
| `export_asm.py` / `export_node_assy.py` | BOM + pick-and-place (CPL) export for manufacturing |

## Stubs / known gaps

| File | State |
|---|---|
| `lanes/c4d-reservoir.py` | `pass` placeholder — the v3 wild-consortium reservoir-compute research lane; not backend |
| `*guardian-verify*` (`agents.scm`) | checks a transparent placeholder tuple — real SAID signature verification lands at that seam |
| firmware LXMF uplink | stub at the `reticulum.scm` seam |

## Coverage rule

Every `.scm` / `.py` / `.ts` source file appears above exactly once.
When files are added or statuses change, update this doc in the same
commit — drift between the gate vocabulary and public claims is a bug,
not a cosmetic issue.
