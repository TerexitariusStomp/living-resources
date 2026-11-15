# SPDX-License-Identifier: AGPL-3.0-or-later
"""gen_hull.py — parametric CAD for the EcoCell submerged hull.

Emits, into hardware/release/mechanical/:
  - .scad parametric source per part (OpenSCAD — human-diffable source
    of truth)
  - .stl previews via a dependency-free revolve mesher
  - dimensions.json — the single number set every emitter shares

All hull parts are rotational solids (tube, end caps, gland seats), so
a revolve-profile mesher covers the whole part set.  STEP export is the
remaining gap for machining quotes — flagged in MECHANICAL.md.

Dimensions derive from PRESSURE-SPEC.md: 110 mm OD / 3 mm wall tube,
double radial O-rings (AS568-244, 98.02 x 3.53 mm Buna-N 70) on the
end-cap plug, 6x M6 SS316 tie rods cap-to-cap.
"""
import json
import math
import os

OUT = os.path.join(os.path.dirname(__file__), '..', '..',
                   'hardware', 'release', 'mechanical')
OUT = os.path.abspath(OUT)

# cap_flange_t=12 -> ~3.5x bending margin at 0.6 MPa proof
# for POM-C (conservative simply-supported-disc model);
# 8 mm would be ~1.5x — too thin for polymer end caps.
# ---- single source of dimensions (mm) ---------------------------------------
D = dict(
    tube_od=110.0, tube_wall=3.0, tube_len=240.0,
    cap_flange_od=118.0, cap_flange_t=12.0,
    plug_len=20.0,                 # engagement into tube
    plug_clearance=0.15,           # radial clearance plug<->tube bore
    oring_cs=3.53, oring_id=98.02,  # AS568-244 Buna-N 70
    gland_depth=2.95,              # Parker radial static, 3.53 CS
    groove_w=4.6,                  # Parker groove width, 3.53 CS
    groove_gap=2.0,                # land between the two grooves
    tierod_d=6.0, tierod_pcd=114.0, tierod_n=6,
    chamfer=1.0,                   # lead-in chamfer on plug nose
    # penetrators on the wet end cap (gland threads)
    gland_tether="M20", gland_tether_d=20.5,
    gland_head_n=3, gland_head_d=16.5,  # M16 hydro/ctd/emit glands
    gland_head_pcd=60.0,
    dome_od=60.0, dome_t=3.0,      # camera optical dome port, dry cap
)
D['tube_id'] = D['tube_od'] - 2 * D['tube_wall']            # 104
D['plug_od'] = D['tube_id'] - 2 * D['plug_clearance']       # 103.7
D['groove_root'] = D['tube_id'] - 2 * D['gland_depth']      # 98.1


def revolve_stl(profile, name, seg=96):
    """profile: ordered [(r, z)] closed? -> triangulated STL (binary)."""
    import struct
    # close the profile on the axis if ends are at r=0 handled by caller
    tris = []
    n = len(profile)
    for i in range(n - 1):
        (r0, z0), (r1, z1) = profile[i], profile[i + 1]
        for j in range(seg):
            a0, a1 = 2 * math.pi * j / seg, 2 * math.pi * (j + 1) / seg
            p = [(r0 * math.cos(a0), r0 * math.sin(a0), z0),
                 (r1 * math.cos(a0), r1 * math.sin(a0), z1),
                 (r1 * math.cos(a1), r1 * math.sin(a1), z1),
                 (r0 * math.cos(a1), r0 * math.sin(a1), z0)]
            if r0 > 1e-9 and r1 > 1e-9:
                tris += [(p[0], p[1], p[2]), (p[0], p[2], p[3])]
            elif r0 <= 1e-9:
                tris.append((p[0], p[1], p[2]))
            elif r1 <= 1e-9:
                tris.append((p[0], p[2], p[3]))
    out = os.path.join(OUT, name + '.stl')
    with open(out, 'wb') as fh:
        fh.write(b'\0' * 80)
        fh.write(struct.pack('<I', len(tris)))
        for t in tris:
            ax = [t[1][k] - t[0][k] for k in range(3)]
            bx = [t[2][k] - t[0][k] for k in range(3)]
            nn = [ax[1] * bx[2] - ax[2] * bx[1],
                  ax[2] * bx[0] - ax[0] * bx[2],
                  ax[0] * bx[1] - ax[1] * bx[0]]
            m = math.sqrt(sum(c * c for c in nn)) or 1.0
            fh.write(struct.pack('<3f', *[c / m for c in nn]))
            for v in t:
                fh.write(struct.pack('<3f', *v))
            fh.write(struct.pack('<H', 0))
    print('wrote', out, len(tris), 'tris')


