#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Post-route signal attach: grid A* on all four copper layers for island
pads that the stitch router + plane pass left behind. Usage:
    python3 tools/pcb/attach_signals.py <board.kicad_pcb>
"""
import sys, heapq, pcbnew

PCB = sys.argv[1]
CU = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
GS = 0.3                 # raster pitch, mm
CLR = 0.22               # clearance vs foreign copper, mm
TW2 = 0.125              # half-width of the tracks we emit, mm
VIA_D, VIA_DRILL = 0.6, 0.3
EDGE = 0.8               # copper keep-out at board edge, mm

board = pcbnew.LoadBoard(PCB)
W = H = None
for gi in board.GetDrawings():
    pass
bb = board.GetBoardEdgesBoundingBox()
W, H = bb.GetRight() / 1e6, bb.GetBottom() / 1e6
NX, NY = int(W / GS) + 2, int(H / GS) + 2

# --- obstacles -----------------------------------------------------------
# obs[layer] = bytearray blocked cells
obs = {l: bytearray(NX * NY) for l in CU}
holes = []               # (x,y,r,netcode) drilled things


def stamp(x, y, r, ly, nc):
    """block cells within r of (x,y) on ly for all nets != nc"""
    x0, x1 = int((x - r) / GS) - 1, int((x + r) / GS) + 2
    y0, y1 = int((y - r) / GS) - 1, int((y + r) / GS) + 2
    for iy in range(max(0, y0), min(NY, y1)):
        for ix in range(max(0, x0), min(NX, x1)):
            cx, cy = ix * GS, iy * GS
            if (cx - x) ** 2 + (cy - y) ** 2 <= (r + 0.01) ** 2:
                obs[ly][iy * NX + ix] = nc if nc else 1
                if nc == 0:
                    obs[ly][iy * NX + ix] = 255


def cell_free(ix, iy, ly, nc):
    v = obs[ly][iy * NX + ix]
    return v == 0 or v == nc


def netcode(item):
    try:
        return item.GetNetCode()
    except Exception:
        return 0


for t in board.GetTracks():
    nc = netcode(t)
    if isinstance(t, pcbnew.PCB_VIA):
        x, y = t.GetPosition().x / 1e6, t.GetPosition().y / 1e6
        r = t.GetWidth(pcbnew.F_Cu) / 2 / 1e6 + CLR + TW2
        for ly in CU:
            stamp(x, y, r, ly, nc if nc else 0)
        holes.append((x, y, t.GetDrillValue() / 2 / 1e6, nc))
    else:
        s, e = t.GetStart(), t.GetEnd()
        ax, ay, bx, by = s.x/1e6, s.y/1e6, e.x/1e6, e.y/1e6
        r = t.GetWidth() / 2 / 1e6 + CLR + TW2
        # walk the segment stamping discs
        L = max(1, int(((bx-ax)**2+(by-ay)**2)**0.5 / (GS*0.5)))
        for i in range(L+1):
            stamp(ax+(bx-ax)*i/L, ay+(by-ay)*i/L, r, t.GetLayer(), nc)

for fp in board.GetFootprints():
    for p in fp.Pads():
        nc = netcode(p)
        bb = p.GetBoundingBox()
        cx, cy = (bb.GetLeft()+bb.GetRight())/2/1e6, (bb.GetTop()+bb.GetBottom())/2/1e6
        r = max(bb.GetRight()-bb.GetLeft(), bb.GetBottom()-bb.GetTop())/2/1e6 \
            + CLR + TW2
        for ly in CU:
            if p.IsOnLayer(ly):
                stamp(cx, cy, r, ly, nc if nc else 0)
        if p.GetDrillSize().x:
            holes.append((cx, cy, p.GetDrillSize().x/2/1e6, nc))

keep_zones = [z for z in board.Zones() if z.GetIsRuleArea()]
for fp in board.GetFootprints():
    keep_zones += [z for z in fp.Zones()
                   if z.GetDoNotAllowTracks() or z.GetDoNotAllowVias()]
for z in keep_zones:
    o = z.Outline()
    for oi in range(o.OutlineCount()):
        lc = o.COutline(oi)
        n = lc.PointCount()
        if not n: continue
        pts = [(lc.CPoint(i).x/1e6, lc.CPoint(i).y/1e6) for i in range(n)]
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        for iy in range(int(min(ys)/GS), int(max(ys)/GS)+2):
            for ix in range(int(min(xs)/GS), int(max(xs)/GS)+2):
                x, y = ix*GS, iy*GS
                inside = False
                j = n-1
                for i in range(n):
                    xi, yi = pts[i]; xj, yj = pts[j]
                    if (yi > y) != (yj > y) and \
                            x < (xj-xi)*(y-yi)/(yj-yi)+xi:
                        inside = not inside
                    j = i
                if not inside:
                    # cell outside the outline still violates if within
                    # track half-width + margin of the boundary
                    dmin = min(abs((pts[(i+1) % n][0]-pts[i][0])*(pts[i][1]-y) -
                                   (pts[i][0]-x)*(pts[(i+1) % n][1]-pts[i][1]))
                               / max(1e-9, ((pts[(i+1) % n][0]-pts[i][0])**2 +
                                            (pts[(i+1) % n][1]-pts[i][1])**2) ** 0.5)
                               for i in range(n))
                    if dmin > TW2 + 0.1:
                        continue
                for ly in CU:
                    obs[ly][iy*NX+ix] = 255

# board edge margin
for iy in range(NY):
    for ix in range(NX):
        x, y = ix*GS, iy*GS
        if x < EDGE + TW2 or y < EDGE + TW2 or \
                x > W-EDGE-TW2 or y > H-EDGE-TW2:
            for ly in CU:
                obs[ly][iy*NX+ix] = 255

# --- island detection ----------------------------------------------------
def refill():
    for z in board.Zones():
        z.SetIsFilled(False)
    try:
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    except Exception:
        board.FillZones()

refill()

def islands():
    conn = board.GetConnectivity()
    todo = []
    for net in board.GetNetsByName().values():
        name = net.GetNetname()
        if not name or name.startswith('unconnected'):
            continue
        nc = net.GetNetCode()
        pads = [p for fp in board.GetFootprints() for p in fp.Pads()
                if p.GetNetCode() == nc]
        if len(pads) < 2: continue
        clus = []
        for p in pads:
            ids = set(x.m_Uuid.AsString()
                      for x in conn.GetConnectedItems(p))
            hit = [c for c in clus if c[0] & ids]
            if hit: hit[0][0] |= ids; hit[0][1].append(p)
            else: clus.append([ids, [p]])
        merged = True
        while merged:
            merged = False
            for i in range(len(clus)):
                for j in range(i+1, len(clus)):
                    if clus[i][0] & clus[j][0]:
                        clus[i][0] |= clus[j][0]
                        clus[i][1] += clus[j][1]; clus.pop(j)
                        merged = True; break
                else: continue
                break
        if len(clus) < 2: continue
        main = max(clus, key=lambda c: len(c[1]))
        for c in clus:
            if c is main: continue
            for p in c[1]:
                # nearest main pad as target
                px, py = p.GetPosition().x/1e6, p.GetPosition().y/1e6
                t = min(main[1], key=lambda q:
                        (q.GetPosition().x/1e6-px)**2 +
                        (q.GetPosition().y/1e6-py)**2)
                todo.append((p, t, nc, name))
    return todo


def pad_layers(p):
    return [l for l in CU if p.IsOnLayer(l)]


VIA_R = VIA_D / 2

def via_ok(x, y, nc):
    # drilled-hole clearance: via drill r=0.15 + 0.25 hole-to-hole + margin
    for hx, hy, hr, hnc in holes:
        if hnc != nc and (x-hx)**2 + (y-hy)**2 < (0.45 + hr) ** 2:
            return False
    # annulus: every layer must be clear within via pad r + clr + margin —
    # the obstacle stamps already carry item_r + CLR + TW2, so a cell inside
    # VIA_R+TW2 of the site approximates the annulus
    r = VIA_R + TW2
    for ly in CU:
        for iy in range(int((y-r)/GS), int((y+r)/GS)+2):
            for ix in range(int((x-r)/GS), int((x+r)/GS)+2):
                if (ix*GS-x)**2 + (iy*GS-y)**2 <= (r+0.01)**2 and \
                        not cell_free(ix, iy, ly, nc):
                    return False
    return True


def astar(start, goals, nc, slayers, glayers):
    """A* over (ix, iy, layer) with via-gated layer transitions."""
    gset = set(goals)          # (ix, iy, layer)
    dist = {}
    prev = {}
    pq = []
    for ly in slayers:
        st = (start[0], start[1], ly)
        dist[st] = 0
        heapq.heappush(pq, (0, st))
    while pq:
        f, (ix, iy, ly) = heapq.heappop(pq)
        if (ix, iy, ly) in gset:
            path = [(ix, iy, ly)]
            cur = (ix, iy, ly)
            while cur in prev:
                cur = prev[cur]
                path.append(cur)
            return path[::-1]
        nbrs = [(ix+1, iy, ly), (ix-1, iy, ly), (ix, iy+1, ly),
                (ix, iy-1, ly)]
        # layer hop: via must fit at this cell on both adjacent layers
        li = CU.index(ly)
        for nl in (CU[li-1] if li > 0 else None,
                   CU[li+1] if li < len(CU)-1 else None):
            if nl is None: continue
            if (cell_free(ix, iy, ly, nc) and
                    cell_free(ix, iy, nl, nc) and
                    via_ok(ix*GS, iy*GS, nc)):
                nbrs.append((ix, iy, nl))
        for nx2, ny2, nl in nbrs:
            if not (0 <= nx2 < NX and 0 <= ny2 < NY):
                continue
            if not cell_free(nx2, ny2, nl, nc):
                continue
            ns = (nx2, ny2, nl)
            nd = dist[(ix, iy, ly)] + (4 if nl != ly else 1)
            if ns not in dist or nd < dist[ns]:
                dist[ns] = nd
                h = min(((nx2-gx)**2 + (ny2-gy)**2)
                        for gx, gy, _ in gset) ** 0.5
                heapq.heappush(pq, (nd + h, ns))
                prev[ns] = (ix, iy, ly)
    return None


def add_track(ax, ay, bx, by, ly, nc):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(int(ax*1e6), int(ay*1e6)))
    t.SetEnd(pcbnew.VECTOR2I(int(bx*1e6), int(by*1e6)))
    t.SetLayer(ly); t.SetWidth(pcbnew.FromMM(0.25))
    t.SetNetCode(nc)
    board.Add(t)


def add_via(x, y, nc):
    for t in board.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA) and t.GetNetCode() == nc:
            vx, vy = t.GetPosition().x/1e6, t.GetPosition().y/1e6
            if (vx-x)**2 + (vy-y)**2 < 0.7**2:
                return
    # record it so later vias in this run dedupe too
    holes.append((x, y, VIA_DRILL/2, nc))
    v = pcbnew.PCB_VIA(board)
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetPosition(pcbnew.VECTOR2I(int(x*1e6), int(y*1e6)))
    v.SetWidth(pcbnew.FromMM(VIA_D)); v.SetDrill(pcbnew.FromMM(VIA_DRILL))
    v.SetNetCode(nc)
    board.Add(v)


for rnd in range(10):
    todo = islands()
    if not todo: break
    print("round", rnd, "islands", len(todo))
    done = 0
    for p, t, nc, name in todo:
        px, py = p.GetPosition().x/1e6, p.GetPosition().y/1e6
        tx, ty = t.GetPosition().x/1e6, t.GetPosition().y/1e6
        scell = (int(px/GS), int(py/GS))
        # goals: pad-center, every own-net-stamped cell within reach of the
        # pad (bridging a walled-in fine-pitch pad via its own copper), and
        # all same-net track endpoints of the main cluster
        goals = []
        for gly in pad_layers(t):
            goals.append((int(tx/GS), int(ty/GS), gly))
            # every own-net-stamped cell within reach of the pad — bridges a
            # walled-in fine-pitch pad through a via onto its own copper
            R = int(1.6 / GS) + 1
            for dy in range(-R, R+1):
                for dx in range(-R, R+1):
                    ix, iy = int(tx/GS)+dx, int(ty/GS)+dy
                    if 0 <= ix < NX and 0 <= iy < NY and \
                            (dx*GS)**2 + (dy*GS)**2 <= 1.6**2 and \
                            obs[gly][iy*NX+ix] == nc:
                        goals.append((ix, iy, gly))
        for tr in board.GetTracks():
            if tr.GetNetCode() != nc: continue
            for pt in (tr.GetStart(), tr.GetEnd()):
                goals.append((int(pt.x/1e6/GS), int(pt.y/1e6/GS),
                              tr.GetLayer()))
        path = astar(scell, goals, nc, pad_layers(p), pad_layers(t))
        if not path:
            print("  unrouted", name, p.GetParentFootprint().GetReference(),
                  p.GetPadName())
            continue
        for i in range(len(path)-1):
            (x0, y0, l0), (x1, y1, l1) = path[i], path[i+1]
            if l0 != l1:
                add_via(x0*GS, y0*GS, nc)
            else:
                add_track(x0*GS, y0*GS, x1*GS, y1*GS, l0, nc)
        # closing stubs: pad center -> first cell, last cell -> target
        (fx, fy, fl) = path[0]
        if (fx*GS, fy*GS) != (px, py):
            add_track(px, py, fx*GS, fy*GS, fl, nc)
        (lx, ly, ll) = path[-1]
        if (lx*GS, ly*GS) != (tx, ty):
            add_track(lx*GS, ly*GS, tx, ty, ll, nc)
        done += 1
    print("  attached", done)
    refill()
    if not done:
        break

pcbnew.SaveBoard(PCB, board)
print("board saved:", PCB)
