#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""lif.py — deterministic LIF inference over packed biological connectomes.

Ports the FlyEngine step semantics (shit-token/contracts/src/fly/FlyEngine.sol,
itself from alextitonis/fly.ai FlyBrain, MIT) to Python so packed wiring
diagrams in ~/fly-data/packed/<name>/ can *witness* encoded observations:
an observation's feature vector is rasterized onto two neuron half-
populations (affirm/refute), spikes propagate along real synaptic paths,
and the verdict — action, confidence, spike digest — is fully replayable.

The claim this backs is narrow and checkable: a preserved wiring diagram
produces a stable, reproducible response signature to a given encoded
reading. It is not biological validation, ecological understanding, or
any claim about the organism's mind — it is verifiable computation on
real EM-derived topology, and every emitted verdict records the encoder
version so reproduction is unambiguous.

  python3 tools/connectome/lif.py --connectome celegans \
      --features '{"confidence":0.91,"event_rate":0.35,"env_anomaly":0.1,"fleet_agreement":1.0}'
  python3 tools/connectome/lif.py --all --features '{...}'
  python3 tools/connectome/lif.py --replay verdict.jsonl

Encoder divergence note: FlyEngine derives per-neuron input variation
with keccak256; this runner uses blake2s (documented as encoder
"lif-sensing-v1"). Same packed data, same step math — variation source
differs, so cross-implementation digests differ by design and are
disambiguated by the encoder field on every verdict.
"""

import argparse
import hashlib
import json
import os
import sys

import numpy as np

PACKED_DIR = os.path.expanduser(
    os.environ.get("CONNECTOME_PACKED_DIR", "~/fly-data/packed"))

# Q24 fixed-point constants — identical values to FlyEngine.sol.
Q24 = 1 << 24
DECAY_Q24 = 13743895        # exp(-0.2) * 2^24
TONIC_Q24 = 2359296         # 0.14 * 2^24
THRESHOLD_Q24 = 16777216    # 1.0
EYE_GAIN_Q24 = 25165824     # 1.5
WEIGHT_SCALE = 7190235      # (3.0 * 2^24) / 7 — current units per nibble
VAR_MOD = 1677720           # same spread as FlyEngine's keccak variation

ENCODER = "lif-sensing-v1"


# ── packed CSR decode ─────────────────────────────────────────────────────
# Blob layout (pack_connectomes.py): [indptr deltas][indices u16be][int4
# weights, 2 per byte]. metadata.json carries the section offsets.

def load_connectome(name):
    d = os.path.join(PACKED_DIR, name)
    meta = json.load(open(os.path.join(d, "metadata.json")))
    blob = b"".join(open(os.path.join(d, f), "rb").read()
                    for f in sorted(os.listdir(d)) if f.startswith("chunk_"))
    blob = blob[: meta["totalSize"]]
    n = meta["nNeurons"]

    if meta["indptrWidth"] == 1:
        deltas = np.frombuffer(
            blob[meta["indptrOffset"]:meta["indicesOffset"]], dtype=np.uint8)
    else:
        deltas = np.frombuffer(
            blob[meta["indptrOffset"]:meta["indicesOffset"]],
            dtype=">u2")
    indptr = np.concatenate(
        [[0], np.cumsum(deltas, dtype=np.int64)]).astype(np.int64)

    n_syn = meta["nSynapses"]
    indices = np.frombuffer(
        blob[meta["indicesOffset"]:meta["indicesOffset"] + 2 * n_syn],
        dtype=">u2").astype(np.int64)

    wb = blob[meta["weightsOffset"]:
              meta["weightsOffset"] + (n_syn + 1) // 2]
    hi = np.frombuffer(wb, dtype=np.uint8) >> 4
    lo = np.frombuffer(wb, dtype=np.uint8) & 0x0F
    w4 = np.empty(n_syn, dtype=np.int8)
    w4[0::2] = hi[: len(w4[0::2])]
    w4[1::2] = lo[: len(w4[1::2])]
    w4 = np.where(w4 >= 8, w4 - 16, w4).astype(np.int64)

    # src-of-each-edge for vectorized scatter
    counts = np.diff(indptr)
    src = np.repeat(np.arange(n, dtype=np.int64), counts)
    return meta, indptr, indices, w4, src


# ── sensing rasterizer (encoder lif-sensing-v1) ───────────────────────────
# An observation is four normalized features: detection confidence, event
# rate vs the lane's declared expected rate, environmental-context anomaly,
# and fleet agreement (fraction of sibling legs agreeing on the detection).
# affirm = confidence * (1-anomaly) * agreement; refute = (1-confidence) *
# anomaly * (1-agreement). Both get EYE_GAIN and a tonic floor, then spread
# across the two half-populations with a documented blake2s variation —
# same shape as FlyEngine's keccak variation, different hash, declared here.

def _norm(x):
    return max(0, min(Q24, int(round(x * Q24))))


def _variation(i, side):
    return int.from_bytes(
        hashlib.blake2s(f"{i}:{side}".encode()).digest()[:4],
        "big") % VAR_MOD


def rasterize(features, n):
    conf = _norm(features["confidence"])
    rate = _norm(features["event_rate"])
    anom = _norm(features["env_anomaly"])
    agree = _norm(features["fleet_agreement"])

    affirm = conf * (Q24 - anom) // Q24
    affirm = affirm * agree // Q24
    affirm = affirm * (Q24 + rate) // (2 * Q24)
    affirm = affirm * EYE_GAIN_Q24 // Q24

    refute = (Q24 - conf) * anom // Q24
    refute = refute * (Q24 - agree) // Q24
    refute = refute * EYE_GAIN_Q24 // Q24

    if affirm < TONIC_Q24:
        affirm = TONIC_Q24
    if refute < TONIC_Q24:
        refute = TONIC_Q24

    half = n // 2
    inp = np.empty(n, dtype=np.int64)
    for i in range(half):
        inp[i] = affirm + _variation(i, "affirm")
    for i in range(half, n):
        inp[i] = refute + _variation(i, "refute")
    return inp


# ── LIF step — identical semantics to FlyEngine._analyze ─────────────────

def simulate(meta, indptr, indices, w4, src, inp):
    n = meta["nNeurons"]
    steps = meta["nSteps"]
    v = np.zeros(n, dtype=np.int64)
    raster = np.zeros((steps, n), dtype=bool)
    for s in range(steps):
        fired = raster[s - 1] if s else np.zeros(n, dtype=bool)
        mask = fired[src]
        current = np.bincount(indices[mask], weights=w4[mask] * WEIGHT_SCALE,
                              minlength=n).astype(np.int64)
        v = (v * DECAY_Q24) >> 24
        v += current + TONIC_Q24 + inp
        fired = v >= THRESHOLD_Q24
        v[fired] = 0
        raster[s] = fired
    return v, raster


def decode(inp, v, raster):
    n = len(inp)
    half = n // 2
    affirm_sum = int(inp[:half].sum())
    refute_sum = int(inp[half:].sum())
    total = affirm_sum + refute_sum
    diff = affirm_sum - refute_sum
    activity = int(v[v > 0].sum())
    spikes = int(raster.sum())
    digest = hashlib.blake2s(raster.tobytes() + v.tobytes()).hexdigest()
    if total <= 0 or diff == 0 or abs(diff) * 100 < 15 * total:
        return 0, 50, spikes, digest
    conf = min(100, 50 + activity // max(1, total // 50))
    return (1 if diff > 0 else -1), conf, spikes, digest


# ── verdict ───────────────────────────────────────────────────────────────

def input_said(features):
    canon = json.dumps(
        {k: features[k] for k in sorted(features)}, separators=(",", ":"))
    return "blake2s:" + hashlib.blake2s(canon.encode()).hexdigest()


def run_connectome(name, features):
    meta, indptr, indices, w4, src = load_connectome(name)
    inp = rasterize(features, meta["nNeurons"])
    v, raster = simulate(meta, indptr, indices, w4, src, inp)
    action, conf, spikes, digest = decode(inp, v, raster)
    return {
        "connectome": name,
        "input_said": input_said(features),
        "features": features,
        "action": action,
        "confidence": conf,
        "spike_count": spikes,
        "spike_digest": "blake2s:" + digest,
        "steps": meta["nSteps"],
        "encoder": ENCODER,
    }


def list_packed():
    return sorted(d for d in os.listdir(PACKED_DIR)
                  if os.path.exists(os.path.join(PACKED_DIR, d,
                                                 "metadata.json")))


def replay(verdict):
    again = run_connectome(verdict["connectome"], verdict["features"])
    same = (again["spike_digest"] == verdict["spike_digest"]
            and again["action"] == verdict["action"]
            and again["input_said"] == verdict["input_said"])
    return same, again


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--connectome", help="packed connectome name")
    ap.add_argument("--all", action="store_true",
                    help="run every packed connectome")
    ap.add_argument("--features", required=False,
                    help="JSON feature vector: confidence, event_rate, "
                         "env_anomaly, fleet_agreement (each 0..1)")
    ap.add_argument("--replay", metavar="FILE",
                    help="rerun verdict(s) from a JSONL file and verify "
                         "digests reproduce")
    ap.add_argument("--list", action="store_true",
                    help="list packed connectomes and exit")
    a = ap.parse_args()

    if a.list:
        for name in list_packed():
            meta = json.load(open(os.path.join(
                PACKED_DIR, name, "metadata.json")))
            print(f"{name}: {meta['nNeurons']} neurons, "
                  f"{meta['nSynapses']} synapses")
        return

    if a.replay:
        ok = True
        for line in open(a.replay):
            line = line.strip()
            if not line:
                continue
            v = json.loads(line)
            same, _ = replay(v)
            tag = "replay-ok" if same else "REPLAY-MISMATCH"
            print(f"{tag} {v['connectome']} "
                  f"action={v['action']} digest={v['spike_digest'][:16]}…")
            ok = ok and same
        sys.exit(0 if ok else 1)

    features = json.loads(a.features or "{}")
    names = list_packed() if a.all else [a.connectome or "celegans"]
    for name in names:
        print(json.dumps(run_connectome(name, features)))


if __name__ == "__main__":
    main()
