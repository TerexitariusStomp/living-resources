# SPDX-License-Identifier: AGPL-3.0-or-later
"""unseal_pins.py — channel-escape stubs for pads sealed by grid margins.

A 1.27 mm-pitch pin field leaves ~1.0 mm of physical gap between pad
edges — a 0.25 mm track fits with real clearance — but the raster grid's
stamp margin seals every channel, so the router sees each pin as an
island.  This pass finds every pad whose connected cluster is just the
pad itself (or a couple of fragments), then greedy-walks a stub through
the flanking channel — checking continuous clearance against real item
geometry at each 0.5 mm step — until the tip reaches a grid cell the
flood fill can roam (obs == 0 or own net).

Usage: python3 tools/pcb/unseal_pins.py board.kicad_pcb
"""
import collections
import sys

sys.argv = ['unseal', sys.argv[1] if len(sys.argv) > 1 else
            'hardware/release/electrical/ecocell-ocean.kicad_pcb']
_src = open('tools/pcb/attach_signals.py').read()
exec(compile(_src[:_src.find('for rnd in range(10):')], 'attach', 'exec'))
import pcbnew

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


def dseg(ax, ay, bx, by, px, py):
    vx, vy = bx-ax, by-ay
    wx, wy = px-ax, py-ay
    l2 = vx*vx + vy*vy
    t = 0 if l2 == 0 else max(0, min(1, (wx*vx+wy*vy)/l2))
    ex, ey = ax+vx*t, ay+vy*t
    return ((px-ex)**2 + (py-ey)**2) ** 0.5


def stub_ok(ax, ay, bx, by, nc, ly, hw=0.125):
    """continuous check: a hw-halfwidth track a->b clears foreign items"""
    for bx_ in range(int(min(ax, bx)/BUCKET)-1,
                     int(max(ax, bx)/BUCKET)+2):
        for by_ in range(int(min(ay, by)/BUCKET)-1,
                         int(max(ay, by)/BUCKET)+2):
            for si in segidx.get((bx_, by_), ()):
                x1, y1, x2, y2, w2, n2, l2 = segs[si]
                if n2 == nc or l2 != ly:
                    continue
                if min(x1, x2) > max(ax, bx)+1 or \
                        max(x1, x2) < min(ax, bx)-1 or \
                        min(y1, y2) > max(ay, by)+1 or \
                        max(y1, y2) < min(ay, by)-1:
                    continue
                hit = False
                for k in range(0, 5):
                    px_, py_ = x1+(x2-x1)*k/4, y1+(y2-y1)*k/4
                    if dseg(ax, ay, bx, by, px_, py_) < w2+hw+CLR-0.02:
                        hit = True
                        break
                if not hit:
                    for k in range(0, 5):
                        px_, py_ = ax+(bx-ax)*k/4, ay+(by-ay)*k/4
                        if dseg(x1, y1, x2, y2, px_, py_) < \
                                w2+hw+CLR-0.02:
                            hit = True
                            break
                if hit:
                    return False
            for ri in rectidx.get((bx_, by_), ()):
                cx, cy, hx2, hy2, n2, lys = rects[ri]
                if n2 == nc or ly not in lys:
                    continue
                for k in range(0, 5):
                    px_, py_ = ax+(bx-ax)*k/4, ay+(by-ay)*k/4
                    if abs(px_-cx) < hx2+hw+CLR and \
                            abs(py_-cy) < hy2+hw+CLR:
                        return False
    return True


def open_cell(x, y, nc, ly):
    ix, iy = int(x/GS), int(y/GS)
    if not (0 <= ix < NX and 0 <= iy < NY):
        return False
    return obs[ly][iy*NX+ix] in (0, nc)


def greedy_escape(px, py, nc, ly):
    """walk 0.5 mm steps; bend once if the straight run stalls; stop at
    an open cell.  Returns [(x,y),...] or None."""
    for d1 in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        for bend in (None, (1, 0), (-1, 0), (0, 1), (0, -1)):
            path = [(px, py)]
            x, y = px, py
            dx, dy = d1
            steps = 0
            ok = True
            while steps < 16:
                nx, ny = x+dx*0.5, y+dy*0.5
                if not stub_ok(x, y, nx, ny, nc, ly):
                    break
                x, y = nx, ny
                path.append((x, y))
                steps += 1
                if open_cell(x, y, nc, ly):
                    break
                if steps == 4 and bend:
                    dx, dy = bend
            if open_cell(x, y, nc, ly) and steps >= 1:
                return path
    return None


def flood_pad(seeds, nc):
    seen = set(seeds)
    dq = collections.deque(seeds)
    while dq:
        ix, iy, ly = dq.popleft()
        for nx, ny in ((ix+1, iy), (ix-1, iy), (ix, iy+1), (ix, iy-1)):
            if 0 <= nx < NX and 0 <= ny < NY and \
                    cell_free(nx, ny, ly, nc) and (nx, ny, ly) not in seen:
                seen.add((nx, ny, ly))
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
                dq.append(st)
    return seen


conn = board.GetConnectivity()
# candidate pads: pads on island nets whose own cluster is small —
# the big-cluster partners already roam
island_nets = set(nc for (_, _, nc, _) in islands())
placed = 0
for fp in board.GetFootprints():
    for p in fp.Pads():
        nc = p.GetNetCode()
        if nc <= 0 or nc not in island_nets:
            continue
        if len(list(conn.GetConnectedItems(p))) > 80:
            continue            # in (or near) the main cluster
        pls = [l for l in CU if p.IsOnLayer(l)]
        if not pls:
            continue
        ly = pls[0]
        px, py = p.GetPosition().x/1e6, p.GetPosition().y/1e6
        gx, gy = int(px/GS), int(py/GS)
        seeds = set()
        for dy in range(-8, 9):
            for dx in range(-8, 9):
                ix, iy = gx+dx, gy+dy
                if 0 <= ix < NX and 0 <= iy < NY and \
                        obs[ly][iy*NX+ix] == nc:
                    seeds.add((ix, iy, ly))
        if not seeds:
            seeds = {(gx, gy, ly)}
        if len(flood_pad(seeds, nc)) > 600:
            continue            # already roams — not sealed
        path = greedy_escape(px, py, nc, ly)
        if path:
            for i in range(len(path)-1):
                add_track(path[i][0], path[i][1],
                          path[i+1][0], path[i+1][1], ly, nc)
            print('escape', fp.GetReference(), p.GetPadName(),
                  p.GetNetname(), '->', round(path[-1][0], 1),
                  round(path[-1][1], 1), flush=True)
            placed += 1
        else:
            print('sealed:', fp.GetReference(), p.GetPadName(),
                  p.GetNetname(), flush=True)

pcbnew.SaveBoard(PCB, board)
print('unseal saved:', PCB, 'escapes:', placed)
