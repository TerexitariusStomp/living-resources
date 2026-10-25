#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""bench.py — evidenced efficiency of connectome-compute vs machines.

Runs LIF workloads over the packed connectomes (via lif.py machinery)
and conventional baselines on the same silicon, and emits benchmark
legs (JSONL) + a SAIDed bundle: ops/decision counted exactly,
bytes/decision from the real formats, wall/CPU/RSS measured, and joules
from RAPL when the counters are readable (or a clearly-labeled estimate
when they are not — never a silent number).

Three efficiency axes:
  ops/decision   exact op-model count — update ops per neuron-step +
                 propagated synaptic events (the wiring computes only
                 its real edges; a dense matmul computes n^2)
  bytes/decision packed blob bytes vs baseline model weight bytes
  joules/decision RAPL package/core/uncore deltas per run ('measured'),
                 or CPU-time x proxy stamped 'estimated' when the
                 counters are unreadable (sudo chmod 444
                 /sys/class/powercap/intel-rapl*/energy_uj unlocks)

Baselines (measured on this machine):
  dense-matmul   fp32 n x n matvec of the same I/O shape — n^2 MACs
  sparse-matmul  fp32 CSR with the connectome's own connectivity —
                 isolates topology from data format

Every leg carries an honesty tier per axis (measured|estimated|cited).
A bundle that does not reproduce op-counts and trace digests on
--replay is flagged, never silently shipped.

  python3 tools/connectome/bench.py run --connectome celegans --reps 20
  python3 tools/connectome/bench.py run --all --reps 10 > bench.jsonl
  python3 tools/connectome/bench.py compare bench.jsonl
  python3 tools/connectome/bench.py --replay bench.jsonl
"""

import argparse
import hashlib
import json
import os
import platform
import resource
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lif

BENCH_ENCODER = "bench-v1"

# Op-model: per neuron per step — decay multiply, add synaptic current,
# add tonic+input, threshold compare, conditional reset = 5 counted ops.
# Each propagated synaptic event = 1 counted op (int add into current).
UPDATE_OPS = 5

RAPL_DOMAINS = {
    "package": "/sys/class/powercap/intel-rapl:0",
    "core": "/sys/class/powercap/intel-rapl:0:0",
    "uncore": "/sys/class/powercap/intel-rapl:0:1",
}


# ── measurement plumbing ─────────────────────────────────────────────────

def _rapl_read(path):
    try:
        return int(open(path).read())
    except (OSError, ValueError):
        return None


def rapl_available():
    return _rapl_read(RAPL_DOMAINS["package"] + "/energy_uj") is not None


def rapl_snapshot():
    """domain → energy_uj (or None if unreadable). Wraparound handled by
    delta() using each domain's max_energy_range_uj."""
    snap = {}
    for name, path in RAPL_DOMAINS.items():
        e = _rapl_read(path + "/energy_uj")
        m = _rapl_read(path + "/max_energy_range_uj")
        snap[name] = (e, m)
    return snap


def rapl_delta(before, after):
    out = {}
    for name in RAPL_DOMAINS:
        b, m = before[name]
        a, _ = after[name]
        if a is None or b is None:
            out[name] = None
        elif a >= b:
            out[name] = a - b
        else:  # counter wrapped
            out[name] = (m - b) + a if m else None
    return out


def rss_kb():
    with open("/proc/self/status") as fh:
        for line in fh:
            if line.startswith("VmRSS:"):
                return int(line.split()[1])
    return 0


def cpu_time_ms():
    r = resource.getrusage(resource.RUSAGE_SELF)
    return (r.ru_utime + r.ru_stime) * 1000.0


def pin_single_core():
    try:
        os.sched_setaffinity(0, {0})
        return True
    except (OSError, AttributeError):
        return False


# ── workloads ─────────────────────────────────────────────────────────────

def lif_workload(name, features):
    """Load once; each rep is one full task (rasterize + simulate)."""
    meta, indptr, indices, w4, src = lif.load_connectome(name)
    inp = lif.rasterize(features, meta["nNeurons"])
    outdeg = np.diff(indptr)

    def rep():
        v, raster = lif.simulate(meta, indptr, indices, w4, src, inp)
        return v, raster

    # exact op counts — computed once from a probe rep
    v, raster = rep()
    ops_prop = int((raster[:-1] * outdeg).sum())
    ops = meta["nNeurons"] * meta["nSteps"] * UPDATE_OPS + ops_prop
    digest = hashlib.blake2s(raster.tobytes() + v.tobytes()).hexdigest()

    return {
        "subject": f"connectome:{name}",
        "rep": rep,
        "ops_per_decision": ops,
        "bytes": meta["totalSize"],
        "spikes": int(raster.sum()),
        "trace_digest": "blake2s:" + digest,
    }


def dense_workload(name):
    """fp32 n x n dense matvec — same I/O shape as the connectome."""
    meta = json.load(open(os.path.join(lif.PACKED_DIR, name,
                                       "metadata.json")))
    n = meta["nNeurons"]
    rng = np.random.default_rng(7)
    W = rng.standard_normal((n, n), dtype=np.float32)
    x = rng.standard_normal(n, dtype=np.float32)

    def rep():
        return W @ x

    return {"subject": f"dense-matmul:{name}",
            "rep": rep,
            "ops_per_decision": n * n,
            "bytes": n * n * 4,
            "spikes": None,
            "trace_digest": None}


