# SPDX-License-Identifier: AGPL-3.0-or-later
"""net2sch.py — native .kicad_sch from the shipped .net file.

The original SKiDL schematic source was lost (see CHANGELOG).  The
.net file is the deterministic connectivity source for the shipped
board, so this emits a connectivity-exact schematic from it: every
component becomes a box symbol carrying the pins its nodes reference,
and every pin gets a net label at its connect point.  Ugly-but-honest
schematic — ERC and netlist round-trip verify it, and a reviewer can
read subsystem connectivity straight off the labels.

Usage: python3 tools/pcb/net2sch.py
"""
import os
import re
import uuid as U

HERE = os.path.dirname(os.path.abspath(__file__))
REL = os.path.normpath(os.path.join(HERE, "..", "..", "hardware",
                                    "release", "electrical"))
NET = os.path.join(REL, "ecocell-ocean.net")
SCH = os.path.join(REL, "ecocell-ocean.kicad_sch")
SHEET_UUID = str(U.uuid4())


def tok(s):
    s = s.replace('(', ' ( ').replace(')', ' ) ')
    return s.split()


def parse(t):
    if not t:
        return None
    x = t.pop(0)
    if x == '(':
        out = []
        while t and t[0] != ')':
            out.append(parse(t))
        t.pop(0)
        return out
    if x == ')':
        raise ValueError('unexpected )')
    return x.strip('"')


tree = parse(tok(open(NET).read()))
comps, nets = [], {}
for node in tree:
    if isinstance(node, list) and node and node[0] == 'components':
        for c in node[1:]:
            ref = value = fp = ''
            for f in c[1:]:
                if f[0] == 'ref':
                    ref = f[1]
                elif f[0] == 'value':
                    value = f[1]
                elif f[0] == 'footprint':
                    fp = f[1]
            comps.append((ref, value, fp))
    if isinstance(node, list) and node and node[0] == 'nets':
        for n in node[1:]:
            name = ''
            pins = []
            for f in n[1:]:
                if f[0] == 'name':
                    name = f[1]
                elif f[0] == 'node':
                    r = p = ''
                    for a in f[1:]:
                        if a[0] == 'ref':
                            r = a[1]
                        elif a[0] == 'pin':
                            p = a[1]
                    pins.append((r, p))
            nets[name] = pins

pins_of = {}
for name, pins in nets.items():
    for r, p in pins:
        pins_of.setdefault(r, []).append((p, name))
for r in pins_of:
    pins_of[r].sort(key=lambda x: (len(x[0]), x[0]))

# ---- emit -------------------------------------------------------------------
P = 2.54            # grid
BW = 30 * P         # box width
HDR = '''(kicad_sch (version 20250114) (generator "net2sch")
\t(generator_version "9.0")
\t(uuid "%s")
\t(paper "A3")
\t(title_block (title "ecocell-ocean — connectivity schematic (generated from .net)") (company "living-resources") (rev "R0"))
\t(lib_symbols
''' % SHEET_UUID


