// SPDX-License-Identifier: AGPL-3.0-or-later
// diff.mjs — prove the TS port reproduces tools/connectome/lif.py bit-for-bit.
// For every packed connectome and a battery of feature vectors, run both
// implementations and compare input_said, trace_digest, spike_digest,
// action, confidence, spike_count, tail_v. Any mismatch exits nonzero —
// this harness IS the cross-implementation verification claim.
//
//   node --experimental-strip-types test/diff.mjs
//   (needs lif.py on PYTHONPATH or CONNECTOME_PACKED_DIR unset + repo cwd)

import { execFileSync } from "node:child_process";
import { readFileSync, readdirSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import {
  parseConnectome, runVerdict, runTask,
} from "../src/lif.ts";

const PACKED = process.env.CONNECTOME_PACKED_DIR
  ?? join(homedir(), "fly-data", "packed");
const LIF_PY = new URL("../../../tools/connectome/lif.py", import.meta.url)
  .pathname;

const FEATURE_SETS = [
  { confidence: 0.91, event_rate: 0.35, env_anomaly: 0.1, fleet_agreement: 1.0 },
  { confidence: 0.5, event_rate: 0.5, env_anomaly: 0.5, fleet_agreement: 0.5 },
  { confidence: 0.0, event_rate: 1.0, env_anomaly: 1.0, fleet_agreement: 0.0 },
  { confidence: 1.0, event_rate: 0.0, env_anomaly: 0.0, fleet_agreement: 1.0 },
  { confidence: 0.33, event_rate: 0.77, env_anomaly: 0.99, fleet_agreement: 0.01 },
  { confidence: 1, event_rate: 1, env_anomaly: 0, fleet_agreement: 1 },
];

const loadLocal = (name) => {
  const dir = join(PACKED, name);
  const meta = JSON.parse(readFileSync(join(dir, "metadata.json"), "utf8"));
  const blob = Buffer.concat(
    readdirSync(dir).filter((f) => f.startsWith("chunk_")).sort()
      .map((f) => readFileSync(join(dir, f))))
    .subarray(0, meta.totalSize);
  return parseConnectome(name, meta,
    blob.buffer.slice(blob.byteOffset, blob.byteOffset + blob.byteLength));
};

const py = (args) =>
  execFileSync("python3", [LIF_PY, ...args], { encoding: "utf8" })
    .trim().split("\n").filter(Boolean).map(JSON.parse);

const names = readdirSync(PACKED)
  .filter((d) => { try { readFileSync(join(PACKED, d, "metadata.json")); return true; }
                   catch { return false; } }).sort();

let checks = 0, fails = 0;
const eq = (label, a, b) => {
  checks++;
  if (JSON.stringify(a) !== JSON.stringify(b)) {
    fails++;
    console.log(`  MISMATCH ${label}: ts=${JSON.stringify(a)} py=${JSON.stringify(b)}`);
  }
};

for (const name of names) {
  const c = loadLocal(name);
  for (const feats of FEATURE_SETS) {
    const ts = runVerdict(c, feats);
    const [pv] = py(["--connectome", name, "--features", JSON.stringify(feats)]);
    eq(`${name} verdict.input_said`, ts.input_said, pv.input_said);
    eq(`${name} verdict.spike_digest`, ts.spike_digest, pv.spike_digest);
    eq(`${name} verdict.action`, ts.action, pv.action);
    eq(`${name} verdict.confidence`, ts.confidence, pv.confidence);
    eq(`${name} verdict.spikes`, ts.spike_count, pv.spike_count);

    const tt = runTask(c, feats);
    const [pt] = py(["--connectome", name, "--task", "--features", JSON.stringify(feats)]);
    eq(`${name} task.input_said`, tt.input_said, pt.input_said);
    eq(`${name} task.trace_digest`, tt.trace_digest, pt.trace_digest);
    eq(`${name} task.spikes`, tt.spike_count, pt.spike_count);
    eq(`${name} task.tail_v`, tt.tail_v, pt.tail_v);
    eq(`${name} task.encoder`, tt.encoder, pt.encoder);
  }
  // raw-input task mode on a short vector
  const tt = runTask(c, { input: [0.85, 0.4, 0.15, 0.9] });
  const [pt] = py(["--connectome", name, "--task",
                   "--features", JSON.stringify({ input: [0.85, 0.4, 0.15, 0.9] })]);
  eq(`${name} raw.trace_digest`, tt.trace_digest, pt.trace_digest);
  eq(`${name} raw.input_said`, tt.input_said, pt.input_said);
  console.log(`${name}: done`);
}

console.log(`\n${checks - fails}/${checks} identical — ${fails ? "FAIL" : "PASS"}`);
process.exit(fails ? 1 : 0);
