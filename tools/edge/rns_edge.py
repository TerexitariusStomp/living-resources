# SPDX-License-Identifier: AGPL-3.0-or-later
# tools/edge/rns_edge.py — the real Reticulum edge.
#
# WHAT THIS IS. The LXMF half of adapters/reticulum.scm, running the
# actual RNS stack: a Reticulum identity announces itself to the mesh,
# real RNS peers (RNode gateways, remote edges, MicroReticulum C++
# firmware variants) deliver packets, and each detection lands as one
# JSONL line — the exact format adapters/mic.scm parses into <reading>.
#
# NODE PATHS. Our MicroPython nodes speak the DET1/AUD1 UDP frames and
# reach this daemon two ways: (a) directly — a UDPInterface carrying raw
# frames to the socket listener in adapters/reticulum.scm, or (b) via an
# RNode/Reticulum hop — real RNS packets arriving here. Both end in the
# same JSONL stream; the gate downstream treats them identically.
#
# Reticulum license note: detection traffic passes through this process
# and is written to the detection ledger for attestation — it is never
# retained for or fed into ML training, per the RNS license terms.
#
# Usage:
#   python3 tools/edge/rns_edge.py --out detections.jsonl \
#       [--identity .edge_id] [--announce-every 60]

import argparse
import json
import os
import sys
import time

import RNS
import LXMF

from durable_ingest import DurableIngest, frame_node
from task_queue import poll_task_file, node_task_dests


def load_or_make_identity(path):
    """The edge's Reticulum identity, persisted across restarts so the
    announced destination hash stays stable for field nodes."""
    if os.path.exists(path):
        with open(path, "rb") as f:
            return RNS.Identity.from_bytes(f.read())
    ident = RNS.Identity()
    with open(path, "wb") as f:
        f.write(ident.get_private_key())
    return ident


def packet_to_detection(body):
    """An LXMF/plain RNS body → record dict | None. Small tagged records
    (DET1/ENV1/RES1/GAP1) have the tag stripped; AUC1 is handled by
    DurableIngest before this legacy JSON parser runs. ENV1 records —
    they land in the same ledger but must never be read as detections
    downstream; consumers filter on the kind field."""
    if isinstance(body, bytes):
        if body[:4] in (b"DET1", b"ENV1", b"RES1", b"GAP1"):
            body = body[4:]
        try:
            body = body.decode()
        except UnicodeDecodeError:
            return None
    try:
        d = json.loads(body)
    except (ValueError, TypeError):
        return None
    if not isinstance(d, dict) or "node" not in d:
        return None
    return d


def _source_destination(msg):
    """Best-effort LXMF reply destination for the message's source."""
    src = getattr(msg, "source", None)
    if src is None and hasattr(msg, "get_source"):
        try:
            src = msg.get_source()
        except Exception:
            src = None
    if src is None:
        ident = RNS.Identity.recall(msg.source_hash)
        if ident is None:
            return None
        src = RNS.Destination(ident, RNS.Destination.OUT,
                              RNS.Destination.SINGLE, "lxmf", "delivery")
    return src


def _send_dest(router, local_dest, dest, payload):
    reply = LXMF.LXMessage(dest, local_dest, payload,
                           desired_method=LXMF.LXMessage.OPPORTUNISTIC)
    router.handle_outbound(reply)


def _send_reply(router, local_dest, msg, payload):
    src = _source_destination(msg)
    if src is None:
        return False
    try:
        _send_dest(router, local_dest, src, payload)
        return True
    except Exception as e:
        RNS.log("LXMF reply failed: %s" % e, RNS.LOG_ERROR)
        return False


def run(out_path, identity_path, announce_every, store_path, task_file=None):
    RNS.Reticulum()
    ident = load_or_make_identity(identity_path)
    os.makedirs(os.path.join(os.path.dirname(identity_path) or ".",
                             "lxmf_store"), exist_ok=True)
    router = LXMF.LXMRouter(
        storagepath=os.path.join(os.path.dirname(identity_path) or ".",
                                 "lxmf_store"))
    dest = router.register_delivery_identity(ident, display_name="ecocell-edge")

    ingest = DurableIngest(store_path, out_path)
    offsets, queue, destinations = {}, {}, {}

    def on_message(msg):
        body = msg.content.encode() if isinstance(msg.content, str) else msg.content
        source = msg.source_hash.hex() if getattr(msg, "source_hash", None) else "unknown"
        node = frame_node(body)
        src = _source_destination(msg)
        if node and src is not None:
            destinations[node] = src
        ack = ingest.handle_frame(body, source)
        if ack:
            _send_reply(router, dest, msg,
                        json.dumps(ack, separators=(",", ":")).encode())
        for key, task_dest in node_task_dests(queue, node, destinations):
            for task in queue.get(key, ()):
                try:
                    _send_dest(router, dest, task_dest,
                               json.dumps(task, separators=(",", ":")).encode())
                except Exception as e:
                    RNS.log("task send failed: %s" % e, RNS.LOG_ERROR)
            queue.pop(key, None)
        if ack:
            return
        det = packet_to_detection(body)
        if det is not None:
            det["edge_ts"] = time.time()
            det["via"] = "lxmf"
            ingest.ledger.write(json.dumps(det) + "\n")
            ingest.ledger.flush()
            os.fsync(ingest.ledger.fileno())
        RNS.log("rx %s" % (det["node"] if det else "undecodable"),
                RNS.LOG_VERBOSE)

    router.register_delivery_callback(on_message)
    dest.announce()
    sys.stderr.write("edge up: destination %s → %s\n"
                     % (RNS.prettyhexrep(dest.hash), out_path))

    while True:
        poll_task_file(task_file, offsets, queue)
        time.sleep(announce_every)
        dest.announce()          # re-announce so late-joining nodes find us


def main():
    p = argparse.ArgumentParser(description="EcoCell Reticulum edge")
    p.add_argument("--out", required=True)
    p.add_argument("--identity", default=".edge_id")
    p.add_argument("--store", default=".edge_ingest",
                   help="durable receipt/reassembly directory")
    p.add_argument("--announce-every", type=int, default=60)
    p.add_argument("--tasks", help="append-only node task JSONL")
    a = p.parse_args()
    run(a.out, a.identity, a.announce_every, a.store, a.tasks)


if __name__ == "__main__":
    main()
