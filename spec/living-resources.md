# living-resources — system spec

**Status:** v1 implementation spec. The shipped lane is passive multimodal
sensing; every other lane is either consent-gated (emit/cast/store) or
evidence-blocked (hop/compute/engineered).

## 1. Architecture

```
[universal field node] ──Reticulum──▶ [Playnet edge] ──▶ [Playnet]
  ESP32-S3, every head populated      laptop: ML, SAIDs,     offers,
  SD spool, duty-cycled               content store          receipts, credit
```

- **Node**: reads living systems; buffers to microSD; flushes on uplink
  windows. Store-and-forward is a property of the node — days offline lose
  nothing.
- **Edge**: runs the classifiers (OpenSoundscape et al.), stamps SAIDs,
  applies the gates, produces witnessed receipts, settles credit.
- **Playnet**: offers, intents, receipts, mutual credit, federation.

## 2. The universal node

One board design. No variants. Every device ships every lane's
electronics; a node's role is software config + which head sits in the
environment.

| Lane | Hardware (on every board) | Gate |
|---|---|---|
| `cam` | OV2640 (XIAO Sense onboard) | evidence |
| `mic` | onboard mic + INMP441 I2S, 48 kHz/16-bit | evidence |
| `env` | BME280 + BH1750 + PIR | evidence |
| `hydro` | piezo hydrophone front-end | evidence |
| `ultra` | MEMS ultrasonic mic, 20–100 kHz | evidence |
| `c4d` | contactless capacitance front-end | evidence |
| `emit` | 40 kHz transducer + PWM/H-bridge | **consent** |
| `store` | microSD (buffer + write lane) | **consent** |
| link | WiFi, optional LoRa / LTE-M / satellite | — |

BOM ≈ $35–45. Role change = firmware flag, never a purchase.

## 3. Transport

| Tier | Link | Payload | Use |
|---|---|---|---|
| T1 | WiFi | full lossless audio + frames + detections | local cells |
| T2 | LoRa / RNode | detections only (≤ ~200 B) | km-range |
| T3 | node→node mesh | relayed payloads | gaps |
| T4 | LTE-M / satellite | detections + scheduled snippets | remote, moored float |

Store-and-forward: LXMF semantics over an SD spool; detections flush
first, media after. Uplink windows are scheduled; the node deep-sleeps
between them.

## 4. Data model

- **Ecological subject** — species / assemblage / plant / culture / reef.
  An agent with a guardian AID, `voice = 0`, consent credential SAID,
  custody account. Registered in `module/living/agents.scm`.
- **Sense offer** — `{subject, kind, cadence, duty-cycle, taxa-scope,
  evidence-said}`. Incomplete declarations refuse.
- **Reading** — `{subject, channel, timestamp, payload, mic-cal, gain}`.
  Photos carry `frame-said` in `mic-cal` — the frame is its own evidence.
- **Fleet leg → witnessed receipt** — quorum merge (min legs + distinct
  nodes) produces `{subject, witnessed, audio-said, detection-said,
  window, quantity, digest}`.
- **Credit** — per-receipt mutual-credit events to the subject's custody;
  node operators credited on write legs.

## 5. The two gates

| Class | Lanes | Admit rule |
|---|---|---|
| evidence | `sense`, `fleet` | gate carries evidence SAID; offer cites it |
| consent | `emit`, `cast`, `store` | intent carries joint consent `{guardian, operator, said}` |
| refused | `hop`, `compute`, `engineered` | always; consent is not evidence |

Every refusal is a `<refusal>` record — `lane`, `reason`, `detail` —
never silence. OPA mirrors the gate in `deploy/policies/living/`.

## 6. Bidirectionality

- **Read** (nature → cloud): sensing lanes.
- **Cloud-write** (cloud → node): downlink tasking, OTA lane modules,
  node-SD `store` — consent-gated, receipted.
- **Bio-write** (cloud → organism): the `emit` lane — 40 kHz transducer,
  duty-cycled minimum-power defaults, joint guardian+operator consent.
  The read↔write loop over a living system is the end state.

## 7. Deployment forms

| Form | Mount | Link |
|---|---|---|
| garden | stake/tree strap | WiFi/LoRa |
| shore-dock | dock mount, hydrophone lead in water | WiFi/LoRa |
| reef float | moored deadweight float, hydrophone below | LoRa/satellite |
| offshore | moored float + satellite | T4 |

Nothing attaches to an organism; nothing enters soil; moorings are
deadweight or existing structure.
