# agent8k — 8-K Brief (budget-bounded paid API experiment)

A small, self-built take on the "automaton" idea: a service that must earn its own model costs.
It sells JSON summaries of SEC Form 8-K filings to software agents for $0.03 per call, paid in USDC
over [x402](https://github.com/coinbase/x402). A daily ledger retires the paid endpoint when
`budget + revenue − model cost ≤ 0`.

Not part of the thesis pipeline; nothing here feeds tiers or cards.

## Safety by construction
- The Worker only knows a **receive** address (`PAY_TO`). No private key is deployed, so the service cannot send money.
- The only money at risk is the Anthropic API key's spend limit (set it in the Console, e.g. $10/month).
- Failed calls (4xx/5xx) are not settled, so buyers are not charged for errors.
- At most `MAX_NEW_SUMMARIES_PER_DAY` model calls per day; summaries are cached per accession number, so repeat calls cost nothing.
- Kill switch: `POST /internal/kill` (bearer `STATS_TOKEN`), also triggered by the ledger.

## Endpoints
| Route | Price | Returns |
|---|---|---|
| `GET /` | free | service description |
| `GET /v1/8k/list?ticker=AAPL` | free | latest 8-K filings: date, item codes, accession |
| `GET /v1/8k/summary?ticker=AAPL[&accession=…]` | $0.03 (x402) | headline, key points, figures, item titles, source URL |
| `GET /internal/stats` | bearer token | daily counters |

## Pieces
- `src/` — Cloudflare Worker (Hono + `@x402/hono`), EDGAR fetch, Claude Haiku 5.5 summary with structured output
- `ledger.py` — daily arithmetic ledger → `ledger.md`; Mondays writes one proposed change to `reflections/` (human reviews; nothing auto-deploys)
- `scripts/buy_test.ts` — pays once with a Base Sepolia **test** wallet to prove the payment flow
- `.github/workflows/agent8k-deploy.yml` (manual) and `agent8k-daily.yml` (00:40 UTC)

## Setup (once)
1. Cloudflare: free account → API token with "Edit Cloudflare Workers" + "Workers KV Storage: Edit" → GitHub secrets `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`.
2. Anthropic Console: API key with a monthly spend limit → secret `ANTHROPIC_API_KEY`.
3. Any random string → secret `AGENT8K_STATS_TOKEN`.
4. Variables: `AGENT8K_PAY_TO` (receive address), `EDGAR_USER_AGENT` (already set). Leave `AGENT8K_NETWORK` unset for the Base Sepolia test run.
5. Run **agent8k-deploy**; copy the printed `workers.dev` URL into variable `AGENT8K_URL`.
6. Test payment: `BUYER_KEY=<test key> AGENT8K_URL=… npx tsx scripts/buy_test.ts AAPL`.
7. Go live: Coinbase Developer Platform API key → secrets `CDP_API_KEY_ID`, `CDP_API_KEY_SECRET`; set `AGENT8K_NETWORK=eip155:8453` and `AGENT8K_START=<today>`; re-run deploy. The CDP facilitator also lists the endpoint in its x402 discovery catalog (Bazaar).

## Verdict rule (set before launch)
After 14 days live on mainnet: pass if external revenue ≥ model cost; otherwise retire and record the numbers.

## agent8k-auto (Conway-style variant, 2026-11-19)

Same machinery, but the paid catalog is data and an agent manages it. 8-K Brief above stays unchanged as the control.
- Worker `agent8k-auto` (`src/auto.ts`, `wrangler.auto.toml`, own KV). Paid route per product: `GET /v1/p/<id>?ticker=XXX`; free `GET /v1/p/<id>/list`.
- Operator `auto_agent.py`, every 4 hours from 10:10 KST (`agent8k-auto-run.yml`): ledger → survival check → one Claude run (Sonnet 5.5) with tools list_products, get_stats, bazaar_search, upsert_product, retire_product, write_journal.
- Survival = $20 budget + revenue − serving cost (Haiku) − the agent's own model cost. ≤ 0 → Worker killed for good. Below $0.50 → ledger only.
- Caps enforced by the Worker, not the prompt: ≤ 12 active products, ≤ 6 new per UTC day, price $0.005–$0.25, allowed SEC forms only, fixed output schema, 40 new summaries per day.
- The agent cannot: move money (no wallet key deployed), contact anyone, change code or caps.
- Everything it does is committed: `auto/journal.md`, `auto/ledger.md`, `auto/agent_costs.csv`.
- Setup: run `agent8k-auto-deploy`, set repo variables `AGENT8K_AUTO_URL` (printed by the deploy) and `AGENT8K_AUTO_START`, then run `agent8k-auto-run` once by hand.
