#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""probe_islands.py — for every island pad, flood its cluster over all
layers, find the closest approach to main-cluster goal cells, and list
the foreign items walling the gap."""
import sys
import math
import collections
import pcbnew

PCB = sys.argv[1]
GS = 0.12
MARG = 0.345
VM = 0.52
CU = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
BUCK = 1.0

board = pcbnew.LoadBoard(PCB)
conn = board.GetConnectivity()

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
            continue
        bb = it.GetBoundingBox()
        x0, y0 = bb.GetLeft() / 1e6, bb.GetTop() / 1e6
        x1, y1 = bb.GetRight() / 1e6, bb.GetBottom() / 1e6
        for bx in range(int(x0 // BUCK) - 1, int(x1 // BUCK) + 2):
            for by in range(int(y0 // BUCK) - 1, int(y1 // BUCK) + 2):
                items[l][(bx, by)].append((it, sh))


for t in board.GetTracks():
    add_item(t)
all_pads = []
for fp in board.GetFootprints():
    for p in fp.Pads():
        add_item(p)
        all_pads.append(p)


def hit(l, qx, qy, marg, nc):
    pt = pcbnew.VECTOR2I(int(qx * 1e6), int(qy * 1e6))
    cl = int(marg * 1e6)
    for it, sh in items[l].get((int(qx // BUCK), int(qy // BUCK)), ()):
        if it.GetNetCode() == nc:
            continue
        if sh.Collide(pt, cl):
            return it
    return None


def via_hit(qx, qy, marg, nc):
    for v in viabuck.get((int(qx // BUCK), int(qy // BUCK)), ()):
        if v.GetNetCode() == nc:
            continue
        vx, vy = v.GetPosition().x / 1e6, v.GetPosition().y / 1e6
        if math.hypot(vx - qx, vy - qy) < marg + 0.3:
            return v
    return None


def free(l, qx, qy, nc):
    return hit(l, qx, qy, MARG, nc) is None and \
        via_hit(qx, qy, MARG, nc) is None


def via_legal(qx, qy, nc):
    pt = pcbnew.VECTOR2I(int(qx * 1e6), int(qy * 1e6))
    cl = int(VM * 1e6)
    for l in CU:
        for it, sh in items[l].get((int(qx // BUCK), int(qy // BUCK)), ()):
            if it.GetNetCode() == nc:
                continue
            if sh.Collide(pt, cl):
                return False
    for v in viabuck.get((int(qx // BUCK), int(qy // BUCK)), ()):
        if v.GetNetCode() == nc:
            continue
        vx, vy = v.GetPosition().x / 1e6, v.GetPosition().y / 1e6
        if math.hypot(vx - qx, vy - qy) < VM + 0.3:
            return False
    return True


def blockers_at(qx, qy, nc, vm=VM):
    out = []
    pt = pcbnew.VECTOR2I(int(qx * 1e6), int(qy * 1e6))
    cl = int(vm * 1e6)
    for l in CU:
        for it, sh in items[l].get((int(qx // BUCK), int(qy // BUCK)), ()):
            if it.GetNetCode() == nc:
                continue
            if sh.Collide(pt, cl):
                out.append(it)
    for v in viabuck.get((int(qx // BUCK), int(qy // BUCK)), ()):
        if v.GetNetCode() == nc:
            continue
        vx, vy = v.GetPosition().x / 1e6, v.GetPosition().y / 1e6
        if math.hypot(vx - qx, vy - qy) < vm + 0.3:
            out.append(v)
    return out


def cells_of_item(it, nc):
    out = []
    try:
        x1, y1 = it.GetStart().x / 1e6, it.GetStart().y / 1e6
        x2, y2 = it.GetEnd().x / 1e6, it.GetEnd().y / 1e6
        ls = [l for l in CU if l in set(it.GetLayerSet().Seq())]
        n = max(1, int(math.hypot(x2 - x1, y2 - y1) / GS))
        for s in range(n + 1):
            xx, yy = x1 + (x2 - x1) * s / n, y1 + (y2 - y1) * s / n
            for l in ls:
                out.append((round(xx / GS), round(yy / GS), l))
    except Exception:
        try:
            pos = it.GetPosition()
            ls = [l for l in CU if l in set(it.GetLayerSet().Seq())]
            bb = it.GetBoundingBox()
            x0, y0 = bb.GetLeft() / 1e6, bb.GetTop() / 1e6
            x1, y1 = bb.GetRight() / 1e6, bb.GetBottom() / 1e6
            n = max(1, int(max(x1 - x0, y1 - y0) / GS))
            for sx in range(n + 1):
                for sy in range(n + 1):
                    xx = x0 + (x1 - x0) * sx / n
                    yy = y0 + (y1 - y0) * sy / n
                    for l in ls:
                        out.append((round(xx / GS), round(yy / GS), l))
        except Exception:
            pass
    return out


def wall_items(qx, qy, ly, nc):
    """foreign items that block this cell on this layer."""
    out = []
    pt = pcbnew.VECTOR2I(int(qx * 1e6), int(qy * 1e6))
    cl = int(MARG * 1e6)
    for it, sh in items[ly].get((int(qx // BUCK), int(qy // BUCK)), ()):
        if it.GetNetCode() == nc:
            continue
        if sh.Collide(pt, cl):
            out.append(it)
    return out


# ---- cluster per net (largest = hub) ---------------------------------
bynet = collections.defaultdict(list)
for p in all_pads:
    if p.GetNetCode() > 0:
        bynet[p.GetNetCode()].append(p)

for nc, pl in sorted(bynet.items(),
                     key=lambda kv: len(kv[1]), reverse=True):
    if len(pl) < 2:
        continue
    clus = []
    for p in pl:
        ids = set(x.m_Uuid.AsString()
                  for x in conn.GetConnectedItems(p))
        ids.add(p.m_Uuid.AsString())
        for c in clus:
            if c[0] & ids:
                c[0] |= ids
                c[1].append(p)
                break
        else:
            clus.append([ids, [p]])
    merged = True
    while merged:
        merged = False
        for i in range(len(clus)):
            for j in range(i + 1, len(clus)):
                if clus[i][0] & clus[j][0]:
                    clus[i][0] |= clus[j][0]
                    clus[i][1] += clus[j][1]
                    clus.pop(j)
                    merged = True
                    break
            else:
                continue
            break
    clus.sort(key=lambda c: len(c[0]), reverse=True)
    if len(clus) < 2:
        continue
    net = board.FindNet(nc).GetNetname()
    # goal cells: every item in the hub cluster
    goals = set()
    uuid2item = {x.m_Uuid.AsString(): x for x in board.GetTracks()}
    for fp in board.GetFootprints():
        for p in fp.Pads():
            uuid2item[p.m_Uuid.AsString()] = p
    for uid in clus[0][0]:
        it = uuid2item.get(uid)
        if it is not None:
            goals.update(cells_of_item(it, nc))
    for ci, c in enumerate(clus[1:], 1):
        seeds = set()
        for uid in c[0]:
            it = uuid2item.get(uid)
            if it is not None:
                seeds.update(cells_of_item(it, nc))
        # flood the island cluster over all layers
        seen = set(seeds)
        dq = collections.deque(seeds)
        dist = {}
        steps = 0
        best = None          # (l1, cell, goal_cell)
        while dq and steps < 400000:
            s = dq.popleft()
            steps += 1
            ix, iy, ly = s
            if s in goals:
                best = (0, s, s)
                break
            nbrs = [(ix + 1, iy, ly), (ix - 1, iy, ly),
                    (ix, iy + 1, ly), (ix, iy - 1, ly)]
            if via_legal(ix * GS, iy * GS, nc):
                li = CU.index(ly)
                for nl in (CU[li - 1] if li > 0 else None,
                           CU[li + 1] if li < len(CU) - 1 else None):
                    if nl is not None:
                        nbrs.append((ix, iy, nl))
            for ns in nbrs:
                if ns in seen:
                    continue
                if free(ns[2], ns[0] * GS, ns[1] * GS, nc):
                    seen.add(ns)
                    dq.append(ns)
        # closest approach (sample goals on the same frontier bbox)
        frontier = sorted(seen, key=lambda s: (s[0] // 1000, s[1] // 1000))
        # subsample both sets for the distance calc
        fs = list(seen)[::max(1, len(seen) // 4000)]
        gs = list(goals)[::max(1, len(goals) // 4000)]
        mind = 1e9
        pair = None
        for f in fs:
            for g in gs:
                if f[2] != g[2]:
                    continue
                d = abs(f[0] - g[0]) + abs(f[1] - g[1])
                if d < mind:
                    mind = d
                    pair = (f, g)
        pads_here = sorted(set(
            p.GetParentFootprint().GetReference() + '.' +
            str(p.GetNumber()) for p in c[1]))
        print(f'== {net} cluster {ci}: pads={pads_here} '
              f'flood={len(seen)} cells, goals={len(goals)}')
        if pair:
            f, g = pair
            print(f'   closest: {mind * GS:.2f} mm on '
                  f'{pcbnew.LayerName(f[2])} at '
                  f'({f[0] * GS:.2f},{f[1] * GS:.2f}) -> '
                  f'({g[0] * GS:.2f},{g[1] * GS:.2f})')
            # walk the straight line, list wall items
            x0, y0 = f[0], f[1]
            x1, y1 = g[0], g[1]
            n = int(math.hypot(x1 - x0, y1 - y0)) or 1
            seen_it = set()
            for s in range(n + 1):
                qx = (x0 + (x1 - x0) * s / n) * GS
                qy = (y0 + (y1 - y0) * s / n) * GS
                for it in wall_items(qx, qy, f[2], nc):
                    u = it.m_Uuid.AsString()
                    if u in seen_it:
                        continue
                    seen_it.add(u)
                    nn = 'PAD'
                    try:
                        nn = it.GetParentFootprint().GetReference() + '.' + \
                            str(it.GetNumber())
                    except Exception:
                        try:
                            nn = board.FindNet(
                                it.GetNetCode()).GetNetname()
                        except Exception:
                            pass
                    kind = type(it).__name__
                    print(f'      wall: {kind} {nn}')
        else:
            print('   no same-layer approach found')
        print()
