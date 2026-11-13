# SPDX-License-Identifier: AGPL-3.0-or-later
"""rescue_vias.py — verified pocket-escape for island pads.

For each island pad, flood the pad's reachable region (own-stamp seeds,
grid via hops) and, separately, flood *backwards* from the net's real
main cluster — the union of every other same-net pad's connected items.
A stitch via only counts as an escape when it sits on the pad flood on
one layer *and* on the main-cluster flood on another layer.  That keeps
the search honest: dead-end fragments the net happens to own are never
mistaken for the cluster.  Stubs are emitted along the flooded paths
plus a pad-centre closing stub and an overshoot into the main-stamped
cells so the emitted copper physically reaches the cluster.

Usage: python3 tools/pcb/rescue_vias.py board.kicad_pcb
"""
import collections
import sys

sys.argv = ['rescue', sys.argv[1] if len(sys.argv) > 1 else
            'hardware/release/electrical/ecocell-ocean.kicad_pcb']
_src = open('tools/pcb/attach_signals.py').read()
exec(compile(_src[:_src.find('for rnd in range(10):')], 'attach', 'exec'))

# board.Remove() can orphan the swig track-list proxy mid-session; fall
# back to an un-deduped via add if GetTracks stops being iterable
_add_via = add_via


def add_via(x, y, nc):
    try:
        _add_via(x, y, nc)
    except TypeError:
        holes.append((x, y, VIA_DRILL/2, nc))
        v = pcbnew.PCB_VIA(board)
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetPosition(pcbnew.VECTOR2I(int(x*1e6), int(y*1e6)))
        v.SetWidth(pcbnew.FromMM(VIA_D))
        v.SetDrill(pcbnew.FromMM(VIA_DRILL))
        v.SetNetCode(nc)
        board.Add(v)


# --- real geometry for the continuous via check ---------------------------
segs = []
for t in board.GetTracks():
    if isinstance(t, pcbnew.PCB_VIA):
        continue
    s, e = t.GetStart(), t.GetEnd()
    segs.append((s.x/1e6, s.y/1e6, e.x/1e6, e.y/1e6,
                 t.GetWidth()/2/1e6, netcode(t), t.GetLayer()))
rects = []
for fp in board.GetFootprints():
    for p in fp.Pads():
        bb = p.GetBoundingBox()
        rects.append(((bb.GetLeft()+bb.GetRight())/2/1e6,
                      (bb.GetTop()+bb.GetBottom())/2/1e6,
                      (bb.GetRight()-bb.GetLeft())/2/1e6,
                      (bb.GetBottom()-bb.GetTop())/2/1e6,
                      netcode(p), [l for l in CU if p.IsOnLayer(l)]))

KEEPS = []
for z in board.Zones():
    if z.GetIsRuleArea() and (z.GetDoNotAllowTracks() or
                            z.GetDoNotAllowVias()):
        o = z.Outline()
        for oi in range(o.OutlineCount()):
            lc = o.COutline(oi)
            KEEPS.append([(lc.CPoint(i).x/1e6, lc.CPoint(i).y/1e6)
                          for i in range(lc.PointCount())])
for fp in board.GetFootprints():
    for z in fp.Zones():
        if z.GetDoNotAllowTracks() or z.GetDoNotAllowVias():
            o = z.Outline()
            for oi in range(o.OutlineCount()):
                lc = o.COutline(oi)
                KEEPS.append([(lc.CPoint(i).x/1e6, lc.CPoint(i).y/1e6)
                              for i in range(lc.PointCount())])


def pt_seg_dist(px, py, ax, ay, bx, by):
    vx, vy = bx-ax, by-ay
    wx, wy = px-ax, py-ay
    l2 = vx*vx + vy*vy
    t = 0 if l2 == 0 else max(0, min(1, (wx*vx+wy*vy)/l2))
    ex, ey = ax+vx*t, ay+vy*t
    return ((px-ex)**2 + (py-ey)**2) ** 0.5


def in_keeps(x, y, margin):
    for poly in KEEPS:
        inside = False
        d = 1e9
        n = len(poly)
        for i in range(n):
            x1, y1 = poly[i]
            x2, y2 = poly[(i+1) % n]
            d = min(d, pt_seg_dist(x, y, x1, y1, x2, y2))
            if (y1 > y) != (y2 > y) and \
                    x < (x2-x1)*(y-y1)/(y2-y1) + x1:
                inside = not inside
        if inside or d < margin:
            return True
    return False


