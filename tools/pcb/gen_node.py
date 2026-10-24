# SPDX-License-Identifier: AGPL-3.0-or-later
"""Generate the EcoCell One integrated-node PCB with pcbnew.

Run inside KiCad's Python (flatpak):

    flatpak run --command=python3 org.kicad.KiCad tools/pcb/gen_node.py

Outputs hardware/pcb/ecocell-node.kicad_pcb — routed 2-layer board,
GND zone on B.Cu. Unlike gen_carrier.py (socketed carrier), this board
is the single-item variant: XIAO + E22 LoRa + BME280/BH1750/AD7746 +
charge/boost power are all SMD-reflowed by the fab. Only external
transducer heads, battery and enclosure remain off-board — by physics,
not by omission.
"""

import os
import pcbnew
from pcbnew import VECTOR2I_MM

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "hardware", "pcb", "ecocell-node.kicad_pcb")
FPLIB = "/app/extensions/Library/Footprints/footprints"

TRACK = 0.5      # signal trace width, mm
PWR = 0.8        # power trace width
BOARD_W, BOARD_H = 100.0, 100.0

board = pcbnew.NewBoard(os.path.abspath(OUT))
# fine-pitch parts (0.65mm LGA/TSSOP) can't keep mask slivers between
# pads — Seeed fabs these parts routinely with mask dams omitted
board.GetDesignSettings().m_SolderMaskMinWidth = pcbnew.FromMM(0)

# ---------------------------------------------------------------- nets
NETS = {}
for i, name in enumerate([
        "GND", "+3V3", "+5V",
        "D0_PIR", "D1_HYDRO", "D2_ULTRA", "D3_EMIT", "EMIT_GATE",
        "EMIT_SW", "SDA", "SCL", "TX_D6", "RX_D7",
        "SCK_D8", "MISO_D9", "MOSI_D10",
        "VIN", "VPROT", "LEDPWR",
        "VBATT", "VBOOST", "SW_NODE", "FB_NODE", "PROG_N", "CHRG_N",
        "ANT", "E22_AUX", "EXC_A", "EXC_B", "CIN_P", "CHRG_LED"], start=1):
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

def module_fp(ref, value, pos, pads):
    """Custom SMD-pad module footprint (castellated modules, odd packages).

    pads: list of (number, dx, dy, w, h) relative to pos.
    """
    fp = pcbnew.FOOTPRINT(board)
    fp.SetReference(ref)
    fp.SetValue(value)
    for num, dx, dy, w, h in pads:
        pad = pcbnew.PAD(fp)
        pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
        pad.SetShape(pcbnew.PAD_SHAPE_RECT)
        pad.SetSize(pcbnew.VECTOR2I_MM(w, h))
        pad.SetPosition(pcbnew.VECTOR2I_MM(dx, dy))
        pad.SetLayerSet(pad.SMDMask())
        pad.SetNumber(str(num))
        fp.Add(pad)
    fp.SetPosition(VECTOR2I_MM(*pos))
    board.Add(fp)
    FPS[ref] = fp
    return fp

def module_net(ref, mapping):
    for p in FPS[ref].Pads():
        if p.GetNumber() in mapping:
            p.SetNet(net(mapping[p.GetNumber()]))

# --- XIAO ESP32-S3 as reflowed SMD module (castellated pads).
# Same pad geometry as the socket rows: 2x7, 2.54mm pitch, 17.78mm rows.
xiao_pads = [(i, -8.89, -7.62 + 2.54 * (i - 1), 1.4, 2.2) for i in range(1, 8)]
xiao_pads += [(i, 8.89, -7.62 + 2.54 * (i - 8), 1.4, 2.2) for i in range(8, 15)]
module_fp("U1", "XIAO-ESP32S3", (48.89, 27.62), xiao_pads)
module_net("U1", {"1": "D0_PIR", "2": "D1_HYDRO", "3": "D2_ULTRA",
                  "4": "D3_EMIT", "5": "SDA", "6": "SCL", "7": "TX_D6",
                  "8": "+5V", "9": "GND", "10": "+3V3", "11": "MOSI_D10",
                  "12": "MISO_D9", "13": "SCK_D8", "14": "RX_D7"})
# XIAO pin positions stay identical to the carrier so all routes below
# keep their coordinates (left col x=40, right col x=57.78).

# --- EBYTE E22-400M22S UART LoRa module (D6/D7 uplink, ~3V3 logic-safe)
# Custom 16-pad castellated footprint, ANT end toward U.FL at top-right.
# PIN MAP IS PROVISIONAL — verify against EBYTE datasheet at first
# article; J7 remains populated so an external UART radio always works.
e22_pads = ([(i, -7.7, -8.75 + 2.5 * (i - 1), 1.2, 2.0)
             for i in range(1, 9)] +
            [(i, 7.7, -8.75 + 2.5 * (i - 9), 1.2, 2.0)
             for i in range(9, 17)])
