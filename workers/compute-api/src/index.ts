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
  WAITLIST: { put(k: string, v: string): Promise<void> };
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

// ── federation ────────────────────────────────────────────────────────────
// The federated lane at the edge: allied networks' devices, provenance-
// tagged, never claimed as our quorum. Each source carries a status the
// site renders honestly — live-now sources are fetched here; the rest are
// the static catalogue until their seam binds.

const FED_SOURCES: [string, string, string][] = [
  // [name, direction, status] — mirrors *federated-sources*
  ["birdweather", "read", "live-now"],
  ["sensorcommunity", "read", "live-now"],
  ["raspberryshake", "read", "live-now"],
  ["usgs-water", "read", "live-now"],
  ["argo", "read", "live-now"],
  ["neon", "read", "live-now"],
  ["phenocam", "read", "live-now"],
  ["orcasound", "read", "public-verify"],
  ["safecast", "read", "public-verify"],
  ["inaturalist", "read", "live-now"],
  ["purpleair", "read", "key-required"],
  ["ebird", "read", "key-required"],
  ["motus", "read", "key-required"],
  ["goe", "read", "gated-partnership"],
  ["rfcx", "read", "gated-partnership"],
  ["frogid", "read", "gated-partnership"],
  ["farmbot-demo", "write", "open-invitation"],
  ["opensprinkler", "write", "opt-in-operator"],
  ["farmbot", "write", "opt-in-operator"],
  ["husqvarna", "write", "opt-in-operator"],
  ["reef-pi", "write", "opt-in-operator"],
  ["lg-sonic", "write", "gated-partnership"],
  ["ttn", "backhaul", "live-now"],
  ["meshtastic", "backhaul", "live-now"],
];

const BIRDWEATHER_GQL = "https://app.birdweather.com/graphql";
let fedCache: { at: number; body: any } | null = null;
const FED_TTL_MS = 5 * 60 * 1000;

async function birdweatherSummary(): Promise<any> {
  const gql = (query: string) =>
    fetch(BIRDWEATHER_GQL, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ query }),
    }).then(r => r.ok ? r.json() : null).catch(() => null);
  const [stations, detections] = await Promise.all([
    gql("{ stations { totalCount } }"),
    gql(`{ detections(first: 10) { edges { node { id timestamp score
          species { commonName } station { id } } } } }`),
  ]);
  return {
    stations: stations?.data?.stations?.totalCount ?? null,
    detections: (detections?.data?.detections?.edges ?? [])
      .map((e: any) => ({
        id: e.node.id, at: e.node.timestamp, score: e.node.score,
        species: e.node.species?.commonName ?? null,
        station: e.node.station?.id ?? null,
      })),
  };
}

// Ephemeral presence — a visitor's browser pings while its sensors are
// granted. In-memory per isolate: nothing persists, nothing is written to
// KV, and the count honestly approximates ("about N") because isolates
// don't share state. Sessions are SHA-256'd before keying.
const presence = new Map<string, number>();
const PRESENCE_WINDOW_MS = 90 * 1000;

