# SPDX-License-Identifier: AGPL-3.0-or-later
"""Generate the EcoCell universal-node carrier PCB with pcbnew.

Run inside KiCad's Python (flatpak):

    flatpak run --command=python3 org.kicad.KiCad tools/pcb/gen_carrier.py

Outputs hardware/pcb/ecocell-carrier.kicad_pcb — routed 2-layer board,
GND zone on B.Cu, all head connectors populated (universal-node spec).
"""

import os
import pcbnew
from pcbnew import VECTOR2I_MM

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "hardware", "pcb", "ecocell-carrier.kicad_pcb")
FPLIB = "/app/extensions/Library/Footprints/footprints"

TRACK = 0.5      # signal trace width, mm
PWR = 0.8        # power trace width
BOARD_W, BOARD_H = 100.0, 80.0

board = pcbnew.NewBoard(os.path.abspath(OUT))

# ---------------------------------------------------------------- nets
NETS = {}
for i, name in enumerate([
        "GND", "+3V3", "+5V",
        "D0_PIR", "D1_HYDRO", "D2_ULTRA", "D3_EMIT", "EMIT_GATE",
        "EMIT_SW", "SDA", "SCL", "TX_D6", "RX_D7",
        "SCK_D8", "MISO_D9", "MOSI_D10",
        "VIN", "VPROT", "LEDPWR"], start=1):
    n = pcbnew.NETINFO_ITEM(board, name)
    n.SetNetCode(i)
    board.Add(n)
    NETS[name] = n

def net(name):
    return NETS[name]

# ---------------------------------------------------------------- edges
def edge(p1, p2):
    s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(VECTOR2I_MM(*p1))
    s.SetEnd(VECTOR2I_MM(*p2))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(pcbnew.FromMM(0.1))
    board.Add(s)

for a, b in [((0, 0), (BOARD_W, 0)), ((BOARD_W, 0), (BOARD_W, BOARD_H)),
             ((BOARD_W, BOARD_H), (0, BOARD_H)), ((0, BOARD_H), (0, 0))]:
    edge(a, b)

# ---------------------------------------------------------- footprints
FPS = {}
def place(libdir, fpname, ref, value, pos, rot=0.0, pin_nets=None):
    fp = pcbnew.FootprintLoad(os.path.join(FPLIB, libdir), fpname)
    fp.SetReference(ref)
    fp.SetValue(value)
    fp.SetPosition(VECTOR2I_MM(*pos))
    if rot:
        try:
            fp.SetOrientationDegrees(rot)
        except AttributeError:
            fp.SetOrientation(pcbnew.EDA_ANGLE(rot, pcbnew.DEGREES_T))
    board.Add(fp)
    for num, n in (pin_nets or {}).items():
        fp.FindPadByNumber(num).SetNet(net(n))
    FPS[ref] = fp
    return fp

def pad_xy(ref, num):
    p = FPS[ref].FindPadByNumber(num).GetPosition()
    return (pcbnew.ToMM(p.x), pcbnew.ToMM(p.y))

HDR = "Connector_PinHeader_2.54mm.pretty"
SCK = "Connector_PinSocket_2.54mm.pretty"

# XIAO socket: two 1x7 sockets, 17.78mm apart, USB at top.
# Left column top->bottom: D0..D6 ; right column: 5V GND 3V3 D10 D9 D8 D7
place(SCK, "PinSocket_1x07_P2.54mm_Vertical", "U1A", "XIAO-L", (40, 20),
      pin_nets={"1": "D0_PIR", "2": "D1_HYDRO", "3": "D2_ULTRA",
                "4": "D3_EMIT", "5": "SDA", "6": "SCL", "7": "TX_D6"})
place(SCK, "PinSocket_1x07_P2.54mm_Vertical", "U1B", "XIAO-R", (57.78, 20),
      pin_nets={"1": "+5V", "2": "GND", "3": "+3V3",
                "4": "MOSI_D10", "5": "MISO_D9", "6": "SCK_D8",
                "7": "RX_D7"})

