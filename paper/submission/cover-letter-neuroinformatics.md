<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# Cover letter — *Neuroinformatics* (Springer)

Dear Editors,

We submit "Machine-checkable ecological evidence: replay-verified
computation over biological connectomes in a consent-gated sensing
commons" for consideration in *Neuroinformatics*.

The paper contributes (i) a deterministic simulation and
replay-verification discipline for biological connectomes — fixed-point
LIF semantics under which independent implementations reproduce
spike-raster digests bit-for-bit; (ii) WiredReplay-1, an open
conformance corpus of fifteen packed wiring diagrams (cellular EM and
mesoscale, resolution declared per dataset) with canonical test vectors
and expected digests, intended as a shared standard for validating
connectome simulators; and (iii) a consent-gated protocol architecture
in which witnessed, content-addressed verdicts serve as receipts for
ecological sensing claims, with refusal modelled as a first-class
protocol value.

We believe the work fits *Neuroinformatics*' scope: it is a
computational-infrastructure contribution over neuroinformatics
resources (public connectome reconstructions) with an explicit
reproducibility artifact. All quantitative results are reproduced by
commands in the accompanying reproducibility capsule; artifacts and
hashes ship in the repository. The code is AGPL-3.0; the corpus spec
and vectors are CC-BY-4.0.

We report a negative result deliberately: a degree-matched shuffled
control shows the measured efficiency gain comes from the sparse packed
representation rather than biological topology, and a small-wiring
benchmark (C. elegans) where the method underperforms both baselines.

The manuscript is original, not under consideration elsewhere, and
contains no human or animal subjects research. A preprint posting
(arXiv or bioRxiv) is planned concurrently; we will update the record
with its identifier when assigned.

Suggested and opposed reviewers are listed in the accompanying
reviewer checklist.

Sincerely,
Thomas R. Price
Temple Earth (Treetable LLC), Colorado, USA
hello@templeearth.cc
