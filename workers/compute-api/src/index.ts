// SPDX-License-Identifier: AGPL-3.0-or-later
// compute-api — replay-verified compute over real EM-derived connectomes.
// Every task emits a receipt whose trace_digest any caller can reproduce:
// POST /verify re-runs the declared input through the declared wiring and
// compares digests. The computation is the proof.

import {
  Connectome, parseConnectome, runVerdict, runTask,
  parseCanon, canon, inputSaid, toPlain,
} from "./lif.ts";
import { blake2sHex } from "./blake2s.ts";

interface Env {
  ASSETS: { fetch: (u: string) => Promise<Response> };
  RECEIPTS: {
    get(k: string): Promise<string | null>;
    put(k: string, v: string): Promise<void>;
    list(o?: { limit?: number }): Promise<{ keys: { name: string }[] }>;
  };
}

const cache = new Map<string, Promise<Connectome>>();
let bundle: Promise<{ manifest: any[]; blob: ArrayBuffer }> | null = null;

// One manifest + one concatenated blob = 2 subrequests total, which keeps
// POST /verdict {"connectome":"all"} under the per-invocation fetch cap.
function loadBundle(env: Env) {
  if (!bundle) {
    bundle = (async () => {
      const [mr, br] = await Promise.all([
        env.ASSETS.fetch("https://assets/packed/manifest.json"),
        env.ASSETS.fetch("https://assets/packed/all.bin"),
      ]);
      if (!mr.ok || !br.ok) throw new Error("packed catalogue missing");
      return { manifest: await mr.json() as any[], blob: await br.arrayBuffer() };
    })();
  }
  return bundle;
}

async function loadConnectome(env: Env, name: string): Promise<Connectome> {
  let p = cache.get(name);
  if (!p) {
    p = (async () => {
      const { manifest, blob } = await loadBundle(env);
      const meta = manifest.find((m: any) => m.name === name);
      if (!meta) throw new Error(`unknown connectome: ${name}`);
      return parseConnectome(name, meta,
        blob.slice(meta.blobOffset, meta.blobOffset + meta.totalSize));
    })();
    cache.set(name, p);
  }
  return p;
}

async function listConnectomes(env: Env): Promise<any[]> {
  return (await loadBundle(env)).manifest;
}

// Responses are emitted canonically (sorted keys, Python-style floats):
// verbatim re-posting reproduces the identical input lexemes, which is
// what makes a receipt's input_said replay-stable.
const json = (body: any, status = 200): Response =>
  new Response(canon(body), {
    status,
    headers: { "content-type": "application/json",
               "access-control-allow-origin": "*" },
  });

