<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# Account/action checklist — what needs Thomas before submission

All free. Order matters for the endorsement-dependent steps.

- [x] **ORCID iD** — registered 2026-10-26:
  **0009-0009-7108-919X** (https://orcid.org/0009-0009-7108-919X).
  Credentials at `~/.local/share/devin/orcid.txt` (outside repo).
- [ ] **Preprint account** — bioRxiv (no endorsement needed; has a
  direct B2J "PCI Ecology" submission route at the end of its form)
  or arXiv (cs.NI / q-bio.NC; first-time submitters need an
  endorsement code from an established arXiv author — line one up
  early). PCI Ecology accepts bioRxiv, EcoEvoRxiv, arXiv, HAL, Zenodo.
- [x] **Zenodo** — GitHub OAuth authorized, living-resources switch
  ON, `paper-v1` release archived: **DOI 10.5281/zenodo.23681503**
  (cite line updated in `corpus/README.md` and `main.tex`).
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