def sparse_workload(name):
    """fp32 CSR matvec on the connectome's own connectivity —
    same edges, conventional format."""
    meta, indptr, indices, w4, src = lif.load_connectome(name)
    n = meta["nNeurons"]
    w = w4.astype(np.float32)
    x = np.random.default_rng(3).standard_normal(n).astype(np.float32)

    def rep():
        return np.add.reduceat(w * x[indices],
                               np.unique(indptr[:-1]))

    return {"subject": f"sparse-matmul:{name}",
            "rep": rep,
            "ops_per_decision": int(meta["nSynapses"]),
            "bytes": int(meta["nSynapses"]) * 6,  # fp32 val + u16 idx
            "spikes": None,
            "trace_digest": None}


# ── measurement ───────────────────────────────────────────────────────────

def measure(work, reps):
    """REPS consecutive reps inside one measurement window."""
    before = rapl_snapshot()
    cpu0 = cpu_time_ms()
    rss0 = rss_kb()
    t0 = time.perf_counter()
    for _ in range(reps):
        work["rep"]()
    wall_ms = (time.perf_counter() - t0) * 1000.0
    cpu_ms = cpu_time_ms() - cpu0
    rss_peak = max(rss_kb(), rss0)
    d = rapl_delta(before, rapl_snapshot())

    tier = "measured" if d.get("package") is not None else "estimated"
    if d.get("package") is not None:
        j = {k: round(v / reps / 1e6, 9) for k, v in d.items()
             if v is not None}
    else:
        # Labeled estimate: measured CPU-time x a 15 W package proxy for
        # this CPU class. Model, not measurement — stamped 'estimated'.
        j = {"package_est": round(cpu_ms / 1000.0 * 15.0 / reps, 9)}

    return {
        "wall_ms_per": round(wall_ms / reps, 6),
        "cpu_ms_per": round(cpu_ms / reps, 6),
        "rss_kb": rss_peak,
        "joules": j,
        "energy_tier": tier,
    }


def run_leg(work, features, reps):
    m = measure(work, reps)
    return {
        "bench": BENCH_ENCODER,
        "subject": work["subject"],
        "features": features,
        "reps": reps,
        "ops_per_decision": work["ops_per_decision"],
        "bytes": work["bytes"],
        "spikes": work["spikes"],
        "trace_digest": work["trace_digest"],
        **m,
    }


def env_block():
    return {
        "cpu": platform.processor() or "unknown",
        "machine": platform.machine(),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pinned": pin_single_core(),
        "rapl": rapl_available(),
        "bench": BENCH_ENCODER,
    }


def bundle_said(legs, env):
    canon = json.dumps({"env": env, "legs": legs},
                       sort_keys=True, separators=(",", ":"))
    return "blake2s:" + hashlib.blake2s(canon.encode()).hexdigest()


# ── compare ───────────────────────────────────────────────────────────────

def compare(path):
    legs = [json.loads(l) for l in open(path) if l.strip()]
    legs = [l for l in legs if "subject" in l]
    legs.sort(key=lambda l: (l["subject"].split(":")[-1], l["subject"]))
    print(f"{'subject':28} {'ops/dec':>10} {'bytes':>10} "
          f"{'ms/dec':>10} {'J/dec':>14} tier")
    for l in legs:
        j = l["joules"]
        jv = j.get("package", j.get("package_est"))
        js = f"{jv:.2e}" if jv is not None else "—"
        print(f"{l['subject']:28} {l['ops_per_decision']:>10} "
              f"{l['bytes']:>10} {l['wall_ms_per']:>10.3f} "
              f"{js:>14} {l['energy_tier']}")
    print("\ntiers: measured = RAPL counter deltas | "
          "estimated = CPU-time x 15W proxy (model, not measurement)")


def replay(path):
    ok = True
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        leg = json.loads(line)
        if "subject" not in leg:
            continue  # bundle/trailer lines
        if not leg["subject"].startswith("connectome:"):
            print(f"skip {leg['subject']} (baseline — no trace digest)")
            continue
        name = leg["subject"].split(":", 1)[1]
        work = lif_workload(name, leg["features"])
        same = (work["ops_per_decision"] == leg["ops_per_decision"]
                and work["trace_digest"] == leg["trace_digest"])
        print(f"{'replay-ok' if same else 'REPLAY-MISMATCH'} "
              f"{leg['subject']} ops={leg['ops_per_decision']}")
        ok = ok and same
    sys.exit(0 if ok else 1)


def main():
    ap = argparse.ArgumentParser(description="connectome efficiency bench")
    sub = ap.add_subparsers(dest="cmd")

    run = sub.add_parser("run")
    run.add_argument("--connectome")
    run.add_argument("--all", action="store_true")
    run.add_argument("--reps", type=int, default=20)
    run.add_argument("--features",
                     default='{"confidence":0.85,"event_rate":0.4,'
                             '"env_anomaly":0.15,"fleet_agreement":0.9}')
    run.add_argument("--baselines", action="store_true",
                     help="also measure dense/sparse matmul references")

    cmp_ = sub.add_parser("compare")
    cmp_.add_argument("legs")
    ap.add_argument("--replay", metavar="FILE",
                    help="re-run connectome legs and verify digests")

    a = ap.parse_args()

    if a.replay:
        replay(a.replay)
        return
    if a.cmd == "compare":
        compare(a.legs)
        return

    if a.cmd != "run":
        ap.print_help()
        return

    features = json.loads(a.features)
    env = env_block()
    names = lif.list_packed() if a.all else [a.connectome or "celegans"]
    legs = []
    for name in names:
        works = [lif_workload(name, features)]
        if a.baselines:
            works += [dense_workload(name), sparse_workload(name)]
        for w in works:
            w["rep"]()  # warmup
            leg = run_leg(w, features, a.reps)
            leg["env"] = env
            legs.append(leg)
            print(json.dumps(leg))
    print(json.dumps({"bench_bundle_said": bundle_said(legs, env),
                      "legs": len(legs), "env": env}))


if __name__ == "__main__":
    main()