const bad = (msg: string, status = 400) => json({ error: msg }, status);

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const url = new URL(req.url);

    if (req.method === "OPTIONS")
      return new Response(null, { headers: {
        "access-control-allow-origin": "*",
        "access-control-allow-methods": "GET,POST,OPTIONS",
        "access-control-allow-headers": "content-type" } });

    if (url.pathname === "/" && req.method === "GET") {
      if ((req.headers.get("accept") ?? "").includes("text/html"))
        return env.ASSETS.fetch(new URL("/index.html", url).toString());
      return json({ service: "replay-verified compute over real organism connectomes",
        site: "GET / with a browser (Accept: text/html) for the live demo",
        docs: "/info" });
    }

    if (url.pathname === "/info" && req.method === "GET")
      return json({
        service: "replay-verified compute over real organism connectomes",
        endpoints: {
          "GET /connectomes": "list wired substrates",
          "POST /task": "{connectome, features|input} → receipt with trace_digest + task_said",
          "POST /verdict": "{connectome|all, features:{confidence,event_rate,env_anomaly,fleet_agreement}} → verdicts",
          "POST /verify": "a receipt → recompute → {verified}",
          "GET /receipts": "content-addressed ledger of issued task_said receipts",
          "GET /receipts/{task_said}": "fetch a stored receipt for replay",
        },
        posture: "every result is deterministic and replayable; the computation is the proof",
        source: "https://github.com/treetable/living-resources (AGPL-3.0)",
      });

    if (url.pathname === "/connectomes" && req.method === "GET")
      return json({ connectomes: await listConnectomes(env) });

    // Public receipt ledger: every /task stores its receipt under its
    // task_said, so the catalogue itself is content-addressed.
    if (url.pathname === "/receipts" && req.method === "GET") {
      const l = await env.RECEIPTS.list({ limit: 100 });
      return json({ receipts: l.keys.map(k => k.name).reverse() });
    }
    if (url.pathname.startsWith("/receipts/") && req.method === "GET") {
      const said = url.pathname.slice("/receipts/".length);
      const v = await env.RECEIPTS.get(said);
      return v ? json(parseCanon(v)) : bad("unknown task_said", 404);
    }

    if (req.method === "POST" &&
        (url.pathname === "/task" || url.pathname === "/verdict" ||
         url.pathname === "/verify")) {
      let body: any;
      try { body = parseCanon(await req.text()); }
      catch { return bad("invalid JSON body"); }

      const obj = body.k === "o"
        ? Object.fromEntries(body.obj.map(([k, x]: [string, any]) => [k, x]))
        : null;
      if (!obj) return bad("body must be a JSON object");

      if (url.pathname === "/verify") {
        // A receipt echoes its input under "features"; rerun and compare.
        const claimed = obj;
        const cx = String(toPlain(claimed.connectome ?? ""));
        const feats = claimed.features;
        if (!cx || !feats) return bad("receipt must carry connectome + features");
        try {
          const c = await loadConnectome(env, cx);
          const again = claimed.trace_digest
            ? runTask(c, feats)
            : runVerdict(c, toPlain(feats));
          const digestsMatch =
            (claimed.trace_digest
              ? again.trace_digest === toPlain(claimed.trace_digest)
              : (again as any).spike_digest === toPlain(claimed.spike_digest)) &&
            again.input_said === toPlain(claimed.input_said);
          return json({
            verified: !!digestsMatch,
            connectome: cx,
            claimed_digest: toPlain(claimed.trace_digest ?? claimed.spike_digest),
            computed_digest: (again as any).trace_digest ?? (again as any).spike_digest,
            input_said_match: again.input_said === toPlain(claimed.input_said),
          });
        } catch (e: any) { return bad(String(e.message ?? e)); }
      }

      const cx = String(toPlain(obj.connectome ?? ""));
      if (!cx) return bad("connectome required");
      const feats = obj.features ?? obj;
      try {
        if (url.pathname === "/verdict" && cx === "all") {
          const names = (await listConnectomes(env)).map((m: any) => m.name);
          const out = [];
          for (const name of names)
            out.push(runVerdict(await loadConnectome(env, name), feats));
          return json({ verdicts: out });
        }
        const c = await loadConnectome(env, cx);
        if (url.pathname === "/verdict")
          return json({ verdict: runVerdict(c, feats) });
        const receipt: any = runTask(c, feats);
        receipt.replay = {
          method: "POST", path: "/verify",
          body: "post this receipt object verbatim as the request body",
        };
        const saidSrc = { ...receipt };
        delete saidSrc.task_said;
        receipt.task_said = "blake2s:" + blake2sHex(canon(saidSrc));
        // Persist under the content address — replayable forever. A
        // ledger hiccup must not sink the task; the receipt stands alone.
        try { await env.RECEIPTS.put(receipt.task_said, canon(receipt)); }
        catch (e) { console.error("receipt log write failed:", e); }
        return json({ receipt });
      } catch (e: any) { return bad(String(e.message ?? e)); }
    }

    // Non-API paths fall through to static assets (deck, docs).
    return env.ASSETS.fetch(req.url);
  },
};
