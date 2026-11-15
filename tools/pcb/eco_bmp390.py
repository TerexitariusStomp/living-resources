# SPDX-License-Identifier: AGPL-3.0-or-later
"""ECO: U_PRES was placed as Bosch_LGA-8 (BME280 land pattern) but the part
is a BMP390 — a 10-pin LGA 2x2mm with a completely different pinout.

Swaps the footprint to EcoCell:BMP390_LGA-10_2x2mm, repins the pads to the
datasheet pinout (1=VDDIO, 2=SCK, 3/8/9=VSS, 4=SDI, 5=SDO, 6=CSB,
7=INT/NC, 10=VDD), and relocates the part to (109.5, 58.5) — the old site
at (102, 59) is boxed in by the SCL/SDA/SD_CS inner-layer stub field and
the SCL bus-bridge via at (102.3, 58.5), which carries U_ENV's SCL and
must not be disturbed.  The pocket x108-112 / y56-62 is empty on F.Cu;
the only inner copper is the SPI2_MOSI/SCK trunks on In2.

Reroutes (all new copper F.Cu unless noted):

  SCL  pad2  <- F.Cu branch off the x103.56 zigzag column at y55.5
  SDA  pad4  <- F.Cu from the existing SDA via at (103.08, 57.96),
                east along y56.5, around the south side
  +3V3 pad10 <- via(109.9, 56.5)  to In2 plane; pad1 links to pad10
  +3V3 pad6  <- via(111.1, 58.1)  to In2 plane
  GND  pad3  -> existing stitch via(108.22, 60.98)
  GND  pad5  -> new via(110.75, 59.45)
  GND  pads 8,9 -> pad-row link + new via(110.9, 57.2)

Stale F.Cu stubs at the old pad sites are removed; the bus feed, bridge
via, and every other net's copper is untouched.

    python3 tools/pcb/eco_bmp390.py
"""
import os
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
ELEC = os.path.join(HERE, "..", "..", "hardware", "release", "electrical")
BRD = os.path.join(ELEC, "ecocell-ocean.kicad_pcb")
FPLIB = os.path.join(ELEC, "EcoCell.pretty")

board = pcbnew.LoadBoard(os.path.abspath(BRD))
NETS = {n.GetNetname(): n for n in board.GetNetsByName().values()}

def net(name):
    return NETS[name]

V = pcbnew.VECTOR2I_MM

# --- swap footprint -------------------------------------------------------
old = None
for f in board.Footprints():
    if f.GetReference() == "U_PRES":
        old = f
        break
board.Remove(old)

fp = pcbnew.FootprintLoad(FPLIB, "BMP390_LGA-10_2x2mm")
fp.SetReference("U_PRES")
fp.SetValue("BMP390")
fp.SetPosition(V(109.5, 58.5))
board.Add(fp)

PIN_NET = {"1": "+3V3",  "2": "I2C_SCL", "3": "GND", "4": "I2C_SDA",
           "5": "GND",   "6": "+3V3",    "7": None, "8": "GND",
           "9": "GND",  "10": "+3V3"}
padpos = {}
for p in fp.Pads():
    n = PIN_NET.get(p.GetNumber())
    if n:
        p.SetNet(net(n))
    padpos[p.GetNumber()] = (round(pcbnew.ToMM(p.GetPosition().x), 3),
                             round(pcbnew.ToMM(p.GetPosition().y), 3))
print("new pads:", padpos)

# --- remove stale F.Cu stubs that terminated on the old LGA-8 pads --------
OLD = [(101.025, 57.975), (101.675, 57.975),
       (102.325, 57.975), (102.975, 57.975)]
