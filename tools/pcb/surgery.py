#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""surgery.py — minimal interventions for sealed island pads.

For every pad whose connected cluster is tiny (island):
  * if a via-in-pad is legal, drop it — the pad's cluster then spans all
    four copper layers and reroute can reach it from anywhere;
  * if the via is blocked only by emitted tracks/vias (never pads), rip
    the blockers and drop the via — the victim nets re-island but reroute
    heals them in open space;
  * report pads that remain sealed so a human pass can see the wall.

usage: surgery.py board.kicad_pcb
"""
import sys
import math
import collections
import pcbnew

PCB = sys.argv[1]
GS = 0.12
VM = 0.52            # via annulus + clearance + slack
VIA_D, VIA_DRILL = 0.6, 0.3
VM_S = 0.45          # small-via margin: 0.225 annulus + 0.2 clr + slack
VIA_DS, VIA_DRILLS = 0.45, 0.2
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


all_tracks = list(board.GetTracks())
for t in all_tracks:
    add_item(t)
all_pads = []
item_by_uuid = {}
for t in all_tracks:
    item_by_uuid[t.m_Uuid.AsString()] = t
for fp in board.GetFootprints():
    for p in fp.Pads():
        add_item(p)
        all_pads.append(p)
        item_by_uuid[p.m_Uuid.AsString()] = p


dead = set()


def dead_(it):
    try:
        return it.m_Uuid.AsString() in dead
    except Exception:
        return False


def blockers_at(qx, qy, nc, vm=VM):
    """foreign items within via margin of point, per layer (tracks/vias
    are rippable, pads are not)."""
    out = []
    for l in CU:
        pt = pcbnew.VECTOR2I(int(qx * 1e6), int(qy * 1e6))
        cl = int(vm * 1e6)
        for it, sh in items[l].get((int(qx // BUCK), int(qy // BUCK)), ()):
            if it.GetNetCode() == nc or dead_(it):
                continue
            if sh.Collide(pt, cl):
                out.append(it)
    for v in viabuck.get((int(qx // BUCK), int(qy // BUCK)), ()):
        if v.GetNetCode() == nc or dead_(v):
            continue
        vx, vy = v.GetPosition().x / 1e6, v.GetPosition().y / 1e6
        if math.hypot(vx - qx, vy - qy) < vm + 0.3:
            out.append(v)
    return out


def via_legal(qx, qy, nc, vm=VM):
    return not blockers_at(qx, qy, nc, vm)


def add_via(x, y, nc, d=VIA_D, drill=VIA_DRILL):
    v = pcbnew.PCB_VIA(board)
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetPosition(pcbnew.VECTOR2I(int(x * 1e6), int(y * 1e6)))
    v.SetWidth(int(d * 1e6))
    v.SetDrill(int(drill * 1e6))
    v.SetNetCode(nc)
    board.Add(v)
    add_item(v)


MARG = 0.345


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
    return hit(l, qx, qy, MARG, nc) is None and \
        via_hit(qx, qy, MARG, nc) is None


def flood_escape(seeds0, nc):
    """bounded BFS over all layers from cluster cells; find the flooded
    cell where a via becomes legal with the fewest track rips (<=3) and
    the flood path to it.  Returns (path_cells, site, rips) or None."""
    seen = set(seeds0)
    dq = collections.deque(seeds0)
    prev = {}
    hp = {s: 0 for s in seeds0}
    best = None          # (nrips, hops, cell, site)
    steps = 0
    while dq and steps < 150000:
        ix, iy, ly = dq.popleft()
        steps += 1
        qx, qy = ix * GS, iy * GS
        # via legality at this flooded cell
        bl = [x for x in blockers_at(qx, qy, nc)
              if not isinstance(x, pcbnew.PAD)]
        npads = len(blockers_at(qx, qy, nc)) - len(bl)
        if npads == 0:
            hops = hp[(ix, iy, ly)]
            if best is None or (len(bl), hops) < (best[0], best[2]):
                best = (len(bl), steps, hops, (ix, iy, ly), (qx, qy))
                if len(bl) == 0 and hops > 3:
                    break
        nbrs = [(ix + 1, iy, ly), (ix - 1, iy, ly),
                (ix, iy + 1, ly), (ix, iy - 1, ly)]
        if via_legal(qx, qy, nc):
            li = CU.index(ly)
            for nl in (CU[li - 1] if li > 0 else None,
                       CU[li + 1] if li < len(CU) - 1 else None):
                if nl is not None:
                    nbrs.append((ix, iy, nl))
        for ns in nbrs:
            nx, ny, nl = ns
            if ns in seen:
                continue
            if free(nl, nx * GS, ny * GS, nc):
                seen.add(ns)
                prev[ns] = (ix, iy, ly)
                hp[ns] = hp[(ix, iy, ly)] + 1
                dq.append(ns)
    if best is None or best[0] > 3:
        return None
    cell = best[3]
    path = [cell]
    while cell in prev:
        cell = prev[cell]
        path.append(cell)
    return path[::-1], best[4], [x for x in blockers_at(*best[4], nc)
                                if not isinstance(x, pcbnew.PAD)]


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


def pad_seed_cells(p, nc):
    out = cells_of_item(p, nc)
    for it in conn.GetConnectedItems(p):
        out += cells_of_item(it, nc)
    return out


def rim_via_site(p, nc):
    """find a via site hugging the pad rim — annulus still touches pad
    copper but sits in the gap direction between neighbours.  Returns
    (qx, qy, via_d, via_drill) or None."""
    px, py = p.GetPosition().x / 1e6, p.GetPosition().y / 1e6
    bb = p.GetBoundingBox()
    hw = max(bb.GetRight() / 1e6 - px, px - bb.GetLeft() / 1e6)
    hh = max(bb.GetBottom() / 1e6 - py, py - bb.GetTop() / 1e6)
    rad = max(hw, hh)
    try:
        psh = p.GetEffectiveShape(pcbnew.F_Cu)
    except Exception:
        psh = None
    for vm, vd, vdr in ((VM_S, VIA_DS, VIA_DRILLS), (VM, VIA_D, VIA_DRILL)):
        vrad = vd / 2
        for r in (rad + 0.02, rad + 0.12, rad + 0.25, rad + 0.4):
            for k in range(32):
                a = k * math.pi / 16
                qx, qy = px + math.cos(a) * r, py + math.sin(a) * r
                # annulus must still overlap pad copper
                if psh is not None and not psh.Collide(
                        pcbnew.VECTOR2I(int(qx * 1e6), int(qy * 1e6)),
                        int(vrad * 1e6)):
                    continue
                if not blockers_at(qx, qy, nc, vm):
                    return (qx, qy, vd, vdr)
    return None


def wedge_escape(p, nc):
    """scan 32 directions x pad's layers from the pad edge outward; find
    the corridor that needs the fewest foreign-track rips (pads veto a
    direction).  Returns (layer, angle, rips, tip) or None."""
    pl = [l for l in CU if l in set(p.GetLayerSet().Seq())]
    px, py = p.GetPosition().x / 1e6, p.GetPosition().y / 1e6
    best = None
    for l in pl:
        for k in range(32):
            a = k * math.pi / 16
            dx, dy = math.cos(a), math.sin(a)
            rips = []
            veto = False
            r = 0.2
            steps = int(1.6 / GS)
            blocked_run = 0
            for s in range(steps):
                qx, qy = px + dx * (r + s * GS), py + dy * (r + s * GS)
                bl = [x for x in blockers_at(qx, qy, nc, MARG)
                      if not dead_(x)]
                pads_in = [x for x in bl if isinstance(x, pcbnew.PAD)]
                if pads_in:
                    veto = True
                    break
                trs = [x for x in bl if not isinstance(x, pcbnew.PAD)]
                for x in trs:
                    if x not in rips:
                        rips.append(x)
                if trs:
                    blocked_run += 1
                else:
                    blocked_run = 0
                if blocked_run > 4:
                    break
            if veto or blocked_run > 4:
                continue
            # corridor clears: score by rips then free ending
            if best is None or len(rips) < len(best[2]):
                best = (l, a, rips,
                        (px + dx * (r + steps * GS),
                         py + dy * (r + steps * GS)))
    return best


def add_track(x1, y1, x2, y2, ly, nc):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(int(x1 * 1e6), int(y1 * 1e6)))
    t.SetEnd(pcbnew.VECTOR2I(int(x2 * 1e6), int(y2 * 1e6)))
    t.SetWidth(250000)
    t.SetLayer(ly)
    t.SetNetCode(nc)
    board.Add(t)
    add_item(t)


# island = pad whose connected cluster is not the largest of its net
islands = []
net_clusters = {}
bynet = collections.defaultdict(list)
for p in all_pads:
    if p.GetNetCode() > 0:
        bynet[p.GetNetCode()].append(p)
for nc, pl in bynet.items():
    if len(pl) < 2:
        continue
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
    net_clusters[nc] = clus
    for c in clus[1:]:
        islands.extend(c[1])
print(f'island pads: {len(islands)}', flush=True)

placed, ripped, sealed = 0, 0, []
for p in islands:
    fp = p.GetParentFootprint()
    if True:
        nc = p.GetNetCode()
        if nc <= 0:
            continue
        ref = fp.GetReference() + '.' + str(p.GetNumber())
        net = board.FindNet(nc).GetNetname()
        px, py = p.GetPosition().x / 1e6, p.GetPosition().y / 1e6
        # best via site over the pad area (cell centres), scored at both
        # the 0.6 mm and the 0.45 mm via margins — fine-pitch neighbours
        # veto the big via but often clear the small one
        site, site_blockers = None, None
        site_s = None
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                qx, qy = (px / GS + i) * GS, (py / GS + j) * GS
                bl = blockers_at(qx, qy, nc)
                tb = [x for x in bl if isinstance(x, pcbnew.PCB_VIA)
                      or not isinstance(x, pcbnew.PAD)]
                if site is None or len(tb) < len(site_blockers):
                    site, site_blockers = (qx, qy), bl
                if site_s is None and not blockers_at(qx, qy, nc, VM_S):
                    site_s = (qx, qy)
        if site_blockers is None:
            site_blockers = []
        pads_only = all(isinstance(x, pcbnew.PAD) for x in site_blockers)
        if via_legal(*site, nc):
            add_via(*site, nc)
            placed += 1
            print(f'{ref} {net}: via-in-pad', flush=True)
        elif site_s is not None:
            add_via(*site_s, nc, VIA_DS, VIA_DRILLS)
            placed += 1
            print(f'{ref} {net}: small via-in-pad', flush=True)
        elif rim_via_site(p, nc):
            qx, qy, vd, vdr = rim_via_site(p, nc)
            add_via(qx, qy, nc, vd, vdr)
            placed += 1
            print(f'{ref} {net}: rim via', flush=True)
        elif pads_only:
            # corridor surgery: flood out, rip cheapest wall for a via
            r = flood_escape(pad_seed_cells(p, nc), nc)
            if r:
                path, vs, rips = r
                for x in rips:
                    board.Remove(x)
                    try:
                        dead.add(x.m_Uuid.AsString())
                    except Exception:
                        pass
                    ripped += 1
                add_via(*vs, nc)
                ly = path[0][2]
                for i in range(len(path) - 1):
                    add_track(path[i][0] * GS, path[i][1] * GS,
                              path[i + 1][0] * GS, path[i + 1][1] * GS,
                              ly, nc)
                placed += 1
                print(f'{ref} {net}: corridor via, {len(rips)} rips, '
                      f'{len(path)}-cell stub', flush=True)
            else:
                # wedge escape: rip a cheap corridor straight out
                w = wedge_escape(p, nc)
                if w:
                    wl, wa, rips, tip = w
                    for x in rips:
                        board.Remove(x)
                        try:
                            dead.add(x.m_Uuid.AsString())
                        except Exception:
                            pass
                        ripped += 1
                    add_track(px, py, tip[0], tip[1], wl, nc)
                    print(f'{ref} {net}: wedge escape, {len(rips)} '
                          f'rips on {pcbnew.LayerName(wl)}', flush=True)
                else:
                    sealed.append((ref, net, 'pads-only wall'))
                    print(f'{ref} {net}: SEALED by pads '
                          f'{[x.GetPadName() for x in site_blockers][:4]}',
                          flush=True)
        else:
            # bounded rip: clear all non-pad items in a small box so the
            # pad gets breathing room; reroute heals the victims
            R = 1.8
            doomed = []
            for x in all_tracks:
                if x.GetNetCode() == nc or dead_(x):
                    continue
                bb = x.GetBoundingBox()
                if (bb.GetRight() / 1e6 < px - R or
                        bb.GetLeft() / 1e6 > px + R or
                        bb.GetBottom() / 1e6 < py - R or
                        bb.GetTop() / 1e6 > py + R):
                    continue
                doomed.append(x)
            for x in doomed:
                board.Remove(x)
                try:
                    dead.add(x.m_Uuid.AsString())
                except Exception:
                    pass
                ripped += 1
            site_blockers = blockers_at(*site, nc)
            if not site_blockers:
                add_via(*site, nc)
                placed += 1
            print(f'{ref} {net}: ripped {len(doomed)} in-box, via '
                  f'{"ok" if not site_blockers else "still blocked"}',
                  flush=True)
            if site_blockers:
                w = wedge_escape(p, nc)
                if w:
                    wl, wa, rips, tip = w
                    for x in rips:
                        board.Remove(x)
                        try:
                            dead.add(x.m_Uuid.AsString())
                        except Exception:
                            pass
                        ripped += 1
                    add_track(px, py, tip[0], tip[1], wl, nc)
                    print(f'{ref} {net}: wedge escape, {len(rips)} '
                          f'rips on {pcbnew.LayerName(wl)}', flush=True)
                else:
                    sealed.append((ref, net, 'post-rip still blocked'))

# ---- hub-cluster escapes: a sealed *main* cluster also needs a window
for nc, clus in net_clusters.items():
    if len(clus) < 2:
        continue
    seeds = set()
    for uid in clus[0][0]:
        it = item_by_uuid.get(uid)
        if it is not None:
            seeds.update(cells_of_item(it, nc))
    if not seeds:
        continue
    r = flood_escape(seeds, nc)
    if not r:
        print(f'{board.FindNet(nc).GetNetname()}: hub pocket unopened')
        continue
    path, site, rips = r
    for x in rips:
        board.Remove(x)
        try:
            dead.add(x.m_Uuid.AsString())
        except Exception:
            pass
        ripped += 1
    add_via(*site, nc)
    placed += 1
    for i in range(len(path) - 1):
        (x1, y1, l1), (x2, y2, l2) = path[i], path[i + 1]
        if l1 != l2:
            add_via(x1 * GS, y1 * GS, nc)
        else:
            add_track(x1 * GS, y1 * GS, x2 * GS, y2 * GS, l1, nc)
    print(f'{board.FindNet(nc).GetNetname()}: hub escape, {len(rips)} '
          f'rips, {len(path)}-cell path', flush=True)

print(f'vias placed: {placed}, items ripped: {ripped}, sealed: {len(sealed)}')
pcbnew.SaveBoard(PCB, board)
print('saved:', PCB)
