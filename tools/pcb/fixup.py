#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""fixup.py — mechanical DRC cleanup, guided by kicad-cli's own report.

Pass the board plus the drc JSON produced by
  kicad-cli pcb drc --format json

Fixes, in order:
  * same-net vias closer than the min hole spacing -> delete extras
  * sub-spec via drills (<0.30 mm) -> delete (re-healed by connect.py)
  * zero-length tracks
  * track endpoints within 0.35 mm of same-net copper -> extend to touch
  * items_not_allowed / copper_edge_clearance / holes_co_located
    offenders -> delete; their nets re-island and heal in open space

usage: fixup.py board.kicad_pcb drc.json
"""
import sys
import json
import math
import collections
import pcbnew

PCB, DRC = sys.argv[1], sys.argv[2]
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
drc = json.load(open(DRC))

# ---- obstacle rasters for via legality -------------------------------
keeps = []
for z in list(board.Zones()):
    if z.GetIsRuleArea() and (z.GetDoNotAllowTracks() or
                              z.GetDoNotAllowVias()):
        keeps.append((z, set(z.GetLayerSet().Seq())))
for fp in board.GetFootprints():
    for z in fp.Zones():
        if z.GetIsRuleArea() and (z.GetDoNotAllowTracks() or
                                  z.GetDoNotAllowVias()):
            keeps.append((z, set(z.GetLayerSet().Seq())))
keep_cells = set()
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
                inside = out.Collide(pt, 550000)
            except Exception:
                inside = bb.Contains(pt)
            if inside:
                for l in ls & set(CU):
                    keep_cells.add((round(gx / GS), round(gy / GS), l))
            gx += GS
        gy += GS

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
        rad = r + 0.3
        px, py = p.GetPosition().x / 1e6, p.GetPosition().y / 1e6
        n = int(rad / GS) + 1
        for ix in range(-n, n + 1):
            for iy in range(-n, n + 1):
                if (ix * GS) ** 2 + (iy * GS) ** 2 <= rad * rad:
                    for l in CU:
                        hole_cells.add(
                            (round(px / GS) + ix,
                             round(py / GS) + iy, l))


def via_legal(qx, qy, nc):
    if (round(qx / GS), round(qy / GS), CU[0]) in hole_cells:
        return False
    for l in CU:
        if (round(qx / GS), round(qy / GS), l) in keep_cells:
            return False
        if hit(l, qx, qy, VIA_MARG, nc) is not None:
            return False
    return via_hit(qx, qy, VIA_MARG, nc) is None


def add_via(x, y, nc):
    for v in viabuck.get((int(x // BUCK), int(y // BUCK)), ()):
        if dead_(v):
            continue
        vx, vy = v.GetPosition().x / 1e6, v.GetPosition().y / 1e6
        if math.hypot(vx - x, vy - y) < 0.35:
            return v.GetNetCode() == nc
    v = pcbnew.PCB_VIA(board)
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetPosition(pcbnew.VECTOR2I(int(x * 1e6), int(y * 1e6)))
    v.SetWidth(int(VIA_D * 1e6))
    v.SetDrill(int(VIA_DRILL * 1e6))
    v.SetNetCode(nc)
    board.Add(v)
    add_item(v)
    all_tracks.append(v)
    return True

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
for fp in board.GetFootprints():
    for p in fp.Pads():
        add_item(p)

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


def own_hit(l, qx, qy, marg, nc, skip):
    """own-net copper item (other than skip) within marg of the point —
    endpoint-extension target."""
    pt = pcbnew.VECTOR2I(int(qx * 1e6), int(qy * 1e6))
    cl = int(marg * 1e6)
    best = None
    for it, sh in items[l].get((int(qx // BUCK), int(qy // BUCK)), ()):
        if it.GetNetCode() != nc or it is skip or dead_(it):
            continue
        if sh.Collide(pt, cl):
            best = it
    for v in viabuck.get((int(qx // BUCK), int(qy // BUCK)), ()):
        if v.GetNetCode() != nc or v is skip or dead_(v):
            continue
        vx, vy = v.GetPosition().x / 1e6, v.GetPosition().y / 1e6
        if math.hypot(vx - qx, vy - qy) < marg + 0.3:
            best = v
    return best


removed = 0


def rip(it, why=''):
    global removed
    board.Remove(it)
    dead.add(it.m_Uuid.AsString())
    removed += 1


uuid2item = {t.m_Uuid.AsString(): t for t in all_tracks}

# ---- 1. same-net vias closer than 0.25 mm hole-edge -> delete --------
allvias = [t for t in all_tracks if isinstance(t, pcbnew.PCB_VIA)]
seen_v = []
for v in allvias:
    if dead_(v):
        continue
    x, y = v.GetPosition().x / 1e6, v.GetPosition().y / 1e6
    dup = None
    for u, ux, uy in seen_v:
        if u.GetNetCode() == v.GetNetCode() and \
                math.hypot(ux - x, uy - y) < 0.25:
            dup = u
            break
    if dup is not None:
        rip(v, 'dup via')
    else:
        seen_v.append((v, x, y))

# ---- 2. sub-spec drills (<0.3mm) -> delete ---------------------------
for v in allvias:
    if dead_(v):
        continue
    if v.GetDrill() < 300000:
        rip(v, 'drill<0.3')

# ---- 3. zero-length tracks -------------------------------------------
for t in all_tracks:
    if dead_(t) or isinstance(t, pcbnew.PCB_VIA):
        continue
    if t.GetLength() < 10000:
        rip(t, 'zero-len')

# ---- 4. endpoint near-miss stitching ---------------------------------
# For every track end sitting in air, find the nearest same-net copper
# on the same layer within 0.45 mm in ANY direction and emit a bridge
# segment, provided the corridor is foreign-free.
stitched = 0


def add_track(x1, y1, x2, y2, ly, nc):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(int(x1 * 1e6), int(y1 * 1e6)))
    t.SetEnd(pcbnew.VECTOR2I(int(x2 * 1e6), int(y2 * 1e6)))
    t.SetWidth(int(TW * 1e6))
    t.SetLayer(ly)
    t.SetNetCode(nc)
    board.Add(t)
    add_item(t)
    all_tracks.append(t)


def nearest_own(ly, ex, ey, nc, skip, rad=0.45):
    """nearest same-net copper point on layer ly within rad of (ex,ey),
    excluding item skip."""
    best = None
    bx, by = int(ex // BUCK), int(ey // BUCK)
    for ddx in (-1, 0, 1):
        for ddy in (-1, 0, 1):
            for it, sh in items[ly].get((bx + ddx, by + ddy), ()):
                if it.GetNetCode() != nc or it is skip or dead_(it):
                    continue
                try:
                    x1, y1 = it.GetStart().x / 1e6, it.GetStart().y / 1e6
                    x2, y2 = it.GetEnd().x / 1e6, it.GetEnd().y / 1e6
                    L = math.hypot(x2 - x1, y2 - y1)
                    if L > 1e-9:
                        t_ = max(0, min(1,
                                 ((ex - x1) * (x2 - x1) +
                                  (ey - y1) * (y2 - y1)) / (L * L)))
                        cx, cy = x1 + t_ * (x2 - x1), y1 + t_ * (y2 - y1)
                    else:
                        cx, cy = x1, y1
                except Exception:
                    try:
                        pos = it.GetPosition()
                        cx, cy = pos.x / 1e6, pos.y / 1e6
                    except Exception:
                        continue
                d = math.hypot(cx - ex, cy - ey)
                if best is None or d < best[0]:
                    best = (d, cx, cy)
            for v in viabuck.get((bx + ddx, by + ddy), ()):
                if v.GetNetCode() != nc or dead_(v):
                    continue
                vx, vy = v.GetPosition().x / 1e6, v.GetPosition().y / 1e6
                d = math.hypot(vx - ex, vy - ey)
                if best is None or d < best[0]:
                    best = (d, vx, vy)
    if best is not None and 0.01 < best[0] <= rad:
        return best[1], best[2]
    return None


for t in list(all_tracks):
    if dead_(t) or isinstance(t, pcbnew.PCB_VIA):
        continue
    nc = t.GetNetCode()
    ly = t.GetLayer()
    x1, y1 = t.GetStart().x / 1e6, t.GetStart().y / 1e6
    x2, y2 = t.GetEnd().x / 1e6, t.GetEnd().y / 1e6
    for ex, ey in ((x1, y1), (x2, y2)):
        if own_hit(ly, ex, ey, 0.02, nc, t) is not None:
            continue
        tgt = nearest_own(ly, ex, ey, nc, t)
        if tgt is None:
            continue
        n = max(1, int(math.hypot(tgt[0] - ex, tgt[1] - ey) / 0.05))
        ok = True
        for s in range(1, n):
            qx = ex + (tgt[0] - ex) * s / n
            qy = ey + (tgt[1] - ey) * s / n
            if hit(ly, qx, qy, MARG - 0.02, nc) is not None or \
                    via_hit(qx, qy, MARG - 0.02, nc) is not None:
                ok = False
                break
        if not ok:
            continue
        add_track(ex, ey, tgt[0], tgt[1], ly, nc)
        stitched += 1

# ---- 4b. authoritative pair bridges ----------------------------------
# For every unconnected pair the DRC named, bridge the two items'
# closest points when the corridor is foreign-free (<=0.6 mm).
pair_bridged = 0
zones_by_uuid = {z.m_Uuid.AsString(): z for z in board.Zones()}
pads_by_uuid = {}
for fp in board.GetFootprints():
    for p in fp.Pads():
        pads_by_uuid[p.m_Uuid.AsString()] = p


def item_point(it):
    try:
        pos = it.GetPosition()
        return pos.x / 1e6, pos.y / 1e6
    except Exception:
        pass
    try:
        x1, y1 = it.GetStart().x / 1e6, it.GetStart().y / 1e6
        x2, y2 = it.GetEnd().x / 1e6, it.GetEnd().y / 1e6
        return (x1 + x2) / 2, (y1 + y2) / 2
    except Exception:
        pass
    return None


def closest_pts(a, b):
    """closest approach between two copper items; returns
    (dist, point_on_a, point_on_b)."""
    pa, pb = item_point(a), item_point(b)
    if pa is None or pb is None:
        return None

    def seg(it):
        try:
            return (it.GetStart().x / 1e6, it.GetStart().y / 1e6,
                    it.GetEnd().x / 1e6, it.GetEnd().y / 1e6)
        except Exception:
            return None

    def proj(px, py, s):
        x1, y1, x2, y2 = s
        L = math.hypot(x2 - x1, y2 - y1)
        if L < 1e-9:
            return x1, y1
        t_ = max(0, min(1, ((px - x1) * (x2 - x1) +
                            (py - y1) * (y2 - y1)) / (L * L)))
        return x1 + t_ * (x2 - x1), y1 + t_ * (y2 - y1)

    sa, sb = seg(a), seg(b)
    if sa and sb:
        # check all endpoint projections both ways
        best = None
        for p, s_ in ((sa[:2], sb), (sa[2:], sb), (sb[:2], sa), (sb[2:], sa)):
            q = proj(p[0], p[1], s_)
            d = math.hypot(q[0] - p[0], q[1] - p[1])
            if best is None or d < best[0]:
                best = (d, p, q, s_ is sa)
        if best[3]:
            return best[0], best[1], best[2]
        return best[0], best[2], best[1]
    if sa:
        q = proj(pb[0], pb[1], sa)
        return math.hypot(q[0] - pb[0], q[1] - pb[1]), q, pb
    if sb:
        q = proj(pa[0], pa[1], sb)
        return math.hypot(q[0] - pa[0], q[1] - pa[1]), pa, q
    return math.hypot(pa[0] - pb[0], pa[1] - pb[1]), pa, pb


for x in drc.get('unconnected_items', []):
    its = []
    for i in x.get('items', []):
        u = i.get('uuid')
        it = uuid2item.get(u) or pads_by_uuid.get(u)
        if it is not None and not dead_(it):
            its.append(it)
    if len(its) != 2:
        continue
    a, b = its
    if a.GetNetCode() != b.GetNetCode():
        continue
    nc = a.GetNetCode()
    r = closest_pts(a, b)
    if r is None:
        continue
    (px1, py1), (px2, py2) = r[1], r[2]
    la = set(a.GetLayerSet().Seq()) & set(CU)
    lb = set(b.GetLayerSet().Seq()) & set(CU)
    shared = la & lb
    bridged = False
    if shared and r[0] <= 0.6:
        ly = sorted(shared)[0]
        n = max(1, int(math.hypot(px2 - px1, py2 - py1) / 0.05))
        ok = True
        for s in range(1, n):
            qx = px1 + (px2 - px1) * s / n
            qy = py1 + (py2 - py1) * s / n
            if hit(ly, qx, qy, MARG - 0.02, nc) is not None or \
                    via_hit(qx, qy, MARG - 0.02, nc) is not None:
                ok = False
                break
        if ok:
            add_track(px1, py1, px2, py2, ly, nc)
            bridged = True
    if not bridged and r[0] <= 0.35:
        # cross-layer near-touch: a via at the midpoint joins both
        mx, my = (px1 + px2) / 2, (py1 + py2) / 2
        if via_legal(mx, my, nc):
            if add_via(mx, my, nc):
                bridged = True
    if bridged:
        pair_bridged += 1


# ---- 5. delete keepout/edge/co-located offenders from the DRC --------
doom = set()
for v in drc.get('violations', []):
    if v['type'] in ('items_not_allowed', 'holes_co_located'):
        for i in v.get('items', []):
            u = i.get('uuid')
            if u and u in uuid2item and not isinstance(
                    uuid2item[u], pcbnew.PAD):
                # co-located pair: delete exactly one member
                if v['type'] == 'holes_co_located':
                    others = [j.get('uuid') for j in v['items']
                              if j.get('uuid') != u]
                    if any(o in doom for o in others):
                        continue
                doom.add(u)
    elif v['type'] in ('copper_edge_clearance', 'track_dangling',
                       'via_dangling', 'clearance', 'hole_clearance'):
        for i in v.get('items', []):
            if i.get('description', '').startswith('Track') or \
                    i.get('description', '').startswith('Via'):
                u = i.get('uuid')
                if u and u in uuid2item:
                    doom.add(u)
for u in doom:
    it = uuid2item[u]
    if not dead_(it):
        rip(it, 'drc-offender')

print(f'removed={removed} stitched={stitched} '
      f'pair_bridged={pair_bridged}', flush=True)
pcbnew.SaveBoard(PCB, board)
print('saved:', PCB, flush=True)
