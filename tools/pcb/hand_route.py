#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""hand_route.py — fine-grid precise router for stranded island pads.

attach_signals.py works on a 0.3 mm raster with clearance stamps inflated
for grid quantization.  In saturated pin fields that margin seals real
channels.  This tool re-checks geometry continuously: A* on a 0.15 mm
grid against actual item shapes (spatial-hashed SHAPE.Collide), with
precise via-site checks for layer transitions.  Emitted tracks are real
copper, so KiCad DRC remains the final arbiter.

usage: hand_route.py board.kicad_pcb [NET:REF.PIN ...]
"""
import sys
import math
import heapq
import collections
import pcbnew

PCB = sys.argv[1]
SPEC = sys.argv[2:]

GS = 0.15            # grid pitch mm
TW = 0.25            # track width
TW2 = TW / 2
CLR = 0.2            # copper clearance
MARG = TW2 + CLR + 0.02       # point-test margin for track cells
VIA_D, VIA_DRILL = 0.6, 0.3
VIA_MARG = VIA_D / 2 + CLR + 0.02  # via annulus + clearance
CU = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]

board = pcbnew.LoadBoard(PCB)
conn = board.GetConnectivity()

# ---- spatial hash of every copper item's effective shape -------------
BUCK = 1.0
items = {l: collections.defaultdict(list) for l in CU}
vias = []
tracks = list(board.GetTracks())
for t in tracks:
    if isinstance(t, pcbnew.PCB_VIA):
        vias.append(t)
        continue
    ls = set(t.GetLayerSet().Seq())
    for l in CU:
        if l in ls:
            items[l][0].append((t, t.GetEffectiveShape()))
for fp in board.GetFootprints():
    for p in fp.Pads():
        ls = set(p.GetLayerSet().Seq())
        for l in CU:
            if l in ls:
                try:
                    sh = p.GetEffectiveShape(l)
                except Exception:
                    continue
                items[l][0].append((p, sh))
# re-bucket by bbox
for l in CU:
    flat = items[l][0]
    items[l] = collections.defaultdict(list)
    for it, sh in flat:
        bb = it.GetBoundingBox()
        x0, y0 = bb.GetLeft() / 1e6, bb.GetTop() / 1e6
        x1, y1 = bb.GetRight() / 1e6, bb.GetBottom() / 1e6
        for bx in range(int(x0 // BUCK) - 1, int(x1 // BUCK) + 2):
            for by in range(int(y0 // BUCK) - 1, int(y1 // BUCK) + 2):
                items[l][(bx, by)].append((it, sh))
viabuck = collections.defaultdict(list)
for v in vias:
    x, y = v.GetPosition().x / 1e6, v.GetPosition().y / 1e6
    for bx in range(int(x // BUCK) - 1, int(x // BUCK) + 2):
        for by in range(int(y // BUCK) - 1, int(y // BUCK) + 2):
            viabuck[(bx, by)].append(v)


def hit(l, qx, qy, marg, nc):
    """foreign item within marg of point on layer l?"""
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
        if math.hypot(vx - qx, vy - qy) < marg + v.GetWidth() / 2e6:
            return v
    return None


def free(l, qx, qy, nc):
    return hit(l, qx, qy, MARG, nc) is None and \
        via_hit(qx, qy, MARG, nc) is None


def via_legal(qx, qy, nc):
    for l in CU:
        if hit(l, qx, qy, VIA_MARG, nc) is not None:
            return False
    return via_hit(qx, qy, VIA_MARG, nc) is None


def cells_of_item(it, nc):
    """grid cells touched by a same-net item (goal/seeds)."""
    out = []
    try:
        x1, y1 = it.GetStart().x / 1e6, it.GetStart().y / 1e6
        x2, y2 = it.GetEnd().x / 1e6, it.GetEnd().y / 1e6
        ls = [l for l in CU if l in set(it.GetLayerSet().Seq())]
        n = max(1, int(math.hypot(x2 - x1, y2 - y1) / GS))
        for s in range(n + 1):
            xx, yy = x1 + (x2 - x1) * s / n, y1 + (y2 - y1) * s / n
            for l in ls:
                out.append((round(xx / GS), round(yy / GS), l, (x2, y2)))
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
                        out.append((round(xx / GS), round(yy / GS), l,
                                    (pos.x / 1e6, pos.y / 1e6)))
        except Exception:
            pass
    return out


def astar(seeds, goals, nc, maxpop=6000000):
    """A* over (ix,iy,layer); goals = set((ix,iy,l))->anchor_pt or set."""
    gset = goals
    dist, prev, pq = {}, {}, []
    for st in seeds:
        dist[st] = 0
        heapq.heappush(pq, (0, st))
    gpts = list(gset)
    pop = 0
    while pq:
        f, cur = heapq.heappop(pq)
        ix, iy, ly = cur
        if cur in gset:
            path = [cur]
            while cur in prev:
                cur = prev[cur]
                path.append(cur)
            return path[::-1]
        pop += 1
        if pop > maxpop:
            return None
        qx, qy = ix * GS, iy * GS
        nbrs = [(ix + 1, iy, ly), (ix - 1, iy, ly),
                (ix, iy + 1, ly), (ix, iy - 1, ly)]
        if via_legal(qx, qy, nc):
            li = CU.index(ly)
            for nl in (CU[li - 1] if li > 0 else None,
                       CU[li + 1] if li < len(CU) - 1 else None):
                if nl is not None:
                    nbrs.append((ix, iy, nl))
        for nx2, ny2, nl in nbrs:
            if not free(nl, nx2 * GS, ny2 * GS, nc) and \
                    (nx2, ny2, nl) not in gset:
                continue
            ns = (nx2, ny2, nl)
            nd = dist[cur] + (40 if nl != ly else 1)
            if ns not in dist or nd < dist[ns]:
                dist[ns] = nd
                h = min(((nx2 - gx) ** 2 + (ny2 - gy) ** 2) ** 0.5
                        for gx, gy, _ in gpts[:400])
                heapq.heappush(pq, (nd + h, ns))
                prev[ns] = cur
    return None


netmap = {n.GetNetname(): n for n in board.GetNetsByName().values()}


def add_track(x1, y1, x2, y2, ly, nc):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(int(x1 * 1e6), int(y1 * 1e6)))
    t.SetEnd(pcbnew.VECTOR2I(int(x2 * 1e6), int(y2 * 1e6)))
    t.SetWidth(int(TW * 1e6))
    t.SetLayer(ly)
    t.SetNetCode(nc)
    board.Add(t)


def add_via(x, y, nc):
    v = pcbnew.PCB_VIA(board)
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetPosition(pcbnew.VECTOR2I(int(x * 1e6), int(y * 1e6)))
    v.SetWidth(int(VIA_D * 1e6))
    v.SetDrill(int(VIA_DRILL * 1e6))
    v.SetNetCode(nc)
    board.Add(v)


pads = {}
for fp in board.GetFootprints():
    for p in fp.Pads():
        pads[(fp.GetReference(), str(p.GetNumber()))] = p

jobs = []
if SPEC:
    for s in SPEC:
        net, rp = s.split(':')
        ref, num = rp.split('.')
        jobs.append((net, ref, num))
else:
    # auto: every pad not sharing its net's largest connected cluster
    allpads = [p for p in pads.values()]
    for net in board.GetNetsByName().values():
        name = net.GetNetname()
        if not name or name.startswith('unconnected'):
            continue
        nc = net.GetNetCode()
        pl = [p for p in allpads if p.GetNetCode() == nc]
        if len(pl) < 2:
            continue
        clus = []
        for p in pl:
            ids = set(x.m_Uuid.AsString()
                      for x in conn.GetConnectedItems(p))
            hit_c = [c for c in clus if c[0] & ids]
            if hit_c:
                hit_c[0][0] |= ids
                hit_c[0][1].append(p)
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
        if len(clus) < 2:
            continue
        clus.sort(key=lambda c: len(c[1]), reverse=True)
        for c in clus[1:]:
            for p in c[1]:
                jobs.append((name, None, None, p))

done = 0
for job in jobs:
    if len(job) == 4:
        net, _, _, p = job
    else:
        net, ref, num = job
        p = pads[(ref, num)]
    nc = netmap[net].GetNetCode()
    px, py = p.GetPosition().x / 1e6, p.GetPosition().y / 1e6
    # island cluster = seeds; all other same-net items = goals.
    # keep an anchor point (real item geometry) per seed/goal cell so the
    # emitted path can be closed with stubs that actually touch copper —
    # cell centres alone sit up to ~0.1 mm off the item.
    isl_ids = set(x.m_Uuid.AsString()
                  for x in conn.GetConnectedItems(p)) | {p.m_Uuid.AsString()}
    seeds = {}
    for it in conn.GetConnectedItems(p):
        for ix, iy, l, anchor in cells_of_item(it, nc):
            seeds.setdefault((ix, iy, l), anchor)
    plset = [l for l in CU if l in set(p.GetLayerSet().Seq())]
    seeds[(round(px / GS), round(py / GS), plset[0])] = (px, py)
    # goals: only copper that belongs to some *other* pad's cluster —
    # orphan stubs and dead-end fragments connect to nothing, and aiming
    # for them strands the route mid-air
    goals = {}
    for q in pads.values():
        if q is p or q.GetNetCode() != nc:
            continue
        if q.m_Uuid.AsString() in isl_ids:
            continue
        for it in conn.GetConnectedItems(q):
            for ix, iy, l, anchor in cells_of_item(it, nc):
                goals.setdefault((ix, iy, l), anchor)
        for ix, iy, l, anchor in cells_of_item(q, nc):
            goals.setdefault((ix, iy, l), anchor)
    if not goals:
        print(f'{net}: no goal copper'); continue
    path = astar(set(seeds), goals, nc)
    if not path:
        print(f'{net} {p.GetParentFootprint().GetReference()}.'
              f'{p.GetPadName()}: NO PATH (goals={len(goals)})')
        continue
    # simplify collinear runs then emit
    pts = [(ix * GS, iy * GS, l) for ix, iy, l in path]
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        (x0, y0, l0), (x1, y1, l1), (x2, y2, l2) = pts[i - 1:i + 2]
        if l0 != l1 or l1 != l2 or (x1 - x0, y1 - y0) != (x2 - x1, y2 - y1):
            out.append(pts[i])
    out.append(pts[-1])
    # closing stubs: real island item point -> first cell, and
    # last cell -> goal anchor (real target item geometry)
    a0 = seeds.get(path[0])
    if a0 and (abs(a0[0] - out[0][0]) > 1e-6 or abs(a0[1] - out[0][1]) > 1e-6):
        add_track(a0[0], a0[1], out[0][0], out[0][1], out[0][2], nc)
    a1 = goals.get(path[-1])
    if a1 and (abs(a1[0] - out[-1][0]) > 1e-6 or abs(a1[1] - out[-1][1]) > 1e-6):
        add_track(out[-1][0], out[-1][1], a1[0], a1[1], out[-1][2], nc)
    for i in range(len(out) - 1):
        (x1, y1, l1), (x2, y2, l2) = out[i], out[i + 1]
        if l1 != l2:
            add_via(x1, y1, nc)
        else:
            add_track(x1, y1, x2, y2, l1, nc)
    print(f'{net} routed: {len(out)-1} segments '
          f'({px:.1f},{py:.1f}) -> ({out[-1][0]:.1f},{out[-1][1]:.1f})')
    done += 1

print('routed', done, 'of', len(jobs))
pcbnew.SaveBoard(PCB, board)
print('saved:', PCB)