# left-edge sensor headers (pin order top->bottom: SIG, 3V3, GND)
place(HDR, "PinHeader_1x03_P2.54mm_Vertical", "J1", "PIR", (10, 20),
      pin_nets={"1": "D0_PIR", "2": "+3V3", "3": "GND"})
place(HDR, "PinHeader_1x03_P2.54mm_Vertical", "J2", "HYDRO", (10, 30),
      pin_nets={"1": "D1_HYDRO", "2": "+3V3", "3": "GND"})
place(HDR, "PinHeader_1x03_P2.54mm_Vertical", "J3", "ULTRA", (10, 40),
      pin_nets={"1": "D2_ULTRA", "2": "+3V3", "3": "GND"})

# right-edge I2C headers (3V3, GND, SDA, SCL)
for ref, y, val in [("J4", 25, "I2C-BME280"), ("J5", 38, "I2C-BH1750"),
                    ("J6", 51, "I2C-AD7746")]:
    place(HDR, "PinHeader_1x04_P2.54mm_Vertical", ref, val, (90, y),
          pin_nets={"1": "+3V3", "2": "GND", "3": "SDA", "4": "SCL"})

# UART/backhaul column (RX, TX, GND, 5V) at x=40
place(HDR, "PinHeader_1x04_P2.54mm_Vertical", "J7", "UART", (40, 64),
      pin_nets={"1": "RX_D7", "2": "TX_D6", "3": "GND", "4": "+5V"})

# SPI/spare along bottom edge, rotated so pins run +x
# (3V3, GND, MOSI, MISO, SCK)
place(HDR, "PinHeader_1x05_P2.54mm_Vertical", "J8", "SPI", (15, 70),
      rot=90, pin_nets={"1": "+3V3", "2": "GND", "3": "MOSI_D10",
                        "4": "MISO_D9", "5": "SCK_D8"})

# battery/5V input (GND, 5V) — p2 sits on the 5V trunk
place(HDR, "PinHeader_1x02_P2.54mm_Vertical", "J9", "5V-IN", (46, 75),
      pin_nets={"1": "GND", "2": "+5V"})
# emit transducer terminal (EMIT_SW, 3V3)
place(HDR, "PinHeader_1x02_P2.54mm_Vertical", "J10", "EMIT-40k", (64, 68),
      pin_nets={"1": "EMIT_SW", "2": "+3V3"})

# emit driver passives
place("Resistor_SMD.pretty", "R_0805_2012Metric", "R1", "100R", (42, 52),
      pin_nets={"1": "D3_EMIT", "2": "EMIT_GATE"})
place("Capacitor_SMD.pretty", "C_0805_2012Metric", "C1", "100nF", (63, 28),
      pin_nets={"1": "+3V3", "2": "GND"})
place("Package_TO_SOT_SMD.pretty", "SOT-23", "Q1", "2N7002", (50, 52),
      pin_nets={"1": "EMIT_GATE", "2": "GND", "3": "EMIT_SW"})
# flyback diode, rotated so cathode faces right (toward 3V3)
place("Diode_SMD.pretty", "D_SOD-123", "D1", "1N4148W", (56, 52), rot=180,
      pin_nets={"1": "+3V3", "2": "EMIT_SW"})

# --- production: protected 5V input + signal TVS + power LED + fiducials
TB = "TerminalBlock_Phoenix.pretty"
place(TB, "TerminalBlock_Phoenix_MKDS-1,5-2_1x02_P5.00mm_Horizontal",
      "J11", "5V-SCREW", (80, 74.5), pin_nets={"1": "VIN", "2": "GND"})
place("Fuse.pretty", "Fuse_1206_3216Metric", "F1", "0.75A", (74, 74.5),
      pin_nets={"1": "VPROT", "2": "VIN"})
