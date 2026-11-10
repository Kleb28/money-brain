"""Sim F — offline test of money-brain 10-K text features against Numerai Signals v3.1 targets.
Protocol: simulation/protocol.md (Sim F). Arithmetic only; no fitting.

Features per (ticker, filing year y1), valid from 1 July y1 to 30 June y1+1:
  F1 = -(number of tracked bigrams the firm mentioned in its 10-K)            [verbosity]
  F2 = F1 restricted to the bottom revenue tercile among matched US tickers that date, 0 otherwise
  F3 = n(T1 signal bigrams) signed by size: - for bottom tercile, + for top tercile, 0 for middle
Metric: per-date Spearman corr with target_jupiter_20 (dates 4 weeks apart) and target_jupiter_60 (12 weeks apart),
raw and after linear neutralization to the Numerai neutralizer matrix. Output: outputs/numerai_signals_test_<split>.md.
Run on GitHub Actions (numer.ai is not reachable from the sandbox). Usage: python -m scripts.numerai_signals_test --split train
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import glob
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "data" / "external"
SIM = ROOT / "simulation"
OUT = ROOT / "outputs"
PRE = "30/0.5/2"
DATA_VERSION = "signals/v3.1"


def load_features() -> pd.DataFrame:
    roles = {}
    for r in csv.DictReader(open(SIM / "filer_queries.csv", encoding="utf-8")):
        roles[(r["bigram"], int(r["year"]))] = r["roles"].split(";")
    n_any: dict[tuple[str, int], int] = defaultdict(int)
    n_t1: dict[tuple[str, int], int] = defaultdict(int)
    for p in glob.glob(str(EXT / "sim_filers_*.csv")):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            t = r["ticker"].strip().upper()
            if not t:
                continue
            key = (r["bigram"], int(r["year"]))
            n_any[(t, key[1])] += 1
            if f"{PRE}:T1" in roles.get(key, []):
                n_t1[(t, key[1])] += 1
    rev = {}
    for r in csv.DictReader(open(EXT / "sim_financials.csv", encoding="utf-8")):
        try:
            if r["revenue"]:
                rev[(r["ticker"].strip().upper(), int(r["fy"]))] = float(r["revenue"])
        except ValueError:
            pass
    rows = [{"ticker": t, "y1": y, "n_any": n, "n_t1": n_t1.get((t, y), 0), "rev": rev.get((t, y - 1))} for (t, y), n in n_any.items()]
    return pd.DataFrame(rows)


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    ra = pd.Series(a).rank().to_numpy()
    rb = pd.Series(b).rank().to_numpy()
    if ra.std() == 0 or rb.std() == 0:
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


def neutralize(x: np.ndarray, M: np.ndarray) -> np.ndarray:
    """Residual of gaussianized ranks of x after linear projection on neutralizer columns M (per date)."""
    from scipy.stats import norm
    r = pd.Series(x).rank().to_numpy()
    g = norm.ppf((r - 0.5) / len(r))
    M = np.nan_to_num(M.astype(float))
    beta, *_ = np.linalg.lstsq(M, g, rcond=None)
    return g - M @ beta


def stats(vals: list[float]) -> dict:
    v = [x for x in vals if not math.isnan(x)]
    n = len(v)
    if n < 2:
        return {"n": n}
    m = sum(v) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in v) / (n - 1))
    return {"n": n, "mean": m, "sd": sd, "t": m / (sd / math.sqrt(n)) if sd > 0 else float("nan"), "pos": sum(1 for x in v if x > 0) / n}


def fmt(s: dict) -> str:
    if s.get("n", 0) < 2:
        return f"– | – | – | – | {s.get('n', 0)}"
    return f"{s['mean']:+.4f} | {s['sd']:.4f} | {s['t']:+.2f} | {s['pos']:.2f} | {s['n']}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["train", "validation"], default="train")
    ap.add_argument("--no-download", action="store_true")
    ap.add_argument("--data-dir", default=str(ROOT / "numerai_data"))
    a = ap.parse_args()
    ddir = Path(a.data_dir); ddir.mkdir(exist_ok=True)
    fn, nfn = f"{a.split}.parquet", f"{a.split}_neutralizer.parquet"
    if not a.no_download:
        from numerapi import SignalsAPI
        napi = SignalsAPI()
        avail = [f for f in napi.list_datasets() if f.startswith(DATA_VERSION)]
        print("datasets:", avail, flush=True)
        for f in (fn, nfn):
            napi.download_dataset(f"{DATA_VERSION}/{f}", dest_path=str(ddir / f))
            print(f"downloaded {f}: {os.path.getsize(ddir / f)/1e6:.0f} MB", flush=True)

    import pyarrow.parquet as pq
    schema = pq.read_schema(ddir / fn)
    cols = schema.names
    print("columns:", len(cols), [c for c in cols if not c.startswith("feature_")][:20], flush=True)
    id_col = "numerai_ticker" if "numerai_ticker" in cols else cols[0]
    want = [c for c in (id_col, "composite_figi", "date", "feature_country", "target_jupiter_20", "target_jupiter_60") if c in cols]
    df = pq.read_table(ddir / fn, columns=want).to_pandas()
    if "date" not in df.columns:
        df = df.reset_index()
    df["date"] = pd.to_datetime(df["date"])
    print(f"{a.split}: {len(df)} rows, {df['date'].nunique()} dates, {df['date'].min().date()} .. {df['date'].max().date()}", flush=True)
    print("ticker examples:", df[id_col].dropna().astype(str).head(5).tolist(), flush=True)

    # US tickers: "AAPL US" style suffix, else feature_country if it looks like a string code
    tk = df[id_col].astype(str)
    us = tk.str.endswith(" US")
    if us.sum() == 0 and "feature_country" in df.columns:
        us = df["feature_country"].astype(str).str.upper().isin(["US", "USA", "UNITED STATES"])
    df = df[us].copy()
    df["ticker"] = tk[us].str.replace(r"\s+US$", "", regex=True).str.replace("/", "-").str.replace(".", "-").str.upper()
    print(f"US rows: {len(df)}, tickers: {df['ticker'].nunique()}", flush=True)

    # join our features
    feats = load_features()
    df["y1"] = np.where(df["date"].dt.month >= 7, df["date"].dt.year, df["date"].dt.year - 1)
    m = df.merge(feats, on=["ticker", "y1"], how="inner")
    cov = m.groupby("date")["ticker"].nunique()
    tot = df.groupby("date")["ticker"].nunique()
    print(f"matched rows: {len(m)}; median tickers/date matched {cov.median():.0f} of {tot.median():.0f}", flush=True)

    # size tercile per date among matched tickers with revenue
    def terc(g):
        r = g["rev"]
        q1, q2 = r.quantile(1 / 3), r.quantile(2 / 3)
        return pd.Series(np.where(r.isna(), 0, np.where(r <= q1, -1, np.where(r > q2, 1, 0))), index=g.index)
    m["size"] = m.groupby("date", group_keys=False).apply(terc)
    m["F1"] = -m["n_any"].astype(float)
    m["F2"] = np.where(m["size"] == -1, -m["n_any"].astype(float), 0.0)
    m["F3"] = m["n_t1"].astype(float) * m["size"].astype(float)

    # date grids
    dates = sorted(m["date"].unique())
    grid = {"target_jupiter_20": dates[::4], "target_jupiter_60": dates[::12]}

    # neutralizer (optional): stream the 7 GB file batch by batch, keep US tickers on the grid dates only
    neut = None
    try:
        pf = pq.ParquetFile(ddir / nfn)
        nschema = pf.schema_arrow
        ncols = [c for c in nschema.names if c not in (id_col, "composite_figi", "date", "data_type")]
        want_dates = {pd.Timestamp(d).strftime("%Y-%m-%d") for d in set(grid["target_jupiter_20"]) | set(grid["target_jupiter_60"])}
        parts = []
        for batch in pf.iter_batches(batch_size=250_000):
            b = batch.to_pandas()
            if "date" not in b.columns:
                b = b.reset_index()
            dstr = pd.to_datetime(b["date"]).dt.strftime("%Y-%m-%d")
            keep = dstr.isin(want_dates) & b[id_col].astype(str).str.endswith(" US")
            if keep.any():
                sub = b.loc[keep, [id_col, "date"] + ncols].copy()
                sub[ncols] = sub[ncols].astype("float32")
                parts.append(sub)
        neut = pd.concat(parts, ignore_index=True)
        neut["date"] = pd.to_datetime(neut["date"])
        print(f"neutralizer: {len(neut)} US rows on grid dates, {len(ncols)} columns", flush=True)
    except Exception as e:  # noqa: BLE001
        print(f"neutralizer not usable: {e!r}"[:300], flush=True)

    lines = [f"# Sim F — Numerai Signals v3.1 offline test ({a.split}; protocol: simulation/protocol.md)", "",
             f"US rows {len(df)} (tickers {df['ticker'].nunique()}); matched to money-brain 10-K features: median {cov.median():.0f} of {tot.median():.0f} tickers per date. "
             f"Dates {min(dates).date()} .. {max(dates).date()}; 20d target on every 4th date, 60d on every 12th. Columns: mean corr | SD | t | share > 0 | n dates.", ""]
    for target, ds in grid.items():
        if target not in m.columns:
            continue
        lines += [f"## {target}", "", "| feature | version | mean | SD | t | pos | n |", "|---|---|---|---|---|---|---|"]
        res = defaultdict(list)
        for d in ds:
            g = m[(m["date"] == d) & m[target].notna()]
            if len(g) < 50:
                continue
            y = g[target].to_numpy(float)
            M = None
            if neut is not None:
                nn = neut[neut["date"] == d].set_index(id_col)
                if len(nn):
                    M = nn.reindex(g[id_col].astype(str))[ncols].to_numpy()
                    if np.isnan(M).all():
                        M = None
            for f in ("F1", "F2", "F3"):
                x = g[f].to_numpy(float)
                res[(f, "raw")].append(spearman(x, y))
                if M is not None:
                    try:
                        res[(f, "neutralized")].append(spearman(neutralize(x, M), y))
                    except Exception:  # noqa: BLE001
                        pass
        for (f, v), vals in sorted(res.items()):
            lines.append(f"| {f} | {v} | {fmt(stats(vals))} |")
        lines.append("")
    OUT.mkdir(exist_ok=True)
    (OUT / f"numerai_signals_test_{a.split}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