module_fp("U5", "E22-400M22S", (76, 16.5), e22_pads)
module_net("U5", {"1": "GND", "2": "GND", "4": "GND",
                  "6": "TX_D6", "7": "RX_D7", "8": "E22_AUX",
                  "9": "+3V3", "10": "GND", "11": "GND", "12": "GND",
                  "13": "ANT", "14": "GND", "15": "GND", "16": "GND"})

# --- BH1750 light sensor (WSOF-6 custom pads, 0.95mm pitch;
# left col top->bottom VCC GND SCL; right col top->bottom SDA DVI ADDR)
bh_pads = ([(i, -0.8, -0.95 + 0.95 * (i - 1), 0.45, 0.55)
            for i in range(1, 4)] +
           [(6, 0.8, -0.95, 0.45, 0.55), (5, 0.8, 0.0, 0.45, 0.55),
            (4, 0.8, 0.95, 0.45, 0.55)])
module_fp("U3", "BH1750", (68.5, 39), bh_pads)
module_net("U3", {"1": "+3V3", "2": "GND", "3": "SCL",
                  "4": "GND", "5": "+3V3", "6": "SDA"})

# left-edge sensor headers (pin order top->bottom: SIG, 3V3, GND)
place(HDR, "PinHeader_1x03_P2.54mm_Vertical", "J1", "PIR", (10, 20),
      pin_nets={"1": "D0_PIR", "2": "+3V3", "3": "GND"})
place(HDR, "PinHeader_1x03_P2.54mm_Vertical", "J2", "HYDRO", (10, 30),
      pin_nets={"1": "D1_HYDRO", "2": "+3V3", "3": "GND"})
place(HDR, "PinHeader_1x03_P2.54mm_Vertical", "J3", "ULTRA", (10, 40),
      pin_nets={"1": "D2_ULTRA", "2": "+3V3", "3": "GND"})

# right-edge connectors: J4 stays a spare I2C expansion header; the
# BME280/BH1750/AD7746 are now bare ICs on-board, so old J5/J6 slots
# become U3's place and the C4D electrode header J6 (EXC_A, EXC_B,
# CIN_P, GND).
place(HDR, "PinHeader_1x04_P2.54mm_Vertical", "J4", "I2C-EXP", (90, 25),
      pin_nets={"1": "+3V3", "2": "GND", "3": "SDA", "4": "SCL"})
place(HDR, "PinHeader_1x04_P2.54mm_Vertical", "J6", "C4D-ELEC", (90, 51),
      pin_nets={"1": "EXC_A", "2": "EXC_B", "3": "CIN_P", "4": "GND"})

# --- on-board I2C sensor ICs
place("Package_LGA.pretty",
      "Bosch_LGA-8_2.5x2.5mm_P0.65mm_ClockwisePinNumbering",
      "U2", "BME280", (74, 30),
      pin_nets={"1": "GND", "2": "+3V3", "3": "SDA", "4": "SCL",
                "5": "GND", "6": "+3V3", "7": "GND", "8": "+3V3"})
place("Package_SO.pretty", "TSSOP-16_4.4x5mm_P0.65mm", "U4", "AD7746",
      (72, 50),
      pin_nets={"1": "SCL", "3": "EXC_A", "4": "EXC_B", "8": "CIN_P",
                "13": "+3V3", "14": "SDA", "15": "GND", "16": "GND"})
place("Resistor_SMD.pretty", "R_0805_2012Metric", "R6", "4.7k", (87, 40),
      pin_nets={"1": "+3V3", "2": "SCL"})
place("Resistor_SMD.pretty", "R_0805_2012Metric", "R7", "4.7k",
      (84.2, 35),
      pin_nets={"1": "+3V3", "2": "SDA"})
place("Capacitor_SMD.pretty", "C_0805_2012Metric", "C2", "100nF", (78, 31),
      pin_nets={"1": "+3V3", "2": "GND"})
place("Capacitor_SMD.pretty", "C_0805_2012Metric", "C3", "100nF",
      (91, 46),
      pin_nets={"1": "+3V3", "2": "GND"})
place("Capacitor_SMD.pretty", "C_0805_2012Metric", "C4", "100nF", (70, 59.5),
      pin_nets={"1": "+3V3", "2": "GND"})

# --- SMA edge-launch pads (Amphenol 132289 lands here): custom pads
# kept inside the board edge to satisfy edge clearance
j14_pads = [(1, 0, 0, 2.0, 1.6), (2, 0, -4.25, 2.0, 1.6),
            (2, 0, 4.25, 2.0, 1.6)]
module_fp("J14", "SMA-EDGE", (98.5, 16), j14_pads)
module_net("J14", {"1": "ANT", "2": "GND"})

