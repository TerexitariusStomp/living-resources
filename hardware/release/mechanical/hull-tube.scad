// SPDX-License-Identifier: AGPL-3.0-or-later
// ecocell-ocean pressure tube — 110mm OD x 3mm wall x 240mm long
$fn = 128;
difference() {
  cylinder(d=110, h=240);
  cylinder(d=104, h=240);
}
