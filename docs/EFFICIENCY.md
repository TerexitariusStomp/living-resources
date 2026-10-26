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
| joules/decision | RAPL `energy_uj` deltas per run window (package+core+uncore) once `sudo chmod 444 /sys/class/powercap/intel-rapl*/energy_uj` lands — wraparound-safe via `max_energy_range_uj`; windows extend to ≥100 ms so sub-ms workloads don't resolve to ~0 J | measured when readable, `estimated` (CPU-time × 15 W proxy, labeled) otherwise |
| wall/cpu/rss | perf_counter + getrusage + /proc | measured |

Baselines measured on the same core (pinned via `sched_setaffinity`):

- **dense-matmul** — fp32 n×n matvec, same I/O shape: n² MACs
- **sparse-matmul** — fp32 CSR on the connectome's own connectivity:
  isolates topology from data format

## First results — measured tier (RAPL, Intel Core Ultra 9 275HX)

Small wiring — celegans (302 neurons):

| subject | ops/decision | bytes | ms/decision | J/decision | tier |
|---|---:|---:|---:|---:|---|
| connectome:celegans | 35,346 | 7,825 | 0.090 | 3.31e-3 | measured |
| dense-matmul | 91,204 | 364,816 | 0.004 | 1.64e-4 | measured |
| sparse-matmul | 3,009 | 18,054 | 0.007 | 2.40e-4 | measured |

Large wiring — medulla (40,000 neurons):

| subject | ops/decision | bytes | ms/decision | J/decision | tier |
|---|---:|---:|---:|---:|---|
| connectome:medulla | 882,532 | 1,079,875 | 3.288 | 1.17e-1 | measured |
| dense-matmul | 1.6e9 | 6.4e9 | 103.733 | 8.30 | measured |
| sparse-matmul | 399,950 | 2,399,700 | 2.799 | 2.11e-1 | measured |

**What the numbers honestly say — a measured crossover:**

- **Footprint (win, all sizes):** packed wiring is 46× (celegans) to
  ~5,900× (medulla) smaller than fp32 dense weights — int4 CSR vs n².
- **Small scale (loss):** a Python-level LIF is ~20× slower and ~20×
  more joules than SIMD matmul at 302 neurons — interpreter overhead
  dominates; we report it, not hide it.
- **Large scale (measured win):** past ~10⁴ neurons the dense baseline's
  O(n²) cost inverts the table — medulla's connectome leg runs in
  **1.17e-1 J vs 8.30 J (~70× less energy) and 3.3 ms vs 104 ms**;
  it also beats the fp32 sparse baseline on joules because int4 packed
  data moves ~2.2× fewer bytes through memory.
- **Topology control (measured):** `--control` benches degree-matched
  *shuffled* wiring — same neurons, same out-degrees, same weights,
  random targets. Real and shuffled wiring are statistically identical
  on every axis (medulla 9.16e-2 vs 8.37e-2 J). **The efficiency is
  sparsity — established computer science, not a biological finding.**
  What real wiring contributes is the *specific* topology: the
  replayable signature, not the speed.
- The LIF's ~35k ops vs the sparse baseline's 3,009 MACs at celegans
  shows the temporal cost — ten steps of dynamics, not a one-shot
  transform. Different compute categories; the table reports both.

## Cited baseline columns (not measured here)

| Baseline | Published figure | Note |
|---|---|---|
| IBM TrueNorth | ~26 pJ / synaptic event (Merolla et al., *Science* 2014) | cited — neuromorphic silicon |
| Intel Loihi | ~23.6 pJ / synaptic op (Davies et al., *IEEE Micro* 2018/2021) | cited — purpose hardware |
| Biological synapse | ~1–100 pJ / event (literature range) | cited — the substrate the wiring came from |
| GPU datacenter | ~0.5–5 mJ / small matvec-class op (TDP × latency) | cited — categorical, batching makes per-op numbers context-dependent |
| Cortical CL1 / FinalSpark | vendor efficiency claims | cited — unverified by us |
| Human brain (event throughput) | ~10¹³–10¹⁶ ops/s on ~20 W (Merkle 1989 via Sandberg 2016, arXiv:1602.04019; Levy & Calvert, PNAS 2021) | cited — order-of-magnitude estimates; synaptic events ≠ FLOPs |
| Fastest supercomputer | 1,809 PFLOP/s Rmax at 29.7 MW (El Capitan, TOP500) | cited — reference point: brain ≈ 10×–10,000× more ops/W |
| Wetware I/O latency | sub-millisecond read/write cycles to 800k lab neurons (Cortical Labs CL1, shipping 2025) | cited — vendor-reported; lab-grown cells, not our substrate |
| DNA retrieval speed | 3,200× faster reconstruction, +40% accuracy (Bar-Lev et al., Nat. Mach. Intell. 2025) | cited — in-vitro pipeline; non-invasive in-vivo interface unknown |

## Claim table — exactly what is and isn't evidenced

| Claim | Status |
|---|---|
| Packed int4 CSR compute is algorithmically sparse (ops ≪ n² dense) | **measured** — counted, replayable |
| Footprint: packed wiring ≈ 46×–5,900× smaller than fp32 dense | **measured** — bytes are exact |
| At scale (≥~10⁴ neurons) connectome legs use fewer measured joules AND less wall-time than dense fp32 on this CPU | **measured** — medulla ~70× J, ~31× wall; consistent with established sparse-vs-dense complexity, not new science |
| The efficiency belongs to biological wiring specifically | **refuted by control** — degree-matched shuffled wiring is statistically identical; biology contributes the signature, not the speed |
| Small connectomes lose to SIMD numpy on J/decision | **measured** — interpreter overhead, reported not hidden |
| Deterministic task traces replay bit-for-bit | **measured** — `--replay` (15/15 legs) |
| On purpose hardware the same wiring would run at ~24 pJ/synop | **projected** — spike counts measured, J/spike cited; projection labeled |
| Wetware vendors' efficiency claims | **cited** — unverified |
| Biology beats silicon ~10×–10,000× on ops/W for event workloads | **cited** — published estimates, not our measurement; synaptic events ≠ FLOPs |
| Sub-millisecond wetware interfaces are commercially shipped | **cited** — vendor-reported (CL1) |
| Serial digital latency/throughput favors silicon today | **measured** — our API answers in ms on a Worker |

## E6 — the experiment

The benchmark IS the experiment: pass = the emitted bundle reproduces
identical op-counts and trace digests on `--replay` across two
independent runs, and every table cell carries its tier. See
`docs/EXPERIMENTS.md` E6.

## Run it

```bash
# unlock real joules once (survives until reboot):
sudo chmod 444 /sys/class/powercap/intel-rapl*/energy_uj
# persist across reboots: udev rule, e.g.
#   echo 'SUBSYSTEM=="powercap", ACTION=="add", \
#     RUN+="/bin/chmod 444 /sys/class/powercap/intel-rapl:*/energy_uj"' \
#     | sudo tee /etc/udev/rules.d/99-rapl-read.rules

python3 tools/connectome/bench.py run --connectome celegans --reps 30 --baselines > bench.jsonl
python3 tools/connectome/bench.py --replay bench.jsonl   # digests must reproduce
python3 tools/connectome/bench.py compare bench.jsonl    # the table
```