def endcap_profile(wet):
    """(r,z) outline of one end cap, flange face at z=0, plug into +z."""
    r_out = D['cap_flange_od'] / 2
    r_plug = D['plug_od'] / 2
    r_root = D['groove_root'] / 2
    ft, pl = D['cap_flange_t'], D['plug_len']
    gw, gg = D['groove_w'], D['groove_gap']
    ch = D['chamfer']
    g1 = ft + ch + 2.0            # first groove start (from flange face)
    g2 = g1 + gw + gg             # second groove start
    prof = [(0, 0), (r_out, 0), (r_out, ft), (r_plug, ft)]
    prof += [(r_plug, g1)]
    prof += [(r_root, g1), (r_root, g1 + gw), (r_plug, g1 + gw)]
    prof += [(r_plug, g2)]
    prof += [(r_root, g2), (r_root, g2 + gw), (r_plug, g2 + gw)]
    prof += [(r_plug, ft + pl - ch), (r_plug - ch, ft + pl),
             (0, ft + pl)]
    return prof


def tube_profile():
    ri, ro, L = D['tube_id'] / 2, D['tube_od'] / 2, D['tube_len']
    return [(ri, 0), (ro, 0), (ro, L), (ri, L), (ri, 0)]


SCAD = {
    'hull-tube': """// SPDX-License-Identifier: AGPL-3.0-or-later
// ecocell-ocean pressure tube — %gmm OD x %gmm wall x %gmm long
$fn = 128;
difference() {
  cylinder(d=%g, h=%g);
  cylinder(d=%g, h=%g);
}
""" % (D['tube_od'], D['tube_wall'], D['tube_len'],
       D['tube_od'], D['tube_len'], D['tube_id'], D['tube_len']),
    'endcap': """// SPDX-License-Identifier: AGPL-3.0-or-later
// end cap — flange %gmm OD x %gmm, plug %gmm OD x %gmm, 2x AS568-244
// radial grooves (root %gmm, width %gmm). wet=true bores the gland
// seats (1x M20 tether + %dx M16 head glands on %gmm PCD).
$fn = 128; wet = true;
difference() {
  rotate_extrude() polygon(points=%s);
  for (a = [0:%g:359])                      // tie-rod circle
    rotate([0,0,a]) translate([%g/2,0,-1])
      cylinder(d=%g, h=%g);
  if (wet) {
    translate([0,0,-1]) cylinder(d=%g, h=%g);   // M20 tether bore
    for (a = [0:360/%d:359])                     // head gland circle
      rotate([0,0,a]) translate([%g/2,0,-1])
        cylinder(d=%g, h=%g);
  }
}
""" % (D['cap_flange_od'], D['cap_flange_t'], D['plug_od'], D['plug_len'],
       D['groove_root'], D['groove_w'],
       D['gland_head_n'], D['gland_head_pcd'],
       str([[round(r, 3), round(z, 3)] for r, z in endcap_profile(False)]),
       360 / D['tierod_n'], D['tierod_pcd'], D['tierod_d'],
       D['cap_flange_t'] + 2,
       D['gland_tether_d'], D['cap_flange_t'] + 2,
       D['gland_head_n'], D['gland_head_pcd'], D['gland_head_d'],
       D['cap_flange_t'] + 2),
}

