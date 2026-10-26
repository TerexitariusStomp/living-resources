<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# Filecoin Open Grant — issue-ready draft (up to $50k)

Submit: new issue at github.com/filecoin-project/devgrants with the
"Open Grant Application" template. Paste the sections below verbatim.
License note: grant-funded work (the Filecoin evidence-store adapter)
ships MIT/Apache-2 dual-licensed as required; the surrounding commons
stays AGPL-3.0 — answer "Yes" since the funded deliverable complies.

---

# Open Grant Proposal: `Receipted ecological evidence store — SAID-addressed field data + replayable compute receipts on Filecoin/IPLD`

**Project Name:** Temple Earth — receipted evidence layer

**Proposal Category:** `Storage` (data onboarding tooling)

**Individual or Entity Name:** Entity — Treetable LLC (Temple Earth)

**Proposer:** `TerexitariusStomp`

**Project Repo(s):** https://github.com/TerexitariusStomp/living-resources

**(Optional) Filecoin ecosystem affiliations:** None.

**(Optional) Technical Sponsor:** None.

**Do you agree to open source all work you do on behalf of this RFP under the MIT/Apache-2 dual-license?:** Yes — the Filecoin adapter built under this grant ships MIT/Apache-2.

# Project Summary

Ecological monitoring produces readings buyers must take on trust. Our
open sensing commons already solves the integrity half: every field
reading is content-addressed (SAID over canonical bytes, blake2s),
merged by a quorum of independent nodes, and issued as a witnessed
receipt that any third party can replay — including deterministic,
replay-verified computation run over real organism connectome wirings.
What it lacks is a *durable public home*: today receipts live in a
Cloudflare KV ledger at the edge — verifiable, but not permanent and
not content-addressed at rest in the way the evidence model demands.

This grant funds the missing seam: a **Filecoin evidence-store adapter**
that writes receipt bundles (readings + quorum witnesses + computation
traces) to Filecoin/IPLD as content-addressed objects, plus a public
replay-verifier anyone can run against stored bundles. The receipts are
already blake2s content addresses; Filecoin makes the storage layer
match the evidence layer — permanent, content-addressed, and retrievable
by anyone without trusting our edge.

## Impact

Pain point: MRV/biodiversity data has no durable, verifiable storage —
evidence dies in vendor silos. For Filecoin: this is a working example
of *verifiable-scientific-data onboarding* — a vertical (ecological MRV,
integrity markets, citizen science) where permanence + content
addressing is the whole product, not a nice-to-have.

Getting this right gives Filecoin a reference implementation of
"replayable evidence on Filecoin" other data producers can adopt; the
receipt format is already specified and exercised in production. The
risk of not doing it is that receipted data stays edge-cached — honest
but ephemeral — and the integrity claims can't outlive a provider.

## Outcomes

- `adapters/filecoin.scm` + a TypeScript edge module: receipt-bundle →
  IPLD object → Filecoin deal, with deal-CID recorded on the receipt
- Public verifier page/tool: given a receipt SAID, fetch the bundle
  from Filecoin by CID and replay-verify the computation digests
- Live migration of the existing public receipt ledger to Filecoin
- Metrics: # receipt bundles stored + retrievable, verifier replay
  success rate, deal renewal health

## Data Onboarding

Receipt bundles are small (KB-scale); volume is driven by field traffic.

- Month #1: existing receipt ledger (~hundreds of KB) + pilot stream
- Month #3: E0 field-pilot receipts — est. 10s of MB
- Month #6: multi-site receipts — est. 100s of MB
- Month #12: federated partners' bundles — est. GB-scale

## Adoption, Reach, and Growth Strategies

Target audience: ecological data producers (sensor networks, MRV
developers, citizen-science platforms) — the federation catalogue on the
site already lists 20+ allied device networks as adapter seams. First
10 adopters come from those networks (BirdWeather-class sources already
integrated); the verifier is the adoption hook — anyone can check a
receipt without trusting us.

## Development Roadmap

| Milestone | Functionality | People | Funding | Time |
|---|---|---|---|---|
| M1 | Receipt-bundle → IPLD schema + local CAR packing + verifier CLI | 1 dev | $12k | 6 wks |
| M2 | Filecoin deal pipeline (adapter + edge module + deal CID on receipts) | 1 dev | $15k | 8 wks |
| M3 | Public verifier UI + ledger migration + docs | 1 dev | $13k | 6 wks |
| M4 | E0-pilot live stream onboarding + renewal monitoring | 1 dev | $10k | 4 wks |

## Total Budget Requested

| Milestone # | Description | Deliverables | Completion Date | Funding |
|---|---|---|---|---|
| 1 | IPLD schema + CAR packer + verifier CLI | adapter, spec doc, tests | +6 wks | $12,000 |
| 2 | Live Filecoin deal pipeline | deal flow in production | +14 wks | $15,000 |
| 3 | Public verifier + migration | verifier UI, docs | +20 wks | $13,000 |
| 4 | Pilot stream + monitoring | live onboarding, dashboards | +24 wks | $10,000 |
| | **Total** | | | **$50,000** |

## Maintenance and Upgrade Plans

AGPL commons maintained as the project's core; the adapter is
MIT/Apache-2 per grant terms. Deal renewal monitoring + spec versioning
are part of the deployed worker; the project lives at templeearth.cc.

# Team

## Team Members

- T.R. Price — founder (Treetable LLC / Temple Earth)

## Team Website

https://templeearth.cc

## Relevant Experience

The working stack is live: deterministic LIF compute over 15 real
EM-derived connectome wirings (bit-identical TS↔Python port, 930/930
checks), a public content-addressed receipt ledger, e2e-verified
sensing→quorum→receipt→settlement pipeline, and a manufacturable ~$40
open hardware field node. The verifier seam this grant funds is the
architecture's stated next step, not a new direction.

## Team code repositories

- https://github.com/TerexitariusStomp/living-resources

# Additional Information

Learned about Open Grants via the Filecoin devgrants repo.
Contact: hello@templeearth.cc