def box_symbol(ref, value, fp, pins):
    n = len(pins)
    half = (n + 1) // 2
    h = max(half, n - half) * P * 2 + P * 4
    top = h / 2
    s = ['\t\t(symbol "gen:%s" (pin_numbers (hide yes)) (pin_names (offset 0.508) (hide yes))'
         ' (exclude_from_sim no) (in_bom yes) (on_board yes)'
         % re.sub(r'[^A-Za-z0-9_]', '_', ref)]
    s.append('\t\t\t(property "Reference" "%s" (at 0 %g 0) (effects (font (size 1.27 1.27))))'
             % (ref, top + P * 2))
    s.append('\t\t\t(property "Value" "%s" (at 0 %g 0) (effects (font (size 1.27 1.27))))'
             % (value.replace('"', "'"), top + P))
    s.append('\t\t\t(property "Footprint" "%s" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))' % fp)
    s.append('\t\t\t(property "Datasheet" "~" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))')
    s.append('\t\t\t(symbol "%s_0_1"' % re.sub(r'[^A-Za-z0-9_]', '_', ref))
    s.append('\t\t\t\t(rectangle (start %g %g) (end %g %g) (stroke (width 0.254) (type default)) (fill (type background)))'
             % (-BW / 2, top - P * 2, BW / 2, -top + P * 2))
    s.append('\t\t\t)')
    s.append('\t\t\t(symbol "%s_1_1"' % re.sub(r'[^A-Za-z0-9_]', '_', ref))
    for i, (pn, net) in enumerate(pins):
        left = i < half
        row = i if left else i - half
        side = -1 if left else 1
        px = side * (BW / 2 + P * 2)
        py = top - P * 3 - row * P * 2
        rot = 0 if left else 180
        nm = net if net else ('p' + pn)
        s.append('\t\t\t\t(pin passive line (at %g %g %d) (length %g)'
                 ' (name "%s" (effects (font (size 0.9 0.9))))'
                 ' (number "%s" (effects (font (size 0.9 0.9)))))'
                 % (px, py, rot, P * 2, nm.replace('"', "'"), pn))
    s.append('\t\t\t)')
    s.append('\t\t)')
    return '\n'.join(s), pins, half, top


cols, gap_x, gap_y = 6, 60 * P, 50 * P
body = [HDR]
instances, labels = [], []
for i, (ref, value, fp) in enumerate(comps):
    pins = pins_of.get(ref, [('1', 'NC'), ('2', 'NC')])
    sym, pins, half, top = box_symbol(ref, value, fp, pins)
    body.append(sym)
    cx = 30 * P + (i % cols) * gap_x
    cy = 30 * P + (i // cols) * gap_y
    lib_id = 'gen:' + re.sub(r'[^A-Za-z0-9_]', '_', ref)
    inst = ['\t(symbol (lib_id "%s") (at %g %g 0) (unit 1)'
            ' (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)'
            % (lib_id, cx, cy)]
    inst.append('\t\t(uuid "%s")' % U.uuid4())
    inst.append('\t\t(property "Reference" "%s" (at %g %g 0) (effects (font (size 1.27 1.27))))'
                % (ref, cx, cy + top + P * 2))
    inst.append('\t\t(property "Value" "%s" (at %g %g 0) (effects (font (size 1.27 1.27))))'
                % (value.replace('"', "'"), cx, cy + top + P))
    inst.append('\t\t(property "Footprint" "%s" (at %g %g 0) (effects (font (size 1.27 1.27)) (hide yes)))'
                % (fp, cx, cy))
    inst.append('\t\t(property "Datasheet" "~" (at %g %g 0) (effects (font (size 1.27 1.27)) (hide yes)))' % (cx, cy))
    for pn, _ in pins:
        inst.append('\t\t(pin "%s" (uuid "%s"))' % (pn, U.uuid4()))
    inst.append('\t\t(instances (project "ecocell-ocean" (path "/%s" (reference "%s") (unit 1))))' % (SHEET_UUID, ref))
    inst.append('\t)')
    instances.append('\n'.join(inst))
    for j, (pn, net) in enumerate(pins):
        left = j < half
        row = j if left else j - half
        side = -1 if left else 1
        px = cx + side * (BW / 2 + P * 2)
        # schematic sheet coords are Y-down; lib pin coords are Y-up
        py = cy - (top - P * 3 - row * P * 2)
        rot = 180 if left else 0
        labels.append('\t(label "%s" (at %g %g %d) (fields_autoplaced yes)'
                      ' (effects (font (size 1.0 1.0)) (justify %s bottom))'
                      ' (uuid "%s"))'
                      % (net, px, py, rot, 'right' if left else 'left',
                         U.uuid4()))

body.append('\t)')
out = '\n'.join(body) + '\n' + '\n'.join(instances) + '\n' + \
    '\n'.join(labels) + '\n\t(sheet_instances (path "/" (page "1")))\n)\n'
open(SCH, 'w').write(out)
print('wrote', SCH, len(comps), 'comps,', len(nets), 'nets,',
      len(labels), 'labels')
