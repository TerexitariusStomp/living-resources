<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# compute-api — replay-verified compute over real connectomes

Live: `https://connectome-compute-api.terexmaps.workers.dev`

Cloudflare Worker (free tier) wrapping the `tools/connectome/lif.py`
semantics — a TypeScript port (`src/lif.ts`) verified **bit-identical**
against the Python runner: `node --experimental-strip-types test/diff.mjs`
runs all 15 packed connectomes × 6 feature vectors × verdict/task/raw-input
modes and asserts every `input_said`, `trace_digest`, `spike_digest`,
`action`, `confidence`, `spike_count`, and `tail_v` matches (930/930).

The packed int4 CSR blobs ship as one static asset (`public/packed/all.bin`,
2.2 MB) + `manifest.json` — two subrequests per cold isolate keeps
`/verdict {"connectome":"all"}` under the fetch cap.

## API

```
GET  /           service info
GET  /connectomes    15 EM-derived substrates (302 → 40,000 neurons)

POST /task     {"connectome":"celegans",
                "features":{"confidence":0.91,"event_rate":0.35,
                            "env_anomaly":0.1,"fleet_agreement":1.0}}
            or {"connectome":"celegans","input":[0.85,0.4,0.15,0.9]}
           → {receipt:{task_said, input_said, trace_digest,
                       spike_count, tail_v, steps, encoder, replay}}

POST /verdict  {"connectome":"celegans"|"all", "features":{...}}
           → {verdict|verdicts: action, confidence, spike_digest, ...}

POST /verify   <a receipt verbatim>
           → {verified, claimed_digest, computed_digest,
              input_said_match}
```

Receipts are emitted in canonical JSON (sorted keys, Python-style float
formatting) — verbatim re-posting reproduces the input lexemes, which is
what keeps `input_said` replay-stable.

## Deploy

```
wrangler deploy          # CLOUDFLARE_ACCOUNT_ID=6c0140469651854b2e358517371a03d3
```

Honesty notes: deterministic ≠ biological validation — this proves
replayability of computation on real EM-derived topology, nothing more.
Cross-implementation digests with FlyEngine.sol differ by design
(keccak256 vs blake2s variation source); `encoder` disambiguates.
