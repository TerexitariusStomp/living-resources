# SPDX-License-Identifier: AGPL-3.0-or-later
# tools/edge/uplink.py — edge→cloud onward path for committed records.
#
# Tails the durable ledger (the JSONL udp_edge.py commits) and POSTs
# batches to any HTTPS receiver — the compute-api's POST /ingest route
# (workers/compute-api, content-addressed ingest/ keys), a Worker
# webhook, or a peer edge. Keep --batch ≤ 20 against /ingest: the free
# plan's 50-subrequest cap means 20 records × get+put is the ceiling. Records already carry
# "via" (the backhaul label udp_edge stamped) so provenance survives
# the hop. Offset state makes restarts idempotent: lines are sent
# once, in order; the receiver dedupes on item_id/sha as designed.
#
#   python3 uplink.py --ledger ledger.jsonl --target https://…/ingest

import argparse
import json
import os
import sys
import time
import urllib.request


def load_offset(path):
    try:
        return int(open(path).read().strip())
    except Exception:
        return 0


def save_offset(path, n):
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        fh.write(str(n))
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def post_batch(target, records, timeout=15):
    body = json.dumps({"records": records},
                      separators=(",", ":")).encode()
    req = urllib.request.Request(
        target, data=body,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status


def run(ledger, target, state, interval, batch, once=False):
    offset = load_offset(state)
    size = os.path.getsize(ledger) if os.path.exists(ledger) else 0
    if offset > size:
        offset = 0                       # ledger rotated: start over
    sys.stderr.write("uplink: %s → %s (offset %d)\n"
                     % (ledger, target, offset))
    pending = []
    pos = offset
    while True:
        if os.path.exists(ledger):
            with open(ledger, "rb") as fh:
                fh.seek(pos)
                for raw in fh:
                    line = raw.strip()
                    pos = fh.tell()
                    if not line:
                        continue
                    try:
                        pending.append(json.loads(line))
                    except ValueError:
                        continue
                if len(pending) >= batch:
                    if _flush(target, pending):
                        save_offset(state, pos)
                    pending = []
        if once:
            if pending and _flush(target, pending):
                save_offset(state, pos)
            return
        if pending and len(pending) < batch:
            time.sleep(interval)          # let the batch fill
            continue
        time.sleep(interval)


def _flush(target, records):
    for attempt in range(5):
        try:
            post_batch(target, records)
            return True
        except Exception as e:
            sys.stderr.write("uplink retry %d: %s\n" % (attempt + 1, e))
            time.sleep(min(2 ** attempt, 30))
    sys.stderr.write("uplink: %d records dropped after retries\n"
                     % len(records))
    # caller still advances the offset — a poisoned record must not
    # wedge the tail; the ledger remains the durable copy.
    return True


def main():
    p = argparse.ArgumentParser(description="EcoCell edge→cloud uplink")
    p.add_argument("--ledger", required=True)
    p.add_argument("--target", required=True,
                   help="HTTPS endpoint accepting {\"records\":[...]}")
    p.add_argument("--state", default=".uplink_offset")
    p.add_argument("--interval", type=float, default=5.0)
    p.add_argument("--batch", type=int, default=50)
    p.add_argument("--once", action="store_true")
    a = p.parse_args()
    run(a.ledger, a.target, a.state, a.interval, a.batch, a.once)


if __name__ == "__main__":
    main()
