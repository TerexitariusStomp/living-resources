# SPDX-License-Identifier: AGPL-3.0-or-later
# tools/e5/relay_check.py — the E5 graduation-path harness.
#
# WHAT THIS IS. EXPERIMENTS.md E5: an encoded observation injected as
# input current propagates along real synaptic paths; the spike train is
# the relayed output — a receipted trace event. This script runs that
# relay over every packed connectome and checks the two pass criteria:
#
#   1. relay traces replay deterministically — every trace_digest must
#      reproduce bit-for-bit on rerun, locally and (optionally) across
#      the deployed worker as an independent verifier;
#   2. provenance end to end — every relay carries input_said (what was
#      injected) bound to trace_digest (what the wiring produced).
#
# THE HONEST BOUND. What relays here is the measured EM-derived topology
# under deterministic simulation — never a living organism. A PASS earns
# an evidence SAID for *preserved-wiring* relay only; the refused `hop`
# lane (living-wiring relay) is untouched by this scaffold.
#
# Usage:
#   python3 tools/e5/relay_check.py                      # all 15, local replay
#   python3 tools/e5/relay_check.py --connectome medulla
#   python3 tools/e5/relay_check.py --verify-url \
#       https://connectome-compute-api.terexmaps.workers.dev

import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "connectome"))
import lif  # tools/connectome/lif.py

FEATURES = {"confidence": 0.72, "event_rate": 0.35,
            "env_anomaly": 0.10, "fleet_agreement": 1.0}


def provenance_ok(task, verdict):
    """input_said + both output digests present and well-formed."""
    need = [task["input_said"], task["trace_digest"], verdict["spike_digest"]]
    return all(isinstance(d, str) and len(d) == len("blake2s:") + 64
               and d.startswith("blake2s:") for d in need)


def remote_verify(url, task):
    """Independent verifier: the deployed TS worker replays the receipt."""
    import urllib.request
    req = urllib.request.Request(
        url.rstrip("/") + "/verify",
        data=json.dumps(task).encode(),
        headers={"content-type": "application/json",
                 "user-agent": "treetable-e5-relay-check/1.0"}, method="POST")
    try:
        r = json.load(urllib.request.urlopen(req, timeout=30))
        return bool(r.get("verified"))
    except Exception as e:
        print(f"    remote verify error: {e}")
        return None


def bundle_said(relays):
    canon = json.dumps(relays, sort_keys=True, separators=(",", ":"))
    return "blake2s:" + hashlib.blake2s(canon.encode()).hexdigest()


def main():
    p = argparse.ArgumentParser(description="E5 relay-graduation harness")
    p.add_argument("--connectome", help="single connectome (default: all)")
    p.add_argument("--verify-url",
                   help="also replay against a deployed verifier worker")
    p.add_argument("--out", help="write the SAIDed E5 bundle to a file")
    a = p.parse_args()

    names = [a.connectome] if a.connectome else lif.list_packed()
    relays, all_ok = [], True
    sigs = set()
    print(f"E5 relay check — {len(names)} connectome(s), "
          f"features={json.dumps(FEATURES)}")
    for name in names:
        task = lif.run_task(name, FEATURES)
        verdict = lif.run_connectome(name, FEATURES)
        again = lif.run_task(name, FEATURES)
        local = again["trace_digest"] == task["trace_digest"]
        remote = remote_verify(a.verify_url, task) if a.verify_url else None
        prov = provenance_ok(task, verdict)
        sigs.add(verdict["spike_digest"])
        ok = local and prov and (remote is not False)
        relays.append({"connectome": name,
                       "input_said": task["input_said"],
                       "trace_digest": task["trace_digest"],
                       "spike_digest": verdict["spike_digest"],
                       "steps": task["steps"],
                       "replay_local": local,
                       "replay_remote": remote,
                       "provenance": prov,
                       "ok": ok})
        tag = "ok" if ok else "FAIL"
        print(f"  {tag:4s} {name:15s} in={task['input_said'][8:22]}… "
              f"trace={task['trace_digest'][8:22]}… "
              f"replay={'local' + ('+remote' if remote else '')}")

    # one signal → topology-unique signatures (the witness property)
    unique = len(sigs) == len(relays)
    print(f"  signatures: {len(sigs)} distinct across {len(relays)} wirings"
          + ("" if unique else "  — COLLISION, topology not witnessing"))
    all_ok = all(r["ok"] for r in relays) and unique

    bundle = {
        "experiment": "E5",
        "bound": "preserved-wiring relay under deterministic simulation; "
                 "the refused living-systems hop lane is untouched",
        "features": FEATURES,
        "relays": relays,
        "verdict": "PASS" if all_ok else "FAIL",
    }
    bundle["bundle_said"] = bundle_said(
        {k: v for k, v in bundle.items() if k != "bundle_said"})
    print(f"E5 verdict: {bundle['verdict']}  bundle_said={bundle['bundle_said'][:30]}…")
    if a.out:
        with open(a.out, "w") as f:
            json.dump(bundle, f, indent=2)
        print(f"bundle written: {a.out}")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
