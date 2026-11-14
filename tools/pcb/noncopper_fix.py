#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""noncopper_fix.py — footprints/mechanical DRC fixes, driven by the
kicad-cli report:

  * drill_out_of_range  -> bump sub-min drills to the board minimum
  * starved_thermal     -> set flagged pads to full zone connection
  * courtyards_overlap  -> nudge the smaller footprint clear
  * silk_overlap        -> shrink the flagged reference text
  * hole_to_hole        -> delete the second via of each too-close pair

usage: noncopper_fix.py board.kicad_pcb drc.json
"""
import sys
import json
import math
import pcbnew

PCB, DRC = sys.argv[1], sys.argv[2]
board = pcbnew.LoadBoard(PCB)
drc = json.load(open(DRC))
CU = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
MIN_DRILL = 300000

tracks_by_uuid = {t.m_Uuid.AsString(): t for t in board.GetTracks()}
pads_by_uuid = {}
fp_by_ref = {}
for fp in board.GetFootprints():
    fp_by_ref[fp.GetReference()] = fp
    for p in fp.Pads():
        pads_by_uuid[p.m_Uuid.AsString()] = p
zones_by_uuid = {z.m_Uuid.AsString(): z for z in board.Zones()}
item_of = {}
item_of.update(tracks_by_uuid)
item_of.update(pads_by_uuid)
item_of.update(zones_by_uuid)

fixed = 0

# ---- drills below fab minimum ----------------------------------------
for v in drc.get('violations', []):
    if v['type'] != 'drill_out_of_range':
        continue
    for i in v.get('items', []):
        p = pads_by_uuid.get(i.get('uuid'))
        if p is None:
            continue
        ds = p.GetDrillSize()
        if ds.x < MIN_DRILL:
            p.SetDrillSize(pcbnew.VECTOR2I(MIN_DRILL, MIN_DRILL))
            fixed += 1
            fp = p.GetParentFootprint()
            print(f'{fp.GetReference()}.{p.GetNumber()}: drill '
                  f'{ds.x/1e6:.2f}->0.30', flush=True)

# ---- starved thermal: solid pour connection for flagged pads ---------
for v in drc.get('violations', []):
    if v['type'] != 'starved_thermal':
        continue
    for i in v.get('items', []):
        p = pads_by_uuid.get(i.get('uuid'))
        if p is None:
            continue
        p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
        fixed += 1
        fp = p.GetParentFootprint()
        print(f'{fp.GetReference()}.{p.GetNumber()}: zone conn -> FULL',
              flush=True)

# ---- courtyard overlap: nudge the smaller footprint ------------------
for v in drc.get('violations', []):
    if v['type'] != 'courtyards_overlap':
        continue
    fps = []
    for i in v.get('items', []):
        ref = i.get('description', '').split()[-1]
        fp = fp_by_ref.get(ref)
        if fp is not None:
            fps.append(fp)
    if len(fps) != 2:
        continue
    a, b = fps
    ba = a.GetBoundingBox(False, False)
    bb = b.GetBoundingBox(False, False)
    ax, ay = a.GetPosition().x / 1e6, a.GetPosition().y / 1e6
    bx, by = b.GetPosition().x / 1e6, b.GetPosition().y / 1e6
    oy = min(ba.GetBottom(), bb.GetBottom()) / 1e6 - \
        max(ba.GetTop(), bb.GetTop()) / 1e6
    ox = min(ba.GetRight(), bb.GetRight()) / 1e6 - \
        max(ba.GetLeft(), bb.GetLeft()) / 1e6
    if ox <= 0 or oy <= 0:
        continue
    if oy <= ox:
        ny = ay + (oy + 0.2) * (1 if ay > by else -1)
        a.SetPosition(pcbnew.VECTOR2I(int(ax * 1e6), int(ny * 1e6)))
        print(f'{a.GetReference()}: nudged y {ay:.2f}->{ny:.2f}', flush=True)
    else:
        nx = ax + (ox + 0.2) * (1 if ax > bx else -1)
        a.SetPosition(pcbnew.VECTOR2I(int(nx * 1e6), int(ay * 1e6)))
        print(f'{a.GetReference()}: nudged x {ax:.2f}->{nx:.2f}', flush=True)
    fixed += 1

# ---- silk overlaps: shrink flagged reference fields ------------------
for v in drc.get('violations', []):
    if v['type'] != 'silk_overlap':
        continue
    for i in v.get('items', []):
        d = i.get('description', '')
        if 'Reference field of' in d:
            ref = d.rsplit(' ', 1)[-1]
            fp = fp_by_ref.get(ref)
            if fp is not None:
                r = fp.Reference()
                r.SetTextWidth(400000)
                r.SetTextHeight(400000)
                fixed += 1
                print(f'{ref}: silk shrunk', flush=True)

# ---- hole_to_hole: delete second via of each close pair --------------
for v in drc.get('violations', []):
    if v['type'] != 'hole_to_hole':
        continue
    vias = [tracks_by_uuid.get(i.get('uuid'))
            for i in v.get('items', [])]
    vias = [x for x in vias
            if x is not None and isinstance(x, pcbnew.PCB_VIA)]
    if len(vias) == 2:
        board.Remove(vias[1])
        fixed += 1
        print('removed close via', flush=True)

print(f'noncopper fixed: {fixed}', flush=True)
zones = [z for z in board.Zones() if not z.GetIsRuleArea()]
try:
    pcbnew.ZONE_FILLER(board).Fill(zones)
except Exception:
    pass
pcbnew.SaveBoard(PCB, board)
print('saved:', PCB, flush=True)
