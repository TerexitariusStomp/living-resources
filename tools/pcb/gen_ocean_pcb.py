#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Build the EcoCell ocean node PCB from the SKiDL netlist with pcbnew.

Reads hardware/release/electrical/ecocell-ocean.net, places every part on a
90x60 mm 2-layer board with functional clustering, assigns pad nets, adds
edge cuts, mounting holes and GND pours, then writes the native .kicad_pcb
and a Specctra DSN for autorouting.

Usage: python3 tools/pcb/gen_ocean_pcb.py
"""
import os
import xml.etree.ElementTree as ET

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
ELEC = os.path.normpath(os.path.join(HERE, "..", "..", "hardware", "release",
                                     "electrical"))
NETFILE = os.path.join(ELEC, "ecocell-ocean.net")
PCB = os.path.join(ELEC, "ecocell-ocean.kicad_pcb")
DSN = os.path.join(ELEC, "ecocell-ocean.dsn")
PRO = os.path.join(ELEC, "ecocell-ocean.kicad_pro")
FPLIBS = "/usr/share/kicad/footprints"

MM = pcbnew.FromMM

# ------------------------------------------------- parse .net netlist ----
def parse_sexpr(text):
    toks = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch.isspace():
            i += 1
        elif ch in "()":
            toks.append(ch); i += 1
        elif ch == '"':
            j = text.index('"', i + 1)
            toks.append(text[i + 1:j]); i = j + 1
        else:
            j = i
            while j < n and not text[j].isspace() and text[j] not in '()"':
                j += 1
            toks.append(text[i:j]); i = j
    stack = [[]]
    for tok in toks:
        if tok == "(":
            stack.append([])
        elif tok == ")":
            node = stack.pop()
            stack[-1].append(node)
        else:
            stack[-1].append(tok)
    return stack[0][0]


def sexpr_val(node, key):
    """Return first scalar child list named key."""
    for sub in node:
        if isinstance(sub, list) and sub and sub[0] == key:
            return sub[1] if len(sub) > 1 else ""
    return ""


with open(NETFILE) as f:
    root = parse_sexpr(f.read())

comps = {}
nets_sect = None
for sect in root:
    if isinstance(sect, list) and sect and sect[0] == "components":
        for comp in sect[1:]:
            ref = sexpr_val(comp, "ref")
            comps[ref] = {"fp": sexpr_val(comp, "footprint"),
                          "value": sexpr_val(comp, "value")}
    if isinstance(sect, list) and sect and sect[0] == "nets":
        nets_sect = sect

padnets = {}
netnames = []
for net in nets_sect[1:]:
    name = sexpr_val(net, "name")
    netnames.append(name)
    for node in net[1:]:
        if isinstance(node, list) and node and node[0] == "node":
            padnets[(sexpr_val(node, "ref"), sexpr_val(node, "pin"))] = name

# ------------------------------------------------------------- board -----
board = pcbnew.NewBoard(PCB)
try:
    board.SetCopperLayerCount(4)   # F.Cu / In1=GND / In2=+3V3 / B.Cu
except Exception as e:
    print("layercount", e)
# Fabrication rules — conservative common-denominator spec any 4L fab meets
# (>=0.2 mm clearance/space, >=0.15 mm track, via >=0.5/0.3 mm, >=0.5 mm
# copper-to-edge). Stitches are generated to a larger margin than these.
ds = board.GetDesignSettings()
ds.m_MinClearance = MM(0.2)
ds.m_TrackMinWidth = MM(0.15)
ds.m_ViasMinSize = MM(0.5)
ds.m_ViasMinAnnularWidth = MM(0.1)
ds.m_MinThroughDrill = MM(0.3)
ds.m_CopperEdgeClearance = MM(0.5)
ds.m_HoleClearance = MM(0.3)
ds.m_HoleToHoleMin = MM(0.5)
nc = board.GetAllNetClasses()["Default"]
nc.SetClearance(MM(0.2))
nc.SetTrackWidth(MM(0.25))
nc.SetViaDiameter(MM(0.6))
nc.SetViaDrill(MM(0.3))

# netinfo for every net
netitems = {}
for name in netnames:
    ni = pcbnew.NETINFO_ITEM(board, name)
    board.Add(ni)
    netitems[name] = ni

# ---------------------------------------------------------- placement ----
# Deterministic, collision-free layout: connectors on the perimeter, majors
# in a center grid, passives on the bottom side in a clean grid.
W, H = 120.0, 90.0
# Explicit layout. The WROOM's 48x21 mm antenna keepout must face the top
# edge, so U_MCU anchors the top-left quadrant and nothing else may enter
# x<52, y<20. Connectors sit on the perimeter (rot 90 = pads along X for
# the bottom-edge row); majors fill a grid clear of the MCU body.
POS = {
    "U_MCU": (33.0, 28.0, 0),
    "J_CAM": (62.0, 8.0, 90), "J_GPS": (85.0, 8.0, 90),
    "J_LORA": (112.0, 42.0, 0), "J_SD": (110.0, 73.0, 0),
    "J_DEBUG": (8.0, 50.0, 0), "J_HYDRO": (8.0, 68.0, 90),
    "J_PIR": (16.0, 80.0, 90), "J_PWR": (28.0, 80.0, 0),
    "J_BAT": (40.0, 80.0, 0), "J_EMIT": (50.0, 80.0, 0),
    "J_SPK": (62.0, 80.0, 90), "J_KILL": (73.0, 80.0, 90),
    "J_CTD": (88.0, 80.0, 0),
    "L_BOOST": (64.0, 14.0, 0), "Q_EMIT": (83.0, 14.0, 0),
    "U_ADC": (102.0, 14.0, 0), "U_AFE": (64.0, 31.0, 0),
    "U_AMP": (83.0, 31.0, 0), "U_BOOST": (102.0, 31.0, 0),
    "U_CHG": (64.0, 44.0, 0), "U_CTD": (83.0, 44.0, 0),
    "U_ENV": (102.0, 44.0, 0), "U_EXP": (26.0, 55.0, 0),
    "U_LDR": (45.0, 55.0, 0),
    "U_LDO": (64.0, 59.0, 0), "U_MIC": (83.0, 59.0, 0),
    "U_PRES": (102.0, 59.0, 0), "U_SW_AMP": (26.0, 68.0, 0),
    "U_SW_CAM": (64.0, 74.0, 0), "U_SW_DAC": (83.0, 70.0, 0),
    "U_SW_ILLUM": (45.0, 68.0, 0),
}
grid_pos = {}
mx, my = 26.0, 14.0
for ref in sorted(comps):
    if ref.startswith(("U_", "Q_")) or ref == "L_BOOST":
        grid_pos[ref] = (mx, my)
        mx += 19.0
        if mx > W - 22:
            mx, my = 26.0, my + 15.0

# Majors on top at POS; passives bottom-side grid.

# --------------------------------------------------------- footprints ----
# Majors on top at POS; all small passives (R_/C_/D_/L_) go to the bottom
# side in a clean grid; test points along the top-bottom edge row.
def overlaps_excl(x, y, excl, margin=1.0):
    for (x0, y0, x1, y1) in excl:
        if x0 - margin < x < x1 + margin and \
                y0 - margin < y < y1 + margin:
            return True
    return False


excl = []          # bounding boxes of top-side parts, keep bottom free
bot_cells = []     # candidate bottom-grid cells
bx, by = 8.0, 8.0
while by < H - 6:
    bot_cells.append((bx, by))
    bx += 4.5
    if bx > W - 8:
        bx, by = 8.0, by + 4.0

# pass 1: connectors, ICs, test points — top side, record exclusions
tp_i = 0.0
for ref in sorted(comps):
    c = comps[ref]
    fpstr = c["fp"]
    if not fpstr or ":" not in fpstr:
        continue                       # power symbols, NC-only symbols
    if ref.startswith(("R_", "C_", "D_", "L_")):
        continue                       # passives handled in pass 2
    lib, name = fpstr.split(":", 1)
    fp = pcbnew.FootprintLoad(os.path.join(FPLIBS, lib + ".pretty"), name)
    if fp is None:
        print("MISSING FP", ref, fpstr)
        continue
    if ref in POS:
        x, y, rot = POS[ref]
    elif ref in grid_pos:
        x, y = grid_pos[ref]
        rot = 0
    elif ref.startswith("TP"):
        x, y, rot = 60.0 + tp_i * 4.4, 22.0, 0
        tp_i += 1
    else:
        x, y, rot = 10.0, H - 12.0, 0
    fp.SetReference(ref)
    fp.SetValue(c["value"])
    fp.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
    if rot:
        try:
            fp.SetOrientationDegrees(rot)
        except Exception:
            pass
    board.Add(fp)
    if ref.startswith(("J_", "TP", "MH")):
        # only through-hole/connecting parts exclude bottom-side cells —
        # SMD passives are meant to sit under the majors' bodies
        bb = fp.GetBoundingBox()
        excl.append((bb.GetLeft() / 1e6, bb.GetTop() / 1e6,
                     bb.GetRight() / 1e6, bb.GetBottom() / 1e6))

# pass 2: passives on the bottom, outside major-part exclusion zones
bot_i = 0
for ref in sorted(comps):
    c = comps[ref]
    if not ref.startswith(("R_", "C_", "D_", "L_")):
        continue
    fpstr = c["fp"]
    if not fpstr or ":" not in fpstr:
        continue
    lib, name = fpstr.split(":", 1)
    fp = pcbnew.FootprintLoad(os.path.join(FPLIBS, lib + ".pretty"), name)
    if fp is None:
        print("MISSING FP", ref, fpstr)
        continue
    while bot_i < len(bot_cells) and \
            overlaps_excl(bot_cells[bot_i][0], bot_cells[bot_i][1], excl):
        bot_i += 1
    if bot_i >= len(bot_cells):
        x, y, rot = 10.0, H - 12.0, 0
    else:
        x, y, rot = bot_cells[bot_i][0], bot_cells[bot_i][1], 0
    bot_i += 1
    fp.SetReference(ref)
    fp.SetValue(c["value"])
    fp.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
    board.Add(fp)
    try:
        fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
    except Exception as e:
        print("flip fail", ref, e)

# assign nets to pads
missing = []
for fp in board.GetFootprints():
    ref = fp.GetReference()
    for pad in fp.Pads():
        nm = padnets.get((ref, pad.GetNumber()))
        if nm:
            pad.SetNet(netitems[nm])

# ------------------------------------------------------ edge + mounts ---
def edge(x0, y0, x1, y1):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(pcbnew.VECTOR2I(MM(x0), MM(y0)))
    s.SetEnd(pcbnew.VECTOR2I(MM(x1), MM(y1)))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(MM(0.05))
    board.Add(s)


edge(0, 0, W, 0); edge(W, 0, W, H); edge(W, H, 0, H); edge(0, H, 0, 0)

MH = None
for mh in ("MountingHole_3.2mm_M3", "MountingHole_3.2mm"):
    fp = pcbnew.FootprintLoad(FPLIBS + "/MountingHole.pretty", mh)
    if fp:
        MH = mh
        break
if MH:
    for i, (x, y) in enumerate([(3, 3), (W - 3, 3), (W - 3, H - 3), (3, H - 3)]):
        f = pcbnew.FootprintLoad(FPLIBS + "/MountingHole.pretty", MH)
        f.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
        board.Add(f)

# Plane pours + silk BEFORE DSN export so planes are part of the route space
gnd = board.FindNet("GND")
p33 = board.FindNet("+3V3")
for layer, net in ((pcbnew.F_Cu, gnd), (pcbnew.In1_Cu, gnd),
                   (pcbnew.In2_Cu, p33), (pcbnew.B_Cu, gnd)):
    z = pcbnew.ZONE(board)
    o = z.Outline()
    o.NewOutline()
    for pt in [(0, 0), (W, 0), (W, H), (0, H)]:
        o.Append(MM(pt[0]), MM(pt[1]))
    z.SetLayer(layer)
    z.SetNetCode(net.GetNetCode())
    try:
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    except Exception:
        pass
    board.Add(z)
    # Footprint keepouts (rule areas): collect polygons of any zone that
    # forbids tracks/vias so the router treats them as blocked on every copper
    # layer (e.g. the ESP32-S3-WROOM-1 antenna keepout).
    KEEPS = []          # list of [(x, y), ...] board-mm polygons


    def collect_keep(z):
        if not (z.GetDoNotAllowTracks() or z.GetDoNotAllowVias()):
            return
        o = z.Outline()
        for oi in range(o.OutlineCount()):
            lc = o.COutline(oi)
            pts = [(lc.CPoint(i).x / 1e6, lc.CPoint(i).y / 1e6)
                   for i in range(lc.PointCount())]
            KEEPS.append(pts)
def seg_dist(ax, ay, bx, by, cx, cy, dx, dy):
    def ccw(px, py, qx, qy, rx, ry):
        return (ry - py) * (qx - px) - (qy - py) * (rx - px)
    d1 = ccw(cx, cy, dx, dy, ax, ay)
    d2 = ccw(cx, cy, dx, dy, bx, by)
    d3 = ccw(ax, ay, bx, by, cx, cy)
    d4 = ccw(ax, ay, bx, by, dx, dy)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)):
        return 0.0
    return min(pt_seg_dist(ax, ay, cx, cy, dx, dy),
               pt_seg_dist(bx, by, cx, cy, dx, dy),
               pt_seg_dist(cx, cy, ax, ay, bx, by),
               pt_seg_dist(dx, dy, ax, ay, bx, by))


CU_LAYERS = (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu)
ALL_CU = frozenset(CU_LAYERS)


def collect_obstacles():
    import math as _m
    for i, (x, y) in enumerate([(3, 3), (W - 3, 3), (W - 3, H - 3), (3, H - 3)]):
        f = pcbnew.FootprintLoad(FPLIBS + "/MountingHole.pretty", MH)
        f.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
        board.Add(f)
        # keepout around the NPTH barrel so pours/tracks honour the
        # hole clearance (zone fills don't clear footprint NPTH drills)
        kz = pcbnew.ZONE(board)
        ko = kz.Outline()
        ko.NewOutline()
        for k in range(8):
            a = k * _m.pi / 4
            ko.Append(MM(x + 2.2 * _m.cos(a)), MM(y + 2.2 * _m.sin(a)))
        kz.SetIsRuleArea(True)
        kz.SetDoNotAllowTracks(True)
        kz.SetDoNotAllowVias(True)
        kz.SetDoNotAllowZoneFills(True)
        ls = pcbnew.LSET()
        ls.addLayer(pcbnew.F_Cu); ls.addLayer(pcbnew.In1_Cu)
        ls.addLayer(pcbnew.In2_Cu); ls.addLayer(pcbnew.B_Cu)
        try:
            kz.SetLayerSet(ls)
        except Exception:
            kz.SetLayer(pcbnew.F_Cu)
        board.Add(kz)


for fp in board.GetFootprints():
    for z in fp.Zones():
        collect_keep(z)
for z in board.Zones():
    if z.GetIsRuleArea():
        collect_keep(z)
print("keepout polys:", len(KEEPS))

pcbnew.SaveBoard(PCB, board)
ok = pcbnew.ExportSpecctraDSN(board, DSN)
print("pcb", PCB, "| dsn", DSN, ok)

def pt_seg_dist(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    L2 = vx * vx + vy * vy
    if L2 == 0:
        return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
    t = max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / L2))
    return ((px - ax - t * vx) ** 2 + (py - ay - t * vy) ** 2) ** 0.5


def add_via(x, y, netcode):
    v = pcbnew.PCB_VIA(board)
def add_track(ax, ay, bx, by, layer, netcode, w=0.25):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(MM(ax), MM(ay)))
    t.SetEnd(pcbnew.VECTOR2I(MM(bx), MM(by)))
    t.SetLayer(layer)
    t.SetWidth(MM(w))
    t.SetNetCode(netcode)
    board.Add(t)
    if GRID is not None:
        stamp_item(GRID, (ax, ay, bx, by, w / 2, netcode, layer))
    return t


def pad_xy(p):
    pos = p.GetPosition()
    return pos.x / 1e6, pos.y / 1e6


def islands(netcode, conn):
    """Connected-pad clusters for one net."""
    pl = []
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.GetNetCode() == netcode:
                pl.append(p)
    clus = [[p] for p in pl]
    changed = True
    while changed:
        changed = False
        for i in range(len(clus)):
            ids = set(x.m_Uuid.AsString()
                      for x in conn.GetConnectedItems(clus[i][0]))
            for j in range(i + 1, len(clus)):
                if any(k.m_Uuid.AsString() in ids for k in clus[j]):
                    clus[i] += clus[j]
                    del clus[j]
                    changed = True
                    break
            if changed:
                break
    return clus


def via_candidates(px, py, smd, pad=None, rr_max=10.0):
    import math
    cands = [(px, py)] if smd else []
    if pad is not None:
        # prefer escaping outward along the pad's long axis
        sz = pad.GetSize()
        half = max(sz.x, sz.y) / 2 / 1e6
        ang = math.radians(pad.GetOrientationDegrees())
        if sz.y > sz.x:
            ang += math.pi / 2
        fpos = pad.GetParent().GetPosition()
        ox = px - fpos.x / 1e6
        oy = py - fpos.y / 1e6
        ux, uy = math.cos(ang), math.sin(ang)
        # pick the long-axis direction pointing away from footprint centre
        if ux * ox + uy * oy < 0:
            ux, uy = -ux, -uy
        d = half + 0.35
        while d < half + rr_max:
            cands.append((px + ux * d, py + uy * d))
            cands.append((px - ux * d, py - uy * d))
            d += 0.4
    rr = 0.8
    while rr <= rr_max:
        for k in range(16):
            cands.append((px + rr * math.cos(k * math.pi / 8),
                          py + rr * math.sin(k * math.pi / 8)))
        rr *= 1.4
    return cands


def in_bounds(x, y):
    return 1 < x < W - 1 and 1 < y < H - 1


def collect_obstacles():
    """Obstacle primitives in board mm.

    dots  — capsule segments (ax,ay,bx,by,r,netcode,layers): vias + round
            pads; radius is the copper half-width.
    segs  — tracks (ax,ay,bx,by,halfw,netcode,layer).
    rects — rotated rectangles (cx,cy,hx,hy,cos,sin,netcode,layers):
            non-round pads modelled exactly so corners block copper.
    holes — drill holes (cx,cy,r,netcode): THT pads and vias; spacing to
            other holes and copper is tighter than copper rules.
    keeps — keepout polygons [[(x,y),...]] blocking every copper layer.
    """
    import math
    dots, segs, rects, holes = [], [], [], []
    for fp in board.GetFootprints():
        for p in fp.Pads():
            pos = p.GetPosition()
            sz = p.GetSize()
            cx, cy = pos.x / 1e6, pos.y / 1e6
            dz = p.GetDrillSize()
            if dz.x > 0:
                holes.append((cx, cy, dz.x / 2 / 1e6, p.GetNetCode()))
            # tiny no-net anchor pads (e.g. QFN mechanical dots inside a
            # thermal pad) shouldn't block vias; NPTH pads have no copper
            if not p.GetNetname() and max(sz.x, sz.y) < 0.8e6:
                continue
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                continue
            wid = min(sz.x, sz.y) / 1e6
            ln = max(sz.x, sz.y) / 1e6
            half = (ln - wid) / 2
            ang = math.radians(p.GetOrientationDegrees())
            if sz.y > sz.x:
                ang += math.pi / 2
            dx, dy = math.cos(ang) * half, math.sin(ang) * half
            layers = set()
            for ly in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu,
                       pcbnew.B_Cu):
                if p.IsOnLayer(ly):
                    layers.add(ly)
            shape = p.GetShape() if hasattr(p, "GetShape") else None
            if shape == pcbnew.PAD_SHAPE_CIRCLE:
                dots.append((cx, cy, cx, cy, wid / 2,
                             p.GetNetCode(), layers))
            else:
                # exact rectangle in the pad's own frame (covers corners)
                a2 = math.radians(p.GetOrientationDegrees())
                rects.append((cx, cy, sz.x / 2 / 1e6, sz.y / 2 / 1e6,
                              math.cos(a2), math.sin(a2),
                              p.GetNetCode(), layers))
    for t in board.GetTracks():
        pos = t.GetPosition()
        if isinstance(t, pcbnew.PCB_VIA):
            dots.append((pos.x / 1e6, pos.y / 1e6, pos.x / 1e6,
                         pos.y / 1e6, t.GetWidth() / 2 / 1e6,
                         t.GetNetCode(), ALL_CU))
            holes.append((pos.x / 1e6, pos.y / 1e6,
                          t.GetDrillValue() / 2 / 1e6
                          if hasattr(t, 'GetDrillValue') else 0.15,
                          t.GetNetCode()))
        else:
            segs.append((t.GetStart().x / 1e6, t.GetStart().y / 1e6,
                         t.GetEnd().x / 1e6, t.GetEnd().y / 1e6,
                         t.GetWidth() / 2 / 1e6, t.GetNetCode(),
                         t.GetLayer()))
    return dots, segs, rects, holes


RECTS = []   # pad rectangles, populated by collect_obstacles()
HOLES = []   # drill holes (cx,cy,r,netcode)

CLR = 0.22            # net clearance used by the router, mm
VIA_D = 0.6            # stitch via diameter, mm
VIA_DRILL = 0.3        # stitch via drill, mm
VIA_R = VIA_D / 2      # copper radius used for clearance checks
H2H = 0.55             # hole-edge to hole-edge clearance + margin
EDGE_M = 0.8           # min copper distance to board edge, mm
GS = 0.5               # raster cell pitch, mm
GNX, GNY = int(W / GS) + 2, int(H / GS) + 2
GRID = None            # built lazily by build_grid()


def new_grid():
    return {ly: [[-1] * GNY for _ in range(GNX)] for ly in CU_LAYERS}


def stamp_item(grid, item):
    """Mark cells covered by one obstacle (dot- or seg-tuple)."""
    ax, ay, bx, by, r, nc, layers = item
    if isinstance(layers, int):
        layers = (layers,)
    rad = r + 0.125 + CLR
    x0 = int((min(ax, bx) - rad) / GS)
    x1 = int((max(ax, bx) + rad) / GS) + 1
    y0 = int((min(ay, by) - rad) / GS)
def pt_rect_dist(px, py, cx, cy, hx, hy, ca, sa):
    """Point to rotated-rect distance (0 inside)."""
    dx, dy = px - cx, py - cy
    lx = dx * ca + dy * sa
    ly = -dx * sa + dy * ca
    ox = max(0.0, abs(lx) - hx)
    oy = max(0.0, abs(ly) - hy)
    return (ox * ox + oy * oy) ** 0.5


def seg_rect_dist(ax, ay, bx, by, cx, cy, hx, hy, ca, sa):
    """Segment to rotated-rect distance (0 on overlap)."""
    d = min(pt_rect_dist(ax, ay, cx, cy, hx, hy, ca, sa),
            pt_rect_dist(bx, by, cx, cy, hx, hy, ca, sa))
    if d == 0.0:
        return 0.0
    cs = [(cx + sx * ca - sy * sa, cy + sx * sa + sy * ca)
          for sx, sy in ((hx, hy), (hx, -hy), (-hx, hy), (-hx, -hy))]
    for i in range(4):
        x1, y1 = cs[i]
        x2, y2 = cs[(i + 1) % 4]
        d = min(d, seg_dist(ax, ay, bx, by, x1, y1, x2, y2))
    return d


def pt_poly_dist(x, y, poly):
    """Point to polygon distance (0 inside)."""
    inside = False
    d = 1e9
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        d = min(d, pt_seg_dist(x, y, x1, y1, x2, y2))
        if (y1 > y) != (y2 > y) and \
                x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return 0.0 if inside else d


def seg_poly_dist(ax, ay, bx, by, poly):
    """Segment to polygon distance (0 on overlap/inside)."""
    if pt_poly_dist(ax, ay, poly) == 0.0 or \
            pt_poly_dist(bx, by, poly) == 0.0:
        return 0.0
    d = 1e9
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        d = min(d, seg_dist(ax, ay, bx, by, x1, y1, x2, y2))
    return d


def in_keeps(x, y):
    """True when (x,y) falls inside a copper keepout polygon."""
    for poly in KEEPS:
        if pt_poly_dist(x, y, poly) < CLR:
            return True
    return False


def pad_layers(pad):
    return [ly for ly in CU_LAYERS if pad.IsOnLayer(ly)]



def via_ok(dots, segs, x, y, netcode, vr=VIA_R):
    if in_keeps(x, y):
        return False
    for hx, hy, hr, nc in HOLES:
        # drill edge to other drills >= 0.5; use drilled radius + margin
        if ((x - hx) ** 2 + (y - hy) ** 2) ** 0.5 < hr + VIA_DRILL / 2 + H2H:
            return False
    for ax, ay, bx, by, r, nc, layers in dots:
        if nc != netcode and pt_seg_dist(x, y, ax, ay, bx, by) < \
                r + vr + max(CLR, 0.32):
            return False
    for ax, ay, bx, by, w, nc, ly in segs:
        if nc != netcode and pt_seg_dist(x, y, ax, ay, bx, by) < w + vr + CLR:
            return False
    for cx, cy, hx, hy, ca, sa, nc, layers in RECTS:
        if nc != netcode and \
                pt_rect_dist(x, y, cx, cy, hx, hy, ca, sa) < vr + CLR:
            return False
    return True


def track_ok(dots, segs, ax, ay, bx, by, netcode, layer, tw=0.25):
    # copper-to-edge: track edge must stay >= 0.5 mm from the outline;
    # endpoints sit on pads which carry their own edge rule, so the
    # strict check applies to the segment midpoint.
    em = 0.5 + tw / 2 + 0.05
    mx_, my_ = (ax + bx) / 2, (ay + by) / 2
    if mx_ < em or mx_ > W - em or my_ < em or my_ > H - em:
        return False
    for hx, hy, hr, nc in HOLES:
        # drill edge to other-net copper >= 0.3; same-net tracks may
        # legitimately terminate on their own THT pads
        if nc != netcode and \
                pt_seg_dist(hx, hy, ax, ay, bx, by) < hr + 0.3 + tw / 2:
            return False
    for poly in KEEPS:
        if seg_poly_dist(ax, ay, bx, by, poly) < tw / 2 + CLR:
            return False
    for sx, sy, ex, ey, r, nc, layers in dots:
        if nc != netcode and layer in layers and \
                seg_dist(ax, ay, bx, by, sx, sy, ex, ey) < r + tw / 2 + CLR:
            return False
    for sx, sy, ex, ey, w, nc, ly in segs:
        if nc != netcode and ly == layer and \
                seg_dist(ax, ay, bx, by, sx, sy, ex, ey) < w + tw / 2 + CLR:
            return False
    for cx, cy, hx, hy, ca, sa, nc, layers in RECTS:
        if nc != netcode and layer in layers and \
                seg_rect_dist(ax, ay, bx, by, cx, cy, hx, hy,
                              ca, sa) < tw / 2 + CLR:
            return False
    return True


def add_via(x, y, netcode):
    v = pcbnew.PCB_VIA(board)
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
    v.SetWidth(MM(VIA_D))
    v.SetDrill(MM(VIA_DRILL))
    v.SetNetCode(netcode)
    board.Add(v)
    HOLES.append((x, y, VIA_DRILL / 2, netcode))
    if GRID is not None:
        stamp_item(GRID, (x, y, x, y, VIA_R, netcode, ALL_CU))
    return v


def islands(netcode, conn):
    """Connected-pad clusters for one net."""
    pl = []
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.GetNetCode() == netcode:
                pl.append(p)
    clus = [[p] for p in pl]
    changed = True
    while changed:
        changed = False
        for i in range(len(clus)):
            ids = set(x.m_Uuid.AsString()
                      for x in conn.GetConnectedItems(clus[i][0]))
            for j in range(i + 1, len(clus)):
                if any(k.m_Uuid.AsString() in ids for k in clus[j]):
                    clus[i] += clus[j]
                    del clus[j]
                    changed = True
                    break
            if changed:
                break
    return clus


def via_candidates(px, py, smd, pad=None, rr_max=10.0):
    import math
    cands = [(px, py)] if smd else []
    if pad is not None:
        # prefer escaping outward along the pad's long axis
        sz = pad.GetSize()
        half = max(sz.x, sz.y) / 2 / 1e6
        ang = math.radians(pad.GetOrientationDegrees())
        if sz.y > sz.x:
            ang += math.pi / 2
        fpos = pad.GetParent().GetPosition()
        ox = px - fpos.x / 1e6
        oy = py - fpos.y / 1e6
        ux, uy = math.cos(ang), math.sin(ang)
        # pick the long-axis direction pointing away from footprint centre
        if ux * ox + uy * oy < 0:
            ux, uy = -ux, -uy
        d = half + 0.35
        while d < half + rr_max:
            cands.append((px + ux * d, py + uy * d))
            cands.append((px - ux * d, py - uy * d))
            d += 0.4
    rr = 0.8
    while rr <= rr_max:
        for k in range(16):
            cands.append((px + rr * math.cos(k * math.pi / 8),
                          py + rr * math.sin(k * math.pi / 8)))
        rr *= 1.4
    return cands


def in_bounds(x, y):
    return EDGE_M < x < W - EDGE_M and EDGE_M < y < H - EDGE_M


def pad_surface(pad):
    return pcbnew.B_Cu if pad.IsOnLayer(pcbnew.B_Cu) and \
        not pad.IsOnLayer(pcbnew.F_Cu) else pcbnew.F_Cu


def try_plane_via(pad, dots, segs, ncode):
    """Drop a via on/next to a pad so a plane pours into it."""
    px, py = pad_xy(pad)
    player = pad_surface(pad)
    smd = pad.GetAttribute() == pcbnew.PAD_ATTRIB_SMD


    for cx, cy in via_candidates(px, py, smd, pad):
        if not in_bounds(cx, cy):
            continue
        if not via_ok(dots, segs, cx, cy, ncode):
            continue
        if (cx, cy) != (px, py) and not track_ok(
                dots, segs, px, py, cx, cy, ncode, player):
            continue
        put_via(dots, cx, cy, ncode)
        if (cx, cy) != (px, py):
            add_track(px, py, cx, cy, player, ncode)
            segs.append((px, py, cx, cy, 0.125, ncode, player))
        return True
    return False

def via_sites(pad, dots, segs, ncode, limit=20):
    """First `limit` via positions reachable from pad by a clear stub.

    """
    px, py = pad_xy(pad)
    player = pad_surface(pad)
    smd = pad.GetAttribute() == pcbnew.PAD_ATTRIB_SMD
    out, seen = [], set()
    for cx, cy in via_candidates(px, py, smd, pad):
        if (round(cx, 2), round(cy, 2)) in seen:
            continue
        seen.add((round(cx, 2), round(cy, 2)))
        if not in_bounds(cx, cy):
            continue
        if not via_ok(dots, segs, cx, cy, ncode):
            continue
        if (cx, cy) != (px, py) and not track_ok(
                dots, segs, px, py, cx, cy, ncode, player):
            continue
        out.append((cx, cy))
        if len(out) >= limit:
            break
    if out:
        return out
    # moated pads (fine-pitch fields fenced by long tracks) need pockets
    # the coarse rings miss — dense sweep for any legal via + stub
    ix = iy = 0
    while iy < 50:
        cx = px - 4 + ix * 0.16
        cy = py - 4 + iy * 0.16
        ix += 1
        if ix >= 50:
            ix = 0
            iy += 1
        if not in_bounds(cx, cy):
            continue
        if not via_ok(dots, segs, cx, cy, ncode):
            continue
        if not track_ok(dots, segs, px, py, cx, cy, ncode, player):
            continue
        out.append((cx, cy))
        if len(out) >= limit:
            break
    return out

def stamp_item(grid, item):
    """Mark cells covered by one obstacle (dot- or seg-tuple)."""
    ax, ay, bx, by, r, nc, layers = item
    if isinstance(layers, int):
        layers = (layers,)
    rad = r + 0.125 + CLR
    x0 = int((min(ax, bx) - rad) / GS)
    x1 = int((max(ax, bx) + rad) / GS) + 1
    y0 = int((min(ay, by) - rad) / GS)
    y1 = int((max(ay, by) + rad) / GS) + 1
    for ly in layers:
        g = grid[ly]
        for cx in range(max(0, x0), min(GNX - 1, x1) + 1):
            px = cx * GS
            for cy in range(max(0, y0), min(GNY - 1, y1) + 1):
                if pt_seg_dist(px, cy * GS, ax, ay, bx, by) <= rad:
                    v = g[cx][cy]
                    if v == -1:
                        g[cx][cy] = nc
                    elif v != nc:
                        g[cx][cy] = -2      # contested: blocks every net


def stamp_rect(grid, cx_, cy_, hx, hy, ca, sa, nc, layers):
    """Rasterize a rotated-rect pad onto blocking grids."""
    import math
    rad = max(hx, hy) + 0.125 + CLR + 0.35
    x0 = int((cx_ - rad) / GS)
    x1 = int((cx_ + rad) / GS) + 1
    y0 = int((cy_ - rad) / GS)
    y1 = int((cy_ + rad) / GS) + 1
    lim = 0.125 + CLR + GS * 0.71     # reach cells the pad's area touches
    for ly in layers:
        g = grid[ly]
        for cx in range(max(0, x0), min(GNX - 1, x1) + 1):
            for cy in range(max(0, y0), min(GNY - 1, y1) + 1):
                if pt_rect_dist(cx * GS, cy * GS, cx_, cy_,
                                hx, hy, ca, sa) <= lim:
                    v = g[cx][cy]
                    if v == -1:
                        g[cx][cy] = nc
                    elif v != nc:
                        g[cx][cy] = -2


def stamp_poly(grid, poly):
    """Keepout polygon: block every copper layer inside + margin."""
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    rad = 0.125 + CLR
    x0 = int((min(xs) - rad) / GS)
    x1 = int((max(xs) + rad) / GS) + 1
    y0 = int((min(ys) - rad) / GS)
    y1 = int((max(ys) + rad) / GS) + 1
    for ly in CU_LAYERS:
        g = grid[ly]
        for cx in range(max(0, x0), min(GNX - 1, x1) + 1):
            for cy in range(max(0, y0), min(GNY - 1, y1) + 1):
                if pt_poly_dist(cx * GS, cy * GS, poly) <= rad + GS * 0.71:
                    g[cx][cy] = -2


def stamp_hole(grid, hx, hy, hr):
    """Drill hole: contested for every net on every layer."""
    rad = hr + 0.3 + 0.125
    x0 = int((hx - rad) / GS); x1 = int((hx + rad) / GS) + 1
    y0 = int((hy - rad) / GS); y1 = int((hy + rad) / GS) + 1
    for ly in CU_LAYERS:
        g = grid[ly]
        for cx in range(max(0, x0), min(GNX - 1, x1) + 1):
            for cy in range(max(0, y0), min(GNY - 1, y1) + 1):
                if ((cx * GS - hx) ** 2 + (cy * GS - hy) ** 2) ** 0.5 <= rad:
                    g[cx][cy] = -2


def build_grid(dots, segs):
    grid = new_grid()
    for it in dots:
        stamp_item(grid, it)
    for it in segs:
        stamp_item(grid, it)
    for cx_, cy_, hx, hy, ca, sa, nc, layers in RECTS:
        stamp_rect(grid, cx_, cy_, hx, hy, ca, sa, nc, layers)
    for poly in KEEPS:
        stamp_poly(grid, poly)
    for hx, hy, hr, nc in HOLES:
        stamp_hole(grid, hx, hy, hr)
    return grid


def via_fits_cell(cx, cy, ncode):
    """Raster check: a via at cell (cx,cy) clears other nets on all layers."""
    vx, vy = cx * GS, cy * GS
    for hx, hy, hr, nc in HOLES:
        if ((vx - hx) ** 2 + (vy - hy) ** 2) ** 0.5 < \
                hr + VIA_DRILL / 2 + H2H:
            return False
    for ly in CU_LAYERS:
        g = GRID[ly]
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                x, y = cx + dx, cy + dy
                if 0 <= x < GNX and 0 <= y < GNY:
                    v = g[x][y]
                    if v != -1 and v != ncode:
                        return False
    return True


def grid_route(starts, goals, ncode, margin=50, goal_states=None,
               start_layers=None):
    """Multi-layer 4-dir A*: state (cx,cy,layer); layer change = via.

    starts/goals are lists of (cx,cy) cells (each valid on all layers).
    goal_states, if given, is a set of (cx,cy,layer) triples — the path
    must then END on one of those exact states.  start_layers, if given,
    maps a start cell to the layers it may be seeded on — otherwise a
    start cell is valid on every copper layer (true for via sites).
    Returns [(cx,cy,layer), ...] or None.
    """
    import heapq
    allx = [s[0] for s in starts] + [g0[0] for g0 in goals]
    ally = [s[1] for s in starts] + [g0[1] for g0 in goals]
    xlo = max(0, min(allx) - margin)
    xhi = min(GNX - 1, max(allx) + margin)
    ylo = max(0, min(ally) - margin)
    yhi = min(GNY - 1, max(ally) + margin)
    goalset = {(g0[0], g0[1]) for g0 in goals}
    gstates = set(goal_states) if goal_states else None
    openh = []
    came, gs = {}, {}
    for s in starts:
        lys = start_layers.get(s, CU_LAYERS) if start_layers else CU_LAYERS
        for ly in lys:
            st = (s[0], s[1], ly)
            gs[st] = 0.0
            came[st] = None
            heapq.heappush(openh, (0.0, st))
    layers = list(CU_LAYERS)
    while openh:
        _, cur = heapq.heappop(openh)
        if (cur in gstates) if gstates is not None \
                else ((cur[0], cur[1]) in goalset):
            path = []
            while cur is not None:
                path.append(cur)
                cur = came[cur]
            return path[::-1]
        cx, cy, ly = cur
        # same-layer steps
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx_, ny_ = cx + d[0], cy + d[1]
            if not (xlo <= nx_ <= xhi and ylo <= ny_ <= yhi):
                continue
            n2 = (nx_, ny_, ly)
            v = GRID[ly][nx_][ny_]
            if (nx_, ny_) not in goalset and v != -1 and v != ncode:
                continue
            ng = gs[cur] + 1.0
            if gs.get(n2, 1e18) <= ng:
                continue
            gs[n2] = ng
            came[n2] = cur
            heapq.heappush(
                openh,
                (ng + min(abs(g0[0] - nx_) + abs(g0[1] - ny_)
                          for g0 in goals), n2))
        # via: switch layer in place
        if via_fits_cell(cx, cy, ncode):
            for ly2 in layers:
                if ly2 == ly:
                    continue
                n2 = (cx, cy, ly2)
                ng = gs[cur] + 4.0
                if gs.get(n2, 1e18) <= ng:
                    continue
                gs[n2] = ng
                came[n2] = cur
                heapq.heappush(
                    openh,
                    (ng + min(abs(g0[0] - cx) + abs(g0[1] - cy)
                              for g0 in goals), n2))
    return None


def try_grid(pad, tpad, dots, segs, ncode, a_sites=None, b_sites=None):
    """Via near each pad, multi-layer raster A* between them."""
    if GRID is None:
        return False


















def try_grid_cluster(pad, cluster, dots, segs, ncode):
    """Attach an island pad to the nearest reachable cluster pad.

    Goals are the cluster pads' own cells qualified by the layers each
    pad lives on; the last hop is a short same-net stub onto the pad.
    """
    if GRID is None:
        return False
    a_sites = via_sites(pad, dots, segs, ncode, limit=12)
    px0, py0 = pad_xy(pad)
    padcell = (round(px0 / GS), round(py0 / GS))
    starts = [(round(x / GS), round(y / GS)) for x, y in a_sites]
    if padcell not in starts:
        starts.append(padcell)          # walk out of a pad moat on its own layer
    if not a_sites and padcell not in starts:
        return False
    goals, gstates, cell_pad, cell_pt = [], set(), {}, {}
    px, py = pad_xy(pad)
    # skip copper inside the pad's own island — attaching to it changes
    # nothing; proximity to OTHER islands/main copper is what we want
    isl_pts = set()
    try:
        for x in board.GetConnectivity().GetConnectedItems(pad):
            ip = x.GetPosition()
            isl_pts.add((round(ip.x / 1e6, 2), round(ip.y / 1e6, 2)))
    except Exception:
        isl_pts.add((round(px, 2), round(py, 2)))

    def near_island(ax_, ay_):
        return any((ax_ - ix) ** 2 + (ay_ - iy) ** 2 < 1.0
                   for ix, iy in isl_pts)
    for q in cluster:
        gx, gy = pad_xy(q)
        gc = (round(gx / GS), round(gy / GS))
        goals.append(gc)
        cell_pad[gc] = q
        for ly in pad_layers(q):
            gstates.add((gc[0], gc[1], ly))
    # any other copper of the same net is a legal attach point: vias on
    # all layers, tracks on their own layer.
    for ax_, ay_, bx_, by_, r, nc, layers in dots:
        if nc != ncode or near_island(ax_, ay_):
            continue
        gc = (round(ax_ / GS), round(ay_ / GS))
        goals.append(gc)
        cell_pt[gc] = (ax_, ay_)
        for ly in layers:
            gstates.add((gc[0], gc[1], ly))
    for ax_, ay_, bx_, by_, w, nc, ly in segs:
        if nc != ncode or (near_island(ax_, ay_) and
                           near_island(bx_, by_)):
            continue
        for ex_, ey_ in ((ax_, ay_), (bx_, by_)):
            gc = (round(ex_ / GS), round(ey_ / GS))
            goals.append(gc)
            cell_pt[gc] = (ex_, ey_)
            gstates.add((gc[0], gc[1], ly))
    player = pad_surface(pad)
    path = grid_route(starts, goals, ncode, goal_states=gstates,
                      start_layers={padcell: (player,)})
    if not path:
        return False
    # emit: pad stub onto the first cell if the start was a via site,
    # per-segment tracks, vias where the path changes layer
    s0 = path[0]
    if (s0[0], s0[1]) != padcell:
        put_via(dots, s0[0] * GS, s0[1] * GS, ncode)
        add_track(px0, py0, s0[0] * GS, s0[1] * GS, player, ncode)
        segs.append((px0, py0, s0[0] * GS, s0[1] * GS,
                     0.125, ncode, player))
    for c0, c1 in zip(path, path[1:]):
        if (c0[0], c0[1]) == (c1[0], c1[1]):
            put_via(dots, c0[0] * GS, c0[1] * GS, ncode)
            continue
        add_track(c0[0] * GS, c0[1] * GS,
                  c1[0] * GS, c1[1] * GS, c0[2], ncode)
        segs.append((c0[0] * GS, c0[1] * GS,
                     c1[0] * GS, c1[1] * GS, 0.125, ncode, c0[2]))
    sb = path[-1]

    # final hop: same-net stub from the goal cell onto the pad/copper
    gcell = (sb[0], sb[1])
    q = cell_pad.get(gcell)
    if q is not None:
        qx, qy = pad_xy(q)
    elif gcell in cell_pt:
        qx, qy = cell_pt[gcell]
    else:
        qx = qy = None
    if qx is not None:
        ex, ey = sb[0] * GS, sb[1] * GS
        if (ex, ey) != (qx, qy):
            add_track(ex, ey, qx, qy, sb[2], ncode)
            segs.append((ex, ey, qx, qy, 0.125, ncode, sb[2]))
    return True


ESC = {}            # pad uuid -> escape-via (x,y) or None
VIAS_PLACED = set()  # rounded (x,y) of stitch vias already on board


def put_via(dots, x, y, ncode):
    """add_via unless a stitch via already sits at this spot."""
    k = (round(x, 3), round(y, 3))
    if k not in VIAS_PLACED:
        add_via(x, y, ncode)
        VIAS_PLACED.add(k)
    dots.append((x, y, x, y, VIA_R, ncode, ALL_CU))


def escape_via(pad, dots, segs, ncode):
    """Reserve one escape via + stub for a pad; cached per pad."""
    k = pad.m_Uuid.AsString()
    if k in ESC:
        return ESC[k]
    sites = via_sites(pad, dots, segs, ncode, limit=1)
    if not sites:
        ESC[k] = None
        return None
    cx, cy = sites[0]
    px, py = pad_xy(pad)
    player = pad_surface(pad)
    put_via(dots, cx, cy, ncode)
    if (cx, cy) != (px, py):
        add_track(px, py, cx, cy, player, ncode)
        segs.append((px, py, cx, cy, 0.125, ncode, player))
    ESC[k] = (cx, cy)
    return ESC[k]


def try_route(pad, tpad, dots, segs, ncode, a_sites=None, b_sites=None):
    """Via-pair + straight/L track between pad and target pad."""
    px, py = pad_xy(pad)
    tx, ty = pad_xy(tpad)
    player = pad_surface(pad)
    tlayer = pad_surface(tpad)
    if a_sites is None:
        a_sites = via_sites(pad, dots, segs, ncode, limit=24)
    if b_sites is None:
        b_sites = via_sites(tpad, dots, segs, ncode, limit=24)
    for rlayer in (pcbnew.B_Cu, pcbnew.F_Cu, pcbnew.In1_Cu,
                     pcbnew.In2_Cu):
        for ax, ay in a_sites:
            near_b = sorted(b_sites,
                            key=lambda s: (s[0] - ax) ** 2 +
                            (s[1] - ay) ** 2)[:8]
            for bx, by in near_b:
                mx1 = (ax + bx) / 2
                mids = [((ax, ay), (bx, by)),
                        ((ax, ay), (ax, by), (bx, by)),
                        ((ax, ay), (bx, ay), (bx, by)),
                        ((ax, ay), (mx1, ay), (mx1, by), (bx, by)),
                        ((ax, ay), (ax, ty), (bx, ty), (bx, by)),
                        ((ax, ay), (tx, ay), (tx, by), (bx, by))]
                for path in mids:
                    if not all(track_ok(dots, segs,
                                        path[k][0], path[k][1],
                                        path[k + 1][0], path[k + 1][1],
                                        ncode, rlayer)
                               for k in range(len(path) - 1)):
                        continue
                    # emit: pad stubs, via pair, routed segments
                    put_via(dots, ax, ay, ncode)
                    put_via(dots, bx, by, ncode)
                    if (ax, ay) != (px, py):
                        add_track(px, py, ax, ay, player, ncode)
                        segs.append((px, py, ax, ay,
                                     0.125, ncode, player))
                    if (bx, by) != (tx, ty):
                        add_track(tx, ty, bx, by, tlayer, ncode)
                        segs.append((tx, ty, bx, by,
                                     0.125, ncode, tlayer))
                    for k in range(len(path) - 1):
                        add_track(path[k][0], path[k][1],
                                  path[k + 1][0], path[k + 1][1],
                                  rlayer, ncode)
                        segs.append((path[k][0], path[k][1],
                                     path[k + 1][0], path[k + 1][1],
                                     0.125, ncode, rlayer))
                    return True
    return False



def stitch():
    planes = {"GND", "+3V3"}
    conn = board.GetConnectivity()
    dots, segs, r, h = collect_obstacles()
    RECTS.clear(); RECTS.extend(r)
    HOLES.clear(); HOLES.extend(h)
    work = []          # [name, ncode, pad, tpad, done]
    for net in board.GetNetsByName().values():
        name = net.GetNetname()
        if not name or name.startswith("unconnected"):
            continue
        ncode = net.GetNetCode()
        clus = islands(ncode, conn)
        if len(clus) < 2:
            continue
        main = max(clus, key=len)
        for c in clus:
            if c is main:
                continue
            for pad in c:
                px, py = pad_xy(pad)
                tpad = min(main, key=lambda q:
                           (pad_xy(q)[0] - px) ** 2 +
                           (pad_xy(q)[1] - py) ** 2)
                work.append([name, ncode, pad, tpad, False, main])
    print("island pads:", len(work))
    # route signals first while the board is clear, then plane fanout;
    # shortest hops first so long routes aren't blocked early
    def wdist(w):
        ax, ay = pad_xy(w[2])
        bx, by = pad_xy(w[3])
        return (ax - bx) ** 2 + (ay - by) ** 2
    work.sort(key=lambda w: (w[0] in planes, wdist(w)))
    global CLR, GRID, ESC, VIAS_PLACED
    ESC, VIAS_PLACED = {}, set()
    # phase A — fanout: reserve an escape via on every island pad and on
    # every signal-net target pad BEFORE any routing exists, so early
    # routes can't seal off later escapes.
    for w in work:
        name, ncode, pad, tpad = w[0], w[1], w[2], w[3]
        escape_via(pad, dots, segs, ncode)
        if name not in planes:
            escape_via(tpad, dots, segs, ncode)
    for rnd in range(4):
        if rnd >= 1:
            GRID = build_grid(dots, segs)
        conn = board.GetConnectivity()
        progress = 0
        for w in work:
            if w[4]:
                continue
            name, ncode, pad, tpad = w[0], w[1], w[2], w[3]
            ids = set(x.m_Uuid.AsString()
                      for x in conn.GetConnectedItems(pad))
            ka = pad.m_Uuid.AsString()
            ea = ESC.get(ka)
            a_sites = [ea] if ea else \
                via_sites(pad, dots, segs, ncode, limit=12)
            # try the whole main cluster nearest-first — the closest
            # pads' own escapes may themselves be congested; a distant
            # THT connector pad is often the attach point that works
            px, py = pad_xy(pad)
            targets = sorted(w[5], key=lambda q:
                             (pad_xy(q)[0] - px) ** 2 +
                             (pad_xy(q)[1] - py) ** 2)[:25]
            done = False
            for t2 in targets:
                if t2.m_Uuid.AsString() in ids:
                    done = True
                    break
                eb = ESC.get(t2.m_Uuid.AsString())
                b_sites = [eb] if eb else \
                    via_sites(t2, dots, segs, ncode, limit=12)
                done = try_route(pad, t2, dots, segs, ncode,
                                 a_sites, b_sites) or \
                    try_grid(pad, t2, dots, segs, ncode,
                             a_sites[:6], b_sites[:6])
                if done:
                    break
            if not done:
                # attach to ANY reachable pad of the main cluster
                done = try_grid_cluster(pad, w[5], dots, segs, ncode)
            if not done and name in planes:
                # speculative: a via into open copper may join the pour
                # after the next refill
                try_plane_via(pad, dots, segs, ncode)
            w[4] = w[4] or done
            progress += done
        print("residue", rnd, "stitched", progress)
        if progress == 0:
            break
    # drop stitch vias/tracks that join nothing across layers — dangling
    # copper is a DRC violation and can sever pour islands
    conn = board.GetConnectivity()
    for _ in range(3):
        dead = []
        for t in list(board.GetTracks()):
            if not isinstance(t, pcbnew.PCB_VIA):
                continue
            ids = set(x.m_Uuid.AsString()
                      for x in conn.GetConnectedItems(t))
            ids.discard(t.m_Uuid.AsString())
            if len(ids) < 2:
                dead.append(t)
        if not dead:
            break
        for t in dead:
            board.Remove(t)
        conn = board.GetConnectivity()
    # drop stitch vias/tracks that join nothing across layers — dangling
    # copper is a DRC violation and can sever pour islands
    conn = board.GetConnectivity()
    for _ in range(3):
        dead = []
        for t in list(board.GetTracks()):
            if not isinstance(t, pcbnew.PCB_VIA):
                continue
            lys = set()
            for x in conn.GetConnectedItems(t):
                if x.m_Uuid.AsString() == t.m_Uuid.AsString():
                    continue
                if isinstance(x, pcbnew.PCB_VIA):
                    lys.update(CU_LAYERS)
                elif isinstance(x, pcbnew.PAD):
                    lys.update(ly for ly in CU_LAYERS if x.IsOnLayer(ly))
                else:
                    lys.add(x.GetLayer())
            if len(lys & set(CU_LAYERS)) < 2:
                dead.append(t)
        if not dead:
            break
        for t in dead:
            board.Remove(t)
        conn = board.GetConnectivity()
    # dead-end tracks: an end that meets no pad/track/via/pour is dangling
    all_zones = list(board.Zones())
    for _ in range(4):
        dead = []
        items = [t for t in board.GetTracks()
                 if not isinstance(t, pcbnew.PCB_VIA)]
        for t in items:
            ly = t.GetLayer()
            for pt in (t.GetStart(), t.GetEnd()):
                ex, ey = pt.x / 1e6, pt.y / 1e6
                covered = False
                for o in board.GetTracks():
                    if o is t or o.GetNetCode() != t.GetNetCode():
                        continue
                    bb = o.GetBoundingBox()
                    if bb.Contains(pt):
                        covered = True
                        break
                if not covered:
                    for fp in board.GetFootprints():
                        hit = False
                        for p in fp.Pads():
                            if p.GetNetCode() == t.GetNetCode() and \
                                    p.GetBoundingBox().Contains(pt):
                                hit = True
                                break
                        if hit:
                            covered = True
                            break
                if not covered:
                    for z in all_zones:
                        if z.GetNetCode() != t.GetNetCode():
                            continue
                        try:
                            if z.HitTestFilledArea(ly, pt):
                                covered = True
                                break
                        except Exception:
                            pass
                if not covered:
                    dead.append(t)
                    break
        if not dead:
            break
        for t in dead:
            board.Remove(t)
    for z in board.Zones():
        z.SetIsFilled(False)
    try:
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    except Exception:
        pass
    conn = board.GetConnectivity()
    report = {}
    for w in work:
        ids = set(x.m_Uuid.AsString()
                  for x in conn.GetConnectedItems(w[2]))
        if w[3].m_Uuid.AsString() not in ids:
            report[w[0]] = report.get(w[0], 0) + 1
    return report


def _xy(p):
    for a in ("x", "X"):
        if hasattr(p, a):
            v = getattr(p, a)
            v = v() if callable(v) else v
            for b_ in ("y", "Y"):
                if hasattr(p, b_):
                    w = getattr(p, b_)
                    w = w() if callable(w) else w
                    return v / 1e6, w / 1e6
    raise TypeError(str(type(p)))


def final_cleanup():
    """Post-route copper hygiene — all decisions geometric.

    SWIG proxies go stale inside mutation loops (reusing a connectivity
    or zone object across board.Remove() crashes pcbnew), so nothing
    here calls GetConnectivity: every removal is connectivity-safe by
    construction — a via touching same-net copper on fewer than two
    layers, or a track with a free end, cannot be a bridge.
    """
    # merge co-located same-net vias (dedup rounding misses in stitch):
    # two same-net vias <0.7 mm apart bridge the same layers at nearly
    # the same point, so dropping one cannot split the net
    for _ in range(8):
        vias = [t for t in board.GetTracks()
                if isinstance(t, pcbnew.PCB_VIA)]
        done = False
        for i in range(len(vias)):
            vi = vias[i]
            xi, yi = _xy(vi.GetPosition())
            for vj in vias[i + 1:]:
                if vj.GetNetCode() != vi.GetNetCode():
                    continue
                xj, yj = _xy(vj.GetPosition())
                if (xi - xj) ** 2 + (yi - yj) ** 2 < 0.7 ** 2:
                    board.Remove(vj)
                    done = True
                    break
            if done:
                break
        if not done:
            break
    # dangling vias: a via touching same-net copper on fewer than two
    # copper layers joins nothing — dead copper, DRC violation
    for _ in range(6):
        dead = []
        vias = [t for t in board.GetTracks()
                if isinstance(t, pcbnew.PCB_VIA)]
        items = [t for t in board.GetTracks()
                 if not isinstance(t, pcbnew.PCB_VIA)]
        for v in vias:
            vx, vy = _xy(v.GetPosition())
            vr = v.GetWidth() / 2 / 1e6 + 0.05
            lys = set()
            for o in items:
                if o.GetNetCode() != v.GetNetCode():
                    continue
                s1, s2 = _xy(o.GetStart()), _xy(o.GetEnd())
                if min((s1[0] - vx) ** 2 + (s1[1] - vy) ** 2,
                       (s2[0] - vx) ** 2 + (s2[1] - vy) ** 2) < vr ** 2:
                    lys.add(o.GetLayer())
            for v2 in vias:
                if v2 is v or v2.GetNetCode() != v.GetNetCode():
                    continue
                x2, y2 = _xy(v2.GetPosition())
                if (x2 - vx) ** 2 + (y2 - vy) ** 2 < (vr + 0.3) ** 2:
                    lys.update(CU_LAYERS)
            for fp in board.GetFootprints():
                for p in fp.Pads():
                    if p.GetNetCode() == v.GetNetCode() and \
                            p.GetBoundingBox().Contains(v.GetPosition()):
                        lys.update(ly for ly in CU_LAYERS
                                   if p.IsOnLayer(ly))
            if len(lys & set(CU_LAYERS)) < 2:
                dead.append(v)
        if not dead:
            break
        for v in dead:
            board.Remove(v)
    # dead-end tracks: an end that meets no same-net pad/track/via is
    # dangling; deleting a leaf can never split a net, so repeat until
    # the whole dead branch is gone
    for _ in range(200):
        dead = []
        items = [t for t in board.GetTracks()
                 if not isinstance(t, pcbnew.PCB_VIA)]
        vias = [t for t in board.GetTracks()
                if isinstance(t, pcbnew.PCB_VIA)]
        for t in items:
            ly = t.GetLayer()
            for pt in (t.GetStart(), t.GetEnd()):
                covered = False
                for o in items:
                    if covered or o is t or \
                            o.GetNetCode() != t.GetNetCode() or \
                            o.GetLayer() != ly:
                        continue
                    for p2 in (o.GetStart(), o.GetEnd()):
                        if p2.x == pt.x and p2.y == pt.y:
                            covered = True
                            break
                if not covered:
                    for v in vias:
                        if v.GetNetCode() != t.GetNetCode():
                            continue
                        vx, vy = _xy(v.GetPosition())
                        if (vx - pt.x / 1e6) ** 2 + \
                                (vy - pt.y / 1e6) ** 2 < \
                                (v.GetWidth() / 2 / 1e6) ** 2:
                            covered = True
                            break
                if not covered:
                    for fp in board.GetFootprints():
                        if covered:
                            break
                        for p in fp.Pads():
                            if p.GetNetCode() == t.GetNetCode() and \
                                    p.GetBoundingBox().Contains(pt):
                                covered = True
                                break
                if not covered:
                    dead.append(t)
                    break
        if not dead:
            break
        for t in dead:
            board.Remove(t)


def debug_via(x, y, ncode, dots, segs):
    """Print which obstacles reject a via at (x,y) — DEBUG_POST aid."""
    for ax, ay, bx, by, r, nc, layers in dots:
        if nc != ncode and pt_seg_dist(x, y, ax, ay, bx, by) \
                < r + VIA_R + CLR:
            print("  via blocked by dot", round(ax, 2), round(ay, 2),
                  "net", nc)
    for ax, ay, bx, by, w, nc, ly in segs:
        if nc != ncode and pt_seg_dist(x, y, ax, ay, bx, by) \
                < w + VIA_R + CLR:
            print("  via blocked by seg", round(ax, 2), round(ay, 2),
                  "ly", ly, "net", nc)


def debug_via_scan(x, y, ncode, dots, segs):
    """Sweep a 4 mm box reporting legal via sites — DEBUG_POST aid."""
    found = []
    iy = ix = 0
    while iy < 50:
        cx, cy = x - 4 + ix * 0.16, y - 4 + iy * 0.16
        ix += 1
        if ix >= 50:
            ix, iy = 0, iy + 1
        if in_bounds(cx, cy) and via_ok(dots, segs, cx, cy, ncode):
            found.append((round(cx, 2), round(cy, 2)))
    print("  legal sites near", round(x, 2), round(y, 2), ":", found[:8])


def post_attach():
    """Attach island pads left over after stitch() on the saved board.

    Runs after SaveBoard so the connectivity audit reads committed
    copper only — in-run SWIG handles went stale mid-mutation and could
    crash pcbnew. Rebuilds obstacles + the routing grid fresh.
    """
    global GRID, ESC, VIAS_PLACED
    ESC, VIAS_PLACED = {}, set()
    for t in board.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA):
            VIAS_PLACED.add((round(t.GetPosition().x / 1e6, 3),
                             round(t.GetPosition().y / 1e6, 3)))
    dots, segs, rects, holes = collect_obstacles()
    RECTS.clear(); RECTS.extend(rects)
    HOLES.clear(); HOLES.extend(holes)
    GRID = build_grid(dots, segs)
    for _round in range(8):
        conn = board.GetConnectivity()
        todo = []
        for net in board.GetNetsByName().values():
            name = net.GetNetname()
            if not name or name.startswith("unconnected"):
                continue
            ncode = net.GetNetCode()
            clus = islands(ncode, conn)
            if len(clus) < 2:
                continue
            main = max(clus, key=len)
            for c in clus:
                if c is main:
                    continue
                for pad in c:
                    todo.append((pad, main, ncode))
        if not todo:
            break
        progress = 0
        for pad, main, ncode in todo:
            if try_grid_cluster(pad, main, dots, segs, ncode):
                progress += 1
            elif os.environ.get("DEBUG_POST"):
                px, py = pad_xy(pad)
                print("post-attach failed at", round(px, 2), round(py, 2),
                      "sites", len(via_sites(pad, dots, segs, ncode,
                                             limit=12)))
                debug_via(px, py, ncode, dots, segs)
                debug_via_scan(px, py, ncode, dots, segs)
        print("post-attach stitched", progress, "of", len(todo))
        if progress == 0:
            break
        try:
            pcbnew.ZONE_FILLER(board).Fill(board.Zones())
        except Exception:
            pass
    final_cleanup()
    pcbnew.SaveBoard(PCB, board)



def silk_cleanup():
    # hide reference fields that collide with silk/pads in dense areas
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    for ref in ("U_BOOST", "R_EN", "D_CHRG"):
        if ref in fps:
            fps[ref].Reference().SetVisible(False)
    # trim J_SD silkscreen items that overhang the board edge (y >= 89.9)
    fp = fps.get("J_SD")
    if not fp:
        return
    for gi in list(fp.GraphicalItems()):
        if gi.GetLayerName() != "F.Silkscreen":
            continue
        try:
            for setter, getter in (("SetStart", "GetStart"),
                                   ("SetEnd", "GetEnd")):
                p = getattr(gi, getter)()
                if p.y / 1e6 > 89.9:
                    getattr(gi, setter)(
                        pcbnew.VECTOR2I(int(p.x), int(89.9e6)))
        except Exception:
            pass
        try:
            bb = gi.GetBoundingBox()
            if bb.GetBottom() / 1e6 > 90.0:
                fp.RemoveNative(gi)
        except Exception:
            pass


ses = os.environ.get("SES")
if (ses and os.path.exists(ses)) or os.environ.get("STITCH"):
    if ses and os.path.exists(ses):
        print("importing", ses)
        pcbnew.ImportSpecctraSES(board, ses)
    report = stitch()
    print("remaining island pads:", report)
    silk_cleanup()
    for z in board.Zones():
        z.SetIsFilled(False)
    try:
        filler = pcbnew.ZONE_FILLER(board)
        filler.Fill(board.Zones())
    except Exception as e:
        print("fill", e)
        board.FillZones()
    pcbnew.SaveBoard(PCB, board)
    print("routed board saved")
    post_attach()

with open(PRO, "w") as f:
    f.write('{"board":{"design_settings":{"defaults":{"board_outline_line_width":0.1}}},'
            '"meta":{"filename":"ecocell-ocean.kicad_pro","version":1}}\n')
