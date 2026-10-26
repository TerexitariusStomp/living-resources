# AGENTS.md — living-resources

A living sensing commons: universal Reticulum field nodes (~$35–45
ESP32-S3, **every head's electronics on every device** — camera, air mic,
env, hydrophone front-end, ultrasonic MEMS, C4D, emit transducer) relay
multimodal detections to a Playnet edge; each ecological subject
(species / assemblage / plant) is an agent with a human guardian and
**voice 0**, contributing `sense`/`fleet` readings that merge via quorum
into witnessed receipts earning per-contribution credit. The node is
bidirectional: it reads living systems and, on joint guardian+operator
consent, writes (bio-write via the emit lane; cloud-write via downlink
tasking and node-SD store).

License: AGPL-3.0-or-later. SPDX header on every source file.

## Build & test

```
make test                  # e2e suites under guile, or static checks without it
make check-custom-budget   # first-party LOC vs adopted-OSS seam stubs
make site                  # build the frontend (site/, AstroWind vendored)
make check-site-budget     # site custom-code ratio vs everything shipped (<5%)
make check-lane-drift      # frontend lane rows vs specs.scm/lane-gate.rego
make check-readability     # / and /how-it-works must stay <= grade 7 (needs textstat: pip install -r tools/site/requirements.txt)
```

Tests run directly:

```
guile --no-auto-compile -L module -L . tests/e2e/sensing-cell.scm
guile --no-auto-compile -L module -L . tests/e2e/refused-lanes.scm
guile --no-auto-compile -L module -L . tests/e2e/write-lanes.scm
```

No system guile? Fedora ships it as `guile30`; a no-sudo local install
works too: `dnf download --resolve guile30`, `rpm2cpio … | cpio -idm`
into a prefix, then run with `LD_LIBRARY_PATH`, `GUILE_LOAD_PATH` and
`GUILE_LOAD_COMPILED_PATH` pointed at it. Verified: 63/63 checks pass.

No build step: Guile modules under `module/`, seam adapters under
`adapters/` (repo root on `-L`), OPA policies under `deploy/policies/`,
MicroPython firmware under `firmware/node/`.

**Degradation contract.** The actors use `define-actor`/`bcom`/portraits
in Goblins style. `module/living/specs.scm` re-exports real Goblins when
`(goblins)` resolves; otherwise it supplies a synchronous spawn/$/bcom
shim so the same suites exercise every act under bare Guile. With no
Guile at all, `make test` runs static checks instead — never a silent pass.

## The three rules (load-bearing)

1. **Two gates.** `sense`/`fleet` are evidence-gated — an offer or intent
   is admitted only if the lane's gate carries an evidence SAID.
   `emit`/`cast`/`store` are **consent-gated** — they ride the joint
   approval of the subject's guardian and the node operator, checked in
   `module/living/offers.scm` and mirrored in
   `deploy/policies/living/lane-gate.rego`; consent is a value on the
   intent, never a default. `hop`/`compute`/`engineered` refuse outright —
   consent is not evidence. A refusal is a value, never silence.
2. **Minimum-disruption.** Passive-listen-only by default. Nothing
   attaches to an organism, nothing enters soil, no anchor moorings.
   Emission is allowed **only** when guardian + operator jointly decide —
   the emit path is fully implemented in firmware
   (`firmware/node/main.py` EmitLane, ConsentRequired without a token)
   and policy (`consent.rego` requires `emit_consent_said`), with
   duty-cycled minimum-power defaults. Every emission is logged and
   receipted — accountability persists whatever the flag.
3. **≤5% custom.** Before any module is written, name the OSS that covers
   it. Detection/ML stays Python-side (OpenSoundscape/BirdNET); adapters
   are thin seams that parse, never classify. `make check-custom-budget`
   counts bespoke lines against the stub list — the adopted-OSS delegation
   files are `adapters/*.scm`.

## Custody model in one line

Subjects earn credit; guardians hold custody. Every mutating act on an
`^eco-agent` requires a guardian signature — `*guardian-verify*` in
`module/living/agents.scm` is the seam where `verify-said-signature` lands
(today it checks a transparent placeholder tuple).

## Layout

```
module/living/   specs · agents (^eco-agent) · sense-subject (^sense-node)
                 attest (quorum→receipt) · settlement (mutual credit)
                 offers (the evidence gate)
adapters/        mic · camera · sonar · c4d · reticulum (UDP socket
                 + LXMF seam) · weather (Open-Meteo context)
firmware/node/   main.py — MicroPython universal node: I2S 48kHz/16-bit →
                 SD spool → LXMF uplink (stub) → duty-cycle sleep; all
                 lanes populated incl. consent-gated EmitLane
deploy/policies/ lane-gate.rego · consent.rego
tests/e2e/       sensing-cell.scm (full pipeline) · refused-lanes.scm
                 · write-lanes.scm (consent-gated writes)
tools/edge/      classify.py (OpenSoundscape seam + energy-gate fallback)
                 · rns_edge.py (real RNS/LXMF edge daemon)
tools/e0/        score.py (blinded-validation scorer for field E0)
tools/e5/        relay_check.py (E5 harness — hop's graduation path)
tools/site/      budget.py (≤5% custom-code ratio) · lane_drift.py
                 (frontend rows vs gate vocabulary) · plant_audio.py
site/            the frontend — AstroWind (MIT, vendored at a pinned commit,
                 see site/UPSTREAM) Astro app; src/components/living/ holds the
                 few custom pieces (lane table, console, globe, board3d,
                 plant audio, value loop, join form); src/data/lanes.json is
                 the single source of truth for lane portrayal
workers/compute-api/  Cloudflare Worker — serves site/dist as assets plus
                 /task /verdict /verify /connectomes /receipts /join APIs
                 (RECEIPTS + WAITLIST KV)
```

## Conventions

Match playnet/localchimera: `define-record-type` + validating `make-*`
keyword constructors; `define-actor` with `#:portrait`/`#:version`/
`#:restore` + a `make-persistence-env`; tagged `(admitted . x)` /
`(refused . <refusal>)` replies; compact code, comment blocks that say why.
