// SPDX-License-Identifier: AGPL-3.0-or-later
// e2e.mjs — end-to-end smoke of the deployed site + worker API.
// Exercises every public route: the pages, static assets, OG metadata,
// and the compute chain (task → receipt → verify → tamper → federation,
// presence, join validation). Nothing is mocked — this is the real
// production contract, the same calls a browser or a curl client makes.
//
//   node test/e2e.mjs                     # against https://templeearth.cc
//   node test/e2e.mjs --base http://x.y   # against a dev/preview origin
//
// The /join check posts a synthetic signup (e2e-selfcheck@…); delete the
// `join:<sha256(email)>` WAITLIST key afterwards if you want a clean list.

const BASE = (process.argv.find(a => a.startsWith("--base")) ?? "")
  .split("=")[1] || "https://templeearth.cc";

let pass = 0, fail = 0, warn = 0;
const ok = (name, cond, detail = "") => {
  if (cond) { pass++; console.log(`  ✓ ${name}`); }
  else { fail++; console.log(`  ✗ ${name}${detail ? " — " + detail : ""}`); }
};
const soft = (name, cond, detail = "") => {
  if (cond) pass++, console.log(`  ✓ ${name}`);
  else warn++, console.log(`  ~ ${name} (soft)${detail ? " — " + detail : ""}`);
};

const get = (path, opts = {}) =>
  fetch(BASE + path, { redirect: "follow", ...opts });
const getJson = async (path, opts) => (await get(path, opts)).json();
const post = (path, body, headers = {}) =>
  get(path, {
    method: "POST",
    headers: { "content-type": "application/json", ...headers },
    body: typeof body === "string" ? body : JSON.stringify(body),
  });
const postJson = async (path, body, headers) =>
  (await post(path, body, headers)).json();

// meta/link attributes come in either order — grab the tag then pick attrs
const tagAttr = (html, tagRe, attr) =>
  new RegExp(attr + '="([^"]+)"').exec(html.match(tagRe)?.[0] ?? "")?.[1];

const FEATS = { confidence: 0.72, event_rate: 0.35, env_anomaly: 0.18,
                fleet_agreement: 0.81 };

// ── pages ────────────────────────────────────────────────────────────────
console.log("\npages");
{
  const r = await get("/", { headers: { accept: "text/html" } });
  const html = await r.text();
  ok("GET / → 200 text/html",
     r.status === 200 && (r.headers.get("content-type") ?? "").includes("text/html"));
  ok("brand rendered on page", /Temple Earth/i.test(html));
  ok("page <title> set", /<title>[^<]+<\/title>/.test(html));
  ok("canonical → templeearth.cc",
     /^https:\/\/templeearth\.cc\/?$/.test(
       tagAttr(html, /<link[^>]*rel="canonical"[^>]*>/, "href") ?? ""));
  ok("og:site_name = Temple Earth",
     tagAttr(html, /<meta[^>]*property="og:site_name"[^>]*>/, "content")
       ?.includes("Temple Earth"));
  ok("no 'Treetable' in rendered HTML", !/Treetable/.test(html));
  ok("hero line present", html.includes("nature was the cloud") ||
     html.includes("living cloud"));
  ok("details drawers render", html.includes("<details"));
  ok("join form present", html.includes('name="email"') || html.includes("join"));

  const og = tagAttr(html, /<meta[^>]*property="og:image"[^>]*>/, "content");
  ok("og:image is absolute templeearth.cc URL",
     !!og && og.startsWith("https://templeearth.cc/"), og ?? "missing");
  if (og) {
    const ir = await fetch(og);
    ok("og:image fetches 200 + is an image",
       ir.status === 200 &&
       (ir.headers.get("content-type") ?? "").startsWith("image/"));
    ok("og:image immutable cache",
       (ir.headers.get("cache-control") ?? "").includes("immutable"));
  }
  const apple = tagAttr(html, /<link[^>]*rel="apple-touch-icon"[^>]*>/, "href");
  ok("apple-touch-icon link present", !!apple);
  if (apple) {
    const ar = await fetch(new URL(apple, BASE));
    ok("apple-touch-icon fetches 200", ar.status === 200);
  }
  const icon = tagAttr(html, /<link[^>]*rel="icon"[^>]*>/, "href");
  ok("svg favicon link present", !!icon);
  if (icon) {
    const fr = await fetch(new URL(icon, BASE));
    ok("svg favicon fetches 200", fr.status === 200);
  }

  // API clients get a JSON pointer, not the HTML page (run_worker_first)
  const jr = await get("/", { headers: { accept: "application/json" } });
  const jj = await jr.json().catch(() => null);
  ok("GET / (Accept: json) → service pointer", jj?.docs === "/info");
}
{
  const dev = await get("/developers");
  const h = await dev.text();
  ok("GET /developers → 200", dev.status === 200);
  ok("developers lists /task + /verify", h.includes("/task") && h.includes("/verify"));
  ok("developers links GitHub repo", h.includes("TerexitariusStomp/living-resources"));
}
for (const p of ["/privacy", "/credits"]) {
  const r = await get(p);
  ok(`GET ${p} → 200`, r.status === 200);
}
{
  const h = await (await get("/privacy")).text();
  ok("privacy contact is hello@templeearth.cc", h.includes("hello@templeearth.cc"));
}
for (const p of ["/science", "/how-it-works", "/this-path-grew-over-404"]) {
  const r = await get(p);
  const h = await r.text();
  ok(`GET ${p} → styled 404`,
     r.status === 404 && /<title>[^<]+<\/title>/.test(h) &&
       /lost|grew over|404/i.test(h),
     `status=${r.status} body=${h.length}b`);
}

