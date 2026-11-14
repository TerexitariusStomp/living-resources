#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""connect.py — guaranteed-progress island healing.

For every island cluster (pad group cut off from its net's hub cluster):
  1. BFS the free-cell space (all 4 copper layers, via transitions at
     via-legal cells, keepout-aware — identical legality to reroute.py)
     seeded from the island's copper cells, targeting hub copper cells.
  2. If BFS exhausts with no path, take the frontier cell closest to a
     goal cell on the same layer, list the foreign items that wall the
     straight corridor, rip emitted tracks/vias (never pads), and retry.
  3. Emit the found path as merged tracks + vias.

Every iteration either connects the island or identifies and removes the
exact items sealing it, so this cannot stall the way blind A* retries do.

usage: connect.py board.kicad_pcb
"""
import sys
import math
import heapq
import collections
import pcbnew

PCB = sys.argv[1]

GS = 0.15
TW = 0.25
TW2 = TW / 2
CLR = 0.2
MARG = TW2 + CLR + 0.02
VIA_D, VIA_DRILL = 0.6, 0.3
VIA_MARG = VIA_D / 2 + CLR + 0.02
CU = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
BUCK = 1.0

board = pcbnew.LoadBoard(PCB)

# ---- keepout raster (same as reroute.py) -----------------------------
keeps = []
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
keep_cells = set()
KO_MARGIN = 550000      # 0.55 mm: vias need VIA_MARG clearance of the
                        # rule-area outline, not just centre-inside
for z, ls in keeps:
    bb = z.GetBoundingBox()
    x0, y0 = bb.GetLeft() / 1e6 - 0.6, bb.GetTop() / 1e6 - 0.6
    x1, y1 = bb.GetRight() / 1e6 + 0.6, bb.GetBottom() / 1e6 + 0.6
    out = z.Outline()
    gy = y0
    while gy <= y1:
        gx = x0
        while gx <= x1:
            pt = pcbnew.VECTOR2I(int(gx * 1e6), int(gy * 1e6))
            try:
                inside = out.Collide(pt, KO_MARGIN)
            except Exception:
                inside = bb.Contains(pt)
            if inside:
                for l in ls & set(CU):
                    keep_cells.add((round(gx / GS), round(gy / GS), l))
            gx += GS
        gy += GS
print(f'keepout cells: {len(keep_cells)}', flush=True)

# ---- Edge.Cuts ring + drilled holes: unrouteable obstacles -----------
EDGE_CLR = 0.75         # board setup: 0.5 mm copper-to-edge
def _seg_cells(x1, y1, x2, y2, rad):
    """grid cells within rad of segment (x1,y1)-(x2,y2)."""
    L = math.hypot(x2 - x1, y2 - y1)
    n = max(1, int(L / (GS / 2)))
    out = []
    for s in range(n + 1):
        qx = x1 + (x2 - x1) * s / n
        qy = y1 + (y2 - y1) * s / n
        m = int(rad / GS) + 1
        cx, cy = round(qx / GS), round(qy / GS)
        for ix in range(-m, m + 1):
            for iy in range(-m, m + 1):
                if (ix * GS) ** 2 + (iy * GS) ** 2 <= rad * rad:
                    out.append((cx + ix, cy + iy))
    return out


for d in board.GetDrawings():
    try:
        if d.GetLayerName() != 'Edge.Cuts':
            continue
        x1, y1 = d.GetStart().x / 1e6, d.GetStart().y / 1e6
        x2, y2 = d.GetEnd().x / 1e6, d.GetEnd().y / 1e6
    except Exception:
        continue
    for cx, cy in _seg_cells(x1, y1, x2, y2, EDGE_CLR):
        for l in CU:
            keep_cells.add((cx, cy, l))
print(f'with edge ring: {len(keep_cells)}', flush=True)

hole_cells = set()
for fp in board.GetFootprints():
    for p in fp.Pads():
        try:
            dx = p.GetDrillSize().x / 1e6
            dy = p.GetDrillSize().y / 1e6
        except Exception:
            continue
        r = max(dx, dy) / 2
        if r <= 0:
            continue
        # holes need drill-to-copper clearance ~0.3 mm
        rad = r + 0.55
        px, py = p.GetPosition().x / 1e6, p.GetPosition().y / 1e6
        n = int(rad / GS) + 1
        for ix in range(-n, n + 1):
            for iy in range(-n, n + 1):
                if (ix * GS) ** 2 + (iy * GS) ** 2 <= rad * rad:
                    for l in CU:
                        hole_cells.add(
                            (round(px / GS) + ix,
                             round(py / GS) + iy, l))


def in_keepout(l, qx, qy):
    return (round(qx / GS), round(qy / GS), l) in keep_cells


# board bounds + 5 mm margin — reject flood runaway
_eb = board.GetBoardEdgesBoundingBox()
BX0 = _eb.GetLeft() / 1e6 - 5
BY0 = _eb.GetTop() / 1e6 - 5
BX1 = _eb.GetRight() / 1e6 + 5
BY1 = _eb.GetBottom() / 1e6 + 5


def in_bounds(qx, qy):
    return BX0 <= qx <= BX1 and BY0 <= qy <= BY1


# ---- spatial hash ----------------------------------------------------
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


all_tracks = list(board.GetTracks())
for t in all_tracks:
    add_item(t)
all_pads = []
for fp in board.GetFootprints():
    for p in fp.Pads():
        add_item(p)
        all_pads.append(p)

dead = set()


def dead_(it):
    try:
        return it.m_Uuid.AsString() in dead
    except Exception:
        return False


def hit(l, qx, qy, marg, nc):
    pt = pcbnew.VECTOR2I(int(qx * 1e6), int(qy * 1e6))
    cl = int(marg * 1e6)
    for it, sh in items[l].get((int(qx // BUCK), int(qy // BUCK)), ()):
        if it.GetNetCode() == nc or dead_(it):
            continue
        if sh.Collide(pt, cl):
            return it
    return None


def via_hit(qx, qy, marg, nc):
    for v in viabuck.get((int(qx // BUCK), int(qy // BUCK)), ()):
        if v.GetNetCode() == nc or dead_(v):
            continue
        vx, vy = v.GetPosition().x / 1e6, v.GetPosition().y / 1e6
        if math.hypot(vx - qx, vy - qy) < marg + 0.3:
            return v
    return None


def free(l, qx, qy, nc):
    if in_keepout(l, qx, qy):
        return False
    if (round(qx / GS), round(qy / GS), l) in hole_cells:
        return False
    return hit(l, qx, qy, MARG, nc) is None and \
        via_hit(qx, qy, MARG, nc) is None


def via_legal(qx, qy, nc):
    cell = (round(qx / GS), round(qy / GS), CU[0])
    if cell in hole_cells:
        return False
    for l in CU:
        if in_keepout(l, qx, qy):
            return False
        if hit(l, qx, qy, VIA_MARG, nc) is not None:
            return False
    return via_hit(qx, qy, VIA_MARG, nc) is None


def cells_of_item(it, nc):
    """cells -> anchor point: emits (ix, iy, l, anchor_xy) so emitted
    paths can close onto real copper, not cell centres."""
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


def add_track(x1, y1, x2, y2, ly, nc):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(int(x1 * 1e6), int(y1 * 1e6)))
    t.SetEnd(pcbnew.VECTOR2I(int(x2 * 1e6), int(y2 * 1e6)))
    t.SetWidth(int(TW * 1e6))
    t.SetLayer(ly)
    t.SetNetCode(nc)
    board.Add(t)
    add_item(t)


def add_via(x, y, nc):
    # never stack on an existing via
    for v in viabuck.get((int(x // BUCK), int(y // BUCK)), ()):
        if dead_(v):
            continue
        vx, vy = v.GetPosition().x / 1e6, v.GetPosition().y / 1e6
        if math.hypot(vx - x, vy - y) < 0.35:
            if v.GetNetCode() == nc:
                return
            raise ValueError(f'via site occupied at {x:.2f},{y:.2f}')
    v = pcbnew.PCB_VIA(board)
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetPosition(pcbnew.VECTOR2I(int(x * 1e6), int(y * 1e6)))
    v.SetWidth(int(VIA_D * 1e6))
    v.SetDrill(int(VIA_DRILL * 1e6))
    v.SetNetCode(nc)
    board.Add(v)
    add_item(v)


def clusters_of(nc, pl, conn):
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
    clus.sort(key=lambda c: len(c[0]), reverse=True)
    return clus


def corridor_walls(f, g, nc):
    """foreign items (per kind) blocking cells on the straight segment
    f->g plus the via test at the goal-side end."""
    (fx, fy, fl), (gx, gy, gl) = f, g
    n = int(math.hypot(gx - fx, gy - fy)) or 1
    walls = {}
    ko = False
    for s in range(n + 1):
        qx = (fx + (gx - fx) * s / n) * GS
        qy = (fy + (gy - fy) * s / n) * GS
        if in_keepout(fl, qx, qy):
            ko = True
            continue
        pt = pcbnew.VECTOR2I(int(qx * 1e6), int(qy * 1e6))
        cl = int(MARG * 1e6)
        for it, sh in items[fl].get((int(qx // BUCK), int(qy // BUCK)), ()):
            if it.GetNetCode() == nc or dead_(it):
                continue
            if sh.Collide(pt, cl):
                walls[it.m_Uuid.AsString()] = it
        for v in viabuck.get((int(qx // BUCK), int(qy // BUCK)), ()):
            if v.GetNetCode() == nc or dead_(v):
                continue
            vx, vy = v.GetPosition().x / 1e6, v.GetPosition().y / 1e6
            if math.hypot(vx - qx, vy - qy) < MARG + 0.3:
                walls[v.m_Uuid.AsString()] = v
    return walls, ko


def bfs(seeds, goals, nc, maxpop=2500000):
    gset = set(goals)
    prev = {}
    dq = collections.deque(seeds)
    seen = set(seeds)
    pop = 0
    while dq:
        cur = dq.popleft()
        pop += 1
        if pop > maxpop:
            return None, seen
        if cur in gset:
            path = [cur]
            while cur in prev:
                cur = prev[cur]
                path.append(cur)
            return path[::-1], seen
        ix, iy, ly = cur
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
            ns = (nx2, ny2, nl)
            if ns in seen:
                continue
            if not in_bounds(nx2 * GS, ny2 * GS):
                continue
            if ns in gset or free(nl, nx2 * GS, ny2 * GS, nc):
                seen.add(ns)
                prev[ns] = cur
                dq.append(ns)
    return None, seen


def cell_blockers(l, qx, qy, nc, marg):
    """foreign items blocking a cell on layer l at the given margin."""
    out = []
    pt = pcbnew.VECTOR2I(int(qx * 1e6), int(qy * 1e6))
    cl = int(marg * 1e6)
    for it, sh in items[l].get((int(qx // BUCK), int(qy // BUCK)), ()):
        if it.GetNetCode() == nc or dead_(it):
            continue
        if sh.Collide(pt, cl):
            out.append(it)
    for v in viabuck.get((int(qx // BUCK), int(qy // BUCK)), ()):
        if v.GetNetCode() == nc or dead_(v):
            continue
        vx, vy = v.GetPosition().x / 1e6, v.GetPosition().y / 1e6
        if math.hypot(vx - qx, vy - qy) < marg + 0.3:
            out.append(v)
    return out


MAXCOST = int(sys.argv[2]) if len(sys.argv) > 2 else 10
RIPCAP = int(sys.argv[3]) if len(sys.argv) > 3 else 24


def mincut(seeds, goals, nc, maxpop=3000000, maxcost=None):
    if maxcost is None:
        maxcost = MAXCOST
    """Dijkstra where entering a blocked cell costs per distinct foreign
    item, via transitions cost 2, ripping through a blocked via-site
    costs extra.  Finds the thinnest wall breach into the goal pocket.
    Returns (path, rip_set) or (None, seen)."""
    gset = set(goals)
    W_BLOCK = 1
    W_VIA = 2
    dist = {}
    prev = {}
    pq = []
    for st in seeds:
        dist[st] = 0
        heapq.heappush(pq, (0, st))
    seen = set()
    pop = 0
    while pq:
        f, cur = heapq.heappop(pq)
        if f > maxcost:
            break
        if cur in seen:
            continue
        seen.add(cur)
        pop += 1
        if pop > maxpop:
            return None, seen
        if cur in gset:
            path = [cur]
            while cur in prev:
                cur = prev[cur]
                path.append(cur)
            return path[::-1], seen
        ix, iy, ly = cur
        qx, qy = ix * GS, iy * GS
        nbrs = [(ix + 1, iy, ly, W_BLOCK), (ix - 1, iy, ly, W_BLOCK),
                (ix, iy + 1, ly, W_BLOCK), (ix, iy - 1, ly, W_BLOCK)]
        # via transition: cheap if legal; pricey per ripped layer;
        # a pad in the via stack vetoes the transition entirely;
        # keepout/hole cells on any layer veto too
        if in_keepout(CU[0], qx, qy) or \
                (round(qx / GS), round(qy / GS), CU[0]) in hole_cells:
            continue
        vcost = W_VIA
        veto = False
        for l in CU:
            if in_keepout(l, qx, qy):
                veto = True
                break
            bl = cell_blockers(l, qx, qy, nc, VIA_MARG)
            if any(isinstance(b, pcbnew.PAD) for b in bl):
                veto = True
                break
            if bl:
                vcost += 4
        li = CU.index(ly)
        if not veto:
            for nl in (CU[li - 1] if li > 0 else None,
                       CU[li + 1] if li < len(CU) - 1 else None):
                if nl is not None:
                    nbrs.append((ix, iy, nl, vcost))
        for nx2, ny2, nl, w in nbrs:
            ns = (nx2, ny2, nl)
            if ns in seen:
                continue
            if not in_bounds(nx2 * GS, ny2 * GS):
                continue
            if ns in gset:
                step = 0
            elif nl != ly:
                step = w
            elif free(nl, nx2 * GS, ny2 * GS, nc):
                step = 0
            elif in_keepout(nl, nx2 * GS, ny2 * GS) or \
                    (nx2, ny2, nl) in hole_cells:
                continue
            else:
                bl = [b for b in cell_blockers(nl, nx2 * GS, ny2 * GS,
                                             nc, MARG)
                      if not isinstance(b, pcbnew.PAD)]
                npads = sum(1 for b in
                            cell_blockers(nl, nx2 * GS, ny2 * GS,
                                          nc, MARG)
                            if isinstance(b, pcbnew.PAD))
                if npads:
                    continue        # pads are never ripped
                step = W_BLOCK * max(1, len(bl))
            nd = dist[cur] + step
            if ns not in dist or nd < dist[ns]:
                dist[ns] = nd
                prev[ns] = cur
                heapq.heappush(pq, (nd, ns))
    return None, seen


def rip_for_path(path, nc):
    """collect the foreign non-pad items that must go for this path:
    blocked cells on their layer plus via sites on all layers."""
    rips = {}
    prev_l = path[0][2]
    for ix, iy, ly in path:
        qx, qy = ix * GS, iy * GS
        for b in cell_blockers(ly, qx, qy, nc, MARG):
            if not isinstance(b, pcbnew.PAD):
                rips[b.m_Uuid.AsString()] = b
        if ly != prev_l:
            for l in CU:
                for b in cell_blockers(l, qx, qy, nc, VIA_MARG):
                    if not isinstance(b, pcbnew.PAD):
                        rips[b.m_Uuid.AsString()] = b
        prev_l = ly
    return list(rips.values())


def emit_path(path, nc, seeds=None, goals=None):
    pts = [(ix * GS, iy * GS, l) for ix, iy, l in path]
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        (x0, y0, l0), (x1, y1, l1), (x2, y2, l2) = pts[i - 1:i + 2]
        if l0 != l1 or l1 != l2 or (x1 - x0, y1 - y0) != (x2 - x1, y2 - y1):
            out.append(pts[i])
    out.append(pts[-1])
    # closing stubs: path ends at cell centres which can sit ~0.1 mm
    # short of the actual copper item — anchor to the item's real point
    if seeds:
        a0 = seeds.get(path[0])
        if a0 and (abs(a0[0] - out[0][0]) > 1e-6 or
                   abs(a0[1] - out[0][1]) > 1e-6):
            add_track(a0[0], a0[1], out[0][0], out[0][1], out[0][2], nc)
    if goals:
        a1 = goals.get(path[-1])
        if a1 and (abs(a1[0] - out[-1][0]) > 1e-6 or
                   abs(a1[1] - out[-1][1]) > 1e-6):
            add_track(out[-1][0], out[-1][1], a1[0], a1[1],
                      out[-1][2], nc)
    for i in range(len(out) - 1):
        (x1, y1, l1), (x2, y2, l2) = out[i], out[i + 1]
        if l1 != l2:
            add_via(x1, y1, nc)
        else:
            add_track(x1, y1, x2, y2, l1, nc)
    return len(out) - 1


conn = board.GetConnectivity()
item_by_uuid = {t.m_Uuid.AsString(): t for t in all_tracks}
for p in all_pads:
    item_by_uuid[p.m_Uuid.AsString()] = p

# pour cells as connection targets
zones = [z for z in board.Zones() if not z.GetIsRuleArea()]
try:
    pcbnew.ZONE_FILLER(board).Fill(zones)
except Exception:
    pass
pour_cells = collections.defaultdict(set)
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

# ---- optional: route DRC-flagged unconnected pairs directly ----------
# kicad-cli DRC names real cluster pairs (pads relying on pour alone
# still need track copper).  With a JSON arg, route each non-zone pair.
DRCJSON = sys.argv[4] if len(sys.argv) > 4 else None
if DRCJSON:
    import json as _json
    _d = _json.load(open(DRCJSON))
    _pairs = 0
    zmap = {z.m_Uuid.AsString(): z for z in board.Zones()}

    def zone_cells(z, nc):
        out = {}
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
                        out.setdefault(
                            (round(gx / GS), round(gy / GS), l),
                            (gx, gy))
                    gx += GS * 3
                gy += GS * 3
        return out

    def zone_outline_cells(z, nc):
        """cells per fill outline -> list of {cell: (x,y)} dicts"""
        outs = []
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
            for i in range(polys.OutlineCount()):
                sub = pcbnew.SHAPE_POLY_SET()
                sub.AddOutline(polys.COutline(i))
                bb = sub.BBox()
                cells = {}
                x0, y0 = bb.GetLeft() / 1e6, bb.GetTop() / 1e6
                x1, y1 = bb.GetRight() / 1e6, bb.GetBottom() / 1e6
                gx, gy = x0, y0
                while gy <= y1:
                    gx = x0
                    while gx <= x1:
                        if sub.Collide(pcbnew.VECTOR2I(int(gx * 1e6),
                                                     int(gy * 1e6)), 0):
                            cells.setdefault(
                                (round(gx / GS), round(gy / GS), l),
                                (gx, gy))
                        gx += GS * 3
                    gy += GS * 3
                if cells:
                    outs.append(cells)
        return outs

    for x in _d.get('unconnected_items', []):
        zs = [zmap.get(i.get('uuid')) for i in x.get('items', [])]
        if all(z is not None for z in zs) and len(zs) == 2:
            za, zb = zs
            if za.GetNetCode() != zb.GetNetCode():
                continue
            nc = za.GetNetCode()
            if za is zb:
                # same-object pair = pour islands inside one zone.
                # route each small outline to the biggest (main) region.
                # goals must NOT include all pour cells — the island's own
                # cells would make every 1-cell path a fake "connection".
                outs = zone_outline_cells(za, nc)
                if len(outs) < 2:
                    continue
                outs.sort(key=len, reverse=True)
                goals = dict(outs[0])
                for isl in outs[1:]:
                    for c in isl:
                        goals.pop(c, None)
                    path, _ = bfs(set(isl), set(goals), nc)
                    if not path:
                        path, _ = mincut(set(isl), set(goals), nc)
                        if path:
                            rips = rip_for_path(path, nc)
                            if len(rips) <= RIPCAP:
                                for w in rips:
                                    board.Remove(w)
                                    dead.add(w.m_Uuid.AsString())
                            else:
                                path = None
                    if path:
                        nseg = emit_path(path, nc, isl, goals)
                        _pairs += 1
                        print(f'island pair connected ({nseg} segs)',
                              flush=True)
                continue
            seeds = zone_cells(za, nc)
            goals = zone_cells(zb, nc)
            if not seeds or not goals:
                continue
            path, seen = bfs(set(seeds), set(goals), nc)
            if not path:
                path, _ = mincut(set(seeds), set(goals), nc)
                if path:
                    rips = rip_for_path(path, nc)
                    if len(rips) <= RIPCAP:
                        for w in rips:
                            board.Remove(w)
                            dead.add(w.m_Uuid.AsString())
                    else:
                        path = None
            if path:
                nseg = emit_path(path, nc, seeds, goals)
                _pairs += 1
                print(f'zone pair connected ({nseg} segs)', flush=True)
            continue
        its = [item_by_uuid.get(i.get('uuid'))
               for i in x.get('items', [])]
        its = [i for i in its if i is not None]
        if len(its) != 2:
            continue
        a, b = its
        nc = a.GetNetCode()
        if nc <= 0 or nc != b.GetNetCode():
            continue
        seeds = {}
        for ix, iy, l, anchor in cells_of_item(a, nc):
            seeds.setdefault((ix, iy, l), anchor)
        goals = {}
        for ix, iy, l, anchor in cells_of_item(b, nc):
            goals.setdefault((ix, iy, l), anchor)
        for cell in pour_cells.get(nc, set()):
            goals.setdefault(cell, (cell[0] * GS, cell[1] * GS))
        if not seeds or not goals:
            continue
        path, seen = bfs(set(seeds), set(goals), nc)
        if not path:
            path, _ = mincut(set(seeds), set(goals), nc)
            if path:
                rips = rip_for_path(path, nc)
                if len(rips) <= RIPCAP:
                    for w in rips:
                        board.Remove(w)
                        dead.add(w.m_Uuid.AsString())
                else:
                    path = None
        if path:
            nseg = emit_path(path, nc, seeds, goals)
            _pairs += 1
            try:
                net = board.FindNet(nc).GetNetname()
            except Exception:
                net = str(nc)
            print(f'{net}: DRC pair connected ({nseg} segs)',
                  flush=True)
    print(f'drc pairs connected: {_pairs}', flush=True)
    zones0 = [z for z in board.Zones() if not z.GetIsRuleArea()]
    try:
        pcbnew.ZONE_FILLER(board).Fill(zones0)
    except Exception:
        pass
    pcbnew.SaveBoard(PCB, board)
    print('saved:', PCB, flush=True)
    sys.exit(0)

bynet = collections.defaultdict(list)
for p in all_pads:
    if p.GetNetCode() > 0:
        bynet[p.GetNetCode()].append(p)

connected = 0
for nc, pl in bynet.items():
    if len(pl) < 2:
        continue
    net = board.FindNet(nc).GetNetname()
    clus = clusters_of(nc, pl, conn)
    if len(clus) < 2:
        continue
    for ci in range(1, len(clus)):
        seeds = {}
        for uid in clus[ci][0]:
            it = item_by_uuid.get(uid)
            if it is not None and not dead_(it):
                for ix, iy, l, anchor in cells_of_item(it, nc):
                    seeds.setdefault((ix, iy, l), anchor)
        goals = {}
        for oi, o in enumerate(clus):
            if oi == ci:
                continue
            for uid in o[0]:
                it = item_by_uuid.get(uid)
                if it is not None and not dead_(it):
                    for ix, iy, l, anchor in cells_of_item(it, nc):
                        goals.setdefault((ix, iy, l), anchor)
        for cell in pour_cells.get(nc, set()):
            goals.setdefault(cell, (cell[0] * GS, cell[1] * GS))
        if not goals:
            continue
        ref = clus[ci][1][0].GetParentFootprint().GetReference() + '.' + \
            str(clus[ci][1][0].GetNumber())
        done = False
        seedset = set(seeds)
        goalset = set(goals)
        for attempt in range(5):
            path, seen = bfs(seedset, goalset, nc)
            if path:
                nseg = emit_path(path, nc, seeds, goals)
                connected += 1
                print(f'{net} {ref}: CONNECTED ({nseg} segs, '
                      f'flood={len(seen)})', flush=True)
                done = True
                break
            # BFS found nothing within pop budget — find the thinnest
            # wall breach with min-cost Dijkstra, rip it, emit the path
            path, mseen = mincut(seedset, goalset, nc)
            if not path:
                print(f'{net} {ref}: no cut <= {MAXCOST} weight '
                      f'(flood={len(seen)})', flush=True)
                break
            rips = rip_for_path(path, nc)
            if len(rips) > RIPCAP:
                print(f'{net} {ref}: cut needs {len(rips)} rips — '
                      f'too many', flush=True)
                break
            for w in rips:
                board.Remove(w)
                dead.add(w.m_Uuid.AsString())
                try:
                    wnet = board.FindNet(w.GetNetCode()).GetNetname()
                except Exception:
                    wnet = '?'
                print(f'   rip {type(w).__name__} {wnet}', flush=True)
            nseg = emit_path(path, nc, seeds, goals)
            connected += 1
            print(f'{net} {ref}: CONNECTED via mincut '
                  f'({len(rips)} rips, {nseg} segs)', flush=True)
            done = True
            break
        if not done:
            print(f'{net} {ref}: still islanded', flush=True)

print(f'connected: {connected}', flush=True)
try:
    pcbnew.ZONE_FILLER(board).Fill(zones)
except Exception as e:
    print('final fill failed:', e)
pcbnew.SaveBoard(PCB, board)
print('saved:', PCB, flush=True)
