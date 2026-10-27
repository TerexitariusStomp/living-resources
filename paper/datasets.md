<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# Corpus datasets — provenance, resolution, licensing

The 15 packed wiring diagrams in `~/fly-data/packed/` (consumed via
`CONNECTOME_PACKED_DIR`, produced by `pack_connectomes.py` —
alextitonis/fly.ai FlyBrain MIT CSR format). **The paper's dataset table
is generated from this file — keep it accurate.**

Resolution classes matter: reviewers will check that a 49-neuron
"drosophila" is described as a *mesoscale* diagram, not a cellular
connectome.

| name | neurons | synapses | packed bytes | resolution | likely upstream source | license tier |
|---|---:|---:|---:|---|---|---|
| celegans | 302 | 3,009 | 7,825 | cellular EM | WormWiring — Cook et al. 2019 (Nature), White et al. 1986 lineage | published/academic — cite + checksum |
| celegans_herm | 453 | 4,878 | 12,648 | cellular EM | WormWiring — Cook et al. 2019 hermaphrodite | published/academic |
| celegans_male | 575 | 5,305 | 13,838 | cellular EM | WormWiring — Cook et al. 2019 male | published/academic |
| drosophila | 49 | 1,950 | 4,924 | **mesoscale** (region-level, NOT FAFB cellular) | verify source — coarse fly-brain graph | verify |
| human | 234 | 7,076 | 17,924 | **mesoscale** (parcellated structural, DTI-class) | Hagmann-class human parcellation | verify |
| mouse | 112 | 6,542 | 16,467 | **mesoscale** | Oh et al. 2014-class interareal matrix | verify |
| rat | 73 | 1,923 | 4,881 | **mesoscale** | BAMS/Bota–Swanson rat connectivity | verify |
| macaque | 93 | 1,692 | 4,323 | **mesoscale** | CoCoMac-derived cortical graph (Markov/Kennedy class) | verify |
| macaque_modha | 242 | 4,090 | 10,467 | **mesoscale** | Modha & Singh 2010 macaque long-distance pathways | published |
| ciona | 205 | 2,902 | 7,460 | cellular EM | Ryan et al. 2016 — *Ciona intestinalis* larva | published/academic |
| larva | 3,016 | 30,149 | 78,389 | cellular EM | Janelia — Drosophila L1 larva CNS (Ohyama/Gerhard class) | Janelia — CC-BY |
| platynereis | 5,000 | 49,991 | 129,978 | cellular EM | Jékely lab — Verasztó et al., *Platynereis dumerilii* larva | published/academic |
| mouse_retina | 1,124 | 90,009 | 227,271 | cellular EM | Helmstaedter et al. 2013 (Nature) — iMICrONS retina | published/academic |
| hemibrain | 21,636 | 216,310 | 584,047 | cellular EM | Janelia hemibrain v1.x — Scheffer et al. 2020 (eLife) | Janelia — CC-BY |
| medulla | 40,000 | 399,950 | 1,079,875 | cellular EM | Janelia FIB-SEM optic lobe — Takemura et al. 2015/2017 | Janelia — CC-BY |

## License tiers for corpus packaging

- **CC-BY (blobs may ship)**: hemibrain, medulla, larva — Janelia terms
  permit redistribution with attribution.
- **Published/academic (cite + checksum; ship only if terms confirm)**:
  celegans×3, ciona, platynereis, mouse_retina, macaque_modha.
- **Verify before shipping**: drosophila, human, mouse, rat, macaque —
  mesoscale sources need upstream identification first.
- **Not in corpus**: `~/fly-data/connectomes/` also contains
  allen-mouse, banc, cat-cortex, fafb-cb, malecns, manc, marmoset,
  microns, mretina — unpacked; excluded (MICrONS/Allen terms would be
  cite-only anyway).
- **Always shipped**: per-blob SHA-256 checksums, `pack_connectomes.py`,
  `all_connectomes.json`, and expected-digest test vectors — the corpus
  is verifiable even where blobs are cite-only.

## Open verification items (Phase 0)

- [ ] Confirm drosophila(49), human(234), mouse(112), rat(73),
      macaque(93) upstream datasets — check `weights.npz` headers and
      any download logs in ~/fly-data or the fly.ai repo
- [ ] Confirm Janelia terms cover *derived packed* redistribution
      (CC-BY yes; mark bundle "derived from Janelia hemibrain v1.x,
      CC-BY 4.0")
- [ ] Record exact upstream URL/DOI per row for the paper's data
      availability statement