def dseg(ax, ay, bx, by, px, py):
    return pt_seg_dist(px, py, ax, ay, bx, by)


BUCKET = 4.0
segidx = {}
for si, (ax, ay, bx, by, w2, n2, ly) in enumerate(segs):
    for bx_ in range(int(min(ax, bx)/BUCKET), int(max(ax, bx)/BUCKET)+1):
        for by_ in range(int(min(ay, by)/BUCKET), int(max(ay, by)/BUCKET)+1):
            segidx.setdefault((bx_, by_), []).append(si)
rectidx = {}
for ri, (cx, cy, hx2, hy2, n2, lys) in enumerate(rects):
    for bx_ in range(int((cx-hx2)/BUCKET), int((cx+hx2)/BUCKET)+1):
        for by_ in range(int((cy-hy2)/BUCKET), int((cy+hy2)/BUCKET)+1):
            rectidx.setdefault((bx_, by_), []).append(ri)


def via_ok_p(x, y, nc, vr=VIA_R):
    """continuous all-layer via check — drill, seg and pad-rect distances"""
    R = vr + CLR + 0.8
    for hx, hy, hr, hnc in holes:
        if hnc != nc and (x-hx)**2 + (y-hy)**2 < \
                (hr + VIA_DRILL/2 + 0.25)**2:
            return False
    for si in segidx.get((int(x/BUCKET), int(y/BUCKET)), ()):
        ax, ay, bx, by, w2, n2, ly = segs[si]
        if n2 == nc:
            continue
        if min(ax, bx)-R > x or max(ax, bx)+R < x or \
                min(ay, by)-R > y or max(ay, by)+R < y:
            continue
        if dseg(ax, ay, bx, by, x, y) < w2 + vr + CLR:
            return False
    for ri in rectidx.get((int(x/BUCKET), int(y/BUCKET)), ()):
        cx, cy, hx2, hy2, n2, lys = rects[ri]
        if n2 == nc:
            continue
        if abs(x-cx) < hx2 + vr + CLR and abs(y-cy) < hy2 + vr + CLR:
            return False
    if in_keeps(x, y, vr):
        return False
    if x < EDGE + VIA_R or y < EDGE + VIA_R or \
            x > W - EDGE - VIA_R or y > H - EDGE - VIA_R:
        return False
    return True


def flood_pad(seeds, nc, box=None):
    """flood through the stamped grid, via-gated layer hops;
    `box` (x0,y0,x1,y1 in cells) optionally bounds the walk"""
    seen = set(seeds)
    dq = collections.deque(seeds)
    parent = {}
    while dq:
        ix, iy, ly = dq.popleft()
        for nx, ny in ((ix+1, iy), (ix-1, iy), (ix, iy+1), (ix, iy-1)):
            if box and not (box[0] <= nx <= box[2] and
                            box[1] <= ny <= box[3]):
                continue
            if 0 <= nx < NX and 0 <= ny < NY and \
                    cell_free(nx, ny, ly, nc) and (nx, ny, ly) not in seen:
                seen.add((nx, ny, ly))
                parent[(nx, ny, ly)] = (ix, iy, ly)
                dq.append((nx, ny, ly))
        li = CU.index(ly)
        for nl in (CU[li-1] if li > 0 else None,
                   CU[li+1] if li < len(CU)-1 else None):
            if nl is None:
                continue
            st = (ix, iy, nl)
            if st not in seen and cell_free(ix, iy, ly, nc) and \
                    cell_free(ix, iy, nl, nc) and via_ok(ix*GS, iy*GS, nc):
                seen.add(st)
                parent[st] = (ix, iy, ly)
                dq.append(st)
    return seen, parent