# rail TVS: rot=180 puts cathode (pad1) at +2.0 -> VPROT side
place("Diode_SMD.pretty", "D_SMA", "D3", "SMAJ5.0A", (68, 76), rot=180,
      pin_nets={"1": "VPROT", "2": "GND"})
# series Schottky (reverse-polarity): pad1 cathode -> +5V, pad2 anode <- VPROT
place("Diode_SMD.pretty", "D_SMA", "D2", "SS14", (59, 74.5),
      pin_nets={"1": "+5V", "2": "VPROT"})
# signal TVS on the exposed head inputs (cathode pad1 -> SIG, anode -> GND)
for ref, y, snet, gndy in [("D4", 22.5, "D0_PIR", 25.08),
                           ("D5", 32.5, "D1_HYDRO", 35.08),
                           ("D6", 42.5, "D2_ULTRA", 45.08)]:
    place("Diode_SMD.pretty", "D_SOD-323", ref, "PESD5V0", (15.5, y),
          rot=270, pin_nets={"1": snet, "2": "GND"})
# power LED: 3V3 -> R2 -> LED anode, LED cathode -> GND
place("Resistor_SMD.pretty", "R_0805_2012Metric", "R2", "1k", (71.5, 20),
      pin_nets={"1": "+3V3", "2": "LEDPWR"})
place("LED_SMD.pretty", "LED_0805_2012Metric", "LED1", "PWR-GRN",
      (76, 20), rot=180, pin_nets={"1": "GND", "2": "LEDPWR"})
# fiducials for the PCBA line (pad has no pin number -> netless marker)
for i, pos in enumerate([(10, 10), (90, 10), (10, 66)], start=1):
    place("Fiducial.pretty", "Fiducial_1mm_Mask3mm", "FID%d" % i,
          "FID", pos)

# mounting holes
HOLES = [(5, 5), (95, 5), (5, 75), (95, 75)]
for i, pos in enumerate(HOLES, start=1):
    place("MountingHole.pretty", "MountingHole_3.2mm_M3",
          "H%d" % i, "M3", pos)

# --------------------------------------------------------------- tracks
def seg(pts, layer, width, netname):
    for a, b in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(VECTOR2I_MM(*a))
        t.SetEnd(VECTOR2I_MM(*b))
        t.SetWidth(pcbnew.FromMM(width))
        t.SetLayer(layer)
        t.SetNet(net(netname))
        board.Add(t)

def via(pos, netname):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(VECTOR2I_MM(*pos))
    v.SetDrill(pcbnew.FromMM(0.4))
    v.SetWidth(pcbnew.FromMM(0.8))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetNet(net(netname))
    board.Add(v)

F, B = pcbnew.F_Cu, pcbnew.B_Cu
J8P = {n: pad_xy("J8", n) for n in ("1", "2", "3", "4", "5")}
print("J8 pads:", J8P)

# --- F.Cu: left headers
seg([(40, 20), (10, 20)], F, TRACK, "D0_PIR")
seg([(40, 22.54), (10, 30)], F, TRACK, "D1_HYDRO")
seg([(40, 25.08), (10, 40)], F, TRACK, "D2_ULTRA")

# --- F.Cu: emit PWM -> R1 (exits diagonally, drops x=36, pad1 from below)
seg([(40, 27.62), (36, 29), (36, 54), (41.09, 54),
     pad_xy("R1", "1")], F, TRACK, "D3_EMIT")
seg([pad_xy("R1", "2"), pad_xy("Q1", "1")], F, TRACK, "EMIT_GATE")

# --- F.Cu: EMIT_SW (Q1 drain -> diode anode -> J10.1)
seg([pad_xy("Q1", "3"), (52.5, 52)], F, TRACK, "EMIT_SW")
seg([(52.5, 52), pad_xy("D1", "2")], F, TRACK, "EMIT_SW")
seg([(52.5, 52), (52.5, 66), (60, 66), (60, 68), (64, 68)], F, TRACK,
    "EMIT_SW")