# --- power chain: TP4056 charger + JST-XH battery + MT3608 boost +
# PWR-SEL jumper (BATT vs DIRECT feed of the protected rail)
place("Package_SO.pretty", "SOP-8_3.76x4.96mm_P1.27mm", "U6", "TP4056",
      (48, 86),
      pin_nets={"1": "GND", "2": "PROG_N", "3": "GND", "4": "VPROT",
                "5": "VBATT", "6": "GND", "7": "CHRG_N", "8": "VPROT"})
place("Connector_JST.pretty", "JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical",
      "J12", "BATT-3.7V", (33, 88), pin_nets={"1": "VBATT", "2": "GND"})
place("Package_TO_SOT_SMD.pretty", "SOT-23-6", "U7", "MT3608", (62, 88),
      pin_nets={"1": "SW_NODE", "2": "GND", "3": "FB_NODE",
                "4": "VBATT", "5": "VBATT"})
place("Inductor_SMD.pretty", "L_1008_2520Metric", "L1", "22uH", (56, 88),
      pin_nets={"1": "VBATT", "2": "SW_NODE"})
place("Diode_SMD.pretty", "D_SMA", "D7", "SS14", (68, 88), rot=0,
      pin_nets={"1": "VBOOST", "2": "SW_NODE"})
place("Capacitor_SMD.pretty", "C_0805_2012Metric", "C5", "22uF", (42, 93),
      pin_nets={"1": "VBATT", "2": "GND"})
place("Capacitor_SMD.pretty", "C_0805_2012Metric", "C6", "22uF", (76.5, 94),
      pin_nets={"1": "VBOOST", "2": "GND"})
place("Resistor_SMD.pretty", "R_0805_2012Metric", "R3", "1.2k", (40, 83.5),
      pin_nets={"1": "GND", "2": "PROG_N"})
place("Resistor_SMD.pretty", "R_0805_2012Metric", "R4", "75k", (68, 94),
      pin_nets={"1": "VBOOST", "2": "FB_NODE"})
place("Resistor_SMD.pretty", "R_0805_2012Metric", "R5", "10k", (72, 94),
      pin_nets={"1": "FB_NODE", "2": "GND"})
place("Resistor_SMD.pretty", "R_0805_2012Metric", "R8", "1k", (52, 82),
      pin_nets={"1": "VPROT", "2": "CHRG_LED"})
place("LED_SMD.pretty", "LED_0805_2012Metric", "LED2", "CHRG-RED",
      (56, 82), rot=0, pin_nets={"1": "CHRG_N", "2": "CHRG_LED"})
place(HDR, "PinHeader_1x03_P2.54mm_Vertical", "J13", "PWR-SEL", (78, 86),
      pin_nets={"1": "VPROT", "2": "+5V", "3": "VBOOST"})

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
for i, pos in enumerate([(10, 10), (88, 8.5), (10, 66)], start=1):
    place("Fiducial.pretty", "Fiducial_1mm_Mask3mm", "FID%d" % i,
          "FID", pos)

# mounting holes
HOLES = [(5, 5), (95, 5), (5, 95), (95, 95)]
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

def via(pos, netname, w=0.8, drill=0.4):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(VECTOR2I_MM(*pos))
    v.SetDrill(pcbnew.FromMM(drill))
    v.SetWidth(pcbnew.FromMM(w))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetNet(net(netname))
    board.Add(v)

F, B = pcbnew.F_Cu, pcbnew.B_Cu
TF = 0.35   # fine track for the 0.65mm-pitch sensor cluster
VF = (0.6, 0.3)  # fine via (pad, drill) for the same region
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

# --- XIAO SMD pads: every net leaves on F.Cu; B.Cu nets hop at x=59.3
# right col pads: 5V(20) GND(22.54) 3V3(25.08) MOSI(27.62) MISO(30.16)
#                 SCK(32.7) RX(35.24) ; left col TX(35.24) also hops.
for y, n in [(20, "+5V"), (22.54, "GND"), (27.62, "MOSI_D10"),
             (30.16, "MISO_D9"), (32.7, "SCK_D8")]:
    seg([(57.78, y), (59.3, y)], F, TRACK, n)
    via((59.3, y), n)
seg([(40, 35.24), (40, 37)], F, TRACK, "TX_D6")
via((40, 37), "TX_D6")

