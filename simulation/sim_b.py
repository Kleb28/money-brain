"""Sim B — returns of baskets formed from the firms that mention a candidate bigram in their 10-K
the year after the patent signal. Protocol: simulation/protocol.md. Arithmetic only.

Inputs: simulation/filer_queries.csv (bigram, year=T+1, roles), data/external/sim_filers_*.csv,
data/external/sim_prices_*.csv.gz. Entry = first trading day on/after 1 July of T+1; hold 1/2/3 years;
equal weight buy-and-hold; excess = basket − SPY (price returns). Baskets need ≥ 3 tickers with prices.
Standard errors are clustered by T (events in the same year share a market path).
Output: outputs/sim_b.md and outputs/sim_b_events.csv.
"""
from __future__ import annotations

import bisect
import csv
import datetime as dt
import glob
import gzip
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIM = ROOT / "simulation"
EXT = ROOT / "data" / "external"
OUT = ROOT / "outputs"
PRE = "30/0.5/2"
HOLDS = (1, 2, 3)
MIN_TICKERS = 3
LAST_DATE = None  # set from data


def load_prices() -> dict[str, tuple[list[dt.date], list[float]]]:
    raw: dict[str, list[tuple[dt.date, float]]] = defaultdict(list)
    for p in glob.glob(str(EXT / "sim_prices_*.csv.gz")):
        with gzip.open(p, "rt", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                raw[r["ticker"]].append((dt.date.fromisoformat(r["date"]), float(r["close"])))
    out = {}
    for t, rows in raw.items():
        rows.sort()
        out[t] = ([d for d, _ in rows], [c for _, c in rows])
    return out


def price_on_or_after(series, day: dt.date, max_gap_days: int = 10):
    dates, closes = series
    i = bisect.bisect_left(dates, day)
    if i >= len(dates) or (dates[i] - day).days > max_gap_days:
        return None
    return closes[i]


def cluster_stats(values: list[float], clusters: list):
    n = len(values)
    if n == 0:
        return {"n": 0}
    mean = sum(values) / n
    by = defaultdict(float)
    for v, c in zip(values, clusters):
        by[c] += v - mean
    se = math.sqrt(sum(s * s for s in by.values())) / n
    med = sorted(values)[n // 2]
    hit = sum(1 for v in values if v > 0) / n
    return {"n": n, "mean": mean, "se": se, "t": mean / se if se > 0 else float("nan"), "median": med, "hit": hit, "clusters": len(by)}


def fmt(s):
    if s["n"] == 0:
        return "– | – | – | – | 0"
    return f"{s['mean']*100:+.1f}% | ±{s['se']*100:.1f} | {s['t']:.1f} | {s['median']*100:+.1f}% / {s['hit']:.2f} | {s['n']} ({s['clusters']})"


def main() -> None:
    prices = load_prices()
    spy = prices.get("SPY")
    if not spy:
        raise SystemExit("SPY prices missing")
    last = max(spy[0])
    roles = {}
    for r in csv.DictReader(open(SIM / "filer_queries.csv", encoding="utf-8")):
        roles[(r["bigram"], int(r["year"]))] = r["roles"].split(";")
    filers: dict[tuple[str, int], set[str]] = defaultdict(set)
    for p in glob.glob(str(EXT / "sim_filers_*.csv")):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            t = r["ticker"].strip().upper()
            if t:
                filers[(r["bigram"], int(r["year"]))].add(t)

    # per-event returns
    events = []   # dict per (bigram, T+1)
    cov_num = cov_den = 0
    for key, tickers in filers.items():
        bg, y1 = key
        T = y1 - 1
        entry_day = dt.date(y1, 7, 1)
        rets = {}
        for k in HOLDS:
            exit_day = dt.date(y1 + k, 7, 1)
            if exit_day > last:
                continue
            spy0, spy1 = price_on_or_after(spy, entry_day), price_on_or_after(spy, exit_day)
            if not spy0 or not spy1:
                continue
            tr = []
            for t in tickers:
                s = prices.get(t)
                if not s:
                    continue
                p0, p1 = price_on_or_after(s, entry_day), price_on_or_after(s, exit_day)
                if p0 and p1 and p0 > 0:
                    tr.append(p1 / p0 - 1)
            if k == 1:
                cov_num += len(tr); cov_den += len(tickers)
            if len(tr) >= MIN_TICKERS:
                rets[k] = (sum(tr) / len(tr) - (spy1 / spy0 - 1), len(tr))
        if rets:
            events.append({"bigram": bg, "T": T, "roles": roles.get(key, []), "n_tickers": len(tickers), "rets": rets})

    lines = ["# Sim B — basket excess returns (protocol: simulation/protocol.md)", "",
             f"Entry: first trading day on/after 1 July of T+1 (10-K season over); exit after 1/2/3 years; equal weight, price returns, excess over SPY. "
             f"Baskets need ≥ {MIN_TICKERS} tickers with prices. Prices end {last}. Ticker coverage at entry (tickers with prices ÷ tickers named in 10-Ks): "
             f"{cov_num/cov_den:.2f} — missing tickers are mostly delisted firms (survivorship bias, same direction for every arm).", "",
             "Columns: mean excess | cluster SE (by T) | t | median / hit rate | n events (T clusters)", ""]

    def select(role_prefix: str, role_suffix: str):
        return [e for e in events if any(r == f"{role_prefix}:{role_suffix}" for r in e["roles"])]

    # 1. pre-registered rule arms + control
    lines += [f"## Pre-registered rule {PRE}: T1 vs mid vs T2 vs no-signal control", "",
              "| arm | hold | mean | SE | t | median / hit | n (clusters) |", "|---|---|---|---|---|---|---|"]
    arms = [("T1 (signal, 10-K < 50)", select(PRE, "T1")), ("mid (signal, 50–199)", select(PRE, "mid")),
            ("T2 (signal, ≥ 200)", select(PRE, "T2")), ("control (no signal, 10-K < 50)", select("control", "T1"))]
    arm_stats = {}
    for name, evs in arms:
        for k in HOLDS:
            vals = [e["rets"][k][0] for e in evs if k in e["rets"]]
            cl = [e["T"] for e in evs if k in e["rets"]]
            s = cluster_stats(vals, cl); arm_stats[(name, k)] = s
            lines.append(f"| {name} | {k}y | {fmt(s)} |")
    lines += ["", "T1 − control (difference of means, SE combined):", ""]
    for k in HOLDS:
        a, b = arm_stats[("T1 (signal, 10-K < 50)", k)], arm_stats[("control (no signal, 10-K < 50)", k)]
        if a["n"] and b["n"]:
            d = a["mean"] - b["mean"]; se = math.sqrt(a["se"] ** 2 + b["se"] ** 2)
            lines.append(f"- {k}y: {d*100:+.1f} pp ± {se*100:.1f} (t = {d/se:.1f})")
    lines += ["", "T1 − T2 (early vs already-discussed):", ""]
    for k in HOLDS:
        a, b = arm_stats[("T1 (signal, 10-K < 50)", k)], arm_stats[("T2 (signal, ≥ 200)", k)]
        if a["n"] and b["n"]:
            d = a["mean"] - b["mean"]; se = math.sqrt(a["se"] ** 2 + b["se"] ** 2)
            lines.append(f"- {k}y: {d*100:+.1f} pp ± {se*100:.1f} (t = {d/se:.1f})")

    # 2. all rules, T1, 2-year hold
    lines += ["", "## All grid rules, T1 baskets", "", "| rule | hold | mean | SE | t | median / hit | n (clusters) |", "|---|---|---|---|---|---|---|"]
    rules = sorted({r.split(":")[0] for e in events for r in e["roles"] if not r.startswith("control")})
    for rule in rules:
        evs = select(rule, "T1")
        for k in HOLDS:
            vals = [e["rets"][k][0] for e in evs if k in e["rets"]]; cl = [e["T"] for e in evs if k in e["rets"]]
            lines.append(f"| {'**' + rule + '**' if rule == PRE else rule} | {k}y | {fmt(cluster_stats(vals, cl))} |")

    # 3. pre-registered T1 by T bucket, 2-year hold
    lines += ["", f"## {PRE} T1 by signal year (2-year hold) with control", "", "| T | T1 mean | SE | n | control mean | SE | n | SPY 2y (mean over events) |", "|---|---|---|---|---|---|---|---|"]
    for a_, b_ in [(2008, 2010), (2011, 2013), (2014, 2016), (2017, 2019), (2020, 2022)]:
        t1 = [e for e in select(PRE, "T1") if a_ <= e["T"] <= b_ and 2 in e["rets"]]
        ct = [e for e in select("control", "T1") if a_ <= e["T"] <= b_ and 2 in e["rets"]]
        s1 = cluster_stats([e["rets"][2][0] for e in t1], [e["T"] for e in t1])
        s2 = cluster_stats([e["rets"][2][0] for e in ct], [e["T"] for e in ct])
        spy_r = []
        for e in t1:
            y1 = e["T"] + 1
            p0, p1 = price_on_or_after(spy, dt.date(y1, 7, 1)), price_on_or_after(spy, dt.date(y1 + 2, 7, 1))
            if p0 and p1:
                spy_r.append(p1 / p0 - 1)
        spy_m = f"{sum(spy_r)/len(spy_r)*100:+.1f}%" if spy_r else "–"
        f1 = f"{s1['mean']*100:+.1f}% | ±{s1['se']*100:.1f} | {s1['n']}" if s1["n"] else "– | – | 0"
        f2 = f"{s2['mean']*100:+.1f}% | ±{s2['se']*100:.1f} | {s2['n']}" if s2["n"] else "– | – | 0"
        lines.append(f"| {a_}–{b_} | {f1} | {f2} | {spy_m} |")

    OUT.mkdir(exist_ok=True)
    (OUT / "sim_b.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    with open(OUT / "sim_b_events.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["bigram", "T", "roles", "n_tickers", "ex1y", "n1", "ex2y", "n2", "ex3y", "n3"])
        for e in events:
            row = [e["bigram"], e["T"], ";".join(e["roles"]), e["n_tickers"]]
            for k in HOLDS:
                row += [f"{e['rets'][k][0]:.4f}" if k in e["rets"] else "", e["rets"][k][1] if k in e["rets"] else ""]
            w.writerow(row)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