# --- SDA: F.Cu feed, via-hop under the SCL trunk at x=82, trunk x=85
seg([(40, 30.16), (46, 30.16), (46, 37), (80, 37)], F, TRACK, "SDA")
via((80, 37), "SDA")
seg([(80, 37), (84, 37)], B, TRACK, "SDA")
via((84, 37), "SDA")
seg([(84, 37), (85, 37)], F, TRACK, "SDA")
seg([(85, 30.08), (85, 37)], F, TRACK, "SDA")
seg([(85, 37), (85, 43.08)], F, TRACK, "SDA")
seg([(85, 43.08), (85, 56.08)], F, TRACK, "SDA")
for y in (30.08, 43.08, 56.08):
    seg([(85, y), (90, y)], F, TRACK, "SDA")

# --- SCL: F.Cu feed + trunk (x=82); stubs hop to B.Cu via 3 vias
seg([(40, 32.7), (43.5, 32.7), (43.5, 50), (82, 50)], F, TRACK, "SCL")
seg([(82, 32.62), (82, 45.62)], F, TRACK, "SCL")
seg([(82, 45.62), (82, 50)], F, TRACK, "SCL")
seg([(82, 50), (82, 58.62)], F, TRACK, "SCL")
for y in (32.62, 45.62, 58.62):
    seg([(82, y), (83.5, y)], F, TRACK, "SCL")
    via((83.5, y), "SCL")
    seg([(83.5, y), (90, y)], B, TRACK, "SCL")

# --- B.Cu: UART TX around J8's left end, enters J7.2 from the left
seg([(40, 35.24), (13.5, 35.24), (13.5, 72.5), (38.5, 72.5),
     (38.5, 66.54), (40, 66.54)], B, TRACK, "TX_D6")

# --- F.Cu: 3V3 tree
seg([(57.78, 25.08), (62, 25.08), (62, 13), (8, 13), (8, 42.54)],
    F, PWR, "+3V3")
for y in (22.54, 32.54, 42.54):
    seg([(8, y), (10, y)], F, PWR, "+3V3")
seg([(62, 15), (95, 15)], F, PWR, "+3V3")
seg([(95, 15), (95, 25), (95, 38), (95, 51), (95, 61)], F, PWR, "+3V3")
for y in (25, 38, 51):
    seg([(95, y), (90, y)], F, PWR, "+3V3")
seg([(95, 61), (59, 61)], F, PWR, "+3V3")
seg([(70, 61), (70, 70.54), (64, 70.54)], F, PWR, "+3V3")
seg([(8, 42.54), (8, 70), (15, 70)], F, PWR, "+3V3")
seg([(62, 25.08), (62, 28), pad_xy("C1", "1")], F, TRACK, "+3V3")
cx, cy = pad_xy("D1", "1")           # cathode (rot180: pad1 lands right)
seg([(cx, cy), (59, cy), (59, 61), (70, 61)], F, TRACK, "+3V3")

# --- B.Cu: 5V perimeter (XIAO 5V -> J9.2 trunk + J7.1 via x=58 feed)
seg([(57.78, 20), (57.78, 16), (97.5, 16), (97.5, 77.54), (46, 77.54)],
    B, PWR, "+5V")
seg([(46, 77.54), (48, 77.54), (48, 73.4), (39.5, 73.4),
     (39.5, 71.62), (40, 71.62)], B, PWR, "+5V")

# --- B.Cu: RX_D7 -> J7.1 (top pin)
seg([(57.78, 35.24), (57.78, 51), (46, 51), (46, 62), (40, 62),
     (40, 64)], B, TRACK, "RX_D7")

# --- B.Cu: SPI fan (nested drops; stubs end at J8 pads)
mosi = J8P["3"]; miso = J8P["4"]; sck = J8P["5"]
seg([(57.78, 27.62), (56, 27.62), (56, 18), (45, 18), (45, 44),
     (mosi[0], 44), (mosi[0], mosi[1])], B, TRACK, "MOSI_D10")
