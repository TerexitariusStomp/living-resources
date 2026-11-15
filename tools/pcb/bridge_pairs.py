#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""bridge_pairs.py — close tiny unconnected-item gaps DRC reports.

cluster_heal/connect route around obstacles but their grid emitters
regularly leave 0.1-1 mm endpoint near-misses no router retries.
This pass reads kicad-cli's unconnected_items JSON and, for each pair,
drops a same-layer track between the facing endpoints or plants a via
plus layer stub for cross-layer pairs — only when the added copper
clears every foreign-net item by the board clearance.

usage: bridge_pairs.py board.kicad_pcb [drc.json]
       (drc.json defaults to <board_dir>/work/drc-deep.json; when absent
       kicad-cli is run to produce it)
"""
import json
import math
import os
import subprocess
import sys

import pcbnew

PCB = sys.argv[1]
DRC = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
    os.path.dirname(PCB), "work", "drc-deep.json")
CLR = 0.20          # board min clearance, mm
VIA_D = 0.6
VIA_DRILL = 0.3
TRACK_W = 0.25
EDGE = 0.5

if not os.path.exists(DRC):
    os.makedirs(os.path.dirname(DRC), exist_ok=True)
    subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json",
                    "--severity-all", "-o", DRC, PCB], check=True)
d = json.load(open(DRC))
pairs = d.get("unconnected_items", [])
if not pairs:
    print("no unconnected items")
    sys.exit(0)

board = pcbnew.LoadBoard(PCB)
MM = 1_000_000

tracks = {t.m_Uuid.AsString(): t for t in board.GetTracks()}


def seg_dist(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    l2 = vx * vx + vy * vy
    if l2 == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / l2))
    return math.hypot(px - ax - t * vx, py - ay - t * vy)


def seg_seg_dist(a1, a2, b1, b2):
    # min distance between segments (sampled endpoints + proper crossing)
    def pt_seg(p, a, b):
        return seg_dist(p[0], p[1], a[0], a[1], b[0], b[1])
    best = min(pt_seg(a1, b1, b2), pt_seg(a2, b1, b2),
               pt_seg(b1, a1, a2), pt_seg(b2, a1, a2))
    # crossing check: if segments intersect, distance is 0
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    d1, d2 = cross(b1, b2, a1), cross(b1, b2, a2)
    d3, d4 = cross(a1, a2, b1), cross(a1, a2, b2)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)):
        return 0.0
    return best


# ---- obstacle snapshot: foreign-net copper + drills, in mm ----
# kinds: 'trk' (ax,ay,bx,by,half,layer) | 'pad' (x,y,r,layers) |
#        'via' (x,y,r) | 'hole' (x,y,r)
obstacles = []
for t in board.GetTracks():
    if isinstance(t, pcbnew.PCB_VIA):
        p = t.GetPosition()
        obstacles.append((t.GetNetCode(), "via",
                          (p.x / MM, p.y / MM, t.GetWidth() / 2 / MM)))
        dz = t.GetDrillValue() / MM if hasattr(t, "GetDrillValue") \
            else 0.15
        obstacles.append((-1, "hole", (p.x / MM, p.y / MM, dz / 2)))
    else:
        s, e = t.GetStart(), t.GetEnd()
        obstacles.append((t.GetNetCode(), "trk",
                          (s.x / MM, s.y / MM, e.x / MM, e.y / MM,
                           t.GetWidth() / 2 / MM, t.GetLayer())))
for fp in board.GetFootprints():
    for p in fp.Pads():
        pos = p.GetPosition()
        sz = p.GetSize()
        cx, cy = pos.x / MM, pos.y / MM
        nc = p.GetNetCode()
        layers = set()
        for ly in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu,
                   pcbnew.B_Cu):
            if p.IsOnLayer(ly):
                layers.add(ly)
        if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH or \
                p.GetDrillSize().x > 0:
            obstacles.append((-1, "hole",
                              (cx, cy, p.GetDrillSize().x / 2 / MM)))
        if p.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH and nc:
            r = math.hypot(sz.x, sz.y) / 2 / MM
            obstacles.append((nc, "pad", (cx, cy, r, layers)))


def seg_ok(ax, ay, bx, by, half, ncode, layer):
    """Candidate track segment on `layer` clears foreign copper."""
    for nc, kind, g in obstacles:
        if nc == ncode:
            continue
        if kind == "trk":
            if g[5] != layer:
                continue
            need = half + g[4] + CLR
            if seg_seg_dist((ax, ay), (bx, by),
                            (g[0], g[1]), (g[2], g[3])) < need:
                return False
        elif kind == "pad":
            if layer not in g[3]:
                continue
            if seg_dist(g[0], g[1], ax, ay, bx, by) < half + g[2] + CLR:
                return False
        elif kind == "via":
            if seg_dist(g[0], g[1], ax, ay, bx, by) < \
                    half + g[2] + CLR:
                return False
        elif kind == "hole":
            if seg_dist(g[0], g[1], ax, ay, bx, by) < \
                    half + g[2] + 0.25:
                return False
    return True


def via_ok(x, y, ncode):
    """Candidate via clears foreign copper on all layers + drills."""
    vr = VIA_D / 2
    for nc, kind, g in obstacles:
        if nc == ncode:
            continue
        if kind == "trk":
            need = vr + g[4] + CLR
            if seg_dist(x, y, g[0], g[1], g[2], g[3]) < need:
                # via spans all layers: any layer's track blocks
                return False
        elif kind == "pad":
            if seg_dist(g[0], g[1], x, y, x, y) < vr + g[2] + CLR:
                return False
        elif kind == "via":
            if math.hypot(g[0] - x, g[1] - y) < vr + g[2] + CLR:
                return False
        elif kind == "hole":
            if math.hypot(g[0] - x, g[1] - y) < \
                    VIA_DRILL / 2 + g[2] + 0.25:
                return False
    return True


def endpoints(t):
    s, e = t.GetStart(), t.GetEnd()
    return ((s.x / MM, s.y / MM), (e.x / MM, e.y / MM))


def facing(a, b):
    """Closest endpoint pair between two tracks."""
    best = None
    for pa in endpoints(a):
        for pb in endpoints(b):
            dd = math.hypot(pa[0] - pb[0], pa[1] - pb[1])
            if best is None or dd < best[0]:
                best = (dd, pa, pb)
    return best


def seg_closest(p1, p2, q1, q2):
    """Closest points between segments p1p2 and q1q2 (mm)."""
    # sample + refine: endpoints projections cover the cases that matter
    # for near-parallel stub gaps; fall back to endpoint pairs
    def proj(p, a, b):
        vx, vy = b[0] - a[0], b[1] - a[1]
        l2 = vx * vx + vy * vy
        if l2 == 0:
            return a
        t = max(0.0, min(1.0, ((p[0] - a[0]) * vx +
                               (p[1] - a[1]) * vy) / l2))
        return (a[0] + t * vx, a[1] + t * vy)
    cands = []
    for p in (p1, p2):
        for q in (q1, q2):
            cands.append((p, proj(p, q1, q2)))
            cands.append((proj(q, p1, p2), q))
    # interior-interior for near-parallel segments
    mx = ((p1[0] + p2[0]) + (q1[0] + q2[0])) / 4
    my = ((p1[1] + p2[1]) + (q1[1] + q2[1])) / 4
    cands.append((proj((mx, my), p1, p2), proj((mx, my), q1, q2)))
    best = None
    for cp, cq in cands:
        dd = math.hypot(cp[0] - cq[0], cp[1] - cq[1])
        if best is None or dd < best[0]:
            best = (dd, cp, cq)
    return best


def candidate_paths(pa, pb):
    """Direct plus dogleg paths around point blockers near the gap."""
    yield [pa, pb]
    dx, dy = pb[0] - pa[0], pb[1] - pa[1]
    L = math.hypot(dx, dy) or 1.0
    ux, uy = -dy / L, dx / L          # perpendicular unit
    mx, my = (pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2
    for off in (0.1, 0.15, 0.2, 0.25, 0.3, 0.5, 0.8,
                -0.1, -0.15, -0.2, -0.25, -0.3, -0.5, -0.8):
        yield [pa, (mx + ux * off, my + uy * off), pb]
    # doglegs near each endpoint for blockers hugging one end
    for f in (0.25, 0.75):
        bx, by = pa[0] + dx * f, pa[1] + dy * f
        for off in (0.3, 0.5, 0.8, -0.3, -0.5, -0.8):
            yield [pa, (bx + ux * off, by + uy * off), pb]


def add_seg(ax, ay, bx, by, layer, ncode):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(int(ax * MM), int(ay * MM)))
    t.SetEnd(pcbnew.VECTOR2I(int(bx * MM), int(by * MM)))
    t.SetLayer(layer)
    t.SetWidth(int(TRACK_W * MM))
    t.SetNetCode(ncode)
    board.Add(t)
    obstacles.append((ncode, "trk",
                      (ax, ay, bx, by, TRACK_W / 2, layer)))


def add_via(x, y, ncode):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(int(x * MM), int(y * MM)))
    v.SetWidth(int(VIA_D * MM))
    v.SetDrill(int(VIA_DRILL * MM))
    v.SetNetCode(ncode)
    board.Add(v)
    obstacles.append((ncode, "via", (x, y, VIA_D / 2)))
    obstacles.append((-1, "hole", (x, y, VIA_DRILL / 2)))


bridged = 0
for pair in pairs:
    items = pair.get("items", [])
    if len(items) < 2:
        continue
    ts = []
    for it in items[:2]:
        t = tracks.get(it.get("uuid"))
        if t is None or isinstance(t, pcbnew.PCB_VIA):
            ts = None
            break
        ts.append(t)
    if not ts or len(ts) < 2:
        continue
    t1, t2 = ts
    ncode = t1.GetNetCode()
    if ncode != t2.GetNetCode():
        continue
    s1, e1 = endpoints(t1)
    s2, e2 = endpoints(t2)
    dd, pa, pb = seg_closest(s1, e1, s2, e2)
    l1, l2 = t1.GetLayer(), t2.GetLayer()
    half = min(t1.GetWidth(), t2.GetWidth()) / 2 / MM
    # same-position cross-layer stubs are exactly what a via joins —
    # only skip degenerate same-layer pairs
    if dd < 0.05 and l1 == l2:
        continue
    if l1 == l2:
        # same layer: first clearing path (direct, then doglegs)
        done = False
        for path in candidate_paths(pa, pb):
            if any(not (EDGE < q[0] < 120 - EDGE and
                        EDGE < q[1] < 90 - EDGE) for q in path):
                continue
            ok = all(seg_ok(path[i][0], path[i][1],
                             path[i + 1][0], path[i + 1][1],
                             half, ncode, l1)
                     for i in range(len(path) - 1))
            if ok:
                for i in range(len(path) - 1):
                    add_seg(path[i][0], path[i][1],
                            path[i + 1][0], path[i + 1][1], l1, ncode)
                bridged += 1
                done = True
                print(f"bridged same-layer {dd:.2f}mm "
                      f"({t1.GetNetname()}, {len(path) - 1} segs)")
                break
        if not done:
            print(f"skip same-layer blocked {dd:.2f}mm "
                  f"({t1.GetNetname()})")
    else:
        # cross-layer: via at pa + stub on t2's layer to pb
        mx, my = (pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2
        # via must sit on t1's copper: pa is t1's endpoint — via there
        vx, vy = pa
        ok = via_ok(vx, vy, ncode)
        stub_ok = seg_ok(vx, vy, pb[0], pb[1], half, ncode, l2)
        if ok and stub_ok:
            add_via(vx, vy, ncode)
            if math.hypot(vx - pb[0], vy - pb[1]) > 0.05:
                add_seg(vx, vy, pb[0], pb[1], l2, ncode)
            bridged += 1
            print(f"bridged cross-layer {dd:.2f}mm "
                  f"({t1.GetNetname()})")
        else:
            # try via at midpoint + stubs on both layers
            ok2 = via_ok(mx, my, ncode)
            s1 = seg_ok(mx, my, pa[0], pa[1], half, ncode, l1)
            s2 = seg_ok(mx, my, pb[0], pb[1], half, ncode, l2)
            if ok2 and s1 and s2:
                add_via(mx, my, ncode)
                add_seg(mx, my, pa[0], pa[1], l1, ncode)
                add_seg(mx, my, pb[0], pb[1], l2, ncode)
                bridged += 1
                print(f"bridged cross-layer(mid) {dd:.2f}mm "
                      f"({t1.GetNetname()})")
                continue
            # via at pb's end + stub on l1 back to pa
            vx2, vy2 = pb
            ok3 = via_ok(vx2, vy2, ncode)
            s3 = seg_ok(vx2, vy2, pa[0], pa[1], half, ncode, l1)
            if ok3 and s3:
                add_via(vx2, vy2, ncode)
                if math.hypot(vx2 - pa[0], vy2 - pa[1]) > 0.05:
                    add_seg(vx2, vy2, pa[0], pa[1], l1, ncode)
                bridged += 1
                print(f"bridged cross-layer(pb) {dd:.2f}mm "
                      f"({t1.GetNetname()})")
            else:
                print(f"skip cross-layer blocked {dd:.2f}mm "
                      f"({t1.GetNetname()})")

print(f"bridges added: {bridged}")
if bridged:
    pcbnew.SaveBoard(PCB, board)
    print("saved:", PCB)
