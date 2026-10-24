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
    """An LXMF/plain RNS body → detection dict | None. Accepts the same
    shapes the UDP path carries: a JSON object, or the DET1 frame the
    firmware emits (tag stripped)."""
    if isinstance(body, bytes):
        if body[:4] == b"DET1":
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


def run(out_path, identity_path, announce_every):
    RNS.Reticulum()
    ident = load_or_make_identity(identity_path)
    os.makedirs(os.path.join(os.path.dirname(identity_path) or ".",
                             "lxmf_store"), exist_ok=True)
    router = LXMF.LXMRouter(
        storagepath=os.path.join(os.path.dirname(identity_path) or ".",
                                 "lxmf_store"))
    dest = router.register_delivery_identity(ident, display_name="ecocell-edge")

    fh = open(out_path, "a")

    def on_message(msg):
        det = packet_to_detection(msg.content)
        if det is not None:
            det["edge_ts"] = time.time()
            det["via"] = "lxmf"
            fh.write(json.dumps(det) + "\n")
            fh.flush()
        RNS.log("rx %s" % (det["node"] if det else "undecodable"),
                RNS.LOG_VERBOSE)

    router.register_delivery_callback(on_message)
    dest.announce()
    sys.stderr.write("edge up: destination %s → %s\n"
                     % (RNS.prettyhexrep(dest.hash), out_path))

    while True:
        time.sleep(announce_every)
        dest.announce()          # re-announce so late-joining nodes find us


def main():
    p = argparse.ArgumentParser(description="EcoCell Reticulum edge")
    p.add_argument("--out", required=True)
    p.add_argument("--identity", default=".edge_id")
    p.add_argument("--announce-every", type=int, default=60)
    a = p.parse_args()
    run(a.out, a.identity, a.announce_every)


if __name__ == "__main__":
    main()
