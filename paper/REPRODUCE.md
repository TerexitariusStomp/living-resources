<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# Reproducibility capsule — paper-v1

Every quantitative claim in the paper is reproducible from this repo
state + `paper/artifacts/` + `paper/corpus/` via the commands below.
Verified on a clean shell; no hidden state.

Environment: Python ≥3.11 + numpy; Node ≥20 (--experimental-strip-types);
guile 3.0 (local prefix fine — see AGENTS.md); CONNECTOME_PACKED_DIR
pointed at `paper/corpus/blobs`.

```bash
# 1. Corpus conformance — 45/45 expected digests
CONNECTOME_PACKED_DIR=paper/corpus/blobs \
  python3 tools/connectome/lif.py --replay paper/corpus/vectors.jsonl

# 2. E5 relay pass — 15/15 relays, 15 distinct signatures
CONNECTOME_PACKED_DIR=paper/corpus/blobs \
  python3 tools/e5/relay_check.py

# 3. Cross-implementation parity — 930/930 identical (TS ↔ Python)
cd workers/compute-api && node --experimental-strip-types test/diff.mjs

# 4. Benchmark legs — reproduces the medulla crossover + celegans loss
python3 tools/connectome/bench.py run --connectome medulla \
  --reps 10 --baselines --control | \
  python3 tools/connectome/bench.py compare /dev/stdin

# 5. Protocol e2e — 121 checks under guile 3.0
guile --no-auto-compile -L module -L . tests/e2e/sensing-cell.scm
guile --no-auto-compile -L module -L . tests/e2e/connectome-witness.scm
guile --no-auto-compile -L module -L . tests/e2e/refused-lanes.scm
guile --no-auto-compile -L module -L . tests/e2e/write-lanes.scm
guile --no-auto-compile -L module -L . tests/e2e/federated.scm

# 6. Live deployment — 71 checks against the production worker
node workers/compute-api/test/e2e.mjs
```

Captured outputs: `paper/artifacts/` (checksums in `MANIFEST.txt`).
Tiers: joules marked `estimated` when RAPL is locked — the measured-tier
numbers quoted in the text come from the RAPL-unlocked runs recorded in
`docs/EFFICIENCY.md` on the same hardware class.
