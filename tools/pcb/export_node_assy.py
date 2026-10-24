# SPDX-License-Identifier: AGPL-3.0-or-later
"""Export manufacturing BOM + pick-and-place for the EcoCell One board."""
import pcbnew, csv, os
b = pcbnew.LoadBoard('hardware/pcb/ecocell-node.kicad_pcb')
rows_bom, rows_cpl = [], []
for f in b.GetFootprints():
    ref = f.GetReference()
    if ref.startswith(('H','FID')): continue
    pos = f.GetPosition(); rot = f.GetOrientation().AsDegrees()
    attr = f.GetAttributes()
    smd = bool(attr & pcbnew.FP_SMD) and not (attr & pcbnew.FP_THROUGH_HOLE)
    rows_bom.append((ref, f.GetValue(), str(f.GetFPID().GetLibItemName())))
    if smd:
        rows_cpl.append((ref, f.GetValue(), str(f.GetFPID().GetLibItemName()),
                         round(pos.x/1e6,3), round(pos.y/1e6,3), round(rot,1), 'top'))
with open('hardware/pcb/assembly/ecocell-node-bom.csv','w',newline='') as fh:
    w=csv.writer(fh); w.writerow(['Reference','Value','Footprint'])
    for r in sorted(rows_bom): w.writerow(r)
with open('hardware/pcb/assembly/ecocell-node-cpl.csv','w',newline='') as fh:
    w=csv.writer(fh); w.writerow(['Designator','Val','Package','Mid X','Mid Y','Rotation','Layer'])
    for r in sorted(rows_cpl): w.writerow(r)
print(len(rows_bom),'bom rows,',len(rows_cpl),'smt parts')
