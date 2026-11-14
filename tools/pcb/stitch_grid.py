#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""stitch_grid.py — blanket GND via stitching.

Standard ground-plane practice: sprinkle vias on a grid wherever they
fit inside the GND pours on all four copper layers.  Every via binds
the four pours locally, collapsing the pour-island pairs that show up
as Zone|Zone unconnected items.

usage: stitch_grid.py board.kicad_pcb [pitch_mm]
"""
import sys
import math
import collections
import pcbnew

PCB = sys.argv[1]
PITCH = float(sys.argv[2]) if len(sys.argv) > 2 else 4.0
TW = 0.25
CLR = 0.2
VIA_D, VIA_DRILL = 0.6, 0.3
VIA_MARG = VIA_D / 2 + CLR + 0.02
CU = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
BUCK = 1.0

board = pcbnew.LoadBoard(PCB)

items = {l: collections.defaultdict(list) for l in CU}
viabuck = collections.defaultdict(list)


def add_item(it):
    ls = set(it.GetLayerSet().Seq()) & set(CU)
    if isinstance(it, pcbnew.PCB_VIA):
        x, y = it.GetPosition().x / 1e6, it.GetPosition().y / 1e6
        for bx in range(int(x // BUCK) - 1, int(x // BUCK) + 2):
            for by in range(int(y // BUCK) - 1, int(y // BUCK) + 2):
                viabuck[(bx, by)].append(it)
        return
    for l in ls:
        try:
            sh = it.GetEffectiveShape(l)
        except Exception:
            try:
                sh = it.GetEffectiveShape()
            except Exception:
                continue
        bb = it.GetBoundingBox()
        x0, y0 = bb.GetLeft() / 1e6, bb.GetTop() / 1e6
        x1, y1 = bb.GetRight() / 1e6, bb.GetBottom() / 1e6
        for bx in range(int(x0 // BUCK) - 1, int(x1 // BUCK) + 2):
            for by in range(int(y0 // BUCK) - 1, int(y1 // BUCK) + 2):
                items[l][(bx, by)].append((it, sh))


for t in board.GetTracks():
    add_item(t)
for fp in board.GetFootprints():
    for p in fp.Pads():
        add_item(p)

gnd_nc = None
zones = [z for z in board.Zones() if not z.GetIsRuleArea()]
fill = []
for z in zones:
    nm = z.GetNetname()
    if nm == 'GND':
        gnd_nc = z.GetNetCode()
    for l in CU:
        if l not in set(z.GetLayerSet().Seq()):
            continue
        try:
            pl = z.GetFilledPolysList(l)
        except Exception:
            continue
        if pl is not None and not pl.IsEmpty():
            fill.append((l, pl))
if gnd_nc is None:
    sys.exit('no GND zone')


def hit(l, qx, qy, marg):
    pt = pcbnew.VECTOR2I(int(qx * 1e6), int(qy * 1e6))
    cl = int(marg * 1e6)
    for it, sh in items[l].get((int(qx // BUCK), int(qy // BUCK)), ()):
        if it.GetNetCode() == gnd_nc:
            continue
        if sh.Collide(pt, cl):
            return True
    return False


def via_hit(qx, qy):
    for v in viabuck.get((int(qx // BUCK), int(qy // BUCK)), ()):
        vx, vy = v.GetPosition().x / 1e6, v.GetPosition().y / 1e6
        if math.hypot(vx - qx, vy - qy) < 0.55:
            return True
    return False


def via_legal(qx, qy):
    if via_hit(qx, qy):
        return False
    for l in CU:
        if hit(l, qx, qy, VIA_MARG):
            return False
    return True


def inside_fill(qx, qy, want=2):
    pt = pcbnew.VECTOR2I(int(qx * 1e6), int(qy * 1e6))
    n = 0
    for l, pl in fill:
        if pl.Collide(pt, 0):
            n += 1
    return n >= want


bb = board.GetBoardEdgesBoundingBox()
x0, y0 = bb.GetLeft() / 1e6 + 1.5, bb.GetTop() / 1e6 + 1.5
x1, y1 = bb.GetRight() / 1e6 - 1.5, bb.GetBottom() / 1e6 - 1.5

placed = 0
gy = y0
row = 0
while gy <= y1:
    gx = x0 + (PITCH / 2 if row % 2 else 0)
    while gx <= x1:
        if inside_fill(gx, gy) and via_legal(gx, gy):
            v = pcbnew.PCB_VIA(board)
            v.SetViaType(pcbnew.VIATYPE_THROUGH)
            v.SetPosition(pcbnew.VECTOR2I(int(gx * 1e6), int(gy * 1e6)))
            v.SetWidth(int(VIA_D * 1e6))
            v.SetDrill(int(VIA_DRILL * 1e6))
            v.SetNetCode(gnd_nc)
            board.Add(v)
            add_item(v)
            placed += 1
        gx += PITCH
    gy += PITCH
    row += 1

print('stitch vias placed:', placed, flush=True)
try:
    pcbnew.ZONE_FILLER(board).Fill(zones)
except Exception:
    pass
pcbnew.SaveBoard(PCB, board)
print('saved:', PCB, flush=True)
