#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# lane_drift.py — fail the build if the frontend lane table drifts from the
# policy source of truth. deploy/policies/living/lane-gate.rego defines the
# closed lane vocabulary; site/src/data/lanes.json is what the site shows.
# Every rego lane must appear (as id or baseLane); page rows may only be a
# rego lane or one of the explicitly-mapped presentation rows below.

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGO = ROOT / "deploy/policies/living/lane-gate.rego"
LANES = ROOT / "site/src/data/lanes.json"

# Presentation rows that are not literal gate lanes.
ALLOWED_EXTRA = {
    "witness": None,          # the API/receipt witness capability
    "store-receipts": "store",   # KV evidence ledger = store-lane machinery
    "store-organism": "store",
    "compute-organism": "compute",
}

rego = REGO.read_text()
gate_lanes = set(re.findall(r'"([a-z-]+)"', re.search(r"lanes := \{([^}]*)\}", rego).group(1)))

rows = json.loads(LANES.read_text())
ids = {r["id"] for r in rows}
bases = {r.get("baseLane") for r in rows if r.get("baseLane")}
covered = ids | bases

missing = gate_lanes - covered
extra = {i for i in ids if i not in gate_lanes and i not in ALLOWED_EXTRA}
bad_base = [r["id"] for r in rows
            if r.get("baseLane") and r["baseLane"] not in gate_lanes]

ok = True
if missing:
    ok = False
    print("rego lanes not represented on the site:", sorted(missing))
if extra:
    ok = False
    print("page rows with no gate lane and no mapping:", sorted(extra))
if bad_base:
    ok = False
    print("rows whose baseLane is not a gate lane:", bad_base)

if ok:
    print(f"lane drift ok — gate {sorted(gate_lanes)} all portrayed; "
          f"{len(ids)} page rows")
sys.exit(0 if ok else 1)
