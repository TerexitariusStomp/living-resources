<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# WiredReplay-1 — a replay-verification corpus of biological wiring diagrams

Version 1 · October 2026 · Temple Earth (Treetable LLC) · AGPL-3.0-or-later
(code) / CC-BY-4.0 (specification text + vectors)

**WiredReplay-1** is a conformance corpus for deterministic simulation
over real biological connectomes: 15 packed wiring diagrams (cellular
EM and mesoscale parcellation, labelled per dataset), 45 canonical
input vectors, and the expected digests a conformant implementation
must reproduce bit-for-bit. If your LIF/connectome runner produces the
same `spike_digest`/`trace_digest` on the same packed blob + input, it
is verified against this corpus — no trust in our implementation
required. Replay is the receipt.

## Contents

```
blobs/<name>/          int4-CSR packed wiring + metadata.json (per-dataset)
all_connectomes.json   summary metadata for all 15
checksums.txt          sha256 of every blob file
vectors.jsonl          45 verdict/task records: input SAID + features +
                       expected digests, action, confidence, spike_count
SPEC.md                normative format/encoder/LIF/digest specification
```

## Datasets

| name | neurons | resolution | upstream |
|---|---:|---|---|
| celegans, celegans_herm, celegans_male | 302–575 | cellular EM | WormWiring (Cook et al. 2019) |
| ciona | 205 | cellular EM | Ryan et al. 2016 |
| larva | 3,016 | cellular EM | Janelia Drosophila L1 (CC-BY) |
| platynereis | 5,000 | cellular EM | Jékely lab (Verasztó et al.) |
| mouse_retina | 1,124 | cellular EM | Helmstaedter et al. 2013 |
| hemibrain | 21,636 | cellular EM | Janelia hemibrain v1.x (CC-BY) |
| medulla | 40,000 | cellular EM | Janelia FIB-SEM optic lobe (CC-BY) |
| drosophila | 49 | **mesoscale** | coarse fly-brain graph |
| human | 234 | **mesoscale** | parcellated structural |
| mouse | 112 | **mesoscale** | interareal matrix |
| rat | 73 | **mesoscale** | BAMS-class |
| macaque | 93 | **mesoscale** | CoCoMac-derived |
| macaque_modha | 242 | **mesoscale** | Modha & Singh 2010 |

Licensing: blobs derived from CC-BY upstreams are redistributable with
attribution; for cite-only sources the checksums + pack script +
upstream citations are the conformance path (regenerate, compare
hashes). See `../datasets.md` for the per-dataset license tier table.

## Validate an implementation

```bash
# with the reference runner (tools/connectome/lif.py, AGPL)
CONNECTOME_PACKED_DIR=paper/corpus/blobs \
  python3 tools/connectome/lif.py --replay paper/corpus/vectors.jsonl
# expect: 45/45 ok
```

Third-party path: implement `SPEC.md` §§1–6, run each vector against
its blob, compare `spike_digest`, `trace_digest`, `input_said`,
`action`, `confidence`, `spike_count` byte-for-byte.

## Cite

> Price, T.R. (2026). *WiredReplay-1: a replay-verification corpus of
> biological wiring diagrams* (v1). Zenodo. DOI pending — use the
> Zenodo record DOI once minted; until then cite the git tag
> `paper-v1` at github.com/TerexitariusStomp/living-resources.