// www serves the same site (as a browser — JSON clients get the pointer)
{
  const r = await fetch("https://www.templeearth.cc/",
    { redirect: "follow", headers: { accept: "text/html" } });
  const h = await r.text();
  ok("www.templeearth.cc serves the site",
     r.status === 200 && /Temple Earth/i.test(h));
}

// ── static assets ────────────────────────────────────────────────────────
console.log("\nassets");
for (const p of ["/robots.txt", "/temple-earth-deck.pdf", "/sitemap-index.xml"]) {
  const r = await get(p);
  ok(`GET ${p} → 200 (${(r.headers.get("content-type") ?? "").split(";")[0]})`,
     r.status === 200);
}
{
  const r = await get("/temple-earth-deck.pdf");
  const b = await r.arrayBuffer();
  ok("deck is a real PDF (>100KB)",
     r.headers.get("content-type")?.includes("pdf") && b.byteLength > 100_000);
}
{
  const r = await fetch(BASE + "/treetable-deck.pdf", { redirect: "manual" });
  ok("legacy deck → 301 to temple-earth-deck.pdf",
     r.status === 301 && (r.headers.get("location") ?? "")
       .includes("temple-earth-deck.pdf"),
     `${r.status} → ${r.headers.get("location")}`);
}

// ── read APIs ────────────────────────────────────────────────────────────
console.log("\nread APIs");
{
  const j = await getJson("/info");
  ok("/info lists endpoints", !!j.endpoints?.["POST /task"]);
  ok("/info source → GitHub repo",
     (j.source ?? "").includes("TerexitariusStomp/living-resources"));
}
let cxNames = [];
{
  const j = await getJson("/connectomes");
  cxNames = (j.connectomes ?? []).map(c => c.name);
  ok("/connectomes returns 15 substrates", cxNames.length === 15,
     `got ${cxNames.length}`);
  ok("connectome names unique", new Set(cxNames).size === cxNames.length);
}
{
  const j = await getJson("/federation");
  const srcs = j.sources ?? [];
  ok("/federation lists allied networks", srcs.length >= 20, `${srcs.length}`);
  ok("birdweather is live-now with a device count",
     srcs.some(s => s.name === "birdweather" && s.status === "live-now"));
  soft("birdweather has live detections",
       (j.latest_detections ?? []).length > 0,
       "BirdWeather may be quiet — shape is what matters");
  ok("provenance note present", (j.note ?? "").includes("provenance"));
}
{
  const j = await getJson("/receipts");
  ok("/receipts returns the ledger", Array.isArray(j.receipts));
}

