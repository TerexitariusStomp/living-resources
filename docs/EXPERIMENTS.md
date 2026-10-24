# EXPERIMENTS — the E-series gates

An experiment is how a lane earns its evidence SAID. Each has a pass
criterion stated *before* it runs, and a refusal is a valid result.

## E0 — sensing-cell validation (gates everything)

- **What:** does our hardware detect what we claim?
- **Method:** universal node + laptop edge; (a) replay known
  xeno-canto/class-labeled recordings through the mic path and score the
  classifier, (b) 48-h field capture at a real site, detections scored
  blinded by a human validator.
- **Also checks:** camera phenology frames, env context stamp, SD spool +
  reconnect replay, detection-first flush ordering.
- **Pass:** precision at the declared taxa-scope ≥ target set with the
  validator before scoring; no unrecovered spool loss on a forced
  disconnect.
- **On pass:** `sense`/`fleet` evidence SAID lands in the gate book;
  offers may be declared. On fail: the pipeline fixes, not the claim.

## E1 — speaker-Doppler canopy motion (consent-gated)

- **What:** 19–22 kHz emission + mic Doppler reads leaf/canopy motion.
- **Status:** emitting lane — requires joint guardian+operator consent
  *and* a site assessment for bat/pet/insect hearing overlap before the
  consent is exercised. Likely outcome: refused at most sites; documented
  either way.
- **Pass:** motion correlation vs sham recording, at minimum power and
  duty cycle.

## E2 — ultrasonic plant clicks (natural dry-down)

- **What:** `ultra` head (20–100 kHz) detects stress clicks from plants
  drying naturally — never induced stress; that would be an emitting act
  on the organism.
- **Pass:** click rate correlates with dry-down stage vs hydrated control
  (Khait et al. rates as prior: tomato ~35/h stressed, ~0 hydrated).

## E3 — C4D biofilm readout (wild *B. subtilis*)

- **What:** C4D front-end reads K⁺-wave signatures through a culture
  vessel wall — contactless, nothing enters the culture.
- **Pass:** periodic signal matching published wave dynamics vs media-only
  control; readout qualifies the `c4d` head for read lanes only —
  compute claims still wait for E4+.

## Emission protocol (applies to every emit act, E-gated or consented)

1. Joint guardian + node-operator consent SAID — required, recorded.
2. Site habitat assessment: band overlap with local sensitive taxa.
3. Minimum power, duty-cycled (firmware ceiling: ≤50 ms on, ≥950 ms off).
4. Every burst logged + receipted — the commons sees each emission.
5. Any sign of behavioral disruption in the sensing data → stop, log,
   revisit consent.
