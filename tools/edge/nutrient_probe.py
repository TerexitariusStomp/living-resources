# SPDX-License-Identifier: AGPL-3.0-or-later
# tools/edge/nutrient_probe.py — Modbus seam for co-located wet-chem
# nutrient analyzers (Kekan KK-750-class, Systea WIZ — RS-232/485).
#
# Thin seam, per the adapters rule: the analyzer outputs calibrated
# concentrations; this tool only transports them. Register maps differ
# per vendor — they live in a JSON config, never hardcoded here.
# Records land in the edge ledger with federated-style provenance
# (source + source_id): the measurement is the instrument's, not our
# quorum — the lane gate treats it as imported evidence, not a node
# reading.
#
# Usage:
#   python3 nutrient_probe.py --port /dev/ttyUSB0 --unit 1 \
#       --map kk750.json --node node-12 --ledger detections.jsonl
#       [--period 3600]        # omit for a single read

import argparse
import json
import os
import sys
import time

try:
    import minimalmodbus                    # Apache-2.0 — oss-inventory
except ImportError:
    minimalmodbus = None

# Default Kekan-class map: scaled 16-bit holding registers. Vendor
# configs override wholesale via --map; scale 0.001 = raw µg/L → mg/L.
DEFAULT_MAP = {
    "nh4_mgl": {"register": 0, "scale": 0.001},
    "no3_mgl": {"register": 1, "scale": 0.001},
    "po4_mgl": {"register": 2, "scale": 0.001},
}


def connect(port, unit, baud=9600):
    """Instrument factory — split out so tests can inject a fake."""
    if minimalmodbus is None:
        raise RuntimeError("minimalmodbus not installed "
                           "(pip install minimalmodbus)")
    dev = minimalmodbus.Instrument(port, unit)
    dev.serial.baudrate = baud
    return dev


def read_params(dev, regmap):
    """regmap entry: {"register": n, "scale": s} or a 32-bit
    {"registers": [hi, lo], "scale": s}. Returns param -> value."""
    out = {}
    for name, spec in regmap.items():
        if "registers" in spec:
            hi = dev.read_register(spec["registers"][0])
            lo = dev.read_register(spec["registers"][1])
            raw = (hi << 16) | lo
        else:
            raw = dev.read_register(spec["register"],
                                    spec.get("decimals", 0))
        out[name] = round(raw * spec.get("scale", 1.0), 4)
    return out


def make_record(node, source_id, params, ts=None):
    """Ledger record with instrument provenance — federated shape, not
    a node reading: downstream treats it as imported evidence."""
    return {"kind": "instrument", "tier": "measured-instrument",
            "source": "nutrient-analyzer", "source_id": source_id,
            "node": node, "ts": ts if ts is not None else int(time.time()),
            "params": params}


def append_ledger(path, rec):
    with open(path, "a") as fh:
        fh.write(json.dumps(rec, separators=(",", ":")) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", required=True)
    ap.add_argument("--unit", type=int, required=True)
    ap.add_argument("--baud", type=int, default=9600)
    ap.add_argument("--map", help="register-map JSON (default: Kekan)")
    ap.add_argument("--source-id", required=True,
                    help="analyzer serial/asset id — the provenance key")
    ap.add_argument("--node", required=True, help="co-located node id")
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--period", type=int, default=0,
                    help="poll interval s; 0 = single read")
    args = ap.parse_args(argv)

    regmap = DEFAULT_MAP
    if args.map:
        with open(args.map) as fh:
            regmap = json.load(fh)
    dev = connect(args.port, args.unit, args.baud)
    while True:
        try:
            rec = make_record(args.node, args.source_id,
                              read_params(dev, regmap))
        except Exception as e:                  # bus fault → refuse,
            rec = {"kind": "instrument-error",  # never an invented value
                   "source": "nutrient-analyzer",
                   "source_id": args.source_id, "node": args.node,
                   "ts": int(time.time()), "error": str(e)}
        append_ledger(args.ledger, rec)
        if not args.period:
            return 0
        time.sleep(args.period)


if __name__ == "__main__":
    sys.exit(main())