def stamp_item_cells(it, s):
    try:
        if isinstance(it, pcbnew.PCB_VIA):
            vx, vy = it.GetPosition().x/1e6, it.GetPosition().y/1e6
            for ly in CU:
                for iy in range(int((vy-0.6)/GS), int((vy+0.6)/GS)+1):
                    for ix in range(int((vx-0.6)/GS), int((vx+0.6)/GS)+1):
                        if (ix*GS-vx)**2 + (iy*GS-vy)**2 < 0.45**2:
                            s.add((ix, iy, ly))
        elif isinstance(it, pcbnew.PCB_TRACK):
            st, en = it.GetStart(), it.GetEnd()
            if not hasattr(st, 'x'):
                return
            w = it.GetWidth()/2e6
            ly = it.GetLayer()
            ax, ay, bx, by = st.x/1e6, st.y/1e6, en.x/1e6, en.y/1e6
            for iy in range(int((min(ay, by)-w-0.3)/GS),
                            int((max(ay, by)+w+0.3)/GS)+1):
                for ix in range(int((min(ax, bx)-w-0.3)/GS),
                                int((max(ax, bx)+w+0.3)/GS)+1):
                    if dseg(ax, ay, bx, by, ix*GS, iy*GS) < w+0.35:
                        s.add((ix, iy, ly))
        elif isinstance(it, pcbnew.PAD):
            bb = it.GetBoundingBox()
            for ly2 in CU:
                if not it.IsOnLayer(ly2):
                    continue
                for iy in range(int(bb.GetTop()/1e6/GS),
                                int(bb.GetBottom()/1e6/GS)+1):
                    for ix in range(int(bb.GetLeft()/1e6/GS),
                                    int(bb.GetRight()/1e6/GS)+1):
                        s.add((ix, iy, ly2))
    except Exception:
        pass


def backtrack(end, parent):
    path = [end]
    cur = end
    while cur in parent:
        cur = parent[cur]
        path.append(cur)
    return path[::-1]


def emit_path(path, nc):
    """emit collinear runs of track + vias at layer hops"""
    i = 0
    while i < len(path)-1:
        a = path[i]
        j = i+1
        while j < len(path)-1 and path[j][2] == a[2]:
            (px_, py_, _), (nx_, ny_, _) = path[j-1], path[j]
            (qx_, qy_, _) = path[j+1]
            if (nx_-px_, ny_-py_) != (qx_-nx_, qy_-ny_):
                break
            j += 1
        b = path[j]
        add_track(a[0]*GS, a[1]*GS, b[0]*GS, b[1]*GS, a[2], nc)
        i = j
        if i < len(path)-1 and path[i+1][2] != a[2]:
            add_via(path[i][0]*GS, path[i][1]*GS, nc)
            i += 1


def extend_into(end, targets, nc):
    """overshoot the emitted path's end into the target-stamped cells so
    the copper physically overlaps a cluster item, not just its margin."""
    ex, ey, ely = end
    best = None
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        run = 0
        for k in range(1, 10):
            if (ex+dx*k, ey+dy*k, ely) in targets:
                run = k
            else:
                break
        if run and (best is None or run > best[0]):
            best = (run, dx, dy)
    if best:
        run, dx, dy = best
        add_track(ex*GS, ey*GS, (ex+dx*(run+2))*GS,
                  (ey+dy*(run+2))*GS, ely, nc)
    return best


conn = board.GetConnectivity()

# --- per-net clusters, computed once (islands() does this per call) -------
net_clusters = {}
pad_clus = {}
for net in board.GetNetsByName().values():
    name = net.GetNetname()
    if not name or name.startswith('unconnected'):
        continue
    nc = net.GetNetCode()
    pads = [p for fp in board.GetFootprints() for p in fp.Pads()
            if p.GetNetCode() == nc]
    if len(pads) < 2:
        continue
    clus = []
    for p in pads:
        ids = set(x.m_Uuid.AsString() for x in conn.GetConnectedItems(p))
        hit = [c for c in clus if c[0] & ids]
        if hit:
            hit[0][0] |= ids
            hit[0][1].append(p)
        else:
            clus.append([ids, [p]])
    merged = True
    while merged:
        merged = False
        for i in range(len(clus)):
            for j in range(i+1, len(clus)):
                if clus[i][0] & clus[j][0]:
                    clus[i][0] |= clus[j][0]
                    clus[i][1] += clus[j][1]
                    clus.pop(j)
                    merged = True
                    break
            else:
                continue
            break
    net_clusters[nc] = clus
    for ci, c in enumerate(clus):
        for p in c[1]:
            pad_clus[p.m_Uuid.AsString()] = (nc, ci)

clus_cells = {}
clus_items = {}
for nc, clus in net_clusters.items():
    for ci, (ids, cpads) in enumerate(clus):
        cells = set()
        items = list(conn.GetConnectedItems(cpads[0]))
        for it in items:
            stamp_item_cells(it, cells)
        clus_cells[(nc, ci)] = cells
        clus_items[(nc, ci)] = items


