---
title: 'Credits & licenses'
layout: '~/layouts/MarkdownLayout.astro'
---

This site is built on open source and public-domain media — the same way the whole
project is built: adopt the commons, credit it, add as little custom as possible.
Target: ≤5% custom code (enforced by `tools/site/budget.py`).

## Data

- **Plant ultrasound recordings** — Khait et al., _Cell_ 2023
  ([doi:10.1016/j.cell.2023.03.009](https://doi.org/10.1016/j.cell.2023.03.009));
  Dryad dataset [doi:10.5061/dryad.jwstqjqf7](https://doi.org/10.5061/dryad.jwstqjqf7),
  released **CC0**. Slowed ~11× by `tools/site/plant_audio.py`.
- **Connectome wiring data** — see `docs/CONNECTOME.md` in the repository for the
  per-dataset citations (EM reconstructions, various open licenses).

## Imagery (Wikimedia Commons, public domain / CC0)

- Hero forest — _Hoh Rainforest, mossy log tree_, NPS / Olympic National Park (public domain)
- Tomato physiologist — Scott Bauer, USDA-ARS (public domain)
- Forest floor fungi — Bernard Spragg, NZ (public domain)
- Reef diver — NOAA National Marine Sanctuaries (public domain)
- Amazon from orbit — NASA / Jeff Schmaltz, MODIS Rapid Response (public domain)

## Open source

| Component                                                                                    | License           |
| -------------------------------------------------------------------------------------------- | ----------------- |
| [Astro](https://astro.build) + [AstroWind template](https://github.com/arthelokyo/astrowind) | MIT               |
| [Tailwind CSS](https://tailwindcss.com)                                                      | MIT               |
| [Three.js](https://threejs.org)                                                              | MIT               |
| [cobe globe](https://github.com/shuding/cobe)                                                | MIT               |
| [wavesurfer.js](https://wavesurfer.xyz)                                                      | BSD-3-Clause      |
| [astro-icon](https://github.com/natemoo-re/astro-icon) + Tabler icons                        | MIT               |
| Inter + JetBrains Mono fonts                                                                 | SIL OFL           |
| living-resources itself                                                                      | AGPL-3.0-or-later |
