# Salton Sea evidence dossier — monitoring-fit review

Review of `salton-sea-evidence.pages.dev` (accessed 2026-11-15, code on
file) against the EcoCell sensor suite. The dossier's Path C is the
hook for us: **"EcoCell-style sensor nodes at the drain/outfall layer
would convert E3 reach-prioritized loads into measured loads"** — 36
priority sites already identified (12 river/drainage terminus "load
gates" + 24 E1 measured-violator outfalls), phased terminus-first.

## What the study actually needs measured

The E1 violation suite (2,303 measured DMR exceedances): selenium,
metals (Cu/Zn/Pb/Tl/Ag/Cr/Hg/Cd/cyanide), nutrients (ammonia, TN,
nitrate, nitrite), salt/TDS, organics (dieldrin, DDT, heptachlor, PAH
suite), plus conventional parameters (pH, DO, TSS/turbidity, flow).
Ambient Sea impairment context: salinity, nutrients, HABs/cyanotoxins,
dust/PM.

A "measured load" = concentration × flow. DMR data already carries
self-reported flow for permitted outfalls; the gap the dossier names is
**ambient verification** — is what the outfall reports actually in the
receiving water, and what is the diffuse drainage load at the river
termini?

## Coverage matrix

| Study parameter | Our hardware | Status |
|---|---|---|
| Water temperature | BME280 (pod interior) / RTD-able | covered |
| Conductivity → salinity/TDS | ADS1220 + 4-electrode CTD cell (J_CTD) | covered — the salt-suite context parameter |
| Stage / water level | BMP390 pressure → level at fixed mount | covered; needs stilling-well mount note |
| Flow | — | partial: DMR carries flow for permitted outfalls; river termini need stage + rating curve (survey task, not a sensor purchase) |
| pH | ADS8681 ch.2–7 free; TI pH reference design exists for this part | **gap — add glass-electrode probe head** |
| Dissolved oxygen | — | **gap — Atlas EZO-DO (I2C) or optical cap on spare AIN** |
| Turbidity / TSS proxy | — | **gap — analog nephelometer on spare AIN; best low-cost proxy for metals/sediment loading, corroborates Sentinel-2 screening in their research doc** |
| Nitrate/nitrite/ammonia/phosphate | — | **in-situ analyzers exist** but not at node cost: submersible wet-chem probes (Systea WIZ/NPA; Kekan KK-750 ~$2,750, ±10%, 0–10 m, ~10 W) and UV nitrate (Sea-Bird SUNA ~$15–20k). Cheap ISEs (~$100) fit our I2C but are event-detection grade only — drift, matrix effects, not evidentiary |
| Metals (Cu/Pb/Cd/Zn) | — | **in-situ voltammetric probes exist** (Idronaut VIP, IFREMER TracMetal — ng/L sensitivity, autonomous) but measure the bioavailable/*dynamic fraction*, not the total concentration DMR/permit limits use. Research-instrument cost; cannot substitute for the analyte |
| Selenium | — | **no deployable in-situ sensor** — ICP-MS lab only. Research microelectrodes measure Se(IV) only; no field product |
| Organics, PFAS, legacy pesticides | — | **no in-situ analyte sensor**. Fluorescence/fDOM probes (incl. Virridy Lume) estimate contamination *risk* — a screening index, not a measured concentration. However: **autonomous in-situ SPE samplers** can collect these analytes automatically for later lab elution — collection is automatable, analysis is not |
| HABs / cyanotoxins | camera (visual bloom evidence) + turbidity proxy | partial — camera documents blooms; toxin needs lab |
| Air PM (dust crisis) | SPS30 PM1/2.5/4/10 + number counts | covered |
| Wind (dust transport attribution) | — | **gap on land nodes — $25–45 anemometer; without it PM events can't be source-attributed** |
| Bioacoustics / visual | hydrophone, mics, OV2640 camera | covered — fish-kill/mortality events are acoustic+visual evidence |
| Provenance / receipts | quorum-witnessed records, SHA-256 manifests | covered — matches their E1–E4 tier model; our records slot between E3 and E1 as independent ambient measurements |

## Board headroom (no respin needed)

The ocean board already has the analog front-end density for the Tier-1
additions:

- **ADS8681 (U_ADC)** uses 1 of 8 channels (ADC_AIN). Channels 2–7 are
  free; the part has an integrated easy-drive buffer rated for
  high-impedance probes — TI publishes a pH-measurement reference
  design on it.
- **I2C bus** (R_I2C_SCL/SDA, TCA9535 expander) takes Atlas Scientific
  EZO probes (pH/DO/ORP/nitrate) with zero board changes.
- **Probe-head penetrator architecture** (PRESSURE-SPEC.md) already
  anticipates wet-side heads on glands — pH/DO/turbidity heads are
  additional penetrators, not a redesign.

## Recommended additions

**Tier 1 — add to pod BOM (~$80–150/node):**
- pH: Atlas EZO-pH (I2C, ~$60) or glass-electrode + ADS8681 channel
- DO: Atlas EZO-DO (I2C, ~$70) — fish-kill detection is a headline Salton Sea issue
- Turbidity: analog nephelometer (~$25–40) → spare ADS8681 AIN
- Optional: ORP EZO for redox context (selenium speciation depends on it)

**Tier 1 — land nodes (~$30):**
- Wind speed + direction anemometer (pulse/I2C → MCU) — required for
  dust-source attribution, the Sea's stated health crisis

**Tier 2 — process + borrowed instruments:**
- Lab-grab protocol: node anomaly (turbidity/DO/pH excursion) triggers
  a sampling event flag in the record; partner lab runs the Se/metal/
  nutrient/organics panel. This mirrors their E1/E3 honesty split —
  we never dress surrogate data as analyte measurements.
- **Nutrient analyzer co-location** — if budget allows, park 1–2
  submersible wet-chem analyzers (Kekan KK-750-class ~$2.75k, or a
  Systea WIZ rental) at the highest-priority terminus sites. NH3/NO2/
  NO3/PO4 measured continuously at real analyte level; EcoCell nodes
  flank them for the cheap physical context.
- **Autonomous SPE sampling** — passive/passive-extraction samplers
  (e.g., sorbent cassettes swapped on the 6-month service interval)
  collect organics/metals/PFAS automatically in-situ; lab elutes and
  runs the panel. This closes the "unmeasurable" analytes with a
  collection-automation answer rather than a sensor answer.
- Flow: survey rating curves at the 12 terminus sites; rely on DMR
  flow for the 24 outfalls.

## What "measurable in-situ" actually means here (verified 2026-11-15)

| Analyte | Deployable in-situ? | What exists | Cost tier | Evidentiary-grade? |
|---|---|---|---|---|
| Nitrate/nitrite | yes | wet-chem submersible analyzers (WIZ, NPA, KK-750); UV (SUNA) | $3k–20k | yes — wet-chem analyzers; NO — $100 ISEs (event detection only) |
| Ammonium | yes | same wet-chem units; ISEs | $3k–20k | yes (analyzer) / no (ISE) |
| Phosphate | yes | same wet-chem units | $3k–20k | yes (analyzer) |
| Cu/Pb/Cd/Zn | partial | voltammetric probes (Idronaut VIP, TracMetal) | research $$$ | measures dynamic fraction, not DMR-comparable total |
| Selenium | **no** | lab ICP-MS only; research Se(IV) microelectrode | — | — |
| Hg/As | partial (research) | TracMetal reports Hg(II)/As(III) | research | not productized |
| Organics/PFAS/pesticides | **no sensor** | fluorescence risk indices only (Virridy Lume et al.) | — | screening index, never an analyte |
| pH/DO/turbidity/EC/stage | yes | our probes | <$100 | yes |

## Bottom line

The platform covers the physical/context layer (T, salinity, stage,
PM, acoustics, imagery, provenance). For the chemical suite the honest
answer is split: **nutrients are automatable in-situ at instrument tier
($3k–20k submersible analyzers — a co-location purchase, not a node
sensor); Se, metals (as DMR-comparable totals), and organics are not
measurable in-situ at any node-relevant cost** — but collection can be
automated via SPE cassettes for lab elution. With ~$100 of Tier-1
probe heads + a wet-chem analyzer on loan at the top terminus sites,
the deployment produces real measured loads for the nutrient lane and
honest surrogate-context + automated collection for everything else —
exactly the E-tier honesty the dossier demands.
