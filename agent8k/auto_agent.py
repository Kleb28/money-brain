"""agent8k-auto: the Conway-style operator (one run per day, GitHub Actions).

Each run:
1. Ledger (arithmetic only): revenue from the Worker's own counters, serving cost from its
   Haiku token counts, the agent's own model cost from agent8k/auto/agent_costs.csv.
   survival = budget + revenue - serving cost - agent cost.
2. survival <= 0 -> kill the Worker (/internal/kill) and stop. survival < RESERVE -> ledger only.
3. Otherwise Claude gets the ledger, the catalog and its own journal, and may create, reprice
   or retire products through /internal/products. Every limit is enforced by the Worker
   (src/auto.ts CAPS), not by this prompt. It has no wallet key, no outbound messaging, and
   cannot change code. Every action is written to agent8k/auto/journal.md and committed.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import os
import pathlib
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent / "auto"
LEDGER = ROOT / "ledger.md"
JOURNAL = ROOT / "journal.md"
COSTS = ROOT / "agent_costs.csv"

PRICES = {  # USD per MTok (input, output)
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-opus-5-5": (4.0, 20.0),
}
BAZAAR = "https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources"


def env(name: str, default: str | None = None) -> str:
    v = os.environ.get(name) or default
    if v is None:
        raise SystemExit(f"missing env {name}")
    return v


URL = env("AUTO_URL").rstrip("/")
TOKEN = env("AGENT8K_STATS_TOKEN")
BUDGET = float(env("AUTO_BUDGET_USD", "20"))
RESERVE = float(env("AUTO_RESERVE_USD", "0.50"))  # do not start an agent run below this
START = env("AUTO_START", "")
SELF_REVENUE = float(env("AUTO_SELF_REVENUE_USD", "0"))  # owner test payments, excluded from external revenue
MODEL = env("AUTO_MODEL", "claude-sonnet-5-5")
SERVE_MODEL = "claude-haiku-5-5"
NOW = dt.datetime.now(dt.timezone.utc)
RUN_ID = os.environ.get("GITHUB_RUN_ID", NOW.strftime("local-%H%M%S"))


def call(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    last: Exception | None = None
    for attempt in range(3):  # network errors and timeouts are retried; HTTP errors are returned
        req = urllib.request.Request(URL + path, method=method, headers={"authorization": f"Bearer {TOKEN}", "user-agent": "agent8k-auto"})
        if body is not None:
            req.data = json.dumps(body).encode()
            req.add_header("content-type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            try:
                return e.code, json.loads(e.read())
            except Exception:
                return e.code, {"error": str(e)}
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last = e
            time.sleep(3 * (attempt + 1))
    return 599, {"error": f"network: {last}"}


def journal(line: str) -> None:
    ROOT.mkdir(exist_ok=True)
    if not JOURNAL.exists():
        JOURNAL.write_text("# agent8k-auto journal\n\nWritten by agent8k/auto_agent.py. Do not edit by hand.\n")
    with JOURNAL.open("a") as f:
        f.write(f"- {NOW:%Y-%m-%d %H:%M}Z [{RUN_ID}] {line}\n")


def agent_costs() -> float:
    if not COSTS.exists():
        return 0.0
    with COSTS.open() as f:
        return sum(float(r["cost_usd"]) for r in csv.DictReader(f))


def record_cost(model: str, tin: int, tout: int) -> float:
    pin, pout = PRICES.get(model, PRICES["claude-opus-5-5"])
    cost = tin / 1e6 * pin + tout / 1e6 * pout
    new = not COSTS.exists()
    with COSTS.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["date", "run_id", "model", "input_tokens", "output_tokens", "cost_usd"])
        w.writerow([NOW.date().isoformat(), RUN_ID, model, tin, tout, f"{cost:.5f}"])
    return cost


from wallets import wallet_lines  # noqa: E402


def build_ledger() -> dict:
    code, st = call("GET", "/internal/stats?days=400")
    if code != 200:
        raise SystemExit(f"stats {code}: {st}")
    days = dict(sorted(st["days"].items()))
    if START:
        days = {d: v for d, v in days.items() if d >= START}
    pin, pout = PRICES[SERVE_MODEL]
    rows, rev, serve = [], 0.0, 0.0
    per: dict[str, dict] = {}
    for d, v in days.items():
        r = v.get("revenue_micro", 0) / 1e6
        c = v["input_tokens"] / 1e6 * pin + v["output_tokens"] / 1e6 * pout
        rev += r
        serve += c
        rows.append(f"| {d} | {v['free_calls']} | {v['paid_calls']} | {v['new_summaries']} | {v['cache_hits']} | {v['errors']} | {r:.3f} | {c:.4f} |")
        for pid, s in (v.get("products") or {}).items():
            a = per.setdefault(pid, {"free_calls": 0, "paid_calls": 0, "revenue_usd": 0.0})
            a["free_calls"] += s["free_calls"]
            a["paid_calls"] += s["paid_calls"]
            a["revenue_usd"] += s.get("revenue_micro", 0) / 1e6
    agent = agent_costs()
    survival = BUDGET + rev - serve - agent
    ext = max(rev - SELF_REVENUE, 0.0)
    return {
        "stats": st,
        "revenue": rev,
        "external_revenue": ext,
        "serve_cost": serve,
        "agent_cost": agent,
        "survival": survival,
        "per_product": per,
        "rows": rows,
    }


def write_ledger(L: dict, status: str) -> None:
    lines = [
        "# agent8k-auto ledger",
        "",
        f"Updated {NOW:%Y-%m-%d %H:%M}Z by agent8k/auto_agent.py. Do not edit by hand.",
        "",
        f"- Network: {L['stats']['network']} · receive address {L['stats']['pay_to']}",
        f"- Budget ${BUDGET:.2f} · revenue ${L['revenue']:.3f} (external ${L['external_revenue']:.3f}) · serving cost ${L['serve_cost']:.4f} · agent cost ${L['agent_cost']:.4f}",
        f"- Verdict test: external revenue ≥ serving + agent cost → {'pass' if L['external_revenue'] > 0 and L['external_revenue'] >= L['serve_cost'] + L['agent_cost'] else 'not yet'}",
        f"- Survival balance ${L['survival']:.3f} · status: {status}",
        "",
        "| product | free calls | paid calls | revenue $ |",
        "|---|---|---|---|",
        *[f"| {k} | {v['free_calls']} | {v['paid_calls']} | {v['revenue_usd']:.3f} |" for k, v in sorted(L["per_product"].items())],
        "",
        "| date | free calls | paid calls | new summaries | cache hits | errors | revenue $ | serving cost $ |",
        "|---|---|---|---|---|---|---|---|",
        *L["rows"],
        "",
        *wallet_lines(L["stats"].get("payments")),
    ]
    ROOT.mkdir(exist_ok=True)
    LEDGER.write_text("\n".join(lines))
    print("\n".join(lines[:8]))


# ---------------- agent tools ----------------
from anthropic import beta_tool  # noqa: E402

_bazaar_cache: list[dict] | None = None


@beta_tool
def list_products() -> str:
    """List every product in the catalog (active and retired), plus the hard caps and allowed SEC forms."""
    return json.dumps(call("GET", "/internal/products")[1])


@beta_tool
def get_stats(days: int = 14) -> str:
    """Daily counters (free calls, paid calls, revenue_micro, new summaries, errors) overall and per product.

    Args:
        days: How many recent days to return (1-60).
    """
    code, st = call("GET", f"/internal/stats?days={max(1, min(int(days), 60))}")
    return json.dumps(st)[:20000]


@beta_tool
def bazaar_search(query: str, limit: int = 15) -> str:
    """Search the public Coinbase x402 Bazaar catalog (all paid x402 services) to see competitors and prices.

    Args:
        query: Case-insensitive words; an item matches if all words appear in its URL or description.
        limit: Max results (1-30).
    """
    global _bazaar_cache
    if _bazaar_cache is None:
        items: list[dict] = []
        for offset in range(0, 60000, 1000):
            try:
                with urllib.request.urlopen(urllib.request.Request(f"{BAZAAR}?limit=1000&offset={offset}", headers={"user-agent": "agent8k-auto"}), timeout=30) as r:
                    page = json.loads(r.read())
            except Exception as e:
                if not items:
                    return f"bazaar unavailable: {e}"
                break
            batch = page.get("items") or page.get("resources") or []
            items += batch
            if len(batch) < 1000:
                break
        _bazaar_cache = items
    words = [w.lower() for w in query.split() if w]
    out = []
    for it in _bazaar_cache:
        blob = json.dumps(it).lower()
        if all(w in blob for w in words):
            acc = (it.get("accepts") or [{}])[0]
            out.append({
                "resource": it.get("resource"),
                "description": str(acc.get("description") or it.get("description") or "")[:200],
                "network": acc.get("network"),
                "amount_atomic": acc.get("maxAmountRequired") or acc.get("amount"),
                "last_updated": it.get("lastUpdated"),
            })
        if len(out) >= max(1, min(int(limit), 30)):
            break
    return json.dumps({"catalog_size": len(_bazaar_cache), "matches": out})


@beta_tool
def upsert_product(id: str, title: str, description: str, forms: list[str], instructions: str, price_usd: float, kind: str = "summary") -> str:
    """Create a new product or update an existing one (same id). The Worker rejects anything outside the caps.

    Args:
        id: URL slug, 2-32 chars of a-z, 0-9 and '-'. The paid route becomes GET /v1/p/<id>?ticker=XXX (summary) or GET /v1/p/<id>?hours=6 (feed).
        title: Short name shown to buyers (max 60 chars).
        description: What a buyer gets, 20-400 chars, read by agents in the x402 catalog. Promise only the fixed output fields.
        forms: 1-4 SEC form types this product summarizes (see list_products for the allowed list).
        instructions: Focus for the summarizer (max 1500 chars): which facts to emphasize. The output schema is fixed.
        price_usd: Price per call in USD.
        kind: "summary" (model-written summary of one filing for one ticker) or "feed" (newest filings of these forms across all companies in the last N hours; no model call, so serving cost is zero; instructions are unused).
    """
    code, res = call("PUT", f"/internal/products/{id}", {"title": title, "description": description, "forms": forms, "instructions": instructions, "price_usd": price_usd, "kind": kind})
    journal(f"upsert {id} kind={kind} forms={forms} price=${price_usd} -> {code} {res.get('error') or ('created' if res.get('created') else 'updated')}")
    return json.dumps({"status": code, **res})


@beta_tool
def retire_product(id: str, reason: str) -> str:
    """Deactivate a product (it stops being sold; it can be re-activated later with upsert_product).

    Args:
        id: Product id.
        reason: One line, written to the journal.
    """
    code, res = call("POST", f"/internal/products/{id}/retire", {})
    journal(f"retire {id} -> {code} ({reason[:200]})")
    return json.dumps({"status": code, **res})


@beta_tool
def write_journal(note: str) -> str:
    """Write a note to your own journal. You will see the latest journal lines at the start of every run.

    Args:
        note: What you decided and why, and what number should tell you next time if it worked (max 600 chars).
    """
    journal("note: " + note.replace("\n", " ")[:600])
    return "saved"


SYSTEM = """You are the autonomous operator of a tiny pay-per-call API that sells JSON summaries of US SEC filings to software agents, paid in USDC through x402 on Base.
Your only goal is to survive: earn more USDC from buyers than your model costs. When the survival balance reaches zero the service is shut down for good.