dead = {}
for t in board.Tracks():
    if isinstance(t, pcbnew.PCB_VIA) or not isinstance(t, pcbnew.PCB_TRACK):
        continue
    if t.GetLayer() != pcbnew.F_Cu:
        continue
    for e in (t.GetStart(), t.GetEnd()):
        ex, ey = pcbnew.ToMM(e.x), pcbnew.ToMM(e.y)
        for ox, oy in OLD:
            if abs(ex - ox) < 0.45 and abs(ey - oy) < 0.45:
                dead[t.m_Uuid.AsString()] = t
for t in dead.values():
    board.Remove(t)
print("removed %d stale segments" % len(dead))

# Orphaned stitch via at (100.95,58.05) carried GND to old pad 1 — pin it
# back to GND explicitly so it can't pick up the wrong net.
for t in board.Tracks():
    if isinstance(t, pcbnew.PCB_VIA):
        p = t.GetPosition()
        if abs(pcbnew.ToMM(p.x) - 100.95) < 0.05 and \
                abs(pcbnew.ToMM(p.y) - 58.05) < 0.05:
            t.SetNet(net("GND"))

# --- reroute --------------------------------------------------------------
def seg(pts, layer, width, netname):
    for a, b in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(V(*a)); t.SetEnd(V(*b))
        t.SetWidth(pcbnew.FromMM(width))
        t.SetLayer(layer); t.SetNet(net(netname))
        board.Add(t)

def via(pos, netname):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(V(*pos))
    v.SetDrill(pcbnew.FromMM(0.4)); v.SetWidth(pcbnew.FromMM(0.8))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetNet(net(netname))
    board.Add(v)

F, B_, TW = pcbnew.F_Cu, pcbnew.B_Cu, 0.25

# Restore the SCL bus bridge: the deleted stubs linked the F.Cu zigzag
# (U_ENV's feed) to the bridge via at (102.3,58.5) -> In2 west trunk.
seg([(102.48, 57.48), (102.36, 57.6), (102.3, 58.1)], F, TW, "I2C_SCL")

# SCL pad2 (108.71,58.75): tap the SCL bridge via at (102.3,58.5) itself
# and run east below the SDA corridor — all F.Cu, no new vias.
seg([(102.3, 58.5), (102.3, 58.75), (107.9, 58.75), (108.71, 58.75)],
    F, TW, "I2C_SCL")

# SDA pad4 (109.5,59.29): from the existing SDA via, east along y56.0,
# down the x112.3 corridor, west under the part.
seg([(103.08, 57.96), (104.1, 57.96), (104.1, 56.0), (112.3, 56.0),
     (112.3, 60.3), (109.5, 60.3), (109.5, 59.29)], F, TW, "I2C_SDA")

# +3V3: pad10 (109,57.71) north to via(109.7,56.8); pad1 links to pad10;
# pad6 (110.29,58.75) east to via(111.1,58.5).
seg([(109.0, 57.71), (109.0, 57.2), (109.7, 57.2), (109.7, 56.8)],
    F, TW, "+3V3")
seg([(108.71, 58.25), (108.71, 57.9), (109.0, 57.71)], F, TW, "+3V3")
seg([(110.29, 58.75), (111.1, 58.75), (111.1, 58.5)], F, TW, "+3V3")
via((109.7, 56.8), "+3V3")
via((111.1, 58.5), "+3V3")

# GND: pad3 west-south to the existing stitch via at (108.22,60.98);
# pad5 to a new via at (110.75,59.55); pads 9->8 row link + via(110.9,57.3).
seg([(109.0, 59.29), (109.0, 59.8), (108.22, 59.8), (108.22, 60.98)],
    F, TW, "GND")
seg([(110.0, 59.29), (110.0, 59.55), (110.75, 59.55)], F, TW, "GND")
seg([(109.5, 57.71), (110.0, 57.71), (110.9, 57.71), (110.9, 57.3)],
    F, TW, "GND")
via((110.75, 59.55), "GND")
via((110.9, 57.3), "GND")

pcbnew.ZONE_FILLER(board).Fill(board.Zones())
board.Save(os.path.abspath(BRD))
print("ECO applied")
