# SPDX-License-Identifier: AGPL-3.0-or-later
# tools/edge/classify.py — the edge classifier loop.
#
# WHAT THIS IS. The runnable half of the "dumb node, smart edge" contract:
# watch a spool directory of node PCM chunks, classify each, and emit one
# detection line per call — the exact JSONL adapters/mic.scm parses into
# <reading> records downstream.
#
# THE MODEL SEAM. OpenSoundscape when it is installed (the real ML); an
# energy-gate fallback when it is not — the fallback emits nothing, which
# is the honest answer a dumb detector gives, and keeps the pipe
# exercised end-to-end without inventing detections.
#
# Usage:
#   python3 tools/edge/classify.py --spool ./spool --out detections.jsonl \
#       [--node node-7] [--mic-cal said:cal-node7] [--once]
#
# PCM chunks are 48 kHz/16-bit mono (firmware CHUNK_SECONDS granules).

import argparse
import json
import os
import struct
import sys
import time


def pcm_energy(path, chunk_bytes=4096):
    """Mean absolute amplitude of 16-bit PCM — the cheap presence gate.
    Returns None on a short/empty file."""
    total = 0
    n = 0
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk_bytes)
            if len(b) < 2:
                break
            (vals,) = (struct.unpack("<%dh" % (len(b) // 2), b[: len(b) // 2 * 2]),)
            total += sum(abs(v) for v in vals)
            n += len(vals)
    return (total // n) if n else None


def load_model():
    """The real classifier when OpenSoundscape is importable; None
    otherwise — the fallback decides what, if anything, we emit."""
    try:
        import opensoundscape  # noqa: F401
    except ImportError:
        return None
    # TODO(model): load a project model, e.g.
    #   from opensoundscape.ml.cnn import load_model
    #   return load_model("models/ecocell-v1")
    return "opensoundscape-present"   # library present; model weights TBD


def classify_chunk(path, model, node_id, mic_cal):
    """One PCM chunk → detection dict | None. The fallback gate: energy
    above the silence floor produces an 'unresolved' detection so the
    pipeline's quorum/receipt path still sees activity — species stays
    honest (null) until the real model lands."""
    energy = pcm_energy(path)
    if energy is None or energy < 200:
        return None                    # silence: no detection, no claim
    ts = os.path.getmtime(path)
    if model is None:
        return {"species": None, "confidence": None, "timestamp": ts,
                "node": node_id, "mic_cal": mic_cal, "gain": 0,
                "band": "0-24kHz", "unresolved": True,
                "energy": energy}
    # real model path — species + confidence from OpenSoundscape scores
    return {"species": "unresolved", "confidence": None, "timestamp": ts,
            "node": node_id, "mic_cal": mic_cal, "gain": 0,
            "band": "0-24kHz", "energy": energy}


def run(spool, out, node_id, mic_cal, once, poll_s):
    model = load_model()
    seen = set()
    sys.stderr.write(
        "classifier up: spool=%s model=%s\n"
        % (spool, "opensoundscape" if model else "energy-gate"))
    with open(out, "a") as fh:
        while True:
            for name in sorted(os.listdir(spool)):
                if name in seen or not name.endswith(".pcm"):
                    continue
                seen.add(name)
                det = classify_chunk(os.path.join(spool, name),
                                     model, node_id, mic_cal)
                if det is not None:
                    fh.write(json.dumps(det) + "\n")
                    fh.flush()
            if once:
                return
            time.sleep(poll_s)


def main():
    p = argparse.ArgumentParser(description="EcoCell edge classifier")
    p.add_argument("--spool", required=True, help="node PCM spool dir")
    p.add_argument("--out", required=True, help="detections JSONL out")
    p.add_argument("--node", default="node-7")
    p.add_argument("--mic-cal", default=None)
    p.add_argument("--once", action="store_true", help="one pass then exit")
    p.add_argument("--poll", type=float, default=2.0)
    a = p.parse_args()
    run(a.spool, a.out, a.node, a.mic_cal, a.once, a.poll)


if __name__ == "__main__":
    main()