# --- SDA: F.Cu feed -> via hop -> B.Cu trunk x=85 (top at y=26.9).
#     The 0.65mm-pitch sensor taps run at TF width with 0.6mm vias.
seg([(40, 30.16), (46, 30.16), (46, 37.2), (76, 37.2)], F, TRACK, "SDA")
via((76, 37.2), "SDA")
seg([(76, 37.2), (85, 37.2)], B, TRACK, "SDA")           # joins trunk
seg([(85, 26.9), (85, 48.8)], B, TRACK, "SDA")           # B.Cu trunk
seg([(85, 30.08), (90, 30.08)], B, TRACK, "SDA")         # J4 p3
# taps: U2 p3 (staggered diag to dodge the SCL stub), U3 p6, U4 p14, R7 p2
seg([(74.325, 28.975), (74.325, 28.2), (74.4, 26.9)], F, TF, "SDA")
via((74.4, 26.9), "SDA", *VF)
seg([(74.4, 26.9), (85, 26.9)], B, TF, "SDA")
seg([(69.3, 38.05), (71.9, 38.05)], F, TF, "SDA")
via((71.9, 38.05), "SDA")
seg([(71.9, 38.05), (85, 38.05)], B, TRACK, "SDA")
seg([(74.862, 49.025), (76.4, 49.025), (76.4, 48.8)], F, TF, "SDA")
via((76.4, 48.8), "SDA", *VF)                             # U4 p14
seg([(76.4, 48.8), (85, 48.8)], B, TF, "SDA")
seg([(85.112, 35), (85.6, 35.3)], F, TRACK, "SDA")       # R7 p2
via((85.6, 35.3), "SDA", *VF)
seg([(85.6, 35.3), (85, 35.3)], B, TRACK, "SDA")         # join trunk

# --- SCL: F.Cu feed (detour under the U4 pad column) + trunk x=82
seg([(40, 32.7), (43.5, 32.7), (43.5, 50.1), (63.2, 50.1), (63.2, 57),
     (80.9, 57), (80.9, 50.4), (82, 50.4)], F, TRACK, "SCL")
seg([(82, 28.2), (82, 50.4)], F, TRACK, "SCL")           # trunk
# J4 p4 swings wide below the EXC_A lane then back up to the pad
seg([(82, 38), (89.8, 38), (89.8, 32.62)], F, TRACK, "SCL")
# taps: U2 p4, U3 p3, U4 p1 (B.Cu hop), R6 p2
seg([(74.975, 28.975), (74.975, 28.2), (82, 28.2)], F, TF, "SCL")
seg([(67.7, 39.95), (67.7, 41.7), (82, 41.7)], F, TRACK, "SCL")
seg([(69.138, 47.725), (71.5, 47.725)], F, TF, "SCL")
via((71.5, 47.725), "SCL")
seg([(71.5, 47.725), (81, 47.725)], B, TRACK, "SCL")
via((81, 47.725), "SCL")
seg([(81, 47.725), (82, 47.725)], F, TRACK, "SCL")
seg([(87.912, 40), (87.912, 41.2), (82, 41.2)], F, TRACK, "SCL")

# --- TX_D6: pad -> via -> B.Cu J7 leg (left edge, around J8);
#     E22 RXD branch: B.Cu up x=38, F.Cu bridge across the walls,
#     back to B.Cu to clear the SPI fan + GND spine, then pad stub
seg([(40, 37), (13.5, 37), (13.5, 72.5), (38.5, 72.5),
     (38.5, 66.54), (40, 66.54)], B, TRACK, "TX_D6")
seg([(40, 37), (38, 37), (38, 17.4)], B, TRACK, "TX_D6")
via((38, 17.4), "TX_D6")
seg([(38, 17.4), (59.6, 17.4), (59.6, 18.3), (61.6, 18.3)],
    F, TRACK, "TX_D6")
via((61.6, 18.3), "TX_D6", 0.55, 0.3)
seg([(61.6, 18.3), (64.5, 18.3)], B, TRACK, "TX_D6")     # under x63.5 spur
via((64.5, 18.3), "TX_D6", 0.55, 0.3)
seg([(64.5, 18.3), (66, 18.3), (66, 20.25), (68.3, 20.25)],
    F, TRACK, "TX_D6")                                   # U5 p6

# --- F.Cu: 3V3 tree (feed routed clear of the H2 keepout)
seg([(57.78, 25.08), (63.5, 25.08), (63.5, 13), (8, 13), (8, 42.54)],
    F, PWR, "+3V3")
for y in (22.54, 32.54, 42.54):
    seg([(8, y), (10, y)], F, PWR, "+3V3")
seg([(63.5, 15), (64, 15), (64, 6), (90, 6), (90, 13), (95, 13)],
    F, PWR, "+3V3")
