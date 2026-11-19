"""Per-wallet view of settled payments, shared by ledger.py and auto_agent.py.

The Worker records one entry per settlement (payer wallet, path, amount) from the day this
was deployed; earlier settlements are not in the list. Crawler wallets buy each new listing
once, so the numbers that matter are repeat buyers and distinct external wallets.
"""
from __future__ import annotations

import os

SELF_WALLETS = {w.strip().lower() for w in os.environ.get("AGENT8K_SELF_WALLETS", "").split(",") if w.strip()}


def wallet_lines(payments: list[dict] | None) -> list[str]:
    payments = payments or []
    by: dict[str, dict] = {}
    for p in sorted(payments, key=lambda p: p["at"]):
        w = by.setdefault(p["payer"], {"calls": 0, "usd": 0.0, "first": p["at"], "last": p["at"], "paths": set()})
        w["calls"] += 1
        w["usd"] += p.get("amount_micro", 0) / 1e6
        w["last"] = p["at"]
        w["paths"].add(p.get("path", "").rsplit("/", 1)[-1])
    ext = {k: v for k, v in by.items() if k not in SELF_WALLETS}
    repeat = sum(1 for v in ext.values() if v["calls"] > 1)
    lines = [
        f"- Buyers (settlements recorded by wallet: {len(payments)}): external wallets {len(ext)} · external wallets with more than one purchase {repeat}",
        "",
        "| wallet | owner | paid calls | revenue $ | first | last | products |",
        "|---|---|---|---|---|---|---|",
    ]
    for k, v in sorted(by.items(), key=lambda kv: (-kv[1]["calls"], kv[1]["first"])):
        lines.append(f"| {k} | {'yes' if k in SELF_WALLETS else ''} | {v['calls']} | {v['usd']:.3f} | {v['first'][:16]}Z | {v['last'][:16]}Z | {', '.join(sorted(v['paths']))} |")
    return lines + [""]
