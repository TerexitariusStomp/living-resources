<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# tools/connectome — wiring diagrams as witnesses

`lif.py` runs deterministic LIF inference over the packed connectomes in
`~/fly-data/packed/<name>/` (int4 CSR blobs + `metadata.json`, produced
by fly.ai's `pack_connectomes.py`). Same step semantics as
`FlyEngine.sol`: decay → current+tonic+input → threshold → reset →
propagate, Q24 fixed-point.

```bash
python3 lif.py --list                                   # 15 packed connectomes
python3 lif.py --connectome celegans \
    --features '{"confidence":0.91,"event_rate":0.35,"env_anomaly":0.1,"fleet_agreement":1.0}'
python3 lif.py --all --features '{...}' > verdicts.jsonl  # one JSONL per wiring diagram
python3 lif.py --replay verdicts.jsonl                  # verify digests reproduce
```

Features (each 0..1): `confidence` (detector's), `event_rate` (vs lane's
expected rate), `env_anomaly` (context deviation), `fleet_agreement`
(sibling-leg agreement). The rasterizer splits affirm/refute across the
two half-populations with a documented blake2s per-neuron variation —
encoder id `lif-sensing-v1` rides every verdict. Per FlyEngine,
direction comes from the input split while the topology modulates
confidence and produces the unique spike digest — the digest is the
witness signature.

Verdicts feed the commons via `adapters/connectome.scm` →
`module/living/connectome.scm` → an optional `connectome-said` leg on
witnessed receipts. See `docs/CONNECTOME.md` for the evidence model and
its honesty table. `CONNECTOME_PACKED_DIR` overrides the blob path.

## bench.py — efficiency evidence

```bash
python3 bench.py run --connectome celegans --reps 30 --baselines > b.jsonl
python3 bench.py --replay b.jsonl    # op-counts + trace digests must reproduce
python3 bench.py compare b.jsonl     # ops/bytes/ms/joules per decision, tiered
```

Measures ops/decision (exact op-model), bytes/decision, wall/CPU/RSS,
and joules via RAPL when `energy_uj` is readable
(`sudo chmod 444 /sys/class/powercap/intel-rapl*/energy_uj` unlocks it;
otherwise a labeled estimate). Baselines: dense and sparse fp32 matmul
on the same silicon. Methodology + claim table: `docs/EFFICIENCY.md`.