seg([(95, 13), (95, 61)], F, PWR, "+3V3")                # trunk
seg([(95, 25), (90, 25)], F, PWR, "+3V3")                # J4 p1
seg([(95, 61), (59, 61)], F, PWR, "+3V3")
seg([(70, 61), (70, 70.54), (64, 70.54)], F, PWR, "+3V3")
seg([(8, 42.54), (8, 70), (15, 70)], F, PWR, "+3V3")
seg([(62, 25.08), (62, 28), pad_xy("C1", "1")], F, TRACK, "+3V3")
cx, cy = pad_xy("D1", "1")           # cathode (rot180: pad1 lands right)
seg([(cx, cy), (59, cy), (59, 61), (70, 61)], F, TRACK, "+3V3")
seg([(83.7, 6), (83.7, 7.75)], F, TRACK, "+3V3")         # U5 p9 VCC
# sensor-cluster 3V3: B.Cu spur y=25.5 from the trunk, F.Cu drops
via((95, 25.5), "+3V3")
seg([(95, 25.5), (67, 25.5)], B, TRACK, "+3V3")
via((70.5, 25.5), "+3V3")
seg([(73.675, 28.975), (73.675, 27.3), (70.5, 27.3)], F, TF, "+3V3")
seg([(73.025, 31.025), (70.5, 31.025)], F, TF, "+3V3")   # U2 p8
seg([(70.5, 25.5), (70.5, 35.1), (70.9, 35.1)], F, TRACK, "+3V3")
via((70.9, 35.1), "+3V3")
seg([(70.9, 35.1), (71, 35.1), (71, 39)], B, TRACK, "+3V3")
via((71, 39), "+3V3")
seg([(71, 39), (69.3, 39)], F, TRACK, "+3V3")            # U3 p5 DVI
via((67, 25.5), "+3V3")
seg([(67, 25.5), (67, 35)], F, TRACK, "+3V3")
via((67, 35), "+3V3")
seg([(67, 35), (66.85, 38.35)], B, TRACK, "+3V3")        # U3 p1 hop
via((66.85, 38.35), "+3V3", *VF)
seg([(66.85, 38.35), (67.7, 38.05)], F, TF, "+3V3")      # U3 p1 VCC
# U2 p6 / C2 p1: B.Cu y=32.5 line fed by the x=84.9 drop off the spur
via((84.9, 25.5), "+3V3", *VF)
seg([(84.9, 25.5), (84.9, 32.5), (84.2, 32.5)], F, TF, "+3V3")
via((84.2, 32.5), "+3V3", *VF)
seg([(84.2, 32.5), (74.5, 32.5)], B, TF, "+3V3")
via((74.5, 32.5), "+3V3", *VF)
seg([(74.5, 32.5), (74.325, 32.5), (74.325, 31.025)], F, TF, "+3V3")
seg([(77.8, 31), (77.8, 32.7)], F, TF, "+3V3")           # C2 p1 bus
via((77.8, 32.5), "+3V3", *VF)
seg([(77.05, 31), (77.8, 31)], F, TF, "+3V3")
# U4 p13 VDD + C3 p1: hop the two trunks (F.Cu SCL x82, B.Cu SDA x85)
seg([(74.862, 49.675), (77.0, 49.675)], F, TF, "+3V3")   # U4 p13
via((77.0, 49.675), "+3V3", *VF)
seg([(77.0, 49.675), (77.0, 50.7), (84.1, 50.7)], B, TF, "+3V3")
via((84.1, 50.7), "+3V3", *VF)
seg([(84.1, 50.7), (88, 50.7), (88, 49.3), (95, 49.3)],
    F, TF, "+3V3")
seg([(90.05, 46), (90.05, 48.6), (93.5, 48.6), (93.5, 49.3)],
    F, TRACK, "+3V3")                                     # C3 p1
# pull-ups R6/R7 beside the trunks; R6 p1 hops the SCL stub on B.Cu
seg([(86.088, 40), (86.088, 40.2)], F, TRACK, "+3V3")    # R6 p1
via((86.088, 40.2), "+3V3")
seg([(86.088, 40.2), (86.088, 42.6)], B, TRACK, "+3V3")
via((86.088, 42.6), "+3V3")
seg([(86.088, 42.6), (95, 42.6)], F, TRACK, "+3V3")
# R7 p1: straight up and across the J4 pad-row gap (y=28.8 lane)
seg([(83.288, 35), (83.288, 28.8), (95, 28.8)], F, TF, "+3V3")
# LEDPWR feed: drop from the y=6 rail down to R2 p1
seg([(70.588, 6), (70.588, 20)], F, TRACK, "+3V3")
# C4 p1 drop to the y=61 rail
seg([(69.05, 59.5), (69.05, 61)], F, TRACK, "+3V3")

# --- B.Cu: 5V perimeter (XIAO via -> right edge -> J9.2/J7.4 feeds)
seg([(59.3, 20), (59.3, 16), (97.5, 16), (97.5, 77.54), (46, 77.54)],
    B, PWR, "+5V")
seg([(46, 77.54), (48, 77.54), (48, 73.4), (39.5, 73.4),
     (39.5, 71.62), (40, 71.62)], B, PWR, "+5V")
# +5V to J13 p2 (PWR-SEL direct feed) down the right edge
seg([(97.5, 77.54), (97.5, 92), (81, 92), (81, 88.54), (78, 88.54)],
    B, PWR, "+5V")

# --- RX_D7: pad -> via -> B.Cu J7 leg; E22 TXD on F.Cu
seg([(57.78, 35.24), (57.78, 35.55)], F, TRACK, "RX_D7")
via((57.78, 35.55), "RX_D7", *VF)
seg([(57.78, 35.55), (57.78, 51), (46, 51), (46, 62), (40, 62),
     (40, 64)], B, TRACK, "RX_D7")
