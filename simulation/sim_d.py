"""Sim D — Ben-David et al. (RFS 2023) check on our thematic-ETF list: ETF return minus SPY over the
12 and 24 months after launch (launch = first available daily close). Fetches adjusted closes with
yfinance on the Actions runner. Output: outputs/sim_d.md"""
from __future__ import annotations

import csv
import datetime as dt
import statistics
from pathlib import Path

import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"


def main() -> None:
    etfs = list(csv.DictReader(open(ROOT / "simulation" / "etf_list.csv", encoding="utf-8")))
    tickers = [e["ticker"] for e in etfs] + ["SPY"]
    px = yf.download(tickers, start="2005-01-01", auto_adjust=True, progress=False, group_by="ticker", threads=False)
    spy = px["SPY"]["Close"].dropna()
    rows, r12, r24 = [], [], []
    for e in etfs:
        t = e["ticker"]
        try:
            s = px[t]["Close"].dropna()
        except KeyError:
            rows.append((t, e["name"], "–", "–", "–", "no data")); continue
        if s.empty:
            rows.append((t, e["name"], "–", "–", "–", "no data")); continue
        d0 = s.index[0]
        if d0 <= dt.datetime(2005, 1, 10):
            rows.append((t, e["name"], d0.date().isoformat(), "–", "–", "pre-2005 history, launch date unknown")); continue
        out = [t, e["name"], d0.date().isoformat()]
        for months, acc in ((12, r12), (24, r24)):
            d1 = d0 + dt.timedelta(days=int(months * 30.44))
            s1 = s[s.index >= d1]; sp0 = spy[spy.index >= d0]; sp1 = spy[spy.index >= d1]
            if s1.empty or sp1.empty or sp0.empty:
                out.append("–"); continue
            ex = (s1.iloc[0] / s.iloc[0] - 1) - (sp1.iloc[0] / sp0.iloc[0] - 1)
            acc.append(ex); out.append(f"{ex*100:+.1f}%")
        out.append("")
        rows.append(tuple(out))
    lines = ["# Sim D — thematic ETFs after launch, excess return over SPY (adjusted closes)", "",
             f"n with 12-month window: {len(r12)}; mean {statistics.mean(r12)*100:+.1f}%, median {statistics.median(r12)*100:+.1f}%, share negative {sum(1 for x in r12 if x < 0)/len(r12):.2f}" if r12 else "no data",
             f"n with 24-month window: {len(r24)}; mean {statistics.mean(r24)*100:+.1f}%, median {statistics.median(r24)*100:+.1f}%, share negative {sum(1 for x in r24 if x < 0)/len(r24):.2f}" if r24 else "", "",
             "Reference: Ben-David·Franzoni·Kim·Moussawi (RFS 2023) report specialized ETFs underperforming by about −30% risk-adjusted over five years after launch; this table is raw price excess over SPY with no risk adjustment.", "",
             "| ticker | ETF | first close | 12m − SPY | 24m − SPY | note |", "|---|---|---|---|---|---|"]
    for r in rows:
        lines.append("| " + " | ".join(str(x) for x in r) + " |")
    OUT.mkdir(exist_ok=True)
    (OUT / "sim_d.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:5]))


if __name__ == "__main__":
    main()
