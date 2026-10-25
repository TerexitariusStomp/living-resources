// SPDX-License-Identifier: AGPL-3.0-or-later
// lif.ts — TypeScript port of tools/connectome/lif.py step semantics.
// Same packed int4 CSR blobs, same Q24 fixed-point math, same digests.
// Verified bit-identical against the Python runner in test/diff.mjs —
// that cross-implementation digest equality IS the product's claim.

import { blake2s, blake2sHex, hex } from "./blake2s.ts";

export const Q24 = 1 << 24;
export const DECAY_Q24 = 13743895;   // exp(-0.2) * 2^24
export const TONIC_Q24 = 2359296;    // 0.14 * 2^24
export const THRESHOLD_Q24 = 16777216;
export const EYE_GAIN_Q24 = 25165824;
export const WEIGHT_SCALE = 7190235; // (3*2^24)/7 per nibble
export const VAR_MOD = 1677720;
export const ENCODER = "lif-sensing-v1";

export interface Connectome {
  name: string;
  meta: { nNeurons: number; nSynapses: number; nSteps: number;
          totalSize: number; indptrWidth: number;
          indptrOffset: number; indicesOffset: number;
          weightsOffset: number; nChunks: number };
  indptr: Int32Array;   // n+1
  indices: Int32Array;  // nSyn
  w4: Int8Array;        // nSyn signed nibbles
  src: Int32Array;      // nSyn — presynaptic neuron of each edge
}

export function parseConnectome(name: string, metaJson: any,
                                blob: ArrayBuffer): Connectome {
  const meta = metaJson as Connectome["meta"];
  const bytes = new Uint8Array(blob, 0, meta.totalSize);
  const dv = new DataView(blob);
  const n = meta.nNeurons, nSyn = meta.nSynapses;

  const indptr = new Int32Array(n + 1);
  let acc = 0;
  for (let i = 0; i < n; i++) {
    acc += meta.indptrWidth === 1
      ? bytes[meta.indptrOffset + i]
      : dv.getUint16(meta.indptrOffset + 2 * i, false);
    indptr[i + 1] = acc;
  }
  const indices = new Int32Array(nSyn);
  for (let e = 0; e < nSyn; e++)
    indices[e] = dv.getUint16(meta.indicesOffset + 2 * e, false);

  const w4 = new Int8Array(nSyn);
  for (let e = 0; e < nSyn; e++) {
    const byte = bytes[meta.weightsOffset + (e >> 1)];
    let nib = (e & 1) === 0 ? byte >> 4 : byte & 0x0f;
    w4[e] = nib >= 8 ? nib - 16 : nib;
  }
  const src = new Int32Array(nSyn);
  for (let i = 0; i < n; i++)
    for (let e = indptr[i]; e < indptr[i + 1]; e++) src[e] = i;
  return { name, meta, indptr, indices, w4, src };
}

// Python round() is round-half-even; JS Math.round is half-away.
const rne = (x: number): number => {
  const r = Math.round(x);
  return Math.abs(x % 1) === 0.5 && r % 2 !== 0 ? r - Math.sign(x) : r;
};

// Python int64 `x >> 24` is arithmetic (floor); `// q` is floor division.
const shr24 = (x: number): number => Math.floor(x / Q24);
const fdiv = (a: number, b: number): number => Math.floor(a / b);

const _norm = (x: number): number =>
  Math.max(0, Math.min(Q24, rne(x * Q24)));

function variation(i: number, side: string): number {
  const d = blake2s(new TextEncoder().encode(`${i}:${side}`));
  // >>> 0: the BE word must stay unsigned — Python's % floors positive,
  // a signed JS int32 would turn first bytes ≥0x80 into negative variation.
  return (((d[0] << 24) | (d[1] << 16) | (d[2] << 8) | d[3]) >>> 0) % VAR_MOD;
}

export function rasterize(features: Record<string, number>,
                          n: number): Float64Array {
  const conf = _norm(features.confidence);
  const rate = _norm(features.event_rate);
  const anom = _norm(features.env_anomaly);
  const agree = _norm(features.fleet_agreement);

  let affirm = fdiv(conf * (Q24 - anom), Q24);
  affirm = fdiv(affirm * agree, Q24);
  affirm = fdiv(affirm * (Q24 + rate), 2 * Q24);
  affirm = fdiv(affirm * EYE_GAIN_Q24, Q24);

  let refute = fdiv((Q24 - conf) * anom, Q24);
  refute = fdiv(refute * (Q24 - agree), Q24);
  refute = fdiv(refute * EYE_GAIN_Q24, Q24);

  if (affirm < TONIC_Q24) affirm = TONIC_Q24;
  if (refute < TONIC_Q24) refute = TONIC_Q24;

  const half = Math.floor(n / 2);
  const inp = new Float64Array(n);
  for (let i = 0; i < half; i++) inp[i] = affirm + variation(i, "affirm");
  for (let i = half; i < n; i++) inp[i] = refute + variation(i, "refute");
  return inp;
}

