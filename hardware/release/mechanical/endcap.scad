// SPDX-License-Identifier: AGPL-3.0-or-later
// end cap — flange 118mm OD x 12mm, plug 103.7mm OD x 20mm, 2x AS568-244
// radial grooves (root 98.1mm, width 4.6mm). wet=true bores the gland
// seats (1x M20 tether + 3x M16 head glands on 60mm PCD).
$fn = 128; wet = true;
difference() {
  rotate_extrude() polygon(points=[[0, 0], [59.0, 0], [59.0, 12.0], [51.85, 12.0], [51.85, 15.0], [49.05, 15.0], [49.05, 19.6], [51.85, 19.6], [51.85, 21.6], [49.05, 21.6], [49.05, 26.2], [51.85, 26.2], [51.85, 31.0], [50.85, 32.0], [0, 32.0]]);
  for (a = [0:60:359])                      // tie-rod circle
    rotate([0,0,a]) translate([114/2,0,-1])
      cylinder(d=6, h=14);
  if (wet) {
    translate([0,0,-1]) cylinder(d=20.5, h=14);   // M20 tether bore
    for (a = [0:360/3:359])                     // head gland circle
      rotate([0,0,a]) translate([60/2,0,-1])
        cylinder(d=16.5, h=14);
  }
}