seg([(57.78, 30.16), (54, 30.16), (54, 46.5), (25, 46.5), (25, 63),
     (miso[0], 63), (miso[0], miso[1])], B, TRACK, "MISO_D9")
seg([(57.78, 32.7), (56, 32.7), (56, 49), (26, 49), (26, 65.5),
     (sck[0], 65.5), (sck[0], sck[1])], B, TRACK, "SCK_D8")

# --- GND backbone (B.Cu trunk + F.Cu hops over walled pockets)
# B.Cu: U1B GND -> x=60.5 spine -> top y=15 bus -> x=12 left drop
seg([(57.78, 22.54), (60.5, 22.54)], B, TRACK, "GND")
seg([(60.5, 17.5), (60.5, 75)], B, TRACK, "GND")
seg([(12, 15), (60.5, 15)], B, TRACK, "GND")
via((60.5, 15), "GND")
seg([(60.5, 15), (60.5, 17.5)], F, TRACK, "GND")
via((60.5, 17.5), "GND")
seg([(12, 15), (12, 74)], B, TRACK, "GND")
# J4-J6 grounds: stubs -> x=92.5 drop -> y=72 back to spine
for y in (27.54, 40.54, 53.54):
    seg([(90, y), (92.5, y)], B, TRACK, "GND")
seg([(92.5, 27.54), (92.5, 72)], B, TRACK, "GND")
seg([(92.5, 72), (60.5, 72)], B, TRACK, "GND")
# C1 via -> B.Cu x=70 drop to spine
c2x, c2y = pad_xy("C1", "2")
seg([(c2x, c2y), (65.5, 29.5)], F, TRACK, "GND")
via((65.5, 29.5), "GND")
seg([(65.5, 29.5), (70, 29.5), (70, 60.5), (60.5, 60.5)], B, TRACK,
    "GND")
# J8.2: F.Cu escape below pad row -> via -> x=12 spine
seg([(17.54, 70), (17.54, 74), (15, 74)], F, TRACK, "GND")
via((15, 74), "GND")
seg([(15, 74), (12, 74)], B, TRACK, "GND")
# J1-J3 grounds: short F.Cu stubs -> vias onto x=12 spine
for y in (25.08, 35.08, 45.08):
    seg([(10, y), (12, y)], F, TRACK, "GND")
    via((12, y), "GND")
# J7.3 + J9.1: F.Cu run along the left, via at (38.5,60) outside the
# B.Cu pocket -> lands in the main fill
seg([(40, 69.08), (38.5, 69.08), (38.5, 75), (46, 75)], F, TRACK, "GND")
seg([(38.5, 69.08), (38.5, 60)], F, TRACK, "GND")
via((38.5, 60), "GND")
qx, qy = pad_xy("Q1", "2")
seg([(qx, qy), (47.5, 54.5), (44, 56), (44, 72), (42, 72), (42, 74),
     (38.5, 74)], F, TRACK, "GND")

# --- protected 5V input chain: J11 -> F1 -> D3 TVS -> D2 Schottky -> trunk
seg([(80, 74.5), (75.4, 74.5)], F, PWR, "VIN")        # J11.1 -> F1.2
seg([(72.6, 74.5), (61, 74.5)], F, PWR, "VPROT")      # F1.1 -> D2.2
seg([(70, 76), (70, 74.5)], F, TRACK, "VPROT")        # D3 cathode tap
seg([(66, 76), (63.5, 76.2)], F, TRACK, "GND")        # D3 anode -> via
via((63.5, 76.2), "GND")
seg([(63.5, 76.2), (60.5, 75)], B, TRACK, "GND")      # joins spine end
seg([(57, 74.5), (57, 77.54)], F, PWR, "+5V")         # D2.1 -> via
via((57, 77.54), "+5V")                               # onto the B.Cu trunk
seg([(85, 74.5), (86.5, 75.5)], F, TRACK, "GND")      # J11.2 -> via
via((86.5, 75.5), "GND")
seg([(86.5, 75.5), (86.5, 72)], B, TRACK, "GND")

