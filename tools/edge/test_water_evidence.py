# SPDX-License-Identifier: AGPL-3.0-or-later
# test_water_evidence.py — nutrient_probe parse + spe_manifest chain.
# Plain asserts; run by `make test` with PYTHONPATH=tools/edge.

import json
import os
import tempfile

from nutrient_probe import DEFAULT_MAP, make_record, read_params
from spe_manifest import append_event, verify


class FakeInstrument:
    """Register-file stub — returns canned register values."""

    def __init__(self, regs):
        self.regs = regs

    def read_register(self, reg, decimals=0):
        return self.regs[reg]


def test_nutrient_parse():
    regs = {0: 4200, 1: 12500, 2: 800}
    params = read_params(FakeInstrument(regs), DEFAULT_MAP)
    assert params == {"nh4_mgl": 4.2, "no3_mgl": 12.5, "po4_mgl": 0.8}, params
    # 32-bit map variant: hi/lo pair packs into one value
    regmap = {"no3_mgl": {"registers": [10, 11], "scale": 0.001}}
    params = read_params(FakeInstrument({10: 0, 11: 12500}), regmap)
    assert params["no3_mgl"] == 12.5, params


def test_record_shape():
    rec = make_record("node-12", "KK750-004", {"no3_mgl": 12.5}, ts=1)
    assert rec["kind"] == "instrument"
    assert rec["tier"] == "measured-instrument"
    assert rec["source"] == "nutrient-analyzer"
    assert rec["source_id"] == "KK750-004"
    # provenance fields present — the gate reads imports by source pair
    assert rec["node"] == "node-12" and rec["ts"] == 1


def test_spe_chain():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "cassette-1.jsonl")
        append_event(path, "issue", {"cassette": "SPX-1",
                                     "operator": "tk"})
        append_event(path, "deploy", {"site": "alamo-terminus",
                                      "depth_m": "0.4"})
        append_event(path, "retrieve", {"days": "30"})
        ok, n, bad = verify(path)
        assert ok and n == 3 and bad is None, (ok, n, bad)
        # tamper: rewriting a middle line passes its own prev check but
        # breaks the NEXT event's — the forgery is caught one line later
        lines = open(path).read().splitlines()
        rec = json.loads(lines[1])
        rec["site"] = "forged-site"
        lines[1] = json.dumps(rec, separators=(",", ":"))
        with open(path, "w") as fh:
            fh.write("\n".join(lines) + "\n")
        ok, n, bad = verify(path)
        assert not ok and bad == 2, (ok, n, bad)


if __name__ == "__main__":
    test_nutrient_parse()
    test_record_shape()
    test_spe_chain()
    print("test_water_evidence: all checks passed")
