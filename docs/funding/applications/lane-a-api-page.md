<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# Replay-verified compute API — product draft

## The API

```
POST /task
  {"connectome": "celegans",
   "input": [0.85, 0.4, 0.15, 0.9]}          # raw vector or feature map
→ {"verdict": {...}, "trace_digest": "blake2s:...",
   "receipt": "said:...", "replay_url": "..."}
GET /replay/{task_id}
→ recompute → {"verified": true, "digest": "..."}
```

Deterministic LIF inference over 15 packed real-organism connectomes
(302 → 40,000 neurons). Every task emits a trace digest; any caller can
replay it — the computation is the proof.

## Why anyone pays

- **Reproducibility-sensitive science**: cite a computation that can be
  re-executed, not re-trusted
- **Audit/compliance tooling**: a task receipt that stands on its own
- **Education/research**: real EM-derived wiring as a compute substrate
- **Wetware-adjacent**: the verifiable layer biological compute lacks

## Pricing (free-tier CF Workers, ~$0 marginal cost)

| Tier | | |
|---|---|---|
| Free | 100 tasks/mo — seeds verification habit | $0 |
| Lab | 10k tasks/mo + private bundles | $99/mo |
| Registry | standing task registry, co-branded receipts | $499/mo |

## Build checklist (the only work left)

- [ ] CF Worker wrapping `tools/connectome/lif.py` logic (port LIF core
      to TS/WASM or call a cheap container — packed blobs are ≤1.1MB)
- [ ] `/replay` endpoint re-running the task, comparing digests
- [ ] API keys + per-task logging
- [ ] Landing page with a live "verify this task" button

## Positioning line

"Compute you can check. Every task ships its own proof."
