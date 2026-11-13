#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Post-route plane attach: for island pads on pour nets (GND/+3V3/+5V/...),
drop a via inside the pad so it pierces the inner plane layer, and a short
same-layer stub from pad edge toward the nearest same-net pour when a via
alone can't help. Refills zones and re-checks connectivity each round.
Usage: python3 tools/pcb/attach_planes.py <board.kicad_pcb>"""
import sys, pcbnew

PCB = sys.argv[1]
CU = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
PLANES = {"GND": pcbnew.In1_Cu, "+3V3": pcbnew.In2_Cu, "+5V": pcbnew.In2_Cu,
          "VBAT": pcbnew.In2_Cu, "AMP_5V": pcbnew.In2_Cu,
          "CAM_3V3": pcbnew.In2_Cu, "DAC_3V3": pcbnew.In2_Cu,
          "VBIAS": pcbnew.In2_Cu, "VIN": pcbnew.In2_Cu}

board = pcbnew.LoadBoard(PCB)

def clusters(ncode, conn):
    pads = [p for fp in board.GetFootprints() for p in fp.Pads()
            if p.GetNetCode() == ncode]
    clus = []
    for p in pads:
        ids = set(x.m_Uuid.AsString() for x in conn.GetConnectedItems(p))
        hit = [c for c in clus if c[0] & ids]
        if hit: hit[0][0] |= ids; hit[0][1].append(p)
        else: clus.append([ids, [p]])
    merged = True
    while merged:
        merged = False
        for i in range(len(clus)):
            for j in range(i + 1, len(clus)):
                if clus[i][0] & clus[j][0]:
                    clus[i][0] |= clus[j][0]
                    clus[i][1] += clus[j][1]; clus.pop(j)
                    merged = True; break
            else: continue
            break
    return clus

def refill():
    for z in board.Zones():
        z.SetIsFilled(False)
    try:
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    except Exception:
        board.FillZones()

refill()
for rnd in range(6):
    conn = board.GetConnectivity()
    stuck = []
    for net in board.GetNetsByName().values():
        name = net.GetNetname()
        if not name or name.startswith("unconnected"):
            continue
        nc = net.GetNetCode()
        cl = clusters(nc, conn)
        if len(cl) < 2: continue
        main = max(cl, key=lambda c: len(c[1]))
        for c in cl:
            if c is main: continue
            for p in c[1]:
                stuck.append((name, nc, p))
    if not stuck: break
    print("round", rnd, "island pads", len(stuck))
    for name, nc, p in stuck:
        pos = p.GetPosition()
        # via-in-pad for pour nets: pierce to the inner plane layer
        if name in PLANES and rnd < 3:
            v = pcbnew.PCB_VIA(board)
            v.SetViaType(pcbnew.VIATYPE_THROUGH)
            v.SetPosition(pcbnew.VECTOR2I(pos.x, pos.y))
            v.SetWidth(pcbnew.FromMM(0.6)); v.SetDrill(pcbnew.FromMM(0.3))
            v.SetNetCode(nc)
            board.Add(v)
        else:
            # same-layer stub toward nearest same-net copper
            lay = p.GetLayer() if p.GetLayer() in CU else pcbnew.F_Cu
            best, bd = None, 1e9
            for t in board.GetTracks():
                if t.GetNetCode() != nc or t.GetLayer() != lay: continue
                for pt in (t.GetStart(), t.GetEnd()):
                    d = (pt.x - pos.x) ** 2 + (pt.y - pos.y) ** 2
                    if d < bd and d > 100: bd, best = d, pt
            if best is not None and bd < (4e6) ** 2:
                tr = pcbnew.PCB_TRACK(board)
                tr.SetStart(pos); tr.SetEnd(best)
                tr.SetLayer(lay); tr.SetWidth(pcbnew.FromMM(0.3))
                tr.SetNetCode(nc)
                board.Add(tr)
    refill()
pcbnew.SaveBoard(PCB, board)
# final audit
conn = board.GetConnectivity()
left = {}
for net in board.GetNetsByName().values():
    name = net.GetNetname()
    if not name or name.startswith("unconnected"): continue
    n = len(clusters(net.GetNetCode(), conn))
    if n > 1: left[name] = n
print("remaining split nets:", left)