// Empirically |v*DECAY| stays < 2.4e15 << 2^53 on all packed connectomes,
// so f64 is exact; guard anyway rather than emit a silently wrong digest.
const EXACT_LIMIT = 2 ** 52;

export function simulate(c: Connectome,
                         inp: Float64Array): { v: Float64Array; raster: Uint8Array } {
  const n = c.meta.nNeurons, steps = c.meta.nSteps;
  const v = new Float64Array(n);
  const fired = new Uint8Array(n);
  const raster = new Uint8Array(steps * n);
  const current = new Float64Array(n);
  for (let s = 0; s < steps; s++) {
    current.fill(0);
    for (let e = 0; e < c.src.length; e++)
      if (fired[c.src[e]]) current[c.indices[e]] += c.w4[e] * WEIGHT_SCALE;
    for (let i = 0; i < n; i++) {
      let x = shr24(v[i] * DECAY_Q24) + current[i] + TONIC_Q24 + inp[i];
      if (x >= THRESHOLD_Q24) { fired[i] = 1; x = 0; }
      else fired[i] = 0;
      if (x > EXACT_LIMIT || x < -EXACT_LIMIT)
        throw new RangeError(`|v| exceeded exact-f64 range at step ${s}`);
      v[i] = x;
      raster[s * n + i] = fired[i];
    }
  }
  return { v, raster };
}

function vBytes(v: Float64Array): Uint8Array {
  const out = new Uint8Array(v.length * 8);
  const dv = new DataView(out.buffer);
  for (let i = 0; i < v.length; i++)
    dv.setBigInt64(i * 8, BigInt(v[i]), true);
  return out;
}

function concatBytes(a: Uint8Array, b: Uint8Array): Uint8Array {
  const out = new Uint8Array(a.length + b.length);
  out.set(a); out.set(b, a.length);
  return out;
}

export function decode(inp: Float64Array, v: Float64Array,
                       raster: Uint8Array)
    : { action: number; confidence: number; spikes: number; digest: string } {
  const n = inp.length, half = Math.floor(n / 2);
  let affirmSum = 0, refuteSum = 0, activity = 0, spikes = 0;
  for (let i = 0; i < half; i++) affirmSum += inp[i];
  for (let i = half; i < n; i++) refuteSum += inp[i];
  for (let i = 0; i < n; i++) if (v[i] > 0) activity += v[i];
  for (let i = 0; i < raster.length; i++) spikes += raster[i];
  const digest = "blake2s:" + hex(blake2s(concatBytes(raster, vBytes(v))));
  const total = affirmSum + refuteSum, diff = affirmSum - refuteSum;
  if (total <= 0 || diff === 0 || Math.abs(diff) * 100 < 15 * total)
    return { action: 0, confidence: 50, spikes, digest };
  const conf = Math.min(100, 50 + Math.floor(activity / Math.max(1, Math.floor(total / 50))));
  return { action: diff > 0 ? 1 : -1, confidence: conf, spikes, digest };
}

// Canonical JSON identical to Python's json.dumps(obj, sort_keys,
// separators=(",",":")) including int-vs-float literal distinction.
// parseCanon preserves the raw number lexemes from the request body.
export interface CanonVal { k: string; v?: any; s?: string;
                            items?: CanonVal[]; obj?: [string, CanonVal][] }

export function parseCanon(text: string): CanonVal {
  let i = 0;
  const ws = () => { while (" \t\n\r".includes(text[i])) i++; };
  const parse = (): CanonVal => {
    ws();
    const ch = text[i];
    if (ch === "{") {
      i++; const obj: [string, CanonVal][] = [];
      ws(); if (text[i] === "}") { i++; return { k: "o", obj }; }
      while (true) {
        ws();
        const key = JSON.parse(readString());
        ws(); i++; // ':'
        obj.push([key, parse()]);
        ws();
        if (text[i] === ",") { i++; continue; }
        i++; break; // '}'
      }
      return { k: "o", obj };
    }
    if (ch === "[") {
      i++; const items: CanonVal[] = [];
      ws(); if (text[i] === "]") { i++; return { k: "a", items }; }
      while (true) {
        items.push(parse());
        ws();
        if (text[i] === ",") { i++; continue; }
        i++; break; // ']'
      }
      return { k: "a", items };
    }
    if (ch === '"') return { k: "s", s: readString() };
    if (text.startsWith("true", i)) { i += 4; return { k: "l", s: "true" }; }
    if (text.startsWith("false", i)) { i += 5; return { k: "l", s: "false" }; }
    if (text.startsWith("null", i)) { i += 4; return { k: "l", s: "null" }; }
    const m = /^-?\d+(\.\d+)?([eE][+-]?\d+)?/.exec(text.slice(i));
    if (!m) throw new Error(`bad JSON at ${i}`);
    i += m[0].length;
    return { k: "n", s: m[0] };
  };
  const readString = (): string => {
    const start = i;
    i++;
    while (text[i] !== '"') i += text[i] === "\\" ? 2 : 1;
    return text.slice(start, ++i);
  };
  const root = parse();
  ws();
  return root;
}

