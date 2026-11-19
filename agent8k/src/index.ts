import { Hono, type Context } from "hono";
import { paymentMiddleware, x402ResourceServer } from "@x402/hono";
import { ExactEvmScheme } from "@x402/evm/exact/server";
import { HTTPFacilitatorClient } from "@x402/core/server";
import { bazaarResourceServerExtension, declareDiscoveryExtension } from "@x402/extensions/bazaar";
import { createFacilitatorConfig } from "@coinbase/x402";
import { HttpError, filingText, normalizeTicker, recent8Ks } from "./edgar";
import { summarize, type Summary } from "./summarize";

export interface Env {
  KV: KVNamespace;
  PAY_TO: string; // receive-only address; the Worker never holds a private key
  NETWORK: string; // "eip155:8453" (Base) or "eip155:84532" (Base Sepolia, testing)
  PRICE: string; // "$0.03"
  MODEL: string;
  MAX_NEW_SUMMARIES_PER_DAY: string;
  EDGAR_USER_AGENT: string;
  ANTHROPIC_API_KEY: string;
  STATS_TOKEN: string;
  CDP_API_KEY_ID?: string;
  CDP_API_KEY_SECRET?: string;
}

type Stats = {
  paid_calls: number;
  new_summaries: number;
  cache_hits: number;
  input_tokens: number;
  output_tokens: number;
  errors: number;
  free_calls: number;
};
const EMPTY: Stats = { paid_calls: 0, new_summaries: 0, cache_hits: 0, input_tokens: 0, output_tokens: 0, errors: 0, free_calls: 0 };
const PAID_PATH = "/v1/8k/summary";

const today = () => new Date().toISOString().slice(0, 10);

async function bump(env: Env, delta: Partial<Stats>) {
  const key = `stats:${today()}`;
  const cur = { ...EMPTY, ...((await env.KV.get<Stats>(key, "json")) ?? {}) };
  for (const [k, v] of Object.entries(delta)) (cur as any)[k] += v as number;
  await env.KV.put(key, JSON.stringify(cur), { expirationTtl: 400 * 86400 });
}

const exampleSummary: Partial<Summary> = {
  ticker: "AAPL",
  company: "Apple Inc.",
  filed: "2026-10-30",
  items: [{ code: "2.02", title: "Results of Operations and Financial Condition" }],
  headline: "Apple reported fiscal Q4 2026 results.",
  key_points: ["Revenue and EPS for the quarter are disclosed in Exhibit 99.1."],
  figures: [{ label: "Quarterly revenue", value: "$..." }],
};

let cachedMw: { key: string; mw: ReturnType<typeof paymentMiddleware> } | null = null;

function payMiddleware(env: Env) {
  const key = `${env.PAY_TO}|${env.NETWORK}|${env.PRICE}|${env.CDP_API_KEY_ID ?? ""}`;
  if (cachedMw?.key === key) return cachedMw.mw;
  const facilitator =
    env.CDP_API_KEY_ID && env.CDP_API_KEY_SECRET
      ? new HTTPFacilitatorClient(createFacilitatorConfig(env.CDP_API_KEY_ID, env.CDP_API_KEY_SECRET))
      : new HTTPFacilitatorClient({ url: "https://x402.org/facilitator" }); // testnets only
  const server = new x402ResourceServer(facilitator)
    .register(env.NETWORK as `${string}:${string}`, new ExactEvmScheme())
    .registerExtension(bazaarResourceServerExtension);
  const mw = paymentMiddleware(
    {
      [`GET ${PAID_PATH}`]: {
        accepts: { scheme: "exact", price: env.PRICE, network: env.NETWORK as `${string}:${string}`, payTo: env.PAY_TO },
        description:
          "Structured JSON summary of a US company's most recent SEC Form 8-K (or a given accession): 8-K item codes, one-line headline, key points, and figures quoted from the filing and its EX-99 press release. Source URL included.",
        mimeType: "application/json",
        serviceName: "8-K Brief",
        tags: ["finance", "sec", "edgar", "8-k", "filings", "summaries"],
        extensions: {
          ...declareDiscoveryExtension({
            input: { ticker: "AAPL" },
            inputSchema: {
              properties: {
                ticker: { type: "string", description: "US ticker, e.g. AAPL" },
                accession: { type: "string", description: "Optional accession number, e.g. 0000320193-26-000123; default latest 8-K" },
              },
              required: ["ticker"],
            },
            output: { example: exampleSummary },
          }),
        },
      },
    },
    server,
  );
  cachedMw = { key, mw };
  return mw;
}

