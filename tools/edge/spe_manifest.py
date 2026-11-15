# SPDX-License-Identifier: AGPL-3.0-or-later
# tools/edge/spe_manifest.py — SPE cassette chain-of-custody manifests.
#
# Passive solid-phase-extraction cassettes collect the analytes no
# in-situ sensor can honestly measure (Se, metals, pesticides, organics)
# for later lab elution. There is no sensor and no firmware — the only
# artifact is the custody record. Each lifecycle event is a JSONL line
# hash-chained to the previous one (prev = sha256 of the last event),
# so a swapped, edited, or reordered entry breaks the chain.
#
# Events: issue → deploy → retrieve → ship → receive → assay. Any
# key=value fields ride along (site, depth_m, operator, lab, ref…).
#
# Usage:
#   spe_manifest.py cassette-42.jsonl issue  cassette=SPX-42 operator=tk
#   spe_manifest.py cassette-42.jsonl deploy site=alamo-terminus depth_m=0.4
#   spe_manifest.py cassette-42.jsonl assay  lab=abc-labs ref=L-991
#   spe_manifest.py cassette-42.jsonl verify

import hashlib
import json
import sys
import time

EVENTS = ("issue", "deploy", "retrieve", "ship", "receive", "assay")


def _sha(blob):
    return hashlib.sha256(blob).hexdigest()


def _last(path):
    """(prev_sha, event_count) — the chain head, or ("", 0) if empty."""
    prev, n = "", 0
    try:
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if line:
                    prev, n = _sha(line.encode()), n + 1
    except FileNotFoundError:
        pass
    return prev, n


def make_event(prev_sha, event, fields, ts=None):
    rec = {"kind": "spe-event", "event": event, "prev": prev_sha,
           "ts": ts if ts is not None else int(time.time())}
    rec.update(fields)
    return rec


def append_event(path, event, fields):
    if event not in EVENTS:
        raise ValueError("unknown event %r — one of %s" % (event, EVENTS))
    prev, _ = _last(path)
    rec = make_event(prev, event, fields)
    with open(path, "a") as fh:
        fh.write(json.dumps(rec, separators=(",", ":")) + "\n")
        fh.flush()
        try:
            import os
            os.fsync(fh.fileno())
        except OSError:
            pass
    return rec


def verify(path):
    """Re-walk the chain: every line's prev must equal the sha of the
    raw previous line. Returns (ok, count, problem-index|None)."""
    prev, n = "", 0
    try:
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if rec.get("prev") != prev:
                    return False, n, n
                prev, n = _sha(line.encode()), n + 1
    except FileNotFoundError:
        return False, 0, 0
    return True, n, None


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) < 2:
        print(__doc__.splitlines()[-8], file=sys.stderr)
        return 2
    path, cmd = argv[0], argv[1]
    if cmd == "verify":
        ok, n, bad = verify(path)
        print("%s: %d events%s" %
              ("OK" if ok else "BROKEN", n,
               "" if ok else " — first bad at line %d" % (bad + 1)))
        return 0 if ok else 1
    fields = {}
    for pair in argv[2:]:
        k, _, v = pair.partition("=")
        fields[k] = v
    rec = append_event(path, cmd, fields)
    print(json.dumps(rec, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