const escStr = (raw: string): string => {
  // raw is the source lexeme; canonical output re-encodes like Python's
  // json.dumps (which matches JSON.stringify for these strings).
  return JSON.stringify(JSON.parse(raw));
};

export function canon(val: CanonVal | any): string {
  if (val && typeof val === "object" && "k" in val) {
    switch (val.k) {
      case "o": {
        const sorted = [...val.obj].sort((a, b) => a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0);
        return "{" + sorted.map(([k, x]) => `${JSON.stringify(k)}:${canon(x)}`).join(",") + "}";
      }
      case "a": return "[" + val.items.map(canon).join(",") + "]";
      case "s": return escStr(val.s);
      case "l": return val.s;
      case "n": {
        const raw = val.s;
        if (/[.eE]/.test(raw)) {
          const num = Number(raw);
          return Number.isInteger(num) ? `${num}.0` : String(num);
        }
        return raw;
      }
    }
  }
  if (typeof val === "number")
    return Number.isInteger(val) ? String(val) : String(val);
  if (typeof val === "string") return JSON.stringify(val);
  if (typeof val === "boolean") return val ? "true" : "false";
  if (val === null) return "null";
  if (Array.isArray(val)) return "[" + val.map(canon).join(",") + "]";
  if (val && typeof val === "object") {
    return "{" + Object.keys(val).sort()
      .map(k => `${JSON.stringify(k)}:${canon(val[k])}`).join(",") + "}";
  }
  throw new Error("uncanonicalizable value");
}

export function inputSaid(features: CanonVal | any): string {
  return "blake2s:" + blake2sHex(canon(features));
}

// CanonVal → plain JS value (for rasterize / response echo).
export function toPlain(val: CanonVal | any): any {
  if (val && typeof val === "object" && "k" in val) {
    switch (val.k) {
      case "o":
        return Object.fromEntries(val.obj.map(([k, x]: [string, CanonVal]) => [k, toPlain(x)]));
      case "a": return val.items.map(toPlain);
      case "s": return JSON.parse(val.s);
      case "l": return val.s === "null" ? null : val.s === "true";
      case "n": return Number(val.s);
    }
  }
  return val;
}

export function runVerdict(c: Connectome,
                           features: CanonVal | Record<string, number>) {
  const inp = rasterize(toPlain(features), c.meta.nNeurons);
  const { v, raster } = simulate(c, inp);
  const d = decode(inp, v, raster);
  return {
    connectome: c.name,
    input_said: inputSaid(features),
    features,
    action: d.action,
    confidence: d.confidence,
    spike_count: d.spikes,
    spike_digest: d.digest,
    steps: c.meta.nSteps,
    encoder: ENCODER,
  };
}

export function runTask(c: Connectome, features: CanonVal | any) {
  const n = c.meta.nNeurons;
  let inp: Float64Array, encoder: string;
  const hasInput = features && typeof features === "object" &&
    ("input" in features ||
     (features.k === "o" && features.obj.some(([k]: [string]) => k === "input")));
  if (hasInput) {
    const vec: number[] = features.k === "o"
      ? features.obj.find(([k]: [string]) => k === "input")[1].items
        .map((x: CanonVal) => Number(x.s))
      : features.input;
    if (vec.length > n) throw new RangeError(`input vector ${vec.length} > neurons ${n}`);
    inp = new Float64Array(n);
    const mx = Math.max(1, ...vec.map(Math.abs));
    for (let i = 0; i < vec.length; i++)
      inp[i] = fdiv(rne(vec[i] * Q24 / mx) * EYE_GAIN_Q24, Q24);
    encoder = "lif-task-v1";
  } else {
    inp = rasterize(toPlain(features), n);
    encoder = ENCODER;
  }
  const { v, raster } = simulate(c, inp);
  let spikes = 0, tail = 0;
  for (let i = 0; i < raster.length; i++) spikes += raster[i];
  for (let i = 0; i < v.length; i++) if (v[i] > 0) tail += v[i];
  return {
    connectome: c.name,
    input_said: inputSaid(features),
    features,
    trace_digest: "blake2s:" + hex(blake2s(concatBytes(raster, vBytes(v)))),
    spike_count: spikes,
    tail_v: Math.floor(tail),
    steps: c.meta.nSteps,
    encoder,
  };
}