const app = new Hono<{ Bindings: Env }>();

app.onError((err, c) => {
  const status = err instanceof HttpError ? err.status : 500;
  c.executionCtx.waitUntil(bump(c.env, { errors: 1 }));
  return c.json({ error: err.message }, status as 400);
});

app.get("/", (c) =>
  c.json({
    service: "8-K Brief",
    what: "Pay-per-call JSON summaries of SEC Form 8-K filings, built for software agents.",
    endpoints: {
      [`GET ${PAID_PATH}?ticker=AAPL[&accession=...]`]: `${c.env.PRICE} per call via x402 (USDC, ${c.env.NETWORK})`,
      "GET /v1/8k/list?ticker=AAPL": "free: latest 8-K filings with item codes and accession numbers",
    },
    notes: ["Failed calls are not charged.", "Summaries are machine-generated; verify against source_url. Not investment advice."],
  }),
);

app.get("/v1/8k/list", async (c) => {
  const ticker = normalizeTicker(c.req.query("ticker"));
  const list = await recent8Ks(ticker, c.env.EDGAR_USER_AGENT, c.env.KV, 10);
  c.executionCtx.waitUntil(bump(c.env, { free_calls: 1 }));
  return c.json({ ticker, filings: list });
});

// Kill switch and validation run BEFORE payment, so a dead or invalid call returns 4xx/5xx unpaid.
app.use(PAID_PATH, async (c, next) => {
  if ((await c.env.KV.get("dead")) === "1") return c.json({ error: "service retired: budget exhausted" }, 503);
  normalizeTicker(c.req.query("ticker"));
  await next();
});
app.use(PAID_PATH, (c, next) => payMiddleware(c.env)(c, next));

app.get(PAID_PATH, async (c) => {
  const env = c.env;
  const ticker = normalizeTicker(c.req.query("ticker"));
  const want = c.req.query("accession")?.trim();
  const list = await recent8Ks(ticker, env.EDGAR_USER_AGENT, env.KV, 40);
  const f = want ? list.find((x) => x.accession === want) : list[0];
  if (!f) throw new HttpError(404, want ? `accession ${want} not among recent 8-Ks for ${ticker}` : `no 8-K found for ${ticker}`);

  const cacheKey = `sum:${f.accession}`;
  const cached = await env.KV.get<Summary>(cacheKey, "json");
  if (cached) {
    c.executionCtx.waitUntil(bump(env, { paid_calls: 1, cache_hits: 1 }));
    return c.json({ ...cached, ticker, cached: true });
  }

  const dayKey = `stats:${today()}`;
  const st = { ...EMPTY, ...((await env.KV.get<Stats>(dayKey, "json")) ?? {}) };
  if (st.new_summaries >= Number(env.MAX_NEW_SUMMARIES_PER_DAY)) throw new HttpError(503, "daily summary budget reached; try a cached filing or tomorrow");

  const text = await filingText(f, env.EDGAR_USER_AGENT);
  const { summary, usage } = await summarize(f, ticker, text, env.ANTHROPIC_API_KEY, env.MODEL);
  await env.KV.put(cacheKey, JSON.stringify(summary));
  c.executionCtx.waitUntil(bump(env, { paid_calls: 1, new_summaries: 1, input_tokens: usage.input_tokens, output_tokens: usage.output_tokens }));
  return c.json({ ...summary, cached: false });
});

function authed(c: Context<{ Bindings: Env }>) {
  return c.env.STATS_TOKEN && c.req.header("authorization") === `Bearer ${c.env.STATS_TOKEN}`;
}

app.get("/internal/stats", async (c) => {
  if (!authed(c)) return c.json({ error: "unauthorized" }, 401);
  const days = Math.min(Number(c.req.query("days") ?? 30), 400);
  const out: Record<string, Stats> = {};
  for (let i = 0; i < days; i++) {
    const d = new Date(Date.now() - i * 86400000).toISOString().slice(0, 10);
    const v = await c.env.KV.get<Stats>(`stats:${d}`, "json");
    if (v) out[d] = { ...EMPTY, ...v };
  }
  return c.json({ dead: (await c.env.KV.get("dead")) === "1", price: c.env.PRICE, network: c.env.NETWORK, pay_to: c.env.PAY_TO, days: out });
});

app.post("/internal/kill", async (c) => {
  if (!authed(c)) return c.json({ error: "unauthorized" }, 401);
  await c.env.KV.put("dead", "1");
  return c.json({ dead: true });
});

export default app;
