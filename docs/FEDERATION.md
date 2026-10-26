<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# Federation — allied networks, honestly labeled

The living cloud is not the only thing listening. Bird trackers, river
gauges, ocean floats, seismographs and citizen-observer apps already
sense the living world — tens of thousands of instruments and millions of
people. The federation is how the commons carries their notes without
pretending they are ours.

## The `federated` lane

One new lane, its own class — deliberately not `sense`/`fleet`, not
`emit`, not `relay`:

- **Admitted on provenance.** An intent must name its `source` network
  and the `source-id` of the upstream record it stands on. Missing either
  → `source-required`.
- **Not our evidence gate.** We did not calibrate BirdWeather's
  microphones; a federated record can never masquerade as quorum-grade.
- **Not consent.** Importing a public observation is not an organism
  write.
- **Mirrored in policy.** `deploy/policies/living/lane-gate.rego`
  carries the same rules; `make check-lane-drift` keeps the site's lane
  table in sync.

The record shape lives in `adapters/federated.scm`
(`<federated-record>`: source, source-id, subject, channel, at,
payload). Payloads keep the upstream's own fields — license, quality
grade, confidence — so the attribution chain survives the import.
Guardians of Earth's BioScore and BCU are carried as GoE's units, never
as our measurements.

## The catalogue

`*federated-sources*` in `adapters/federated.scm` is the whole map in
one readable place. Every entry marks a **direction** and a **status**:

| direction | meaning |
|---|---|
| `read` | the network's observations import as federated records |
| `write` | the network's devices can act — always consent-gated |
| `backhaul` | the network carries our packets (TTN, Meshtastic, APRS) |

| status | meaning |
|---|---|
| `live-now` | open API, no key — verified working |
| `public-verify` | open, but the exact endpoint is still being checked |
| `key-required` | free registration stands between us and the data |
| `gated-partnership` | real data flows only through a relationship |
| `open-invitation` | the owner publicly opened the device — anyone may drive it under their published terms (FarmBot's demo garden) |
| `opt-in-operator` | owner-keyed — the owner must volunteer; unreachable by default |
| `human-actuator` | the "device" is a person — cleanups, quests (Litterati-class, GoE BioQuest) |
| `excluded` | named and never carried — lethal actuation sits outside the consent model (pest traps, spray units) |

## What "reachable" actually means

Device counts are the **addressable hardware ceiling**, not a fleet we
can touch. Every write path is owner-keyed by the platforms themselves —
there is no endpoint that actuates a stranger's garden. The federation's
novelty is not reach; it is the consent-and-receipt layer that lets an
owner *volunteer* a device (`open-invitation` is the volunteered state).

Every write additionally requires:

1. the device/operator's own authorization,
2. the guardian's consent where a living subject is affected,
3. the cell's declared `write-kinds` (an irrigation valve cannot be
   asked for acoustic playback),
4. duty-cycle/minimum-disruption rules, and
5. a content-addressed intent and receipt.

## Visitor browsers as nodes

A browser is a permission-gated sensor node: the permission prompt **is**
the operator consent — per-session, revocable, platform-enforced.
Classification runs on-device (energy gate now; YAMNet/BirdNET-lite
class when bound); what can leave is a detection **receipt**, never raw
audio or images. Records carry `source: web-visitor` and
`uncalibrated: true` — honest tiering, below quorum-grade by
construction.

Speaker, screen/flash and vibration are emit-lane writes — still
guardian+operator, the browser supplying only the operator half.
WebUSB/WebSerial/WebBluetooth can bridge a session to local actuators
the visitor owns.

`POST /presence` keeps an ephemeral count of granted sessions — hashed
session ids in isolate memory, ~90 s window, nothing persisted; the
count is honestly approximate.

## Guardians of Earth

GoE's nouns map almost one-to-one onto ours: **Nature Realms** are
subjects, **Guardians** are guardians, **BioScore/BCU** are their
measures (labeled theirs), verifiers are a human quorum. The flow we
are building is GoE's device/app ecosystem **into** the living cloud —
BirdWeather stations are already `live-now`; `api.guardiansofearth.io`
is `gated-partnership` pending advisor-provided API documentation.
