"""Daily ledger for the 8-K Brief experiment (agent8k).

Arithmetic only: reads the Worker's own counters and the on-chain USDC balance of the
receive address, writes agent8k/ledger.md, and retires the paid endpoint when the
survival balance (budget + revenue - model cost) reaches zero.

On Mondays it also asks Claude for one proposed change (agent8k/reflections/), which a
human reviews; nothing is deployed automatically.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
LEDGER = ROOT / "ledger.md"
REFLECT_DIR = ROOT / "reflections"

USDC = {
    "eip155:8453": ("https://mainnet.base.org", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"),
    "eip155:84532": ("https://sepolia.base.org", "0x036CbD53842c5426634e7929541eC2318f3dCF7e"),
}


def env(name: str, default: str | None = None) -> str:
    v = os.environ.get(name) or default
    if v is None:
        raise SystemExit(f"missing env {name}")
    return v


def http_json(url: str, headers: dict | None = None, data: dict | None = None) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "agent8k-ledger", **(headers or {})})
    if data is not None:
        req.data = json.dumps(data).encode()
        req.add_header("content-type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def usdc_balance(network: str, address: str) -> float | None:
    if network not in USDC:
        return None
    rpc, token = USDC[network]
    calldata = "0x70a08231" + address.lower().replace("0x", "").rjust(64, "0")
    try:
        res = http_json(rpc, data={"jsonrpc": "2.0", "id": 1, "method": "eth_call", "params": [{"to": token, "data": calldata}, "latest"]})
        return int(res["result"], 16) / 1e6
    except Exception as e:  # RPC hiccups should not break the ledger
        print("balance lookup failed:", e)
        return None


def main() -> None:
    url = env("AGENT8K_URL").rstrip("/")
    token = env("AGENT8K_STATS_TOKEN")
    budget = float(env("AGENT8K_BUDGET_USD", "10"))
    in_price = float(env("AGENT8K_IN_PER_MTOK", "0.10"))  # claude-haiku-5-5
    out_price = float(env("AGENT8K_OUT_PER_MTOK", "0.50"))
    start = env("AGENT8K_START", "")

    st = http_json(f"{url}/internal/stats?days=400", headers={"authorization": f"Bearer {token}"})
    price = float(str(st["price"]).replace("$", ""))
    days = dict(sorted(st["days"].items()))
    if start:
        days = {d: v for d, v in days.items() if d >= start}

    rows, cum_rev, cum_cost = [], 0.0, 0.0
    for d, v in days.items():
        rev = v["paid_calls"] * price
        cost = v["input_tokens"] / 1e6 * in_price + v["output_tokens"] / 1e6 * out_price
        cum_rev += rev
        cum_cost += cost
        rows.append(
            f"| {d} | {v['free_calls']} | {v['paid_calls']} | {v['new_summaries']} | {v['cache_hits']} | {v['errors']} | "
            f"{rev:.2f} | {cost:.4f} | {budget + cum_rev - cum_cost:.2f} |"
        )

    survival = budget + cum_rev - cum_cost
    bal = usdc_balance(st["network"], st["pay_to"])
    dead = st["dead"]
    killed_now = False
    if survival <= 0 and not dead:
        http_json(f"{url}/internal/kill", headers={"authorization": f"Bearer {token}"}, data={})
        dead = killed_now = True

    today = dt.date.today().isoformat()
    lines = [
        "# 8-K Brief ledger",
        "",
        f"Updated {today} by agent8k/ledger.py. Do not edit by hand.",
        "",
        f"- Network: {st['network']} · price {st['price']}/call · receive address {st['pay_to']}",
        f"- Budget ${budget:.2f} · revenue (paid calls × price) ${cum_rev:.2f} · model cost (estimated from tokens) ${cum_cost:.4f}",
        f"- Survival balance ${survival:.2f} · on-chain USDC {'n/a' if bal is None else f'${bal:.2f}'}",
        f"- Status: {'RETIRED' + (' today' if killed_now else '') if dead else 'alive'}",
        "",
        "| date | free calls | paid calls | new summaries | cache hits | errors | revenue $ | model cost $ | survival $ |",
        "|---|---|---|---|---|---|---|---|---|",
        *rows,
        "",
    ]
    LEDGER.write_text("\n".join(lines))
    print("\n".join(lines[:9]))

    if dt.date.today().weekday() == 0 and os.environ.get("ANTHROPIC_API_KEY") and not dead:
        reflect(LEDGER.read_text())


def reflect(ledger: str) -> None:
    import anthropic

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-opus-5-5",
        max_tokens=16000,
        output_config={"effort": "medium"},
        system=(
            "You run a tiny pay-per-call API (8-K Brief: JSON summaries of SEC 8-K filings, paid in USDC via x402) "
            "whose only goal is to earn more than its model cost. You cannot spend money, send outreach, or deploy code. "
            "Read the ledger and propose exactly ONE concrete change for the human to review (price, description, "
            "endpoint shape, where to list it). Say what number in the ledger would show it worked. Under 150 words."
        ),
        messages=[{"role": "user", "content": ledger}],
    )
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    REFLECT_DIR.mkdir(exist_ok=True)
    (REFLECT_DIR / f"{dt.date.today().isoformat()}.md").write_text(text + "\n")
    print("reflection written")


if __name__ == "__main__":
    main()
