#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""dedup_copper.py — remove exactly-duplicated tracks and vias.

Repeated heal/route passes emit the same segment many times; stacks of
identical copper wall routing corridors for every other net.  Dropping
duplicates is connectivity-safe (the first copy remains).

usage: dedup_copper.py board.kicad_pcb
"""
import sys

import pcbnew

PCB = sys.argv[1]
board = pcbnew.LoadBoard(PCB)
MM = 1_000_000

seen_t, seen_v, dead = set(), set(), []
for t in board.GetTracks():
    if isinstance(t, pcbnew.PCB_VIA):
        p = t.GetPosition()
        key = (t.GetNetCode(), round(p.x / MM, 3), round(p.y / MM, 3),
               round(t.GetDrillValue() / MM, 3)
               if hasattr(t, "GetDrillValue") else 0)
        if key in seen_v:
            dead.append(t)
        else:
            seen_v.add(key)
        continue
    s, e = t.GetStart(), t.GetEnd()
    a = (round(s.x / MM, 3), round(s.y / MM, 3))
    b = (round(e.x / MM, 3), round(e.y / MM, 3))
    if b < a:
        a, b = b, a
    key = (t.GetNetCode(), t.GetLayer(), a, b,
           round(t.GetWidth() / MM, 3))
    if key in seen_t:
        dead.append(t)
    else:
        seen_t.add(key)

for t in dead:
    board.Remove(t)
print(f"duplicates removed: {len(dead)}", flush=True)
pcbnew.SaveBoard(PCB, board)
print("saved:", PCB)