seg([(57.78, 35.24), (66.1, 35.24), (66.1, 22.75), (68.3, 22.75)],
    F, TRACK, "RX_D7")                                    # U5 p7

# --- B.Cu: SPI fan (nested drops from the via column; stubs end at J8)
mosi = J8P["3"]; miso = J8P["4"]; sck = J8P["5"]
seg([(59.3, 27.62), (56, 27.62), (56, 18), (45, 18), (45, 44),
     (mosi[0], 44), (mosi[0], mosi[1])], B, TRACK, "MOSI_D10")
seg([(59.3, 30.16), (54, 30.16), (54, 46.5), (25, 46.5), (25, 63),
     (miso[0], 63), (miso[0], miso[1])], B, TRACK, "MISO_D9")
seg([(59.3, 32.7), (56, 32.7), (56, 49), (26, 49), (26, 65.5),
     (sck[0], 65.5), (sck[0], sck[1])], B, TRACK, "SCK_D8")

# --- GND backbone (B.Cu trunk + F.Cu hops over walled pockets)
# B.Cu: U1 GND via -> x=60.5 spine -> top y=15 bus -> x=12 left drop
seg([(59.3, 22.54), (60.5, 22.54)], B, TRACK, "GND")
seg([(60.5, 17.0), (60.5, 75)], B, TRACK, "GND")
seg([(12, 15), (60.5, 15)], B, TRACK, "GND")
via((60.5, 15), "GND")
seg([(60.5, 15), (60.5, 17.0)], F, TRACK, "GND")
via((60.5, 17.0), "GND")
seg([(12, 15), (12, 74)], B, TRACK, "GND")
# J4 p2 + J6 p4 grounds: stubs -> x=92.5 drop -> y=72 back to spine
for y in (27.54, 58.62):
    seg([(90, y), (92.5, y)], B, TRACK, "GND")