// ── the compute chain — the core e2e ─────────────────────────────────────
console.log("\ncompute chain (task → receipt → verify → tamper)");
const cx = cxNames.includes("celegans") ? "celegans" : cxNames[0];
let receipt = null;
{
  const j = await postJson("/task", { connectome: cx, features: FEATS });
  receipt = j.receipt;
  ok("POST /task → receipt", !!receipt);
  ok("receipt has blake2s task_said",
     (receipt?.task_said ?? "").startsWith("blake2s:"));
  ok("receipt carries trace_digest + input_said",
     !!receipt?.trace_digest && !!receipt?.input_said);
  ok("receipt points at /verify replay", receipt?.replay?.path === "/verify");
}
if (receipt) {
  const stored = await getJson(`/receipts/${receipt.task_said}`);
  ok("receipt persisted under its content address",
     stored.task_said === receipt.task_said);

  const v = await postJson("/verify", receipt);
  ok("POST /verify receipt → verified", v.verified === true,
     `claimed=${v.claimed_digest} computed=${v.computed_digest}`);
  ok("input_said recomputes", v.input_said_match === true);

  const bad = { ...receipt, trace_digest: receipt.trace_digest.replace(/^../, "00") };
  const tv = await postJson("/verify", bad);
  ok("tampered digest → verified:false", tv.verified === false);

  // KV list is eventually consistent — retry a few times, then warn
  let inLedger = false;
  for (let i = 0; i < 4 && !inLedger; i++) {
    await new Promise(r => setTimeout(r, 4000));
    const ledger = await getJson("/receipts");
    inLedger = ledger.receipts.includes(receipt.task_said);
  }
  soft("new receipt shows in the ledger (KV list latency)", inLedger);
}
{
  const j = await postJson("/verdict", { connectome: cx, features: FEATS });
  ok("POST /verdict single → verdict",
     !!j.verdict?.action && !!j.verdict?.spike_digest);
}
{
  // Free-plan contract: 'all' can't fit one invocation's ~10ms budget,
  // so the endpoint must answer with a readable JSON error — not die as
  // an opaque Cloudflare 1102 HTML page. Pinned as a hard check.
  const r = await post("/verdict", { connectome: "all", features: FEATS });
  const j = await r.json().catch(() => null);
  ok("POST /verdict all → honest JSON 503 (free-plan CPU)",
     r.status === 503 && /once per connectome/i.test(j?.error + (j?.hint ?? "")),
     `status ${r.status}`);
}
{
  const j = await postJson("/task",
    { connectome: cx, input: [0.85, 0.4, 0.15, 0.9] });
  ok("POST /task raw-input mode → receipt", !!j.receipt?.task_said);
}

// ── validation + guardrails ──────────────────────────────────────────────
console.log("\nvalidation + guardrails");
{
  const cases = [
    ["task: no connectome → 400", "/task", {}, 400],
    ["task: unknown connectome → 400", "/task",
      { connectome: "doesnotexist", features: FEATS }, 400],
    ["task: garbage body → 400", "/task", "not json", 400],
    ["task: array body → 400", "/task", [1, 2, 3], 400],
    ["verify: empty → 400", "/verify", {}, 400],
    ["join: bad email → 400", "/join",
      { email: "nope", role: "just curious", consent: true }, 400],
    ["join: unknown role → 400", "/join",
      { email: "a@b.co", role: "overlord", consent: true }, 400],
    ["join: no consent → 400", "/join",
      { email: "a@b.co", role: "just curious" }, 400],
  ];
  for (const [name, path, body, want] of cases) {
    const r = await post(path, body);
    ok(name, r.status === want, `got ${r.status}`);
  }
  const r = await get("/receipts/blake2s:00000000deadbeef");
  ok("receipts: unknown said → 404", r.status === 404);
}
{
  const r = await post("/join",
    { email: "a@b.co", role: "just curious", consent: true,
      website: "http://spam" });
  const j = await r.json();
  ok("join honeypot pretends success", r.status === 200 && j.ok === true);
}
{
  const r = await post("/join",
    { email: "a@b.co", role: "just curious", consent: true },
    { origin: "https://evil.example" });
  ok("join cross-origin → 403", r.status === 403, `got ${r.status}`);
}
{
  const r = await post("/join",
    { email: "e2e-selfcheck@templeearth.cc", role: "just curious",
      place: "e2e", consent: true });
  const j = await r.json();
  ok("join valid signup → ok", r.status === 200 && j.ok === true,
     `got ${r.status}`);
}
{
  const big = "x".repeat(3000);
  const r = await post("/presence", { session: big });
  ok("presence oversized body → 400", r.status === 400, `got ${r.status}`);
}
{
  const j = await postJson("/presence", { session: "e2e-" + Date.now() });
  ok("presence ping → counted", j.listening >= 1 && j.approximate === true);
  const g = await getJson("/presence");
  ok("presence GET → valid shape",
     typeof g.listening === "number" && g.approximate === true);
  soft("presence count shared with POST isolate",
       g.listening >= 1, "counts are isolate-local by design (~90s window)");
}
{
  const r = await get("/task", { method: "OPTIONS" });
  ok("CORS preflight → allow-origin *",
     r.headers.get("access-control-allow-origin") === "*");
}
{
  const r = await post("/verify", {});
  const j = await r.json();
  ok("error bodies are {error}", typeof j.error === "string");
}

// ── summary ──────────────────────────────────────────────────────────────
console.log(`\n${pass} passed, ${fail} failed, ${warn} soft-warnings — ${BASE}`);
process.exit(fail ? 1 : 0);
