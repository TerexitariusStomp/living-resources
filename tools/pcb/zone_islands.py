#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""zone_islands.py — bridge same-layer pour islands with direct tracks.

For every fill layer of every zone, split the filled poly set into
distinct outlines.  The largest outline is taken as 'main'; every
other outline is an island that survived because it holds net items.
Find the closest approach between the island and main-region copper
(fill outlines + same-net pads/tracks/vias on that layer) and emit a
direct track across the gap.  Refill afterwards.

usage: zone_islands.py board.kicad_pcb
"""
import sys
import math
import collections
import pcbnew

PCB = sys.argv[1]
TW = 0.25
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


def outlines_of(ps):
    """split a SHAPE_POLY_SET into per-outline poly sets"""
    outs = []
    try:
        n = ps.OutlineCount()
    except Exception:
        return outs
    for i in range(n):
        sub = pcbnew.SHAPE_POLY_SET()
        sub.AddOutline(ps.COutline(i))
        outs.append(sub)
    return outs


def edge_pts(ps, step=0.3):
    """sampled boundary points of a poly set"""
    pts = []
    for i in range(ps.OutlineCount()):
        o = ps.COutline(i)
        m = o.PointCount()
        for k in range(m):
            a = o.CPoint(k)
            b = o.CPoint((k + 1) % m)
            ax, ay = a.x / 1e6, a.y / 1e6
            bx, by = b.x / 1e6, b.y / 1e6
            d = math.hypot(bx - ax, by - ay)
            n = max(1, int(d / step))
            for s in range(n):
                t = s / n
                pts.append((ax + (bx - ax) * t, ay + (by - ay) * t))
    return pts


def seg_hit(l, ax, ay, bx, by, nc):
    """foreign-copper test along a segment, stepped"""
    d = math.hypot(bx - ax, by - ay)
    n = max(2, int(d / 0.2))
    for s in range(n + 1):
        t = s / n
        qx, qy = ax + (bx - ax) * t, ay + (by - ay) * t
        pt = pcbnew.VECTOR2I(int(qx * 1e6), int(qy * 1e6))
        for it, sh in items[l].get((int(qx // BUCK), int(qy // BUCK)), ()):
            if it.GetNetCode() == nc:
                continue
            if sh.Collide(pt, int((TW / 2 + 0.2) * 1e6)):
                return True
    return False


def add_track(x1, y1, x2, y2, ly, nc):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(int(x1 * 1e6), int(y1 * 1e6)))
    t.SetEnd(pcbnew.VECTOR2I(int(x2 * 1e6), int(y2 * 1e6)))
    t.SetWidth(int(TW * 1e6))
    t.SetLayer(ly)
    t.SetNetCode(nc)
    board.Add(t)
    add_item(t)


# collect every fill outline grouped by (net, layer)
groups = collections.defaultdict(list)
for z in board.Zones():
    if z.GetIsRuleArea():
        continue
    nc = z.GetNetCode()
    for l in CU:
        if l not in set(z.GetLayerSet().Seq()):
            continue
        try:
            pl = z.GetFilledPolysList(l)
        except Exception:
            continue
        if pl is None or pl.IsEmpty():
            continue
        for o in outlines_of(pl):
            groups[(nc, l)].append(o)

placed = 0
for (nc, l), outs in groups.items():
    if len(outs) < 2:
        continue
    outs.sort(key=lambda o: -abs(o.Area()))
    main = outs[0]
    mpts = edge_pts(main)
    for isl in outs[1:]:
        ipts = edge_pts(isl)
        best = None
        for ix, iy in ipts[::3]:
            for mx, my in mpts[::3]:
                d = math.hypot(ix - mx, iy - my)
                if best is None or d < best[0]:
                    best = (d, ix, iy, mx, my)
        if best is None:
            continue
        d, ix, iy, mx, my = best
        if seg_hit(l, ix, iy, mx, my, nc):
            continue
        add_track(ix, iy, mx, my, l, nc)
        placed += 1
        print(f'island bridge L{l} {d:.1f}mm '
              f'({ix:.1f},{iy:.1f})->({mx:.1f},{my:.1f})', flush=True)

print('island bridges placed:', placed, flush=True)
zones = [z for z in board.Zones() if not z.GetIsRuleArea()]
try:
    pcbnew.ZONE_FILLER(board).Fill(zones)
except Exception:
    pass
pcbnew.SaveBoard(PCB, board)
print('saved:', PCB, flush=True)
