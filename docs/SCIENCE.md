# SCIENCE — claim table

Every claim the system rests on, with its evidence status. This file is
the honesty layer: a lane ships only as far down this table as its row
says.

## Demonstrated

| Claim | Source | Consequence |
|---|---|---|
| Plants emit airborne ultrasonic clicks under stress (drought, cut) | Khait et al., *Cell* 2023 — tomato ~35/h, tobacco ~11/h, 20–100 kHz | Real signal; needs ≥40 kHz mic — our `ultra` head, not the 48 kHz audio mic |
| Reef acoustic complexity tracks biodiversity and recovery | J Appl Ecol 2022 (restored reefs sound like healthy reefs) + 2025 human-in-the-loop AI over 12 mo × 45 sites | Reef-health lane demonstrated; dense cheap hydrophone cells are the contribution |
| Biofilms propagate K⁺ electrical waves (YugO channels) | Prindle et al., *Nature* 2015 | Biofilm readout lane has a physical substrate |
| Separate biofilms co-synchronize growth for nutrient time-sharing | Liu et al., *Science* 2017 | Two-culture interlink is plausible |
| K⁺ waves attract distant motile cells across species | Humphries et al., *Cell* 2017 | Biofilm is a broadcast channel, not just internal |
| Passive acoustics + human validation produce credible MRV | standard practice; SAGED criteria below | Our guardian/witness architecture matches field methodology |
| C4D (capacitively-coupled contactless conductivity detection) | established analytical technique | Non-invasive biofilm electrical readout through vessel walls |

## Plausible (worth an experiment, not a lane)

| Claim | Status |
|---|---|
| Reef/vegetation acoustic "enrichment" attracts larvae | Demonstrated as an effect — but it is an *emitting* lane; consent-gated, never default |
| Built-in speaker/mic Doppler senses leaf/canopy motion at 19–22 kHz | SoundWave-like; band overlaps bat/pet/insect hearing — emission requires consent |
| Wild biofilm dynamics usable as a reservoir compute substrate | Unproven — E-gated research lane |

## Unproven or refused

| Claim | Status |
|---|---|
| Plant-to-plant acoustic communication | Unproven (New Phytologist reviews) |
| General-purpose computation in living systems | Unproven (Pieters Sci Rep 2022 — eco-physiological tasks only) |
| Ultrasound as a programmable instruction set for wild organisms | Refused — perturbation ≠ programming; engineered circuits out of scope |
| `hop`/`compute`/`store`-into-organism lanes | Refused until evidence SAID lands |

## SAGED MRV criteria (Ford et al., J Appl Ecol 2024)

| Criterion | How v1 meets it |
|---|---|
| Scalable | ~$35–45 universal node, duty-cycled, store-and-forward |
| Accessible | open hardware, open firmware, open pipeline |
| Granular | per-detection records with confidence + SAIDs |
| Evidenceable | lossless media in content store + detection ledger, calibration SAID per node |
| Directly measured | passive sensing of the actual ecology — not proxy inference; **taxa-scope declared honestly on every offer** |

## Known limits, stated

- Fish species-level ID is weaker than bird ID — many reef calls
  unidentified; scope declares `reef` not species.
- Snapping-shrimp energy extends past 24 kHz — our `hydro` lane covers
  the core band; partial coverage is declared.
- Reef sound propagation is geometry-sensitive (2026 review) —
  hydrophone depth and duty-cycle are part of every deployment record.