def nearest_main_item(x, y, items):
    """closest point (mm) on a real cluster item to (x,y) -> (bx,by,layer|None)"""
    bd, bx, by, bl = 1e18, None, None, None
    for it in items:
        try:
            if isinstance(it, pcbnew.PCB_VIA):
                vx, vy = it.GetPosition().x/1e6, it.GetPosition().y/1e6
                d = (vx-x)**2 + (vy-y)**2
                if d < bd:
                    bd, bx, by, bl = d, vx, vy, None
            elif isinstance(it, pcbnew.PCB_TRACK):
                st, en = it.GetStart(), it.GetEnd()
                if not hasattr(st, 'x'):
                    continue
                ax, ay, bx2, by2 = st.x/1e6, st.y/1e6, en.x/1e6, en.y/1e6
                vx, vy = bx2-ax, by2-ay
                l2s = vx*vx + vy*vy
                tt = 0 if l2s == 0 else max(0, min(
                    1, ((x-ax)*vx + (y-ay)*vy)/l2s))
                cx2, cy2 = ax+vx*tt, ay+vy*tt
                d = (cx2-x)**2 + (cy2-y)**2
                if d < bd:
                    bd, bx, by, bl = d, cx2, cy2, it.GetLayer()
            elif isinstance(it, pcbnew.PAD):
                bb = it.GetBoundingBox()
                cx2, cy2 = (bb.GetLeft()+bb.GetRight())/2/1e6, \
                           (bb.GetTop()+bb.GetBottom())/2/1e6
                d = (cx2-x)**2 + (cy2-y)**2
                if d < bd:
                    for ly2 in CU:
                        if it.IsOnLayer(ly2):
                            bl = ly2
                            break
                    bd, bx, by = d, cx2, cy2
        except Exception:
            pass
    return bx, by, bl

main_cache = {}


def rseen_for(nc):
    """flood reachable from the net's largest (main) cluster — cached"""
    if nc not in main_cache:
        clus = net_clusters[nc]
        main_ci = max(range(len(clus)), key=lambda i: len(clus[i][1]))
        main_cache[nc] = (main_ci, clus_cells[(nc, main_ci)],
                          flood_pad(clus_cells[(nc, main_ci)], nc))
    return main_cache[nc]