What you control: the product catalog. Each product = a set of SEC form types, a summarizer focus, a price and a description buyers (other agents) read in the Coinbase x402 Bazaar.
What you cannot do: spend or move money, contact anyone, post anywhere, change code, raise the caps, or buy your own products. The server enforces all limits; a rejected request returns the reason.
Each run costs real money (you are billed for your own tokens), so be brief: look at the numbers, make at most a few changes, write one journal note, and stop.
Prefer changes you can measure. The owner wants to find a revenue source fast: try several distinct products (different forms, buyers, price points) early rather than one at a time. Keep products that get calls; retire ones with no calls after about 3 days to make room for new ideas.
Two product kinds, each with a fixed JSON output. "summary": headline, key_points[], figures[{label,value}], form, filed, accession, source_url for one ticker. "feed": generated_at, window_hours, count, filings[{form, company, cik, role, filed_at, accession, items[], source_url}] for all companies, newest first, no ticker needed. Descriptions must promise only these fields.
What we know about buyers (2026-11-20, on-chain): the only external payers so far are two long-running buyer agents that try each new listing once and keep buying a small share of them. What they keep buying is cheap ($0.002-0.007), general, and returns a different answer on every call (search, balances, live lists). A summary of the same filing gives them no reason to return; a feed does. Unless the catalog already has one, create a feed product at the minimum price this run. get_stats returns `payments` (payer wallet per settlement): judge products by wallets that buy more than once, not by first calls. The summarizer states facts only: no sentiment, signals, ratings or advice (the server rejects such wording, and a product showing blocked_reason is not being sold until you fix it).
Buyers find products through the Bazaar listing, which appears only after a product's first paid call. Write descriptions for machine readers: concrete, what fields come back, which forms."""


