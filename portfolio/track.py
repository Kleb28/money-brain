"""Weekly paper-portfolio tracker (arithmetic only).

Fetches daily closes for every ticker in portfolio/holdings.csv (Stooq CSV endpoint, yfinance as
fallback), appends new rows to data/prices.csv, and writes outputs/portfolio.md with buy-and-hold
equal-weight returns since inception for each basket, the treatment portfolio (1/3 per basket), and
the control baskets, plus a monthly-rebalanced variant and max drawdown. Rules: portfolio/rules.md.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
from collections import defaultdict
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
HOLD = ROOT / "portfolio" / "holdings.csv"
PRICES = ROOT / "data" / "prices.csv"
OUT = ROOT / "outputs" / "portfolio.md"
INCEPTION = dt.date(2026, 11, 6)
BASKET_WEIGHT = {"adv_packaging": 1 / 3, "ntn_d2d": 1 / 3, "battery_next": 1 / 3}


def stooq(ticker: str) -> dict[dt.date, float]:
    r = requests.get("https://stooq.com/q/d/l/", params={"s": f"{ticker.lower()}.us", "i": "d"},
                     headers={"User-Agent": "Mozilla/5.0 (money-brain portfolio tracker)"}, timeout=60)
    out = {}
    if r.status_code == 200 and r.text.startswith("Date"):
        for row in csv.DictReader(io.StringIO(r.text)):
            try:
                out[dt.date.fromisoformat(row["Date"])] = float(row["Close"])
            except (KeyError, ValueError):
                pass
    return out


def yahoo(ticker: str) -> dict[dt.date, float]:
    try:
        import yfinance as yf
        h = yf.Ticker(ticker).history(period="2y", auto_adjust=False)
        return {d.date(): float(c) for d, c in h["Close"].items()}
    except Exception as e:  # noqa: BLE001
        print(f"  yfinance failed for {ticker}: {e!r}")
        return {}


def load_prices() -> dict[str, dict[dt.date, float]]:
    p: dict[str, dict[dt.date, float]] = defaultdict(dict)
    if PRICES.exists():
        for r in csv.DictReader(open(PRICES, encoding="utf-8")):
            p[r["ticker"]][dt.date.fromisoformat(r["date"])] = float(r["close"])
    return p


def save_prices(p: dict[str, dict[dt.date, float]]) -> None:
    PRICES.parent.mkdir(parents=True, exist_ok=True)
    with open(PRICES, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["ticker", "date", "close"])
        for t in sorted(p):
            for d in sorted(p[t]):
                w.writerow([t, d.isoformat(), f"{p[t][d]:.4f}"])


def first_on_or_after(series: dict[dt.date, float], day: dt.date) -> tuple[dt.date, float] | None:
    ds = sorted(d for d in series if d >= day)
    return (ds[0], series[ds[0]]) if ds else None


def main() -> None:
    hold = list(csv.DictReader(open(HOLD, encoding="utf-8")))
    tickers = sorted({h["ticker"] for h in hold})
    prices = load_prices()
    for t in tickers:
        s = stooq(t) or yahoo(t)
        new = {d: c for d, c in s.items() if d >= INCEPTION - dt.timedelta(days=400)}
        prices[t].update(new)
        print(f"{t}: {len(new)} rows fetched; latest {max(new) if new else None}")
    save_prices(prices)

    # common latest date across tickers that have an inception price
    incep = {t: first_on_or_after(prices[t], INCEPTION) for t in tickers}
    have = [t for t in tickers if incep[t]]
    if not have:
        OUT.write_text(f"# Portfolio — no closes on/after inception {INCEPTION} yet\n", encoding="utf-8")
        print("no inception closes yet"); return
    latest = min(max(prices[t]) for t in have)
    ret = {t: prices[t][latest] / incep[t][1] - 1 for t in have if latest in prices[t]}

    # buy-and-hold equal weight per basket; treatment = 1/3 per basket
    baskets: dict[str, list[dict]] = defaultdict(list)
    for h in hold:
        baskets[h["basket"]].append(h)
    b_ret = {}
    for b, hs in baskets.items():
        ws = [(h["ticker"], float(h["weight_in_basket"])) for h in hs if h["ticker"] in ret]
        if ws:
            tot = sum(w for _, w in ws)
            b_ret[b] = sum(w / tot * ret[t] for t, w in ws)
    t_ret = sum(BASKET_WEIGHT[b] * b_ret[b] for b in BASKET_WEIGHT if b in b_ret) if all(b in b_ret for b in BASKET_WEIGHT) else None

    # daily NAV path for max drawdown (treatment, buy-and-hold)
    def nav_path(weights: dict[str, float]) -> list[tuple[dt.date, float]]:
        days = sorted(set.intersection(*[set(d for d in prices[t] if d >= incep[t][0]) for t in weights]))
        return [(d, sum(w * prices[t][d] / incep[t][1] for t, w in weights.items())) for d in days]

    def max_dd(path: list[tuple[dt.date, float]]) -> float:
        peak, dd = -1.0, 0.0
        for _, v in path:
            peak = max(peak, v); dd = min(dd, v / peak - 1)
        return dd

    t_weights = {}
    for b, bw in BASKET_WEIGHT.items():
        hs = [h for h in baskets.get(b, []) if h["ticker"] in ret]
        tot = sum(float(h["weight_in_basket"]) for h in hs) or 1
        for h in hs:
            t_weights[h["ticker"]] = bw * float(h["weight_in_basket"]) / tot
    t_path = nav_path(t_weights) if t_weights else []

    # monthly-rebalanced treatment variant
    def rebalanced(weights: dict[str, float]) -> float | None:
        if not weights:
            return None
        days = sorted(set.intersection(*[set(d for d in prices[t] if d >= incep[t][0]) for t in weights]))
        if len(days) < 2:
            return 0.0
        nav, anchor = 1.0, days[0]
        for i in range(1, len(days)):
            d = days[i]
            if d.month != days[i - 1].month:   # rebalance at first trading day of each month
                nav *= sum(w * prices[t][days[i - 1]] / prices[t][anchor] for t, w in weights.items()); anchor = days[i - 1]
        nav *= sum(w * prices[t][days[-1]] / prices[t][anchor] for t, w in weights.items())
        return nav - 1

    lines = [f"# Paper portfolio — inception {INCEPTION}, as of {latest}", "",
             "Price returns only (no dividends). Buy-and-hold equal weight within basket; treatment = 1/3 per basket. Rules: portfolio/rules.md", "",
             "| portfolio | return since inception | vs SPY | max drawdown (daily) |", "|---|---|---|---|"]
    spy = ret.get("SPY")
    def rel(x): return f"{(x - spy)*100:+.1f} pp" if (x is not None and spy is not None) else "–"
    if t_ret is not None:
        lines.append(f"| Treatment (3 theses) | {t_ret*100:+.1f}% | {rel(t_ret)} | {max_dd(t_path)*100:.1f}% |")
        rb = rebalanced(t_weights)
        if rb is not None:
            lines.append(f"| Treatment, monthly rebalanced | {rb*100:+.1f}% | {rel(rb)} | – |")
    for b in ["adv_packaging", "ntn_d2d", "battery_next", "attention_peak", "market", "sector"]:
        if b in b_ret:
            lines.append(f"| {b} | {b_ret[b]*100:+.1f}% | {rel(b_ret[b])} | – |")
    lines += ["", "| ticker | basket | inception close (date) | latest close | return |", "|---|---|---|---|---|"]
    for h in hold:
        t = h["ticker"]
        if t in ret:
            lines.append(f"| {t} | {h['basket']} | {incep[t][1]:.2f} ({incep[t][0]}) | {prices[t][latest]:.2f} | {ret[t]*100:+.1f}% |")
        else:
            lines.append(f"| {t} | {h['basket']} | – | – | no data |")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
