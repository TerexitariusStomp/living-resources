<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# Assembly drawing — ecocell-ocean R0

- `assy-top.svg` — F.Fab + F.Silkscreen + courtyards + edge: refdes and
  outlines for every top-side part.
- `assy-bottom.svg` — B.Fab + B.Silkscreen + courtyards: 0603 passives
  + LDR on the bottom.
- Polarity: D_CHRG/D_STDBY (LEDs) — silk cathode bar; JST/J-header
  connectors are keyed by footprint; verify TP4056 SOIC-8-EP substitute
  pad fit on the first article (see FAB-NOTES + CHANGELOG).
- Fiducials FID1–6 are on both drawings inside the U_MCU courtyard —
  bare pads, not components (declared deviation, see FAB-NOTES).
- PTH (JST XH + 2.54 headers + SD socket) — wave or hand; microSD
  Molex 104031-0811 wants paste-in-hole or careful hand reflow.
