#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# drc_loop.sh — iterate fixup/connect/gnd_heal/orphan_sweep + kicad DRC
# until unconnected stops improving or N rounds elapse.
set -u
cd "$(dirname "$0")/../.."
B=hardware/release/electrical/ecocell-ocean.kicad_pcb
W=hardware/release/electrical/work
N=${1:-4}
for i in $(seq 1 "$N"); do
    echo "=== round $i ==="
    timeout 240 python3 tools/pcb/fixup.py "$B" "$W/drcA.json" 2>/dev/null | \
        grep -E 'removed=|saved:'
    timeout 240 python3 tools/pcb/connect.py "$B" 60 200 "$W/drcA.json" \
        2>/dev/null | grep -E 'pairs connected|saved:'
    timeout 200 python3 tools/pcb/gnd_heal.py "$B" "$W/drcA.json" \
        2>/dev/null | grep -E 'placed:|saved:'
    timeout 200 python3 tools/pcb/orphan_sweep.py "$B" 2>/dev/null | \
        grep -E 'orphans|saved:'
    timeout 240 python3 tools/pcb/connect.py "$B" 60 200 2>/dev/null | \
        grep -E 'connected:|saved:'
    kicad-cli pcb drc "$B" --format json -o "$W/drcA.json" 2>/dev/null | \
        grep -E 'Found'
done
