<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# Account/action checklist — what needs Thomas before submission

All free. Order matters for the endorsement-dependent steps.

- [ ] **ORCID iD** — register at orcid.org (2 min). Required by the
  Springer Editorial Manager submission and most venues.
- [ ] **Preprint account** — bioRxiv (no endorsement needed; has a
  direct B2J "PCI Ecology" submission route at the end of its form)
  or arXiv (cs.NI / q-bio.NC; first-time submitters need an
  endorsement code from an established arXiv author — line one up
  early). PCI Ecology accepts bioRxiv, EcoEvoRxiv, arXiv, HAL, Zenodo.
- [ ] **Zenodo** — sign in with GitHub OAuth; enable the
  living-resources repo; the `paper-v1` tag release mints the DOI
  automatically. Update README/corpus cite line with the minted DOI.
- [ ] **GitHub release** — create release on tag `paper-v1` after the
  artifact/corpus commits land (Zenodo picks it up).
- [ ] **Editorial Manager account** — *Neuroinformatics* portal at
  springer.com/journal/12021 (submission guidelines: "Research
  Article" type; single-blind or double-blind per journal policy —
  check at submission time).
- [ ] **PCI Ecology account** (fallback path only) — register at
  ecology.peercommunityin.org; needs the preprint DOI first, plus
  **5–10 suggested recommenders** and the Zenodo data/code DOIs ready
  at submission time.
- [ ] **Author sign-off** — read main.tex end-to-end; the manuscript
  asserts sole authorship, self-funding, and a competing-interest
  statement (Temple Earth operator). Confirm all three are true.
- [ ] **License confirmation** — spot-check the corpus license tiers
  in `paper/datasets.md` against upstream terms before the release
  ships packed blobs (CC-BY tiers redistribute; cite-only tiers stay
  checksum-only — see README wording).

## After submission

- Save the Editorial Manager confirmation number + PDF proof into
  `paper/submission/`.
- Update `docs/FUNDING.md`/site claim labels only when a decision
  letter arrives — "submitted" ≠ "accepted" anywhere public.
