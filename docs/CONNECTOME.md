<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# CONNECTOME — biological wiring as the living cloud's evidence layer

How real neural connectomes — the packed EM-derived wiring diagrams in
`~/fly-data` and the LIF machinery already deployed in fly.ai's
`FlyEngine` — make the living cloud's evidence unmatched by any existing
system. What is built, what is claimed, and what is deliberately not
claimed.

## What we have that nobody else does

| Asset | Where | Status |
|---|---|---|
| 15 packed connectome datasets (C. elegans ×3, drosophila, human, mouse, rat, macaque ×2, ciona, larva, platynereis, mouse retina, hemibrain 21.6k neurons, medulla 40k) | `~/fly-data/packed/` | on disk, int4 CSR |
| Deterministic LIF inference over packed graphs | `FlyEngine.sol` + `tools/connectome/lif.py` | deployed on-chain; ported |
| Evidence chain: readings → quorum → receipts → credit | `module/living/` | e2e-verified |
| Literature connectome family (PlantConnectome 14.5M edges, YeastKG) | connectome.tools | external, citation-level |

## The five layers

### L1 — Connectome witnesses (built, phase 1)

A packed wiring diagram runs LIF inference over an *encoded
observation*: `{confidence, event_rate, env_anomaly, fleet_agreement}`
rasterized onto two neuron half-populations (affirm/refute), spikes
propagate along real synaptic paths for `nSteps`, and the result is a
verdict — action, confidence, and a **spike digest** committing to the
full raster + final membrane state.

The witness is the *signature*, not the verdict's content: each
connectome's digest is unique to its topology (celegans fires 2.5k
spikes on a sample input; medulla 88k on a refute input). A quorum of
≥3 verdicts across ≥3 *distinct* connectomes folds into one evidence
digest that a witnessed receipt binds alongside its audio/detection
SAIDs — additive, never load-bearing.

The claim is precisely: **"the preserved wiring of a real organism
produces a replayable response signature to this encoded reading."**
Any third party with the packed graph + the encoder version
(`lif-sensing-v1`) reproduces the digest bit-for-bit via `--replay`.

### L2 — Literature claim-chains

connectome.tools graphs (PlantConnectome, YeastKG) are literature
edges — source–relationship–target triples backed by PMIDs. A lane's
gate `evidence-said` can point to a SAIDed bundle of edges grounding
the claim (e.g. drought→cavitation→acoustic emission for `ultra`;
K⁺-wave propagation for `c4d`). Every SCIENCE.md claim becomes a
machine-checkable citation chain. LLM-extracted edges (~85% accuracy)
are *leads*: bundles keep basis text for human verification before the
gate trusts them. Bulk graph access needs the Mutwil data-request —
this pass works citation-level.

### L3 — The living cloud's own connectome (the public artifact)

Witnessed observations accumulate into a knowledge graph in
connectome.tools form: entity–relationship–entity edges citing
**receipt SAIDs** instead of PMIDs. A public catalogue — every edge
clickable through to the receipts — is the visible artifact:
competitors publish dashboards and PDF reports; this publishes a
machine-checkable evidence graph that grows from the field.

### L2.5 — Resource lanes: what connectomes can and cannot provide

`compute` — **real, narrow, uniquely verifiable.** A connectome is a
fixed recurrent dynamical system: input vector in, spike-trace transform
out (reservoir-computing shape). The proof property no competitor has:
**replay is the receipt** — independent verifiers recompute input→trace
and require bit-identical digests; unanimity, not majority. Topology-
parameterized: *which organism's wiring ran the task* is part of the
result. Built: `--task` mode in lif.py, `<connectome-task>` +
`replays-agree?` + `task-evidence-digest` in connectome.scm. The refused
`compute` lane (living systems computing) stays refused — a
connectome-compute lane would be its own graduation via E4.

`store` — **honestly no for organism-side persistence.** LIF state is
transient (membrane decay → fading memory). What is real: trace digests
are commitments and checkpoints are tamper-evident state — evidence
material, not bulk storage. The `store` lane stays node-SD hardware.

