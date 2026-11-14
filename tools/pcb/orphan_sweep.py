#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""orphan_sweep.py — delete copper fragments attached to no pad.

Every track/via that belongs to no pad's connected cluster is dead
copper: it carries no signal, only DRC noise.  Deleting it is always
connectivity-safe.

usage: orphan_sweep.py board.kicad_pcb
"""
import sys
import pcbnew

board = pcbnew.LoadBoard(sys.argv[1])
conn = board.GetConnectivity()

live = set()
for fp in board.GetFootprints():
    for p in fp.Pads():
        live.add(p.m_Uuid.AsString())
        for it in conn.GetConnectedItems(p):
            live.add(it.m_Uuid.AsString())

dead = [t for t in board.GetTracks()
        if t.m_Uuid.AsString() not in live]
for t in dead:
    board.Remove(t)
print(f'orphans removed: {len(dead)}', flush=True)
pcbnew.SaveBoard(sys.argv[1], board)
print('saved:', sys.argv[1], flush=True)
