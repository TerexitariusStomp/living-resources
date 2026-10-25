<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# EFFICIENCY — evidenced efficiency of connectome-compute

How efficient is compute over packed biological wiring diagrams,
*measured and receipted* — not claimed. Every number below carries an
honesty tier (**measured** | **estimated** | **cited**); the bundle is
replay-verifiable; unfavorable cells ship alongside favorable ones —
that asymmetry is what makes the favorable ones credible.

## The two claims that must never blur

1. **Simulated-on-silicon** — LIF over int4 CSR on x86, what we actually
   run. Expected profile: wins on algorithmic parsimony and footprint,
   loses to SIMD on wall-joules. We report whatever the counters say.
2. **Substrate projection** — measured spike counts × published
   J/spike → the "biological neurons are efficient" story. A labeled
   extrapolation, never presented as a measurement.

## Method

`tools/connectome/bench.py` drives `lif.py`'s packed-blob decode and
LIF simulate as the system under test, plus numpy baselines:

| Axis | Method | Tier |
|---|---|---|
| ops/decision | exact op-model: `n_neurons × n_steps × 5` update ops + Σ out-degree of every fired neuron (counted from the raster) | measured (counted) |
| bytes/decision | packed blob bytes vs fp32 weight bytes | measured |
| joules/decision | RAPL `energy_uj` deltas per run window (package+core+uncore) once `sudo chmod 444 /sys/class/powercap/intel-rapl*/energy_uj` lands — wraparound-safe via `max_energy_range_uj` | measured when readable, `estimated` (CPU-time × 15 W proxy, labeled) otherwise |
| wall/cpu/rss | perf_counter + getrusage + /proc | measured |

Baselines measured on the same core (pinned via `sched_setaffinity`):

- **dense-matmul** — fp32 n×n matvec, same I/O shape: n² MACs
- **sparse-matmul** — fp32 CSR on the connectome's own connectivity:
  isolates topology from data format

## First results (celegans, 302 neurons — estimated tier until RAPL)

| subject | ops/decision | bytes | ms/decision | J/decision | tier |
|---|---:|---:|---:|---:|---|
| connectome:celegans | 35,346 | 7,825 | 0.102 | ~1.5e-3 | estimated |
| dense-matmul | 91,204 | 364,816 | 0.005 | ~7.8e-5 | estimated |
| sparse-matmul | 3,009 | 18,054 | 0.022 | ~3.3e-4 | estimated |

**What the numbers honestly say:** the packed wiring is **46× denser**
than the equivalent fp32 weights and does **2.6× fewer counted ops**
than the dense transform — but a Python-level simulator is ~20× slower
on wall-time than SIMD matmul. The sparse baseline's 3,009 MACs (one
matvec) vs the LIF's ~35k ops shows the LIF's *temporal* cost: ten
steps of dynamics, not a one-shot transform. These are different
compute categories; the table reports both rather than picking a
flattering axis.

## Cited baseline columns (not measured here)

| Baseline | Published figure | Note |
|---|---|---|
| IBM TrueNorth | ~26 pJ / synaptic event (Merolla et al., *Science* 2014) | cited — neuromorphic silicon |
| Intel Loihi | ~23.6 pJ / synaptic op (Davies et al., *IEEE Micro* 2018/2021) | cited — purpose hardware |
| Biological synapse | ~1–100 pJ / event (literature range) | cited — the substrate the wiring came from |
| GPU datacenter | ~0.5–5 mJ / small matvec-class op (TDP × latency) | cited — categorical, batching makes per-op numbers context-dependent |
| Cortical CL1 / FinalSpark | vendor efficiency claims | cited — unverified by us |

## Claim table — exactly what is and isn't evidenced

| Claim | Status |
|---|---|
| Packed int4 CSR compute is algorithmically sparse (ops ≪ n² dense) | **measured** — counted, replayable |
| Footprint: packed wiring ≈ 46× smaller than fp32 dense weights | **measured** — bytes are exact |
| Deterministic task traces replay bit-for-bit | **measured** — `--replay` |
| Connectome-compute is energy-cheaper than SIMD on this CPU | **not claimed** — Python simulator pays interpreter overhead; measured/estimated cells say so |
| On purpose hardware the same wiring would run at ~24 pJ/synop | **projected** — spike counts measured, J/spike cited; projection labeled |
| Wetware vendors' efficiency claims | **cited** — unverified |

## E6 — the experiment

The benchmark IS the experiment: pass = the emitted bundle reproduces
identical op-counts and trace digests on `--replay` across two
independent runs, and every table cell carries its tier. See
`docs/EXPERIMENTS.md` E6.

## Run it

```bash
# unlock real joules once (survives until reboot):
sudo chmod 444 /sys/class/powercap/intel-rapl*/energy_uj

python3 tools/connectome/bench.py run --connectome celegans --reps 30 --baselines > bench.jsonl
python3 tools/connectome/bench.py --replay bench.jsonl   # digests must reproduce
python3 tools/connectome/bench.py compare bench.jsonl    # the table
```