`hop` — **real but vision-tier** (L4): propagation along real synaptic
paths is a relay through organism topology — a receipted trace, not
throughput. E5 is its graduation path.

`emit`/`cast` — unchanged: consent-gated; rasterization is already the
input direction of a response loop.

### L4 — Signal relay through wiring (vision-tier)

Route a sensed signal *through* a connectome: encoded input injected as
current propagates along real synaptic paths, and the emitted spike
train is the relayed output — logged and receipted. Honest framing: the
organism's *measured topology* relays the signal (a digital twin of
wiring), never the organism. Rides the `hop` lane — refused until its
own evidence SAID lands.

### L5 — The guardian analogy (documented, no code)

A scanned organism's connectome is a voice-0 witness by construction:
its "guardian" is the dataset custodian (FlyWire/Janelia/et al.
attribution), its verdicts earn nothing, and it never consents, holds
custody, or acts as subject. Witnesses, not participants.

## Competitive position — how this surpasses

| Class | Players | Their evidence | Ours |
|---|---|---|---|
| Acoustic loggers | AudioMoth (~$100, ~14k units), Wildlife Acoustics | Audio + classifier CSV | Per-reading witnessed receipts + connectome signatures |
| MRV platforms | NatureMetrics (4.3M detections), Pivotal | Aggregate metrics, human survey review | Granular machine-checkable evidence; subjects as credited providers |
| Eco-credit ledgers | Regen Network, ~450 schemes | Project-level documentation | Credits minted from per-reading receipts |
| Biocomputing | Cortical CL1 ($35k wetware), FinalSpark organoids | Engineered neurons, lab-bound | Wild systems, non-invasive, $40 node + preserved wiring as witness |
| Literature KGs | connectome.tools | Static PMID-cited past science | Live receipt-cited graph growing from the field |
| Connectome research | OpenWorm, FlyWire | Maps for neuroscience | Wiring deployed as evidence actors — unique |

Checkable surpass metrics: **3 witness classes** vs 1; **per-reading
SAIDs** vs aggregate metrics; **replayable verdicts** vs
trust-the-pipeline; **subjects earn credit** vs organisms as
commodities; **$35–45/node** vs £640 incumbents / $35k wetware;
**non-invasive** vs probes/eDNA sampling/culture.

Stated gaps: NatureMetrics' decade of validated detections and
AudioMoth's deployed fleet are real. The architecture surpasses; the
field record is what E0 + first-article build.

## Honesty table — what is and is not claimed

| Claim | Status |
|---|---|
| Verdicts are deterministic and replayable | Demonstrated — `--replay` reproduces digests |
| Each connectome's response signature is topology-unique | Demonstrated — per-connectome spike digests/counts differ |
| A wiring diagram *understands* or *validates* ecology | **Not claimed** — verdicts are witness signatures, not cognition |
| Rasterized features carry ecological meaning | Unproven — encoder discrimination power is an E-gate question |
| Literature edges prove a lane | Leads only — PMID bundles need human verification |
| A connectome is a participant organism | Refused — it is a preserved structure used as a witness |

## Phase state

- **L1 built**: `tools/connectome/lif.py` (FlyEngine-faithful LIF +
  sensing rasterizer + replay), `module/living/connectome.scm`
  (verdicts, distinct-topology quorum, evidence digest),
  `adapters/connectome.scm` (thin parse), `attest.scm` (additive
  `connectome-said` on receipts), `tests/e2e/connectome-witness.scm`
  (20 checks).
- **Next**: encoder discrimination study across connectomes (E-gate
  material), verdict provenance (signed runner output), catalogue
  skeleton rendering the receipt graph (L3), literature bundles for
  the existing lanes (L2).

## Run it

```bash
# list the packed wiring diagrams
python3 tools/connectome/lif.py --list

# a verdict set from all 15 connectomes on one observation
python3 tools/connectome/lif.py --all \
  --features '{"confidence":0.91,"event_rate":0.35,"env_anomaly":0.1,"fleet_agreement":1.0}' \
  > verdicts.jsonl

# verify every verdict replays bit-for-bit
python3 tools/connectome/lif.py --replay verdicts.jsonl
```