seg([(92.5, 27.54), (92.5, 72)], B, TRACK, "GND")
seg([(92.5, 72), (60.5, 72)], B, TRACK, "GND")
# C1 via -> B.Cu x=70 drop to spine
c2x, c2y = pad_xy("C1", "2")
seg([(c2x, c2y), (65, 29)], F, TRACK, "GND")
via((65, 29), "GND")
seg([(65, 29), (70, 29), (70, 60.5), (60.5, 60.5)], B, TRACK,
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
seg([(72.412, 20), (75.062, 20)], F, TRACK, "LEDPWR")
seg([(76.938, 20), (76.938, 22.5)], F, TRACK, "GND")
via((76.938, 22.5), "GND")
seg([(76.94, 22.5), (76.94, 24), (60.5, 24)], B, TRACK, "GND")

# --- E22: ANT pad -> SMA edge-mount centre pin on the right edge;
#     GND pads stitched to the pour
seg([(83.7, 17.75), (88, 17.75), (88, 16), (93.5, 16),
     (93.5, 18)], F, TRACK, "ANT")
via((93.5, 18), "ANT")
seg([(93.5, 18), (96, 18)], B, TRACK, "ANT")             # under +5V/3V3
via((96, 18), "ANT")
seg([(96, 18), (98.5, 18), (98.5, 16)], F, TRACK, "ANT")
for y in (7.75, 10.25):                     # U5 left-col GND pads
    via((66.5, y), "GND")
    seg([(66.5, y), (68.3, y)], F, TRACK, "GND")
via((66.5, 14.8), "GND")                    # U5 p4, jogged off +5V lane
seg([(66.5, 14.8), (68.3, 15.25)], F, TRACK, "GND")
for y, vx in [(10.25, 85.5), (12.75, 85.5), (20.25, 85.5),
              (22.75, 85.5), (23.8, 85.5)]:
    via((vx, y), "GND")
    seg([(vx, y), (83.7, 25.25 if y == 23.8 else y)], F, TRACK, "GND")
via((85.5, 14.9), "GND")                    # U5 p12, jogged off +5V lane
seg([(85.5, 14.9), (83.7, 15.25)], F, TRACK, "GND")
for sy in (11.75, 20.25):                   # J14 SMA shield pads
    seg([(96.5, sy), (98.5, sy)], F, TRACK, "GND")
    via((96.5, sy), "GND")

# --- AD7746 excitation/sense pads -> J6 electrode header
# (left col x=69.138, right col x=74.862, rows y=47.725..52.275)
# EXC_A: stub -> B.Cu hop up the pocket (x=66), F.Cu run under the
# trunks, then B.Cu drop to J6
seg([(69.138, 49.025), (66.0, 48.8)], F, TF, "EXC_A")
via((66.0, 48.8), "EXC_A", *VF)
seg([(66.0, 48.8), (66.0, 36.2)], B, TRACK, "EXC_A")
via((66.0, 36.2), "EXC_A", *VF)
seg([(66.0, 36.2), (80, 36.2)], F, TRACK, "EXC_A")
via((80, 36.2), "EXC_A")
seg([(80, 36.2), (84, 36.2)], B, TRACK, "EXC_A")
via((84, 36.2), "EXC_A")
seg([(84, 36.2), (88.9, 36.2)], F, TRACK, "EXC_A")
via((88.9, 36.2), "EXC_A")
seg([(88.9, 36.2), (88.9, 50.8)], B, TRACK, "EXC_A")
via((88.9, 50.8), "EXC_A")
seg([(88.9, 50.8), (89.6, 51), (90, 51)], F, TRACK, "EXC_A")
seg([(69.138, 49.675), (64.8, 49.675), (64.8, 53.9), (78.4, 53.9)],
    F, TF, "EXC_B")
via((78.4, 53.9), "EXC_B")
seg([(78.4, 53.9), (84.1, 53.9)], B, TRACK, "EXC_B")
via((84.1, 53.9), "EXC_B", *VF)
seg([(84.1, 53.9), (86, 53.9), (86, 53.54), (90, 53.54)],
    F, TRACK, "EXC_B")
seg([(69.138, 52.275), (69.6, 53.0), (79.4, 53.0), (79.4, 56.08),
     (80, 56.08)], F, TF, "CIN_P")
via((80, 56.08), "CIN_P")
seg([(80, 56.08), (84.1, 56.08)], B, TRACK, "CIN_P")
via((84.1, 56.08), "CIN_P", *VF)
seg([(84.1, 56.08), (90, 56.08)], F, TRACK, "CIN_P")
# local grounds: U4 p15/p16, U3 p2/ADDR, decap caps, BME280
# U4 p15/p16 share one fine via + a B.Cu escape around the SCL lane
seg([(74.862, 48.375), (76.2, 46.9)], F, TF, "GND")      # U4 p15
seg([(74.862, 47.725), (76.2, 46.9)], F, TF, "GND")      # U4 p16
via((76.2, 46.9), "GND", *VF)
seg([(76.2, 46.9), (78, 46.9), (78, 44.8), (70, 44.8)], B, TRACK,
    "GND")
seg([(91.95, 46), (91.95, 46.8)], F, TRACK, "GND")       # C3 p2
via((91.95, 46.8), "GND")
seg([(91.95, 46.8), (92.5, 46.8)], B, TRACK, "GND")      # join x92.5
seg([(67.7, 39), (66.9, 39.6)], F, TF, "GND")            # U3 p2
via((66.9, 39.6), "GND", *VF)
seg([(66.9, 39.6), (66.9, 50.4), (60.5, 50.4)], B, TRACK, "GND")
seg([(69.3, 39.95), (72, 40.2)], F, TF, "GND")           # U3 p4 ADDR
via((72, 40.2), "GND")
seg([(78.95, 31), (80.5, 31)], F, TRACK, "GND")          # C2 p2
via((80.5, 31), "GND")
seg([(73.025, 28.975), (72, 28.975)], F, TF, "GND")      # U2 p1
via((72, 28.975), "GND")
seg([(73.675, 31.025), (73.675, 34.4)], F, TF, "GND")    # U2 p7
via((73.675, 34.4), "GND")
seg([(74.975, 31.025), (76, 31.025), (76, 34.4)], F, TF, "GND")
via((76, 34.4), "GND")                                   # U2 p5
seg([(70.95, 59.5), (72.5, 59.5)], F, TRACK, "GND")      # C4 p2
via((72.5, 59.5), "GND")

# --- power chain: VPROT down to U6 + J13.1; TP4056, MT3608, jumper
# U6 SOP-8 pads: left col x=45.462, right col x=50.538, y=84.095..87.905
seg([(61, 74.5), (61, 78.8), (50.538, 78.8), (50.538, 84.095)],
    F, PWR, "VPROT")                                     # -> U6 p8
seg([(51.087, 82), (50.538, 82)], F, TRACK, "VPROT")     # -> R8 p1
seg([(50.538, 84.095), (48.5, 84.095), (48.5, 88.6), (45.462, 88.6),
     (45.462, 87.905)], F, PWR, "VPROT")                 # -> U6 p4
seg([(70, 76), (70, 80), (78, 80), (78, 86)], F, PWR, "VPROT")
# TP4056 PROG -> R3 p2; R3 p1 to GND; CHRG -> LED2 -> R8
seg([(45.462, 85.365), (40.913, 85.365), (40.913, 83.5)], F, TRACK,
    "PROG_N")
seg([(39.087, 83.5), (37, 83.5)], F, TRACK, "GND")
via((37, 83.5), "GND")
seg([(50.538, 85.365), (53, 85.365), (53, 83.4), (55.062, 83.4),
     (55.062, 82)], F, TRACK, "CHRG_N")
seg([(56.938, 82), (56.938, 80.5), (52.913, 80.5), (52.913, 82)],
    F, TRACK, "CHRG_LED")
# TP4056 + J12 local grounds
for sx, sy, vx, vy in [(45.462, 84.095, 43.5, 84.095),
                       (45.462, 86.635, 43.5, 86.635),
                       (50.538, 86.635, 53.5, 86.635),
                       (35.5, 88, 37.5, 90)]:
    seg([(sx, sy), (vx, vy)], F, TRACK, "GND")
    via((vx, vy), "GND")
# VBATT bus: J12 -> U6 p5 -> C5 -> L1 -> U7 p4/p5/p6
seg([(33, 88), (33, 91), (58, 91), (58, 92.2), (63.138, 92.2),
     (63.138, 88)], F, PWR, "VBATT")
seg([(50.538, 87.905), (50.538, 91)], F, PWR, "VBATT")   # U6 p5 tap
seg([(41.05, 93), (41.05, 91)], F, TRACK, "VBATT")       # C5 p1
seg([(42.95, 93), (42.95, 95.2)], F, TRACK, "GND")       # C5 p2
via((42.95, 95.2), "GND")
seg([(54.925, 88), (54.925, 91)], F, TRACK, "VBATT")     # L1 p1 tap
# SW node: L1 p2 -> U7 p1 -> via hop -> D7 p2 anode
seg([(57.075, 88), (58, 88), (58, 87.05), (61.5, 87.05), (61.5, 86),
     (62.5, 86)], F, TRACK, "SW_NODE")
via((62.5, 86), "SW_NODE")
seg([(62.5, 86), (71.5, 86)], B, TRACK, "SW_NODE")
via((71.5, 86), "SW_NODE")
seg([(71.5, 86), (71.5, 88), (70, 88)], F, TRACK, "SW_NODE")
# U7 p2 GND stub
seg([(60.862, 88), (59.5, 88)], F, TRACK, "GND")
via((59.5, 88), "GND")
# VBOOST: D7 p1 cathode -> R4 p1 + C6 p1 + J13 p3
seg([(66, 88), (66, 95.5), (75.55, 95.5), (75.55, 94)], F, PWR,
    "VBOOST")
seg([(67.088, 94), (66, 94)], F, TRACK, "VBOOST")        # R4 p1
seg([(77.45, 94), (78.9, 93.4)], F, TRACK, "GND")        # C6 p2
via((78.9, 93.4), "GND")
seg([(75.55, 95.5), (81.5, 95.5), (81.5, 91.08), (78, 91.08)],
    F, PWR, "VBOOST")                                    # J13 p3
# FB divider: U7 p3 -> (B.Cu under VBATT) -> R4 p2 -> R5 p1 ; R5 p2 -> GND
seg([(60.862, 88.95), (60.862, 90), (61.6, 90)], F, TRACK, "FB_NODE")
via((61.6, 90), "FB_NODE")
seg([(61.6, 90), (70.5, 90)], B, TRACK, "FB_NODE")
via((70.5, 90), "FB_NODE")
seg([(70.5, 90), (70.5, 94)], F, TRACK, "FB_NODE")
seg([(68.912, 94), (71.088, 94)], F, TRACK, "FB_NODE")   # R4p2 -> R5p1
seg([(72.912, 94), (74.5, 93)], F, TRACK, "GND")         # R5 p2
via((74.5, 93), "GND")

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

text("EcoCell One v1 - living-resources AGPL", (42, 4), 1.2)
text("XIAO-S3 USB-up", (44, 13), 1.0)
text("E22-400M22S", (76, 4.5), 0.9)
text("ANT", (88, 12.5), 0.9)
text("J1 PIR / J2 HYDRO / J3 ULTRA", (16, 55), 1.0)
text("I2C-EXP", (91.5, 36.5), 0.9)
text("C4D ELEC", (86, 62), 0.9)
text("EMIT: consent-gated", (52, 44), 1.0)
text("5V-IN protected", (58, 78.8), 0.9)
text("PWR", (70.5, 14.5), 0.9)
text("BATT 3.7V", (33, 81.5), 0.9)
text("PWR-SEL", (78, 80.5), 0.9)
text("CHARGE+BOOST", (56, 96.5), 0.9)
# tidy refs: J14 sits on the edge (clipped); U3's default lands on pads
FPS["J14"].Reference().SetPosition(VECTOR2I_MM(96, 13.5))
FPS["U3"].Reference().SetPosition(VECTOR2I_MM(68.5, 42.5))
FPS["C6"].Reference().SetPosition(VECTOR2I_MM(76.5, 96.5))

# -------------------------------------------------------------- fill+save
try:
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
except Exception as e:
    print("zone fill deferred to export:", e)

board.Save(os.path.abspath(OUT))
print("wrote", os.path.abspath(OUT))
