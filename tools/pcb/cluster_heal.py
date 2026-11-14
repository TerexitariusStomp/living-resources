#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""cluster_heal.py — fix unconnected items by real cluster analysis.

KiCad's GetConnectedItems treats a whole zone object as one node, so
pour islands look 'connected' while DRC (rightly) reports them as
unconnected.  This tool builds a union-find over every copper item and
every zone *fill outline* separately, identifies each net's dominant
cluster, then BFS/mincut-routes every smaller cluster into it.

Reuses connect.py's obstacle model and routers via exec() of its
preamble (everything before the connectivity section).

usage: cluster_heal.py board.kicad_pcb [maxcost] [ripcap]
"""
import sys
import math
import collections
import pcbnew

# pull connect.py's world (board, items, free, bfs, mincut, emit_path…)
src = open('tools/pcb/connect.py').read()
head = src.split('conn = board.GetConnectivity()')[0]
ns = {'sys': sys, '__name__': '__main__'}
exec(compile(head, 'connect.py', 'exec'), ns)

board = ns['board']
CU = ns['CU']
GS = ns['GS']
bfs = ns['bfs']
mincut = ns['mincut']
rip_for_path = ns['rip_for_path']
emit_path = ns['emit_path']
pcbnew_ = pcbnew

# ---------- union-find -------------------------------------------------
parent = {}


def find(a):
    while parent[a] != a:
        parent[a] = parent[parent[a]]
        a = parent[a]
    return a


def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb:
        parent[rb] = ra


nodes = {}          # node_id -> (item, layer, outline_idx or None)
node_cells = {}     # node_id -> set(cells)
cell_owner = {}     # (ix,iy,l) -> set(node_id)
nid = 0


def new_node(item, layer=None, oidx=None):
    global nid
    nodes[nid] = (item, layer, oidx)
    node_cells[nid] = set()
    parent[nid] = nid
    nid += 1
    return nid - 1


def stamp(nid_, cells):
    node_cells[nid_] |= set(cells)
    for c in cells:
        cell_owner.setdefault(c, set()).add(nid_)


# stamp tracks
for t in board.GetTracks():
    n = new_node(t)
    if isinstance(t, pcbnew.PCB_VIA):
        x, y = t.GetPosition().x / 1e6, t.GetPosition().y / 1e6
        for l in CU:
            stamp(n, [(round(x / GS), round(y / GS), l)])
        continue
    l = t.GetLayer()
    x1, y1 = t.GetStart().x / 1e6, t.GetStart().y / 1e6
    x2, y2 = t.GetEnd().x / 1e6, t.GetEnd().y / 1e6
    L = math.hypot(x2 - x1, y2 - y1)
    steps = max(1, int(L / (GS / 2)))
    cells = set()
    for s in range(steps + 1):
        qx = x1 + (x2 - x1) * s / steps
        qy = y1 + (y2 - y1) * s / steps
        cells.add((round(qx / GS), round(qy / GS), l))
    stamp(n, cells)

# stamp pads
for fp in board.GetFootprints():
    for p in fp.Pads():
        n = new_node(p)
        ls = set(p.GetLayerSet().Seq()) & set(CU)
        bb = p.GetBoundingBox()
        x0, y0 = bb.GetLeft() / 1e6, bb.GetTop() / 1e6
        x1, y1 = bb.GetRight() / 1e6, bb.GetBottom() / 1e6
        cells = set()
        gx = x0
        while gx <= x1 + GS / 2:
            gy = y0
            while gy <= y1 + GS / 2:
                for l in ls:
                    cells.add((round(gx / GS), round(gy / GS), l))
                gy += GS
            gx += GS
        stamp(n, cells)

# stamp zone fill outlines (one node per outline — this is what
# GetConnectedItems can't do)
zones = [z for z in board.Zones() if not z.GetIsRuleArea()]
try:
    pcbnew.ZONE_FILLER(board).Fill(zones)
except Exception:
    pass
for z in zones:
    zls = set(z.GetLayerSet().Seq())
    for l in CU:
        if l not in zls:
            continue
        try:
            polys = z.GetFilledPolysList(l)
        except Exception:
            continue
        if polys is None or polys.IsEmpty():
            continue
        for i in range(polys.OutlineCount()):
            sub = pcbnew.SHAPE_POLY_SET()
            sub.AddOutline(polys.COutline(i))
            n = new_node(z, l, i)
            bb = sub.BBox()
            x0, y0 = bb.GetLeft() / 1e6, bb.GetTop() / 1e6
            x1, y1 = bb.GetRight() / 1e6, bb.GetBottom() / 1e6
            cells = set()
            gx, gy = x0, y0
            while gy <= y1:
                gx = x0
                while gx <= x1:
                    if sub.Collide(pcbnew.VECTOR2I(int(gx * 1e6),
                                                 int(gy * 1e6)), 0):
                        cells.add((round(gx / GS), round(gy / GS), l))
                    gx += GS * 2
                gy += GS * 2
            stamp(n, cells)

# union same-net nodes sharing a cell
for c, ids in cell_owner.items():
    ids = list(ids)
    for a in ids[1:]:
        ia = nodes[a][0]
        ib = nodes[ids[0]][0]
        if ia.GetNetCode() == ib.GetNetCode():
            union(a, ids[0])

# group nodes by (net, cluster)
by_net = collections.defaultdict(lambda: collections.defaultdict(list))
for n_, (it, l, oi) in nodes.items():
    by_net[it.GetNetCode()][find(n_)].append(n_)

# per net: dominant cluster = most pads; route every other cluster in
RIPCAP = int(sys.argv[3]) if len(sys.argv) > 3 else 24
dead = ns['dead']
fixed = 0
for nc, clusters in by_net.items():
    if nc <= 0 or len(clusters) < 2:
        continue
    def npads(cl):
        return sum(1 for n_ in cl
                   if isinstance(nodes[n_][0], pcbnew.PAD))
    main = max(clusters.values(), key=npads)
    main_cells = {}
    for n_ in main:
        for c in node_cells[n_]:
            main_cells.setdefault(c, (c[0] * GS, c[1] * GS))
    for cl in clusters.values():
        if cl is main:
            continue
        seeds = {}
        for n_ in cl:
            for c in node_cells[n_]:
                seeds.setdefault(c, (c[0] * GS, c[1] * GS))
        if not seeds or not main_cells:
            continue
        path, _ = bfs(set(seeds), set(main_cells), nc)
        if not path:
            path, _ = mincut(set(seeds), set(main_cells), nc)
            if path:
                rips = rip_for_path(path, nc)
                if len(rips) <= RIPCAP:
                    for w in rips:
                        board.Remove(w)
                        dead.add(w.m_Uuid.AsString())
                else:
                    path = None
        if path:
            nseg = emit_path(path, nc, seeds, main_cells)
            fixed += 1
            net = board.FindNet(nc).GetNetname()
            print(f'{net}: cluster healed ({nseg} segs)', flush=True)

print('clusters healed:', fixed, flush=True)
try:
    pcbnew.ZONE_FILLER(board).Fill(
        [z for z in board.Zones() if not z.GetIsRuleArea()])
except Exception:
    pass
pcbnew.SaveBoard(sys.argv[1], board)
print('saved:', sys.argv[1], flush=True)