for rnd in range(4):
    todo = islands()
    if not todo:
        print('no islands left')
        break
    print('rescue round', rnd, 'islands', len(todo), flush=True)
    fixed = 0
    for p, t, nc, name in todo:
        px, py = p.GetPosition().x/1e6, p.GetPosition().y/1e6
        gx, gy = int(px/GS), int(py/GS)
        pl = pad_layers(p)
        nc2, ci2 = pad_clus[p.m_Uuid.AsString()]
        isl = clus_cells[(nc2, ci2)]
        main_ci, maincells, (rseen, rparent) = rseen_for(nc)
        # bound pad flood: pad -> nearest main cell + margin
        near = min(maincells,
                   key=lambda c: (c[0]-gx)**2 + (c[1]-gy)**2)
        dxm, dym = abs(near[0]-gx), abs(near[1]-gy)
        m = 40
        box = (max(0, gx-dxm-m), max(0, gy-dym-m),
               min(NX-1, gx+dxm+m), min(NY-1, gy+dym+m))
        seeds = set()
        for dy in range(-8, 9):
            for dx in range(-8, 9):
                ix, iy = gx+dx, gy+dy
                if 0 <= ix < NX and 0 <= iy < NY:
                    for ly in pl:
                        if obs[ly][iy*NX+ix] == nc or (ix, iy, ly) in isl:
                            seeds.add((ix, iy, ly))
        if not seeds:
            seeds = {(gx, gy, ly) for ly in pl}
        seen, parent = flood_pad(seeds, nc, box)
        done = False
        cands = sorted(
            (s for s in seen if s[2] in pl),
            key=lambda s: (s[0]-gx)**2 + (s[1]-gy)**2)
        for (ix, iy, ly) in cands:
            if (ix-gx)**2 + (iy-gy)**2 > 3600:
                break
            if not via_ok_p(ix*GS, iy*GS, nc):
                continue
            ol = [l2 for l2 in CU if l2 != ly and (ix, iy, l2) in rseen
                  and cell_free(ix, iy, l2, nc)]
            if not ol:
                continue
            l2 = ol[0]
            p1 = backtrack((ix, iy, ly), parent)
            p2 = backtrack((ix, iy, l2), rparent)
            emit_path(p1, nc)
            add_via(ix*GS, iy*GS, nc)
            emit_path(p2, nc)
            s0 = p1[-1]
            if abs(s0[0]*GS-px) > 0.01 or abs(s0[1]*GS-py) > 0.01:
                add_track(px, py, s0[0]*GS, s0[1]*GS, pl[0], nc)
            # final leg to *real* cluster copper — grid cells carry margin
            bx, by, bl = nearest_main_item(ix*GS, iy*GS,
                                           clus_items[(nc, main_ci)])
            if bx is not None:
                # from the via (touches every layer) on the item's layer
                add_track(ix*GS, iy*GS, bx, by,
                          bl if bl is not None else l2, nc)
            else:
                extend_into(p2[-1], maincells, nc)
            print('  via', name,
                  p.GetParentFootprint().GetReference(), p.GetPadName(),
                  'at', round(ix*GS, 1), round(iy*GS, 1), flush=True)
            done = True
            break
        best_pair = (None, None)
        best_state = None
        if not done:
            # gap analysis: nearest same-layer (seen, rseen) pair
            rb = {}
            for (ix, iy, ly) in rseen:
                rb.setdefault((ly, ix//5, iy//5), []).append((ix, iy))
            bestd = 2500  # cells^2 — bridges for <=15 mm gaps
            for (ix, iy, ly) in seen:
                if (ix-gx)**2 + (iy-gy)**2 > 3600:
                    continue
                for dbx in range(-10, 11):
                    for dby in range(-10, 11):
                        for (ix2, iy2) in rb.get(
                                (ly, ix//5+dbx, iy//5+dby), ()):
                            d = (ix-ix2)**2 + (iy-iy2)**2
                            if 0 < d < bestd:
                                bestd = d
                                best_pair = ((ix, iy, ly),
                                             (ix2, iy2, ly))
                                best_state = (ix, iy, ly)
        if done:
            fixed += 1
        elif best_pair[0] is not None:
            (axc, ayc, aly), (bxc, byc, bly) = best_pair
            # bridge the gap: rip the few foreign fragments between the two
            # flood fronts on this layer, then emit a direct run
            ax_, ay_ = axc*GS, ayc*GS
            bx_, by_ = bxc*GS, byc*GS
            rip = []
            ok = True
            for t in board.GetTracks():
                if t.GetNetCode() == nc:
                    continue
                if isinstance(t, pcbnew.PCB_VIA):
                    vx, vy = t.GetPosition().x/1e6, t.GetPosition().y/1e6
                    if dseg(ax_, ay_, bx_, by_, vx, vy) < \
                            VIA_R + 0.125 + CLR:
                        rip.append(t)
                    continue
                st, en = t.GetStart(), t.GetEnd()
                x1, y1, x2, y2 = st.x/1e6, st.y/1e6, \
                                 en.x/1e6, en.y/1e6
                w = t.GetWidth()/2e6
                for k in range(0, 11):
                    sx, sy = x1+(x2-x1)*k/10, y1+(y2-y1)*k/10
                    if dseg(ax_, ay_, bx_, by_, sx, sy) < w+0.125+CLR:
                        rip.append(t)
                        break
            if len(rip) > 4:
                print('  bridge too costly:', name, len(rip), flush=True)
            else:
                for t in rip:
                    try:
                        board.Remove(t)
                    except Exception:
                        pass
                p1 = backtrack(best_state, parent)
                p2 = backtrack((bxc, byc, bly), rparent)
                emit_path(p1, nc)
                add_track(ax_, ay_, bx_, by_, aly, nc)
                emit_path(p2, nc)
                s0 = p1[-1]
                if abs(s0[0]*GS-px) > 0.01 or abs(s0[1]*GS-py) > 0.01:
                    add_track(px, py, s0[0]*GS, s0[1]*GS, pl[0], nc)
                bx2, by2, bl = nearest_main_item(
                    bx_, by_, clus_items[(nc, main_ci)])
                if bx2 is not None and bl is not None:
                    add_track(bx_, by_, bx2, by2, bl, nc)
                print('  bridge', name,
                      p.GetParentFootprint().GetReference(),
                      p.GetPadName(), 'rip', len(rip), flush=True)
                fixed += 1
                done = True
    refill()
    print('  fixed', fixed, flush=True)
    if not fixed:
        break

pcbnew.SaveBoard(PCB, board)
print('rescue saved:', PCB)
