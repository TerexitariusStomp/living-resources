#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""gnd_heal.py — stitch GND pour islands and stranded pads.

Reads the kicad-cli DRC JSON; for every unconnected pair on a pour net:
  * Zone|Zone      -> via inside each island's fill + track on a middle
                      layer between them
  * Pad|Zone       -> via at the pad rim touching pad copper (pad then
                      reaches every layer's copper)
  * Pad|Pad/Track  -> same via-at-rim, or a direct stub bridge
Zones are refilled afterwards so the new copper lands inside real pour.

usage: gnd_heal.py board.kicad_pcb drc.json
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


for t in board.GetTracks():
    add_item(t)
pads_by_uuid = {}
for fp in board.GetFootprints():
    for p in fp.Pads():
        add_item(p)
        pads_by_uuid[p.m_Uuid.AsString()] = p
tracks_by_uuid = {t.m_Uuid.AsString(): t for t in board.GetTracks()}
zones_by_uuid = {z.m_Uuid.AsString(): z for z in board.Zones()}


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


def via_legal(qx, qy, nc):
    for l in CU:
        if hit(l, qx, qy, VIA_MARG, nc) is not None:
            return False
    return via_hit(qx, qy, VIA_MARG, nc) is None


def add_via(x, y, nc):
    for v in viabuck.get((int(x // BUCK), int(y // BUCK)), ()):
        vx, vy = v.GetPosition().x / 1e6, v.GetPosition().y / 1e6
        if math.hypot(vx - x, vy - y) < 0.35:
            if v.GetNetCode() == nc:
                return v
            return None
    v = pcbnew.PCB_VIA(board)
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetPosition(pcbnew.VECTOR2I(int(x * 1e6), int(y * 1e6)))
    v.SetWidth(int(VIA_D * 1e6))
    v.SetDrill(int(VIA_DRILL * 1e6))
    v.SetNetCode(nc)
    board.Add(v)
    add_item(v)
    return v


def add_track(x1, y1, x2, y2, ly, nc):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(int(x1 * 1e6), int(y1 * 1e6)))
    t.SetEnd(pcbnew.VECTOR2I(int(x2 * 1e6), int(y2 * 1e6)))
    t.SetWidth(int(TW * 1e6))
    t.SetLayer(ly)
    t.SetNetCode(nc)
    board.Add(t)
    add_item(t)


def zone_fill_pt(z, nc, tx=None, ty=None):
    """a point inside the zone's filled area on one of its layers,
    near (tx,ty) if given."""
    zlayers = set(z.GetLayerSet().Seq()) & set(CU)
    best = None
    for l in sorted(zlayers):
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
                    d = 0 if tx is None else math.hypot(gx - tx,
                                                        gy - ty)
                    if best is None or d < best[0]:
                        best = (d, gx, gy, l)
                gx += GS * 2
            gy += GS * 2
    if best:
        return best[1], best[2], best[3]
    return None


placed = 0
for x in drc.get('unconnected_items', []):
    descs = [i.get('description', '') for i in x.get('items', [])]
    if not any('GND' in d for d in descs):
        continue
    uids = [i.get('uuid') for i in x.get('items', [])]
    its = [zones_by_uuid.get(u) or tracks_by_uuid.get(u)
           or pads_by_uuid.get(u) for u in uids]
    its = [i for i in its if i is not None]
    if len(its) != 2:
        continue
    nc = its[0].GetNetCode()
    za = its[0] if isinstance(its[0], pcbnew.ZONE) else None
    zb = its[1] if isinstance(its[1], pcbnew.ZONE) else None
    pa = its[0] if isinstance(its[0], pcbnew.PAD) else None
    pb = its[1] if isinstance(its[1], pcbnew.PAD) else None

    if za is not None and zb is not None:
        # first: one via at a point inside BOTH zones' fills (cross-layer
        # pairs); otherwise a via per island + middle-layer track
        lsa = set(za.GetLayerSet().Seq()) & set(CU)
        lsb = set(zb.GetLayerSet().Seq()) & set(CU)
        done = False
        for l in sorted(lsa):
            try:
                pa_ = za.GetFilledPolysList(l)
            except Exception:
                continue
            if pa_ is None or pa_.IsEmpty():
                continue
            for l2 in sorted(lsb):
                try:
                    pb_ = zb.GetFilledPolysList(l2)
                except Exception:
                    continue
                if pb_ is None or pb_.IsEmpty():
                    continue
                # scan za's fill for a point also inside zb's fill
                bb = pa_.BBox()
                x0, y0 = bb.GetLeft() / 1e6, bb.GetTop() / 1e6
                x1, y1 = bb.GetRight() / 1e6, bb.GetBottom() / 1e6
                gx, gy = x0, y0
                while gy <= y1:
                    gx = x0
                    while gx <= x1:
                        pt = pcbnew.VECTOR2I(int(gx * 1e6), int(gy * 1e6))
                        if pa_.Collide(pt, 0) and pb_.Collide(pt, 0) and \
                                via_legal(gx, gy, nc):
                            add_via(gx, gy, nc)
                            placed += 1
                            print(f'zone pair: shared-fill via at '
                                  f'{gx:.2f},{gy:.2f}', flush=True)
                            done = True
                            break
                        gx += GS * 2
                    if done:
                        break
                    gy += GS * 2
                if done:
                    break
            if done:
                break
        if done:
            continue
        fa = zone_fill_pt(za, nc)
        fb = zone_fill_pt(zb, nc, *(fa[:2] if fa else (None, None)))
        if not fa or not fb:
            print('zone pair: no fill point')
            continue
        (ax, ay, al), (bx, by, bl) = fa, fb
        if not (via_legal(ax, ay, nc) and via_legal(bx, by, nc)):
            print('zone pair: via blocked')
            continue
        add_via(ax, ay, nc)
        add_via(bx, by, nc)
        add_track(ax, ay, bx, by, pcbnew.In1_Cu, nc)
        placed += 1
        print(f'zone pair stitched ({ax:.1f},{ay:.1f})-({bx:.1f},{by:.1f})',
              flush=True)
        continue

    if pa is not None or pb is not None:
        p = pa or pb
        px, py = p.GetPosition().x / 1e6, p.GetPosition().y / 1e6
        # rim via: annulus overlapping pad edge
        bb = p.GetBoundingBox()
        hw = max(bb.GetRight() / 1e6 - px, px - bb.GetLeft() / 1e6)
        hh = max(bb.GetBottom() / 1e6 - py, py - bb.GetTop() / 1e6)
        rad = max(hw, hh)
        try:
            psh = p.GetEffectiveShape(p.GetLayer())
        except Exception:
            psh = None
        done = False
        for r in (rad + 0.02, rad + 0.1, rad + 0.2):
            for k in range(24):
                a = k * math.pi / 12
                qx, qy = px + math.cos(a) * r, py + math.sin(a) * r
                if psh is not None and not psh.Collide(
                        pcbnew.VECTOR2I(int(qx * 1e6), int(qy * 1e6)),
                        int((VIA_D / 2) * 1e6)):
                    continue
                if not via_legal(qx, qy, nc):
                    continue
                add_via(qx, qy, nc)
                placed += 1
                ref = p.GetParentFootprint().GetReference() + '.' + \
                    str(p.GetNumber())
                print(f'{ref}: rim via at {qx:.2f},{qy:.2f}', flush=True)
                done = True
                break
            if done:
                break
        if not done:
            # via-in-pad: the pad is own-net so hit() skips it; works
            # whenever neighbours clear the annulus on all layers
            ref = p.GetParentFootprint().GetReference() + '.' + \
                str(p.GetNumber())
            for i in (-1, 0, 1):
                for j in (-1, 0, 1):
                    qx, qy = px + i * GS, py + j * GS
                    if via_legal(qx, qy, nc):
                        add_via(qx, qy, nc)
                        placed += 1
                        print(f'{ref}: via-in-pad at {qx:.2f},{qy:.2f}',
                              flush=True)
                        done = True
                        break
                if done:
                    break
            if not done:
                print(f'{ref}: no rim-via site', flush=True)

print(f'vias/stitches placed: {placed}', flush=True)
zones = [z for z in board.Zones() if not z.GetIsRuleArea()]
try:
    pcbnew.ZONE_FILLER(board).Fill(zones)
except Exception as e:
    print('fill failed:', e)
pcbnew.SaveBoard(PCB, board)
print('saved:', PCB, flush=True)