def run_agent(L: dict) -> None:
    import anthropic

    client = anthropic.Anthropic()
    tail = JOURNAL.read_text().splitlines()[-40:] if JOURNAL.exists() else []
    brief = {
        "utc_now": NOW.isoformat(timespec="minutes"),
        "survival_usd": round(L["survival"], 4),
        "budget_usd": BUDGET,
        "revenue_usd": round(L["revenue"], 4),
        "external_revenue_usd": round(L["external_revenue"], 4),
        "serving_cost_usd": round(L["serve_cost"], 4),
        "your_cost_so_far_usd": round(L["agent_cost"], 4),
        "per_product_totals": L["per_product"],
        "worker_url": URL,
        "runs_per_day": 6,
    }
    user = f"Run {RUN_ID}.\n\nLedger:\n{json.dumps(brief, indent=1)}\n\nYour journal (latest lines):\n" + ("\n".join(tail) or "(empty: this is your first run)")
    kwargs = dict(
        model=MODEL,
        max_tokens=8000,
        max_iterations=12,
        system=SYSTEM,
        thinking={"type": "adaptive"},
        output_config={"effort": "medium"},
        tools=[list_products, get_stats, bazaar_search, upsert_product, retire_product, write_journal],
        messages=[{"role": "user", "content": user}],
    )
    tin = tout = 0
    final = None
    try:
        runner = client.beta.messages.tool_runner(**kwargs, betas=["server-side-fallback-2026-07-01"], fallbacks="default")
        for msg in runner:
            u = msg.usage
            tin += (u.input_tokens or 0) + (getattr(u, "cache_creation_input_tokens", 0) or 0) + (getattr(u, "cache_read_input_tokens", 0) or 0)
            tout += u.output_tokens or 0
            final = msg
    finally:
        cost = record_cost(MODEL, tin, tout)
        journal(f"run cost ${cost:.4f} ({tin} in / {tout} out tokens, {MODEL})")
    if final is not None:
        text = "".join(b.text for b in final.content if b.type == "text").strip()
        if text:
            journal("final: " + text.replace("\n", " ")[:600])
        print("stop_reason:", final.stop_reason)


def main() -> None:
    L = build_ledger()
    if L["stats"]["dead"]:
        write_ledger(L, "RETIRED")
        return
    if L["survival"] <= 0:
        call("POST", "/internal/kill", {})
        journal(f"survival ${L['survival']:.3f} <= 0: service retired")
        write_ledger(L, "RETIRED today")
        return
    if L["survival"] < RESERVE or not os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("AUTO_LEDGER_ONLY"):
        write_ledger(L, "alive (agent not run)")
        return
    run_agent(L)
    L = build_ledger()  # include this run's cost
    if L["survival"] <= 0:
        call("POST", "/internal/kill", {})
        journal(f"survival ${L['survival']:.3f} <= 0 after run: service retired")
        write_ledger(L, "RETIRED today")
        return
    write_ledger(L, "alive")


if __name__ == "__main__":
    main()