function prunePresence(now: number) {
  for (const [k, t] of presence)
    if (now - t > PRESENCE_WINDOW_MS) presence.delete(k);
}

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
          "POST /verdict": "{connectome, features:{confidence,event_rate,env_anomaly,fleet_agreement}} → verdict — one substrate per call",
          "POST /verify": "a receipt → recompute → {verified}",
          "GET /receipts": "content-addressed ledger of issued task_said receipts",
          "GET /receipts/{task_said}": "fetch a stored receipt for replay",
          "GET /federation": "allied device networks — status, live counts, latest detections",
          "POST /presence": "{session} → ephemeral listener count (in-memory, ~90s window)",
        },
        posture: "every result is deterministic and replayable; the computation is the proof",
        source: "https://github.com/TerexitariusStomp/living-resources (AGPL-3.0)",
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

    if (url.pathname === "/federation" && req.method === "GET") {
      const now = Date.now();
      if (!fedCache || now - fedCache.at > FED_TTL_MS) {
        const bw = await birdweatherSummary();
        fedCache = { at: now, body: {
          generated_at: new Date(now).toISOString(),
          sources: FED_SOURCES.map(([name, direction, status]) => ({
            name, direction, status,
            ...(name === "birdweather" && bw.stations
                ? { devices: bw.stations } : {}),
          })),
          latest_detections: bw.detections,
          note: "provenance-tagged imports from allied networks — not " +
                "this commons' own measurements; statuses mark what is " +
                "live vs awaiting keys or partnership",
        }};
      }
      return json(fedCache.body);
    }

    // Presence: a granted-sensor session pings; we keep only a hash and a
    // timestamp in isolate memory for ~90s. Nothing is logged or persisted.
    if (url.pathname === "/presence" && req.method === "POST") {
      if (Number(req.headers.get("content-length") ?? 0) > 1024)
        return bad("body too large");
      let b: any;
      try { b = JSON.parse(await req.text()); }
      catch { return bad("invalid JSON body"); }
      const session = String(b?.session ?? "");
      if (!session || session.length > 128) return bad("session required");
      const digest = await crypto.subtle.digest(
        "SHA-256", new TextEncoder().encode(session));
      const key = [...new Uint8Array(digest)]
        .map(x => x.toString(16).padStart(2, "0")).join("");
      const now = Date.now();
      presence.set(key, now);
      prunePresence(now);
      return json({ listening: presence.size, approximate: true });
    }
    if (url.pathname === "/presence" && req.method === "GET") {
      prunePresence(Date.now());
      return json({ listening: presence.size, approximate: true });
    }

    // Guardian waitlist — separate KV from the public receipt ledger so PII
    // never shares a namespace with content-addressed data. No GET route:
    // nothing can enumerate or read signups back out.
    if (url.pathname === "/join" && req.method === "POST") {
      const origin = req.headers.get("origin");
      if (origin && new URL(origin).host !== url.host)
        return bad("cross-origin", 403);
      if (Number(req.headers.get("content-length") ?? 0) > 2048)
        return bad("body too large");
      let b: any;
      try { b = JSON.parse(await req.text()); }
      catch { return bad("invalid JSON body"); }
      if (b?.website) return json({ ok: true }); // honeypot: pretend success
      const email = String(b?.email ?? "").trim().toLowerCase();
      const roles = ["guardian of a place", "host a listener", "funder",
                     "scientist", "just curious"];
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email) || email.length > 254)
        return bad("valid email required");
      if (!roles.includes(b?.role)) return bad("unknown role");
      if (b?.consent !== true) return bad("consent required");
      const place = b?.place ? String(b.place).slice(0, 120) : undefined;
      const digest = await crypto.subtle.digest(
        "SHA-256", new TextEncoder().encode(email));
      const key = "join:" + [...new Uint8Array(digest)]
        .map(x => x.toString(16).padStart(2, "0")).join("");
      await env.WAITLIST.put(key, JSON.stringify({
        email, role: b.role, place, ts: new Date().toISOString() }));
      return json({ ok: true });
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
      // Raw-input mode: {connectome, input:[...]} — wrap as CanonVal so
      // runTask's vector path sees numeric lexemes, not the whole body.
      const feats = obj.features ??
        (obj.input ? { k: "o", obj: [["input", obj.input]] } : obj);
      try {
        if (url.pathname === "/verdict" && cx === "all") {
          // Free-plan honesty: 15 sims can't fit one ~10ms invocation and
          // every fan-out shape fails (SELF shares the budget, HTTP loops
          // 522). Answer with a readable error instead of an opaque 1102.
          return json({
            error: "connectome:'all' exceeds this plan's per-invocation " +
                   "compute budget",
            hint: "call /verdict once per connectome — each call is a " +
                  "separate invocation; GET /connectomes lists the fifteen",
          }, 503);
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

    // The assets binding rewrites _redirects internally (200 + target body)
    // — keep the legacy deck path a real 301 so links and caches update.
    if (url.pathname === "/treetable-deck.pdf")
      return Response.redirect(
        new URL("/temple-earth-deck.pdf", url).toString(), 301);

    // Non-API paths fall through to static assets (deck, docs).
    return env.ASSETS.fetch(req.url);
  },
};