# --- signal TVS stubs (pad_xy picks up the actual rotated pad spots)
for ref, sig_y, gnd_y, snet in [("D4", 20, 25.08, "D0_PIR"),
                                ("D5", 30, 35.08, "D1_HYDRO"),
                                ("D6", 40, 45.08, "D2_ULTRA")]:
    cx, cy = pad_xy(ref, "1")
    ax, ay = pad_xy(ref, "2")
    seg([(cx, cy), (cx, sig_y), (10, sig_y)], F, TRACK, snet)
    seg([(ax, ay), (ax, gnd_y), (10, gnd_y)], F, TRACK, "GND")

# --- power LED chain: 3V3 -> R2 -> LED anode; cathode -> GND via spine
seg([(70.56, 15), (70.56, 20)], F, TRACK, "+3V3")
seg([(72.44, 20), (75.06, 20)], F, TRACK, "LEDPWR")
seg([(76.94, 20), (76.94, 22.5)], F, TRACK, "GND")
via((76.94, 22.5), "GND")
seg([(76.94, 22.5), (76.94, 24), (60.5, 24)], B, TRACK, "GND")

# --------------------------------------------------------------- zones
# GND plane on B.Cu
zone = pcbnew.ZONE(board)
zone.SetLayer(pcbnew.B_Cu)
zone.SetNet(net("GND"))
zone.SetMinThickness(pcbnew.FromMM(0.25))
zone.SetLocalClearance(pcbnew.FromMM(0.35))
try:
    zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
except AttributeError:
    pass
outline = zone.Outline()
outline.NewOutline()
for p in [(0.5, 0.5), (BOARD_W - 0.5, 0.5), (BOARD_W - 0.5, BOARD_H - 0.5),
          (0.5, BOARD_H - 0.5)]:
    outline.Append(VECTOR2I_MM(*p))
board.Add(zone)

# keepout rule areas around mounting holes: fill only, copper allowed
for hx, hy in HOLES:
    k = pcbnew.ZONE(board)
    k.SetIsRuleArea(True)
    k.SetDoNotAllowTracks(False)
    k.SetDoNotAllowVias(False)
    k.SetDoNotAllowPads(False)
    k.SetDoNotAllowFootprints(False)
    k.SetDoNotAllowZoneFills(True)
    ls = pcbnew.LSET()
    ls.AddLayer(pcbnew.B_Cu)
    k.SetLayerSet(ls)
    ko = k.Outline()
    ko.NewOutline()
    for p in [(hx - 2.6, hy - 2.6), (hx + 2.6, hy - 2.6),
              (hx + 2.6, hy + 2.6), (hx - 2.6, hy + 2.6)]:
        ko.Append(VECTOR2I_MM(*p))
    board.Add(k)

# ------------------------------------------------------------ silk text
def text(s, pos, size=1.2, layer=pcbnew.F_SilkS):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s)
    t.SetTextPos(VECTOR2I_MM(*pos))
    t.SetLayer(layer)
    t.SetTextSize(VECTOR2I_MM(size, size))
    t.SetTextThickness(pcbnew.FromMM(0.2))
    board.Add(t)

text("EcoCell carrier v1 - living-resources AGPL", (50, 7), 1.4)
text("XIAO-S3 USB-up", (44, 13), 1.0)
text("J1 PIR / J2 HYDRO / J3 ULTRA", (16, 55), 1.0)
text("I2C x3", (86, 62), 1.0)
text("EMIT: consent-gated", (52, 44), 1.0)
text("5V-IN protected", (58, 78.8), 0.9)
text("PWR", (68, 17), 0.9)

# -------------------------------------------------------------- fill+save
try:
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
except Exception as e:
    print("zone fill deferred to export:", e)

board.Save(os.path.abspath(OUT))
print("wrote", os.path.abspath(OUT))
