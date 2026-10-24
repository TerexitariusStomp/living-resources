# SPDX-License-Identifier: AGPL-3.0-or-later
"""Export manufacturing BOM + CPL from the generated carrier board."""
import pcbnew, csv
b = pcbnew.LoadBoard("/home/terex/CascadeProjects/living-resources/hardware/pcb/ecocell-carrier.kicad_pcb")
rows, cpl = [], []
for fp in b.GetFootprints():
    ref = fp.GetReference()
    if ref.startswith(("H", "FID")):
        continue
    smt = fp.GetAttributes() & pcbnew.FP_SMD and not fp.GetAttributes() & pcbnew.FP_THROUGH_HOLE
    pos = fp.GetPosition()
    x, y = pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y)
    pkg = fp.GetFPID().GetLibItemName()
    layer = "top" if not fp.IsFlipped() else "bottom"
    rows.append([ref, fp.GetValue(), pkg, layer,
                 "SMT - PCBA" if smt else "THT - hand solder"])
    if smt:
        cpl.append([ref, fp.GetValue(), pkg, round(x, 2), round(y, 2),
                    fp.GetOrientationDegrees(), layer])
rows.sort(key=lambda r: (r[0][0], int("".join(c for c in r[0] if c.isdigit()))))
with open("/home/terex/CascadeProjects/living-resources/hardware/pcb/assembly/ecocell-carrier-bom.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Designator", "Val", "Package", "Layer", "Notes"])
    w.writerows(rows)
with open("/home/terex/CascadeProjects/living-resources/hardware/pcb/assembly/ecocell-carrier-cpl.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Designator", "Val", "Package", "Mid X", "Mid Y", "Rotation", "Layer"])
    w.writerows(sorted(cpl))
print("BOM:", len(rows), "CPL:", len(cpl))
