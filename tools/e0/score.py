# SPDX-License-Identifier: AGPL-3.0-or-later
# tools/e0/score.py — the E0 blinded-validation scorer.
#
# WHAT THIS IS. The harness half of experiment E0 (docs/EXPERIMENTS.md):
# ground-truth labels in, our pipeline's detection JSONL in, precision /
# recall / confusion out — per declared taxa-scope. The validator scores
# blinded: this tool never shows which chunk was which during capture;
# it joins on window timestamps only.
#
# GROUND TRUTH. One label per window, CSV:
#   window_start,window_end,species
#   1792818000,1792818010,Turdus migratorius
#   1792818010,1792818020,<none>            # silence / non-target window
#
# DETECTIONS. classify.py's JSONL: {species, confidence, timestamp, node}.
# A detection with species null is an "unresolved" energy event — counted
# as activity, never as a correct ID.
#
# Usage:
#   python3 tools/e0/score.py --truth truth.csv --dets detections.jsonl \
#       [--tolerance-s 30] [--min-precision 0.7]

import argparse
import csv
import json
import sys
from collections import Counter


def load_truth(path):
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            rows.append({"start": float(r["window_start"]),
                         "end": float(r["window_end"]),
                         "species": r["species"] or None})
    return rows


def load_dets(path):
    dets = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                dets.append(json.loads(line))
    return dets


def det_for_window(dets, start, end, tol):
    """The highest-confidence detection overlapping a window, or None."""
    best = None
    for d in dets:
        ts = d.get("timestamp") or 0
        if start - tol <= ts <= end + tol:
            if best is None or (d.get("confidence") or 0) > (best.get("confidence") or 0):
                best = d
    return best


def score(truth, dets, tol, min_precision):
    tp = fp = fn = tn = 0
    confusion = Counter()
    for w in truth:
        d = det_for_window(dets, w["start"], w["end"], tol)
        got = d["species"] if d else None
        want = w["species"]
        if want is None:                    # silence window
            if got is None:
                tn += 1
            else:
                fp += 1
                confusion[("silence", got)] += 1
        else:
            if got == want:
                tp += 1
            elif got is None:
                fn += 1
            else:
                fp += 1
                fn += 1                  # wrong species: miss + false hit
                confusion[(want, got)] += 1
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    print("E0 score report")
    print("  windows: %d | tp=%d fp=%d fn=%d tn=%d"
          % (len(truth), tp, fp, fn, tn))
    print("  precision=%.3f  recall=%.3f" % (precision, recall))
    if confusion:
        print("  confusion (want → got):")
        for (want, got), n in confusion.most_common():
            print("    %-28s → %-24s ×%d" % (want or "silence",
                                             got or "none", n))
    verdict = "PASS" if precision >= min_precision else "FAIL"
    print("  verdict: %s (precision target %.3f)" % (verdict, min_precision))
    return 0 if verdict == "PASS" else 1


def main():
    p = argparse.ArgumentParser(description="E0 blinded scorer")
    p.add_argument("--truth", required=True)
    p.add_argument("--dets", required=True)
    p.add_argument("--tolerance-s", type=float, default=30)
    p.add_argument("--min-precision", type=float, default=0.7)
    a = p.parse_args()
    sys.exit(score(load_truth(a.truth), load_dets(a.dets),
                   a.tolerance_s, a.min_precision))


if __name__ == "__main__":
    main()
