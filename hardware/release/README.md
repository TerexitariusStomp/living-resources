




























| Enclosure revision | `TBD` — pressure-hull + biota-disguised float CAD pending |
| Firmware revision | `firmware/node/main.py` as committed; image hash recorded per unit |
| Regional radio variant | `E22-400M22S` (433 MHz) or `E22-900M22S` (868/915) — one per build, declared |
| Approved suppliers | `TBD` — quote-backed, per-part, with lifecycle/stock check |

## Release artifacts (required for R0)

| Artifact | Path / source | Status |
|---|---|---|
| Native KiCad schematic | `hardware/release/electrical/` | **missing** — ocean respin required |
| Native KiCad PCB | `hardware/release/electrical/` | **missing** — ocean respin required |
| Gerbers + drill (or IPC-2581) | `hardware/release/electrical/` | **missing** — regenerate post-respin |
| Board stack-up / fab drawing | `hardware/release/electrical/` | **missing** |
| Controlled BOM (MPN + alternates) | `hardware/release/bom/` | **partial** — `hardware/BOM.md` + `hardware/FIELD-KIT.md` updated; quote-backed MPNs pending |
| CPL with verified origin/rotation | `hardware/release/assembly/` | **missing** — regenerate post-respin |
| Assembly drawing | `hardware/release/assembly/` | **missing** |
| Harness drawings | `hardware/release/harness/` | **missing** |
| Mechanical CAD + STEP + drawings | `hardware/release/mechanical/` | **missing** — pressure hull, optical port, tether, float |
| Pressure/leak spec | `hardware/release/mechanical/` | **missing** — derive from deployment envelope |
| Test fixture spec | `hardware/release/TEST-PLAN.md` | **present** |
| Unit traveler / calibration record | `hardware/release/UNIT-TRAVELER.md` | **present** |
| Firmware image + hash | `firmware/node/` build | **partial** — source present; reproducible build/hash pending |
| Release manifest + checksums | `hardware/release/manifest.json` | **present** |
| DFM/DFT review record | `hardware/release/` | **missing** — supplier engagement required |

No artifact may be silently replaced: any change goes through the ECO
procedure below and bumps the relevant revision.

