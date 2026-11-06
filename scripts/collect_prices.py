"""Sim B prices: daily closes since 2008 for every ticker in data/external/sim_filers_*.csv (+ SPY).
Stooq CSV first; when Stooq stops answering with CSV (daily hit limit), yfinance for the rest.
Output: data/external/sim_prices_<shard>.csv.gz (ticker, date, close). Resumable per ticker.
Run on the Actions runner (Stooq/Yahoo are not reachable from the sandbox)."""
from __future__ import annotations

import argparse
import csv
import glob
import gzip
import io
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "data" / "external"
START = "2008-01-01"


def stooq(ticker: str) -> list[tuple[str, float]] | None:
    sym = ticker.lower().replace(".", "-") + ".us"
    r = requests.get("https://stooq.com/q/d/l/", params={"s": sym, "i": "d", "d1": START.replace("-", "")},
                     headers={"User-Agent": "Mozilla/5.0 (money-brain simulation)"}, timeout=60)
    if r.status_code != 200:
        return None
    if not r.text.startswith("Date"):
        if "Exceeded" in r.text or "limit" in r.text.lower():
            return None          # daily limit → caller switches to yfinance
        return []                # no such symbol
    out = []
    for row in csv.DictReader(io.StringIO(r.text)):
        try:
            out.append((row["Date"], float(row["Close"])))
        except (KeyError, ValueError):
            pass
    return out


def yahoo_batch(tickers: list[str]) -> dict[str, list[tuple[str, float]]]:
    import yfinance as yf
    out: dict[str, list[tuple[str, float]]] = {}
    for i in range(0, len(tickers), 50):
        chunk = tickers[i:i + 50]
        try:
            df = yf.download(chunk, start=START, auto_adjust=False, progress=False, threads=True, group_by="ticker")
        except Exception as e:  # noqa: BLE001
            print(f"  yfinance batch failed: {e!r}", flush=True); continue
        for t in chunk:
            try:
                s = df[t]["Close"].dropna() if len(chunk) > 1 else df["Close"].dropna()
                out[t] = [(d.strftime("%Y-%m-%d"), float(v)) for d, v in s.items()]
            except Exception:  # noqa: BLE001
                out[t] = []
        time.sleep(2)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    a = ap.parse_args()
    tickers = {"SPY"}
    for p in glob.glob(str(EXT / "sim_filers_*.csv")):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            t = r["ticker"].strip().upper()
            if t and t.isascii() and len(t) <= 6:
                tickers.add(t)
    mine = sorted(t for t in tickers if (sum(ord(c) for c in t) % a.nshards) == a.shard or t == "SPY")
    out = EXT / f"sim_prices_{a.shard}.csv.gz"
    have: set[str] = set()
    rows: list[tuple[str, str, float]] = []
    if out.exists():
        with gzip.open(out, "rt", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                have.add(r["ticker"]); rows.append((r["ticker"], r["date"], float(r["close"])))
    todo = [t for t in mine if t not in have]
    print(f"shard {a.shard}: {len(mine)} tickers, {len(todo)} to fetch", flush=True)
    use_yahoo = False
    pending_yahoo: list[str] = []
    for i, t in enumerate(todo):
        if not use_yahoo:
            s = stooq(t)
            if s is None:
                print(f"  stooq unavailable at {t}; switching to yfinance", flush=True); use_yahoo = True
            else:
                rows.extend((t, d, c) for d, c in s); have.add(t)
                time.sleep(0.3)
                if i % 200 == 0:
                    print(f"  {i}/{len(todo)}", flush=True)
                continue
        pending_yahoo.append(t)
    if pending_yahoo:
        got = yahoo_batch(pending_yahoo)
        for t, s in got.items():
            rows.extend((t, d, c) for d, c in s); have.add(t)
    with gzip.open(out, "wt", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["ticker", "date", "close"])
        w.writerows(sorted(rows))
    n_with = len({t for t, _, _ in rows})
    print(f"shard {a.shard}: wrote {len(rows)} rows for {n_with} tickers ({len(mine) - n_with} without data)", flush=True)


if __name__ == "__main__":
    main()
