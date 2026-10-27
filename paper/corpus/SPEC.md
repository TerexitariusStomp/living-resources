<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# WiredReplay-1 specification — packed blob, encoder, LIF semantics, digests

Normative spec for the conformance corpus. An implementation that
reproduces every `trace_digest`/`spike_digest` in `vectors.jsonl`
against the packed blobs is conformant.

## 1. Packed blob format (FlyBrain CSR, MIT — alextitonis/fly.ai)

Each `<connectome>/` dir holds `metadata.json` + `chunk_*.bin` files
(EIP-170 ≤24,575 B chunks; concatenate in sorted order, truncate to
`totalSize`). Blob layout:

```
[ indptr deltas ][ indices u16be ][ int4 weights, 2 nibbles/byte ]
```

- `indptrWidth` 1 → deltas are u8; 2 → big-endian u16. `indptr =
  [0] ++ cumsum(deltas)` (length nNeurons+1)
- `indices`: nSynapses × big-endian u16 target ids
- `weights`: nSynapses × int4 (two per byte, high nibble first); values
  ≥8 → subtract 16 (two's complement). Effective weight = nibble ×
  `weightScale` (from metadata; ≈0.1428 in Q-units)

`metadata.json` fields: `name, nNeurons, nSynapses, nSteps,
indptrWidth, indptrOffset, indicesOffset, weightsOffset, weightScale,
totalSize, nChunks`.

## 2. Q24 fixed-point constants (identical to FlyEngine.sol)

```
Q24           = 1 << 24          = 16777216
DECAY_Q24     = exp(-0.2)*2^24   = 13743895
TONIC_Q24     = 0.14*2^24        = 2359296
THRESHOLD_Q24 = 1.0*2^24         = 16777216
EYE_GAIN_Q24  = 1.5*2^24         = 25165824
WEIGHT_SCALE  = 3.0*2^24 / 7     = 7190235   (current per nibble)
VAR_MOD       = 1677720          (per-neuron variation spread)
```

All arithmetic is integer; divisions are floor; `>>24` for Q24
rescaling. Rounding: `_norm` uses round-half-even to Q24.

## 3. Input SAID

`input_said = "blake2s:" + blake2s(json(features, keys sorted,
separators=(",",":")))`. Four features, each normalized 0..1:
`confidence, event_rate, env_anomaly, fleet_agreement`.

## 4. Rasterizer — encoder `lif-sensing-v1`

```
affirm = conf·(1-anom)·agree·(1+rate)/2 · EYE_GAIN     (Q24 math)
refute = (1-conf)·anom·(1-agree) · EYE_GAIN
affirm = max(affirm, TONIC_Q24); refute = max(refute, TONIC_Q24)
inp[i<half]  = affirm + variation(i,"affirm")
inp[i≥half]  = refute + variation(i,"refute")
variation(i,side) = blake2s(f"{i}:{side}")[0:4] as u32be mod VAR_MOD
```

`half = nNeurons // 2`. First half = affirm population; second = refute.
(Divergence from FlyEngine: keccak256 → blake2s for the variation;
documented divergence, everything else identical.)

## 5. LIF step semantics (`nSteps`, typically 10)

```
v[0] = 0
for s in 0..steps-1:
    current[j] = Σ over edges (i→j) of fired[i]·w4·WEIGHT_SCALE   (scatter)
    v = (v·DECAY_Q24) >> 24
    v += current + TONIC_Q24 + inp
    fired[s] = v ≥ THRESHOLD_Q24
    v[fired] = 0                        # reset
```

`spike_digest = "blake2s:" + blake2s(raster.tobytes() ++ v.tobytes())`
(bool raster as bytes, then int64 v little-endian — see `decode`).
`trace_digest` (task mode) = blake2s over input_said ‖ raster ‖ v
(workers/compute-api/src/lif.ts, same byte order).

## 6. Verdict decode

```
affirm_sum = Σ inp[:half]; refute_sum = Σ inp[half:]
diff = affirm_sum − refute_sum; total = affirm_sum + refute_sum
if total ≤ 0 or diff = 0 or |diff|·100 < 15·total → (0, 50)
else action = sign(diff); conf = min(100, 50 + activity·50//total)
activity = Σ v[v>0]; spike_count = raster.sum()
```

## 7. Conformance

`python3 tools/connectome/lif.py --replay vectors.jsonl` must report
`ok` for all 45 rows (15 connectomes × 3 canonical feature sets).
A third-party implementation replays by recomputing §§1–6 from the
packed blobs and comparing digests byte-for-byte.
