// SPDX-License-Identifier: AGPL-3.0-or-later
// The claim ledger — every headline claim on the landing page, its real
// status in one plain line (`plain`), and the technical footnote
// (`body`) rendered on /developers. TierLink anchors point at the `id`s.

export interface HonestyRow {
  id: string;
  /** the claim, quoted as it appears on the page */
  title: string;
  /** one plain-English line summarizing the claim's real status */
  plain: string;
  /** the technical footnote — shown on /developers, readability-exempt */
  body: string;
}

export const honesty: HonestyRow[] = [
  {
    id: 'truth-jobs',
    title: '"Nature listens, thinks, remembers"',
    plain:
      'Each part is at a different step. Listening is built. Receipts are live. Brain-map thinking runs on ordinary computers today.',
    body: `Listen — <b>built</b>, field test E0 next. Check — <b>works today</b> via the live receipt API
      (<code>/verify</code>). Think — <b>works today</b> on silicon over real connectomes; organism compute itself is
      refused. Remember — receipts <b>today</b>; organism-bound store is <b>consent-gated</b>; DNA storage is
      <b>someday</b>. The split is the point.`,
  },
  {
    id: 'truth-plant-sound',
    title: '"A thirsty plant makes a sound"',
    plain:
      'Real science from 2023. The clicks are actual plant recordings, slowed so we can hear them. Our own boxes still need their outdoor test.',
    body: `The clicks are real — recorded by Khait et al., published in <em>Cell</em> 2023, released CC0 on Dryad. What you
      hear is a ~11× slowdown of actual 500&nbsp;kHz recordings; the plant's own signal, transposed into human hearing.
      Our hardware can't yet record those — field validation (E0) is pending.
      <a class="underline" href="https://doi.org/10.1016/j.cell.2023.03.009">paper</a> ·
      <a class="underline" href="https://doi.org/10.5061/dryad.jwstqjqf7">data</a>`,
  },
  {
    id: 'truth-listener',
    title: '"A $40 listener that never touches anything"',
    plain:
      'The box is built and its software passes every check. It has not spent a season outdoors yet — that test is next.',
    body: `EcoCell One exists as a manufacturable KiCad board (real Gerbers, pick-and-place files) plus MicroPython
      firmware that passes its e2e suites. It has not yet been deployed in a field pilot — that is what E0 tests.`,
  },
  {
    id: 'truth-loop',
    title: '"Nature is already worth more alive"',
    plain:
      'The credit and guardian machinery is built and tested. Whether it protects nature for real is the question we exist to answer.',
    body: `The mechanism is implemented and e2e-tested — quorum witnessing (<code>attest.scm</code>), per-contribution
      mutual credit (<code>settlement.scm</code>), guardian custody (<code>agents.scm</code>). Whether that changes
      real-world protection economics is the hypothesis this project exists to test — not a measured result.`,
  },
  {
    id: 'truth-network',
    title: '"Send a signal through 15 real brain maps"',
    plain:
      'You can call the brain maps right now — every answer can be replayed. The globe dots are where listeners could go, not where they are.',
    body: `Live today: deterministic LIF tasks over 15 EM-derived connectome wirings, every receipt replayable — TS port
      verified bit-identical to the Python engine (930/930 checks). The globe markers are places the living cloud
      <em>could</em> listen; no field nodes are deployed yet.`,
  },
  {
    id: 'truth-promises',
    title: '"Four rules the whole cloud follows"',
    plain:
      'These are rules written in code, not promises on a poster. The code itself refuses actions that break them.',
    body: `Not aspirations — code. The lane gate (<code>lane-gate.rego</code> / <code>offers.scm</code>) admits evidence
      lanes only with an evidence fingerprint, consent lanes only with a joint guardian+operator credential, and
      refuses <code>hop</code>, <code>compute</code>, and <code>engineered</code> outright. 121/121 e2e checks pass.`,
  },
  {
    id: 'truth-cloud-map',
    title: '"One organism that grows with nature"',
    plain:
      'One step at a time. Computers still win on speed today — we measured it, and we say so.',
    body: `The next-cloud thesis, on the record: one step at a time, silicon wins <em>today</em> — measured and we
      say so. Per watt and at scale, published evidence already favors living systems; turning that into useful work
      is the roadmap above.`,
  },
  {
    id: 'truth-organism',
    title: '"An AI organism that grows with nature"',
    plain:
      'The “organism” is a way of picturing real working parts. The helper is a rule-following program, not a living mind.',
    body: `The nested organism is a metaphor over real parts. Each ecosystem's companion is an <code>^eco-agent</code>
      actor (<code>agents.scm</code>, e2e-tested): a capability-secure record with guardian custody and voice 0 —
      <b>not a learning model</b>. The ears already use AI: OpenSoundscape/BirdNET models via
      <code>classify.py</code>, with an energy-gate fallback. Duty-cycling runs on fixed dawn/dusk windows, re-tunable
      by a consent-gated <code>duty</code> downlink; autonomous tuning is not built. The sparse-wiring footprint is
      measured (46×–5,900× smaller, ~70× J at medulla) — and the degree-matched shuffle control shows the gain is
      <b>sparsity</b>, not biological topology. Generational replace-only-if-receipts-show-less is a proposed rule,
      measurable today with E6 replay bundles, not yet enforced. Moving work into living systems stays behind the
      consent and refused lanes.`,
  },
  {
    id: 'truth-federation',
    title: '"You are not the first ears out here"',
    plain:
      'Those device numbers belong to the partner networks — their devices, their counts, labeled as theirs. Write devices always need their owner to say yes.',
    body: `The device counts are the networks' own published numbers, spot-checked live (BirdWeather's public graph
      returned 26k+ stations when we looked). Federated imports ride provenance — each record names whose device
      heard it — and are never shown as our quorum. Writes are different: every actuator is owner-keyed.
      <b>Open-invitation</b> means a stranger may drive it under the owner's published terms (FarmBot's demo garden
      is the working example); <b>opt-in</b> fleets mean the owner must volunteer. Nobody's device is reachable by
      default. Your browser's permission prompt is the operator consent — and nothing is recorded unless you say yes.`,
  },
  {
    id: 'truth-market',
    title: '"Not just proof — sensing, compute and storage by nature"',
    plain:
      'Market sizes come from outside researchers. Useful direction, not our measurement. No revenue yet.',
    body: `Market sizes are third-party research estimates, cited — not our measurements. Pricing tiers are real
      numbers from our funding docs, but billing isn't wired and no revenue is claimed. The ladder is the plan, in
      order: services → hardware → catalogue → credit rails.`,
  },
];
