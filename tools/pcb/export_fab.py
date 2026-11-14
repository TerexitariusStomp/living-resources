# SPDX-License-Identifier: AGPL-3.0-or-later
"""export_fab.py — fabrication outputs for the EcoCell ocean board.

Runs kicad-cli exports into hardware/release/electrical/fab/:
Gerbers (all copper + mask + silk + paste + edge), Excellon drill,
and the pick-and-place centroid file.  Then writes fab/MANIFEST.sha256
covering every emitted file.

Usage: python3 tools/pcb/export_fab.py
"""
import hashlib
import os
import subprocess
import sys

REL = 'hardware/release/electrical'
PCB = os.path.join(REL, 'ecocell-ocean.kicad_pcb')
FAB = os.path.join(REL, 'fab')

LAYERS = ('F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,'
          'B.Silkscreen,F.Paste,B.Paste,Edge.Cuts')

os.makedirs(FAB, exist_ok=True)


def run(cmd):
    print('$', ' '.join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout)
        print(r.stderr, file=sys.stderr)
        sys.exit(1)


run(['kicad-cli', 'pcb', 'export', 'gerbers', PCB,
     '--layers', LAYERS,
     '--subtract-soldermask',
     '--no-x2',
     '-o', os.path.join(FAB, 'ecocell-ocean')])
run(['kicad-cli', 'pcb', 'export', 'drill', PCB,
     '--format', 'excellon',
     '--excellon-separate-th',
     '--drill-origin', 'plot',
     '-o', os.path.join(FAB, 'ecocell-ocean')])
run(['kicad-cli', 'pcb', 'export', 'pos', PCB,
     '--format', 'csv',
     '--units', 'mm',
     '--side', 'both',
     '--smd-only',
     '-o', os.path.join(FAB, 'ecocell-ocean-cpl.csv')])

# manifest over everything in fab/ (recursive — gerbers land in a subdir)
names = []
for root, _dirs, files in os.walk(FAB):
    for fn in files:
        rel = os.path.relpath(os.path.join(root, fn), FAB)
        if rel != 'MANIFEST.sha256':
            names.append(rel)
names.sort()
h = hashlib.sha256()
for name in names:
    p = os.path.join(FAB, name)
    h.update(name.encode() + b'\0' + open(p, 'rb').read())
with open(os.path.join(FAB, 'MANIFEST.sha256'), 'w') as f:
    f.write('# EcoCell ocean fab package\n')
    f.write('# sha256 of (name\\0 + contents) concat, file order: sorted\n')
    f.write(h.hexdigest() + '\n')
    for name in names:
        p = os.path.join(FAB, name)
        f.write(hashlib.sha256(open(p, 'rb').read()).hexdigest() +
                '  ' + name + '\n')
print('fab outputs:', len(names))
