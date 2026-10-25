<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# NSF SBIR Phase I — full proposal draft skeleton ($275k)

Entity + SAM.gov confirmed — eligible today. SBIR proposals are structured;
this maps our content to their required sections. Check the current
solicitation window (typically 3/yr) at seedfund.nsf.gov.

## Project title

Verifiable Ecological Sensing: Content-Addressed Evidence Chains for
Biodiversity and Environmental Monitoring

## Pitch (their format)

### The problem

Environmental and biodiversity data lacks provenance integrity.
Readings from distributed sensors are indistinguishable from fabricated
data once exported; aggregate reports can't be audited. This blocks
trust in biodiversity credits, carbon MRV, regulatory compliance, and
federated science.

### The innovation

A sensing pipeline where every reading is content-addressed (SAID),
merged by independent-node quorum, and issued as a witnessed,
replay-verifiable receipt — plus deterministic replay-verified
computation (input→trace digest→independent replay reproduces
bit-for-bit). Technical novelty: evidence travels *with* the reading;
verification is a property of the artifact, not the vendor's word.

### Technical risk addressed in Phase I

- Quorum integrity under heterogeneous, intermittently-connected nodes
  (Reticulum/LXMF store-and-forward under real field conditions)
- Replay verification performance at fleet scale (bundle digests
  over thousands of readings)
- Calibration-to-receipt binding: can a witnessed receipt carry
  sensor-calibration provenance end-to-end?

### Commercial opportunity

MRV/biodiversity-monitoring buyers facing integrity scrutiny (carbon
project developers post-ICVCM, insurers, compliance). Revenue model:
node hardware + verification services + hosted receipt catalogue.
Comparable spend: conservation-tech + MRV is a multi-$B and growing
segment; integrity tooling is the acknowledged bottleneck.

## Phase I work plan (6–12 mo, $275k)

| Work package | Months | $ |
|---|---|---|
| WP1 Receipt protocol hardening + calibration binding | 1–4 | 80k |
| WP2 Fleet-scale replay/verification benchmark | 2–6 | 70k |
| WP3 Field deployment: 10-node pilot, soak test | 4–10 | 90k |
| WP4 Commercialization: pilot customers + Phase II prep | 8–12 | 35k |

## Required appendices checklist

- [ ] Company commercialization history
- [ ] Letters of support (a conservation/monitoring partner — get one)
- [ ] Facilities + equipment (field access + this machine's RAPL bench)
- [ ] Data management plan
- [ ] 2-page concept note attached from `concept-note.md`

## Reviewer-proofing notes

- SBIR wants *innovation* + *commercialization*: lead technical novelty
  (replay-verified evidence) then market
- Include the measured-efficiency table — reviewers reward honesty
  signaling; the "we published our unfavorable numbers" point lands