os.makedirs(OUT, exist_ok=True)
json.dump(D, open(os.path.join(OUT, 'dimensions.json'), 'w'), indent=1)
revolve_stl(tube_profile(), 'hull-tube')
revolve_stl(endcap_profile(False), 'endcap-dry')
revolve_stl(endcap_profile(True), 'endcap-wet')
for name, src in SCAD.items():
    open(os.path.join(OUT, name + '.scad'), 'w').write(src)
print('wrote', len(SCAD), 'scad sources + dimensions.json ->', OUT)

# ---- STEP export (cadquery, optional) ---------------------------------------
def step_export():
    import cadquery as cq
    ft, pl = D['cap_flange_t'], D['plug_len']

    def cap(wet):
        wp = cq.Workplane('XZ').polyline(
            [(r, z) for r, z in endcap_profile(wet)]).close()
        solid = wp.revolve(360, (0, 0), (0, 1))
        pcd = D['tierod_pcd'] / 2
        holes = (cq.Workplane('XY')
                 .polarArray(pcd, 0, 360, D['tierod_n'])
                 .circle(D['tierod_d'] / 2).extrude(ft + 2)
                 .translate((0, 0, -1)))
        solid = solid.cut(holes)
        if wet:
            solid = solid.cut(cq.Workplane('XY')
                              .circle(D['gland_tether_d'] / 2)
                              .extrude(ft + 2).translate((0, 0, -1)))
            g = (cq.Workplane('XY')
                 .polarArray(D['gland_head_pcd'] / 2, 0, 360,
                             D['gland_head_n'])
                 .circle(D['gland_head_d'] / 2).extrude(ft + 2)
                 .translate((0, 0, -1)))
            solid = solid.cut(g)
        return solid

    tube = (cq.Workplane('XY').circle(D['tube_od'] / 2)
            .circle(D['tube_id'] / 2).extrude(D['tube_len']))
    wet_top = (cap(True).rotate((0, 0, 0), (1, 0, 0), 180)
               .translate((0, 0, D['tube_len'] + ft)))
    assy = (cq.Workplane('XY').add(tube)
            .add(cap(False).translate((0, 0, -ft)))
            .add(wet_top))

    # chassis sled: board (120x90, M3 holes at 3-inset corners) + battery
    # on a plate that slides into the 104mm bore. Width 96 keeps 4mm
    # radial clearance for wire routing past the tray.
    tw, tl, tt = 96.0, 200.0, 3.0
    tray = (cq.Workplane('XY').sketch().rect(tw, tl)
            .circle(tw / 2 - 4, mode='s').finalize().extrude(tt))
    # board's 90mm side spans tray-x (fits Ø104 bore), 120mm along tray-y
    hx, hy = (90.0 - 6) / 2, (120.0 - 6) / 2    # 3mm-inset hole pattern
    hole_pts = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]
    tray = (tray.faces('>Z').workplane().pushPoints(hole_pts).hole(3.2))
    for px, py in hole_pts:                  # M3 standoff bosses, 9mm
        tray = tray.union(cq.Workplane('XY').center(px, py)
                          .circle(4).extrude(9).translate((0, 0, tt)))
    tray = tray.translate((0, 0, D['tube_id'] / 2 - tt - 18))

    # reference float shell: closed-cell-foam outer form carrying
    # antenna + GPS + solar top; sized to spec, carved not machined.
    fw, fl, fh = 140.0, 180.0, 60.0
    flt = (cq.Workplane('XY')
           .box(fw, fl, fh, centered=(True, True, False))
           .edges('|X').fillet(12).edges('>Z').fillet(8))
    flt = (flt.faces('>Z').workplane().rect(80, 60).cutBlind(-6)
           .faces('>Z').workplane().center(0, fl / 2 - 15).hole(8)
           .edges('<<Z').chamfer(1))

    for name, solid in (('hull-tube', tube), ('endcap-dry', cap(False)),
                        ('endcap-wet', cap(True)), ('assembly', assy),
                        ('tray', tray), ('float-ref', flt)):
        cq.exporters.export(solid, os.path.join(OUT, name + '.step'))
        print('wrote', name + '.step')


try:
    step_export()
except ImportError:
    print('cadquery not installed — STEP skipped (pip install cadquery '
          'in a venv for machining-quote exports)')
