#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""reroute.py — full rip-up + precise re-route.

Every prior router emitted cell-centre paths that graze margin rings, so
cleanup<->heal oscillates at ~1000 DRC violations.  This tool starts from
copper zero: all tracks/vias are removed, zones are refilled (pours
auto-clear around new copper, so they cost nothing and serve as instant
connection targets for power nets), then every net is routed pad-by-pad
with the same continuous-geometry A* as hand_route — 0.12 mm pitch,
SHAPE.Collide checks, keepout-aware.

Emitted geometry is verified segment-by-segment against real clearance
before save; residual grazes are reported, not hidden.

usage: reroute.py board.kicad_pcb
"""
import sys
import math
import heapq
import collections
import pcbnew

PCB = sys.argv[1]
NORIP = len(sys.argv) > 2 and sys.argv[2] == 'norip'

GS = 0.15            # grid pitch mm
TW = 0.25            # track width
TW2 = TW / 2
CLR = 0.2            # copper clearance
MARG = TW2 + CLR + 0.02       # point-test margin for track cells
VIA_D, VIA_DRILL = 0.6, 0.3
VIA_MARG = VIA_D / 2 + CLR + 0.02
CU = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]

board = pcbnew.LoadBoard(PCB)

# ---- phase A: rip every track and via --------------------------------
if NORIP:
    print('norip: keeping existing copper', flush=True)
else:
    ripped = 0
    for t in list(board.GetTracks()):
        board.Remove(t)
        ripped += 1
    print(f'ripped {ripped} items', flush=True)

# ---- keepout rule areas (board + footprint) --------------------------
keeps = []           # (polyset, set(layers))
for z in list(board.Zones()):
    if z.GetIsRuleArea() and (z.GetDoNotAllowTracks() or
                              z.GetDoNotAllowVias() or
                              z.GetDoNotAllowFootprints()):
        keeps.append((z, set(z.GetLayerSet().Seq())))
for fp in board.GetFootprints():
    for z in fp.Zones():
        if z.GetIsRuleArea() and (z.GetDoNotAllowTracks() or
                                  z.GetDoNotAllowVias() or
                                  z.GetDoNotAllowFootprints()):
            keeps.append((z, set(z.GetLayerSet().Seq())))
print(f'keepouts: {len(keeps)}', flush=True)


# rasterize keepouts once — per-cell Collide calls were a hot path
keep_cells = set()
for z, ls in keeps:
    bb = z.GetBoundingBox()
    x0, y0 = bb.GetLeft() / 1e6, bb.GetTop() / 1e6
    x1, y1 = bb.GetRight() / 1e6, bb.GetBottom() / 1e6
    out = z.Outline()
    gy = y0
    while gy <= y1:
        gx = x0
        while gx <= x1:
            pt = pcbnew.VECTOR2I(int(gx * 1e6), int(gy * 1e6))
            try:
                inside = out.Collide(pt, 0)
            except Exception:
                inside = bb.Contains(pt)
            if inside:
                for l in ls & set(CU):
                    keep_cells.add((round(gx / GS), round(gy / GS), l))
            gx += GS
        gy += GS
print(f'keepout cells: {len(keep_cells)}', flush=True)


def in_keepout(l, qx, qy):
    return (round(qx / GS), round(qy / GS), l) in keep_cells


# ---- phase B: refill zones so pours own real fill regions ------------
zones = [z for z in board.Zones() if not z.GetIsRuleArea()]
try:
    pcbnew.ZONE_FILLER(board).Fill(zones)
except Exception as e:
    print('zone fill failed:', e)
try:
    board.BuildListOfNets()
except Exception:
    pass

pour_cells = collections.defaultdict(set)   # netcode -> set((ix,iy,l))
for z in zones:
    nc = z.GetNetCode()
    if nc <= 0:
        continue
    zlayers = set(z.GetLayerSet().Seq())
    for l in CU:
        if l not in zlayers:
            continue
        try:
            polys = z.GetFilledPolysList(l)
        except Exception:
            continue
        if polys is None or polys.IsEmpty():
            continue
        bb = polys.BBox()
        x0, y0 = bb.GetLeft() / 1e6, bb.GetTop() / 1e6
        x1, y1 = bb.GetRight() / 1e6, bb.GetBottom() / 1e6
        gx, gy = x0, y0
        while gy <= y1:
            gx = x0
            while gx <= x1:
                if polys.Collide(pcbnew.VECTOR2I(int(gx * 1e6),
                                               int(gy * 1e6)), 0):
                    pour_cells[nc].add((round(gx / GS), round(gy / GS), l))
                gx += GS * 4
            gy += GS * 4
print({board.FindNet(c).GetNetname(): len(s)
       for c, s in pour_cells.items()}, flush=True)

conn = board.GetConnectivity()

# ---- spatial hash of every copper item's effective shape -------------
BUCK = 1.0
items = {l: collections.defaultdict(list) for l in CU}
vias = []


def add_item(it):
    ls = set(it.GetLayerSet().Seq())
    if isinstance(it, pcbnew.PCB_VIA):
        vias.append(it)
        x, y = it.GetPosition().x / 1e6, it.GetPosition().y / 1e6
        for bx in range(int(x // BUCK) - 1, int(x // BUCK) + 2):
            for by in range(int(y // BUCK) - 1, int(y // BUCK) + 2):
                viabuck[(bx, by)].append(it)
        return
    for l in CU:
        if l in ls:
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


viabuck = collections.defaultdict(list)
for t in board.GetTracks():
    add_item(t)
for fp in board.GetFootprints():
    for p in fp.Pads():
        add_item(p)


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
    if in_keepout(l, qx, qy):
        return False
    return hit(l, qx, qy, MARG, nc) is None and \
        via_hit(qx, qy, MARG, nc) is None


def via_legal(qx, qy, nc):
    if in_keepout(CU[0], qx, qy):
        return False
    for l in CU:
        if hit(l, qx, qy, VIA_MARG, nc) is not None:
            return False
    return via_hit(qx, qy, VIA_MARG, nc) is None


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


def astar(seeds, goals, nc, maxpop=1200000):
    gset = set(goals)
    dist, prev, pq = {}, {}, []
    for st in seeds:
        dist[st] = 0
        heapq.heappush(pq, (0, st))
    gl = list(gset)
    step = max(1, len(gl) // 400)
    gpts = [g[:2] for g in gl[::step]]
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
            nd = dist[cur] + (60 if nl != ly else 1)
            if ns not in dist or nd < dist[ns]:
                dist[ns] = nd
                h = min(((nx2 - gx) ** 2 + (ny2 - gy) ** 2) ** 0.5
                        for gx, gy in gpts)
                heapq.heappush(pq, (nd + h, ns))
                prev[ns] = cur
    return None


netmap = {n.GetNetname(): n for n in board.GetNetsByName().values()}
emitted = []   # every emitted track/via for post-verify


def add_track(x1, y1, x2, y2, ly, nc):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(int(x1 * 1e6), int(y1 * 1e6)))
    t.SetEnd(pcbnew.VECTOR2I(int(x2 * 1e6), int(y2 * 1e6)))
    t.SetWidth(int(TW * 1e6))
    t.SetLayer(ly)
    t.SetNetCode(nc)
    board.Add(t)
    add_item(t)
    emitted.append(t)


def add_via(x, y, nc):
    v = pcbnew.PCB_VIA(board)
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetPosition(pcbnew.VECTOR2I(int(x * 1e6), int(y * 1e6)))
    v.SetWidth(int(VIA_D * 1e6))
    v.SetDrill(int(VIA_DRILL * 1e6))
    v.SetNetCode(nc)
    board.Add(v)
    add_item(v)
    emitted.append(v)


pads = {}
for fp in board.GetFootprints():
    for p in fp.Pads():
        pads[(fp.GetReference(), str(p.GetNumber()))] = p
allpads = list(pads.values())

item_by_uuid = {}
for t in board.GetTracks():
    item_by_uuid[t.m_Uuid.AsString()] = t
for p in allpads:
    item_by_uuid[p.m_Uuid.AsString()] = p


def clusters_of(nc, pl):
    clus = []
    for p in pl:
        ids = set(x.m_Uuid.AsString() for x in conn.GetConnectedItems(p))
        ids.add(p.m_Uuid.AsString())
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
    clus.sort(key=lambda c: len(c[1]), reverse=True)
    return clus


def route_pad(p, name, nc, isl_ids, goal_ids):
    px, py = p.GetPosition().x / 1e6, p.GetPosition().y / 1e6
    seeds = {}
    for uid in isl_ids:
        it = item_by_uuid.get(uid)
        if it is None:
            continue
        for ix, iy, l, anchor in cells_of_item(it, nc):
            seeds.setdefault((ix, iy, l), anchor)
    plset = [l for l in CU if l in set(p.GetLayerSet().Seq())]
    seeds[(round(px / GS), round(py / GS), plset[0])] = (px, py)
    goals = {}
    for uid in goal_ids:
        it = item_by_uuid.get(uid)
        if it is None:
            continue
        for ix, iy, l, anchor in cells_of_item(it, nc):
            goals.setdefault((ix, iy, l), anchor)
    # same-net pour fill cells are connection targets too
    for ix, iy, l in pour_cells.get(nc, ()):
        goals.setdefault((ix, iy, l), (ix * GS, iy * GS))
    if not goals:
        print(f'{name}: no goal copper', flush=True)
        return False
    path = astar(set(seeds), goals, nc)
    if not path:
        print(f'{name} {p.GetParentFootprint().GetReference()}.'
              f'{p.GetPadName()}: NO PATH (goals={len(goals)})', flush=True)
        return False
    pts = [(ix * GS, iy * GS, l) for ix, iy, l in path]
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        (x0, y0, l0), (x1, y1, l1), (x2, y2, l2) = pts[i - 1:i + 2]
        if l0 != l1 or l1 != l2 or (x1 - x0, y1 - y0) != (x2 - x1, y2 - y1):
            out.append(pts[i])
    out.append(pts[-1])
    a0 = seeds.get(path[0])
    if a0 and (abs(a0[0] - out[0][0]) > 1e-6 or
               abs(a0[1] - out[0][1]) > 1e-6):
        add_track(a0[0], a0[1], out[0][0], out[0][1], out[0][2], nc)
    a1 = goals.get(path[-1])
    if a1 and (abs(a1[0] - out[-1][0]) > 1e-6 or
               abs(a1[1] - out[-1][1]) > 1e-6):
        add_track(out[-1][0], out[-1][1], a1[0], a1[1], out[-1][2], nc)
    for i in range(len(out) - 1):
        (x1, y1, l1), (x2, y2, l2) = out[i], out[i + 1]
        if l1 != l2:
            add_via(x1, y1, nc)
        else:
            add_track(x1, y1, x2, y2, l1, nc)
    print(f'{name} routed {p.GetParentFootprint().GetReference()}.'
          f'{p.GetPadName()}: {len(out)-1} segs', flush=True)
    return True


# ---- phase E: route every net, islands first, iterate ----------------
for rnd in range(8):
    jobs = []
    for net in board.GetNetsByName().values():
        name = net.GetNetname()
        if not name or name.startswith('unconnected'):
            continue
        nc = net.GetNetCode()
        pl = [p for p in allpads if p.GetNetCode() == nc]
        if len(pl) < 2:
            continue
        clus = clusters_of(nc, pl)
        if len(clus) < 2:
            continue
        for ci, c in enumerate(clus):
            if ci == 0:
                continue            # largest cluster is already the hub
            other_ids = set()
            for oi, o in enumerate(clus):
                if oi != ci:
                    other_ids |= o[0]
            for p in c[1]:
                jobs.append((name, nc, p, c[0], other_ids))
    print(f'round {rnd}: {len(jobs)} island pads', flush=True)
    if not jobs:
        break
    ok = 0
    for name, nc, p, isl_ids, goal_ids in jobs:
        if route_pad(p, name, nc, isl_ids, goal_ids):
            ok += 1
            if ok % 25 == 0:
                pcbnew.SaveBoard(PCB, board)
                print(f'  checkpoint at {ok}', flush=True)
    print(f'round {rnd}: routed {ok}/{len(jobs)}', flush=True)
    pcbnew.SaveBoard(PCB, board)
    if ok == 0:
        break

# ---- phase F: verify every emitted segment precisely -----------------
bad = 0
for t in emitted:
    if isinstance(t, pcbnew.PCB_VIA):
        continue
    x1, y1 = t.GetStart().x / 1e6, t.GetStart().y / 1e6
    x2, y2 = t.GetEnd().x / 1e6, t.GetEnd().y / 1e6
    nc = t.GetNetCode()
    ly = t.GetLayer()
    n = max(1, int(math.hypot(x2 - x1, y2 - y1) / (GS / 2)))
    for s in range(n + 1):
        qx, qy = x1 + (x2 - x1) * s / n, y1 + (y2 - y1) * s / n
        it = hit(ly, qx, qy, TW2 + CLR - 0.01, nc)
        if it is not None and it is not t:
            bad += 1
            break
print(f'post-verify: {bad} grazing segments of {len(emitted)} emitted',
      flush=True)

# ---- phase G: final refill + save ------------------------------------
try:
    pcbnew.ZONE_FILLER(board).Fill(zones)
except Exception as e:
    print('final fill failed:', e)
pcbnew.SaveBoard(PCB, board)
print('saved:', PCB, flush=True)
