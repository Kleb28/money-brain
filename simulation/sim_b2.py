"""Sim B2 — three pre-registered alternative firm linkages (protocol: simulation/protocol.md, Sim B2).
V1 niche events (3-10 mentioning firms), V2 firm ranking by number of T1 signal bigrams mentioned,
V3 R&D-intensive mentioners (needs data/external/sim_financials.csv; skipped if absent).
Same price handling as sim_b.py. Pass bar: t >= 2.5 and above the matching control. Output outputs/sim_b2.md.
"""
from __future__ import annotations

import csv
import datetime as dt
import glob
import gzip
import math
from collections import defaultdict
from pathlib import Path

from simulation.sim_b import (HOLDS, MAX_TICKER_RETURN, MIN_ENTRY_PRICE, MIN_TICKERS, PRE, cluster_stats, fmt,
                              load_prices, price_on_or_after)

ROOT = Path(__file__).resolve().parents[1]
SIM = ROOT / "simulation"
EXT = ROOT / "data" / "external"
OUT = ROOT / "outputs"
NICHE = (3, 10)
TOP_FRAC = 0.10
RD_MIN = 0.10


def ticker_return(prices, t, entry_day, exit_day):
    s = prices.get(t)
    if not s:
        return None
    p0, p1 = price_on_or_after(s, entry_day), price_on_or_after(s, exit_day)
    if p0 and p1 and p0 >= MIN_ENTRY_PRICE:
        return min(p1 / p0 - 1, MAX_TICKER_RETURN)
    return None


def basket_excess(prices, spy, tickers, y1, k):
    entry_day, exit_day = dt.date(y1, 7, 1), dt.date(y1 + k, 7, 1)
    if exit_day > max(spy[0]):
        return None
    spy0, spy1 = price_on_or_after(spy, entry_day), price_on_or_after(spy, exit_day)
    if not spy0 or not spy1:
        return None
    tr = [r for r in (ticker_return(prices, t, entry_day, exit_day) for t in tickers) if r is not None]
    if len(tr) < MIN_TICKERS:
        return None
    return sum(tr) / len(tr) - (spy1 / spy0 - 1), len(tr)


def main() -> None:
    prices = load_prices()
    spy = prices["SPY"]
    roles = {}
    for r in csv.DictReader(open(SIM / "filer_queries.csv", encoding="utf-8")):
        roles[(r["bigram"], int(r["year"]))] = r["roles"].split(";")
    filers: dict[tuple[str, int], set[str]] = defaultdict(set)
    cik_of: dict[str, str] = {}
    for p in glob.glob(str(EXT / "sim_filers_*.csv")):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            t = r["ticker"].strip().upper()
            if t:
                filers[(r["bigram"], int(r["year"]))].add(t); cik_of[t] = r["cik"].strip().lstrip("0")
    t1_keys = [k for k, rs in roles.items() if f"{PRE}:T1" in rs]
    ctl_keys = [k for k, rs in roles.items() if "control:T1" in rs]
    lines = ["# Sim B2 — alternative firm linkages (pre-registered 2026-11-08; pass bar t ≥ 2.5 and above control)", "",
             "Columns: mean excess | cluster SE (by T) | t | median / hit | n (clusters). Same price rules as Sim B.", ""]

    # ---- V1 niche events ----
    lines += ["## V1 — niche events (3–10 mentioning firms in the T+1 10-Ks)", "", "| arm | hold | mean | SE | t | median / hit | n (clusters) |", "|---|---|---|---|---|---|---|"]
    for name, keys in (("T1 niche", t1_keys), ("control niche", ctl_keys)):
        for k in HOLDS:
            vals, cl = [], []
            for (bg, y1) in keys:
                tk = filers.get((bg, y1), set())
                if not (NICHE[0] <= len(tk) <= NICHE[1]):
                    continue
                r = basket_excess(prices, spy, tk, y1, k)
                if r:
                    vals.append(r[0]); cl.append(y1 - 1)
            lines.append(f"| {name} | {k}y | {fmt(cluster_stats(vals, cl))} |")
    lines.append("")

    # ---- V2 firm ranking by count of T1 signal bigrams mentioned in year y1 ----
    lines += ["## V2 — firm ranking: top 10% of firms by number of T1 signal bigrams in their 10-K (per year) vs the rest", "",
              "| arm | hold | mean | SE | t | median / hit | n (clusters) |", "|---|---|---|---|---|---|---|",]
    def firm_counts(keys):
        by_year: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for (bg, y1) in keys:
            for t in filers.get((bg, y1), set()):
                by_year[y1][t] += 1
        return by_year
    for name, keys in (("T1-signal vocabulary", t1_keys), ("no-signal vocabulary (control)", ctl_keys)):
        cnt = firm_counts(keys)
        for k in HOLDS:
            top_vals, rest_vals, cl_top, cl_rest = [], [], [], []
            for y1, fc in sorted(cnt.items()):
                ranked = sorted(fc.items(), key=lambda x: -x[1])
                n_top = max(MIN_TICKERS, int(len(ranked) * TOP_FRAC))
                top = [t for t, _ in ranked[:n_top]]; rest = [t for t, _ in ranked[n_top:]]
                rt, rr = basket_excess(prices, spy, top, y1, k), basket_excess(prices, spy, rest, y1, k)
                if rt and rr:
                    top_vals.append(rt[0]); rest_vals.append(rr[0]); cl_top.append(y1 - 1); cl_rest.append(y1 - 1)
            st, sr = cluster_stats(top_vals, cl_top), cluster_stats(rest_vals, cl_rest)
            lines.append(f"| {name}: top 10% | {k}y | {fmt(st)} |")
            lines.append(f"| {name}: rest | {k}y | {fmt(sr)} |")
            if st["n"] and sr["n"]:
                diffs = [a - b for a, b in zip(top_vals, rest_vals)]
                sd = cluster_stats(diffs, cl_top)
                lines.append(f"| {name}: top − rest (paired by year) | {k}y | {fmt(sd)} |")
    lines.append("")

    # ---- V3 R&D-intensive mentioners ----
    fin = EXT / "sim_financials.csv"
    if fin.exists():
        rd_ratio: dict[tuple[str, int], float] = {}
        for r in csv.DictReader(open(fin, encoding="utf-8")):
            try:
                if r["revenue"] and r["rd"] and float(r["revenue"]) > 0:
                    rd_ratio[(r["ticker"], int(r["fy"]))] = float(r["rd"]) / float(r["revenue"])
            except ValueError:
                pass
        lines += [f"## V3 — R&D-intensive mentioners (R&D / revenue ≥ {RD_MIN:.0%} in fiscal year T)", "",
                  "| arm | hold | mean | SE | t | median / hit | n (clusters) |", "|---|---|---|---|---|---|---|"]
        for name, keys in (("T1, R&D-intensive", t1_keys), ("control, R&D-intensive", ctl_keys)):
            for k in HOLDS:
                vals, cl = [], []
                for (bg, y1) in keys:
                    T = y1 - 1
                    tk = {t for t in filers.get((bg, y1), set()) if rd_ratio.get((t, T), rd_ratio.get((t, y1), 0.0)) >= RD_MIN}
                    r = basket_excess(prices, spy, tk, y1, k)
                    if r:
                        vals.append(r[0]); cl.append(T)
                lines.append(f"| {name} | {k}y | {fmt(cluster_stats(vals, cl))} |")
        lines.append("")
    else:
        lines += ["## V3 — R&D-intensive mentioners: financials not collected yet (data/external/sim_financials.csv missing)", ""]

    OUT.mkdir(exist_ok=True)
    (OUT / "sim_b2.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
