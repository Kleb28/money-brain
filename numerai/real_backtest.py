"""Sim H — trade Numerai-style predictions on real US prices (pre-registered in simulation/protocol.md).

Predictions: (1) the kleb28 recipe (same as numerai/train_baseline.py, trained on data up to 2018-12),
(2) Numerai's benchmark lgbm_jupiter_60. Validation dates (2019-) are out of sample for both.
Every 4th validation date -> US tickers -> yfinance adjusted closes -> 4-week holding portfolios:
long-short deciles, long-only top decile / top 50, equal-weight universe, SPY. Costs 10 bp one-way x turnover.
Writes outputs/numerai_real_backtest.md. Runs on GitHub Actions (numer.ai and Yahoo are not reachable from the sandbox).
Usage: python -m numerai.real_backtest
"""
from __future__ import annotations

import json
import math
import os
import time

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from numerai.train_baseline import DATA, FEATURE_SET, OUT, PARAMS, log, pick_version

STEP = 4              # every 4th validation date ~ 4 weeks
TRAIN_STEP = 4
COST_BP = 10.0        # one-way, per unit of turnover
DECILE = 0.10
TOP_N = 50
BENCH = "lgbm_jupiter_60"
PER_YEAR = 52 / STEP


def yahoo_symbol(t: str) -> str | None:
    t = str(t)
    if not t.endswith(" US"):
        return None
    return t[:-3].strip().replace("/", "-").replace(".", "-")


def download_prices(symbols: list[str], start: str, end: str) -> pd.DataFrame:
    import yfinance as yf
    frames = []
    for i in range(0, len(symbols), 100):
        chunk = symbols[i:i + 100]
        for attempt in range(3):
            try:
                df = yf.download(chunk, start=start, end=end, auto_adjust=True, progress=False, threads=True, group_by="column")
                close = df["Close"] if isinstance(df.columns, pd.MultiIndex) else df[["Close"]].rename(columns={"Close": chunk[0]})
                frames.append(close)
                break
            except Exception as e:  # noqa: BLE001
                log(f"yfinance chunk {i} failed ({attempt}): {e!r}"[:200]); time.sleep(20 * (attempt + 1))
        if (i // 100) % 5 == 0:
            log(f"prices {min(i + 100, len(symbols))}/{len(symbols)}")
    px = pd.concat(frames, axis=1)
    px = px.loc[:, ~px.columns.duplicated()].sort_index()
    px.index = pd.to_datetime(px.index).tz_localize(None)
    return px


def stats(r: pd.Series) -> dict:
    r = r.dropna()
    if len(r) < 3:
        return {k: float("nan") for k in ("mean", "ann", "vol", "sharpe", "t", "dd", "pos")} | {"n": len(r)}
    sd = r.std()
    wealth = (1 + r).cumprod()
    dd = float((1 - wealth / wealth.cummax()).max())
    return {"mean": r.mean(), "ann": (1 + r).prod() ** (PER_YEAR / len(r)) - 1, "vol": sd * math.sqrt(PER_YEAR),
            "sharpe": r.mean() / sd * math.sqrt(PER_YEAR) if sd else float("nan"), "t": r.mean() / (sd / math.sqrt(len(r))) if sd else float("nan"),
            "dd": dd, "pos": (r > 0).mean(), "n": len(r)}


def row(name: str, r: pd.Series) -> str:
    s = stats(r)
    return (f"| {name} | {s['mean']*100:+.2f}% | {s['ann']*100:+.1f}% | {s['vol']*100:.1f}% | {s['sharpe']:.2f} | {s['t']:+.2f} | "
            f"{s['dd']*100:.1f}% | {s['pos']:.2f} | {s['n']} |")


def turnover(prev: dict, cur: dict) -> float:
    keys = set(prev) | set(cur)
    return 0.5 * sum(abs(cur.get(k, 0.0) - prev.get(k, 0.0)) for k in keys)


def main() -> None:
    from numerapi import NumerAPI
    napi = NumerAPI()
    ver = pick_version(napi)
    DATA.mkdir(exist_ok=True)
    for f in ["features.json", "train.parquet", "validation.parquet", "validation_benchmark_models.parquet"]:
        if not (DATA / f).exists():
            napi.download_dataset(f"{ver}/{f}", dest_path=str(DATA / f))
            log(f"downloaded {f}: {os.path.getsize(DATA / f)/1e6:.0f} MB")
    meta = json.load(open(DATA / "features.json"))
    feats = meta["feature_sets"][FEATURE_SET]
    schema = pq.read_schema(DATA / "train.parquet").names
    era_col = "date" if "date" in schema else "era"
    target = "target"

    def load(path: str, step: int, need_target: bool) -> pd.DataFrame:
        cols = [era_col, "numerai_ticker", target] + feats + (["data_type"] if "data_type" in pq.read_schema(DATA / path).names else [])
        df = pq.read_table(DATA / path, columns=cols).to_pandas()
        if "data_type" in df.columns:
            df = df[df["data_type"].isin(["train", "validation"])]
        if need_target:
            df = df.dropna(subset=[target])
        dates = sorted(df[era_col].unique())
        keep = set(dates[::step])
        return df[df[era_col].isin(keep)].copy()

    train = load("train.parquet", TRAIN_STEP, True)
    str_feats = [f for f in feats if not pd.api.types.is_numeric_dtype(train[f])]
    val = load("validation.parquet", STEP, False)
    vocab = {f: {v: i for i, v in enumerate(sorted(set(train[f].dropna().astype(str)) | set(val[f].dropna().astype(str))))} for f in str_feats}
    for df in (train, val):
        for f, m in vocab.items():
            df[f] = df[f].astype(str).map(m).fillna(-1).astype(np.int32)
    import lightgbm as lgb
    model = lgb.LGBMRegressor(**PARAMS)
    t0 = time.time()
    model.fit(train[feats].astype(np.float32), train[target], categorical_feature=[feats.index(f) for f in str_feats] or "auto")
    log(f"trained on {train[era_col].nunique()} dates in {(time.time()-t0)/60:.1f} min")
    del train

    val["sym"] = val["numerai_ticker"].map(yahoo_symbol)
    val = val[val["sym"].notna()].copy()
    val["ours"] = model.predict(val[feats].astype(np.float32))
    val = val[[era_col, "numerai_ticker", "sym", "ours"]]
    bm = pq.read_table(DATA / "validation_benchmark_models.parquet").to_pandas()
    if "numerai_ticker" not in bm.columns:
        bm = bm.reset_index()
    bcol = BENCH if BENCH in bm.columns else None
    if bcol:
        key = lambda x: pd.to_datetime(x).dt.strftime("%Y-%m-%d")
        val["_k"] = key(val[era_col]); bm["_k"] = key(bm[era_col])
        val = val.merge(bm[["numerai_ticker", "_k", bcol]], on=["numerai_ticker", "_k"], how="left").drop(columns="_k")
        log(f"benchmark {bcol} coverage of US rows: {val[bcol].notna().mean():.1%}")
    models = ["ours"] + ([bcol] if bcol else [])
    val["d"] = pd.to_datetime(val[era_col])
    dates = sorted(val["d"].unique())
    log(f"validation US rows {len(val):,}, {len(dates)} rebalance dates {dates[0]:%Y-%m-%d}..{dates[-1]:%Y-%m-%d}, "
        f"{val['sym'].nunique()} symbols, median {val.groupby('d').size().median():.0f}/date")

    syms = sorted(val["sym"].unique())
    px = download_prices(syms + ["SPY"], (pd.Timestamp(dates[0]) - pd.Timedelta(days=10)).strftime("%Y-%m-%d"), pd.Timestamp.today().strftime("%Y-%m-%d"))
    tdays = px.index
    have = set(px.columns[px.notna().any()])
    log(f"price series found for {len(have & set(syms))}/{len(syms)} symbols")

    def entry_day(d: pd.Timestamp) -> pd.Timestamp | None:
        i = tdays.searchsorted(d, side="right") + 1      # 2nd trading day after the feature date
        return tdays[i] if i < len(tdays) else None

    entries = [entry_day(pd.Timestamp(d)) for d in dates]
    periods = []
    for k in range(len(dates)):
        e0 = entries[k]
        e1 = entries[k + 1] if k + 1 < len(dates) else None
        if e0 is None:
            continue
        if e1 is None:   # last date: hold 20 trading days if available
            i = tdays.get_loc(e0) + 20
            if i >= len(tdays):
                continue
            e1 = tdays[i]
        periods.append((dates[k], e0, e1))
    log(f"{len(periods)} holding periods")

    res = {m: {"LS": [], "LS_net": [], "LO10": [], "LO10_net": [], "LO50": [], "LO10_xEW": [], "LO10_xEW_net": []} for m in models}
    common = {"EW": [], "SPY": [], "date": [], "n": [], "cover": []}
    prev_w = {m: {"L": {}, "S": {}, "T": {}} for m in models}
    for d, e0, e1 in periods:
        g = val[val["d"] == d]
        p0, p1 = px.loc[e0], px.loc[e1]
        r = (p1 / p0 - 1).reindex(g["sym"]).to_numpy()
        price_ok = p0.reindex(g["sym"]).to_numpy() >= 1.0
        g = g.assign(ret=np.clip(r, -0.95, 5.0))[price_ok & np.isfinite(r)]
        common["date"].append(pd.Timestamp(d)); common["n"].append(len(g)); common["cover"].append(len(g) / max(1, (val["d"] == d).sum()))
        common["EW"].append(g["ret"].mean())
        common["SPY"].append(float(p1.get("SPY", np.nan) / p0.get("SPY", np.nan) - 1))
        for m in models:
            gm = g.dropna(subset=[m]).sort_values(m)
            if len(gm) < 100:
                for key in res[m]:
                    res[m][key].append(np.nan)
                continue
            k10 = max(1, int(len(gm) * DECILE))
            short, long_ = gm.iloc[:k10], gm.iloc[-k10:]
            top50 = gm.iloc[-TOP_N:]
            ls = long_["ret"].mean() - short["ret"].mean()
            wl = {s: 1 / len(long_) for s in long_["sym"]}; ws = {s: 1 / len(short) for s in short["sym"]}
            c_ls = COST_BP / 1e4 * (turnover(prev_w[m]["L"], wl) + turnover(prev_w[m]["S"], ws)) * 2   # buy+sell legs of each rebalance
            c_lo = COST_BP / 1e4 * turnover(prev_w[m]["L"], wl) * 2
            prev_w[m]["L"], prev_w[m]["S"] = wl, ws
            lo10 = long_["ret"].mean()
            res[m]["LS"].append(ls); res[m]["LS_net"].append(ls - c_ls)
            res[m]["LO10"].append(lo10); res[m]["LO10_net"].append(lo10 - c_lo)
            res[m]["LO50"].append(top50["ret"].mean())
            res[m]["LO10_xEW"].append(lo10 - g["ret"].mean()); res[m]["LO10_xEW_net"].append(lo10 - c_lo - g["ret"].mean())

    idx = pd.DatetimeIndex(common["date"])
    ew, spy = pd.Series(common["EW"], idx), pd.Series(common["SPY"], idx)
    lines = [f"# Sim H — Numerai 예측을 실제 미국 주가로 매매 ({ver}, {pd.Timestamp.today():%Y-%m-%d})", "",
             f"리밸런스 {len(idx)}회({idx.min():%Y-%m-%d} .. {idx.max():%Y-%m-%d}, 약 4주 보유), 날짜당 가격 있는 미국 종목 중앙값 "
             f"{int(np.median(common['n']))}개(Numerai 미국 행 대비 {np.median(common['cover']):.0%}). 비용 한쪽 {COST_BP:.0f} bp × 회전율, 공매도 대여비 0 가정. "
             "열: 기간 평균 | 연율 복리 | 연 변동성 | 연 Sharpe | t | max DD | 양의 비율 | n.", "",
             "| 포트폴리오 | 기간 평균 | 연율 | 연 vol | Sharpe | t | max DD | pos | n |", "|---|---|---|---|---|---|---|---|---|"]
    lines.append(row("SPY", spy)); lines.append(row("미국 universe 동일 비중(EW)", ew))
    names = {"ours": "kleb28 recipe", bcol: f"benchmark {bcol}"}
    for m in models:
        S = {k: pd.Series(v, idx) for k, v in res[m].items()}
        lines += [row(f"{names[m]} · LS 상위10%−하위10% (gross)", S["LS"]), row(f"{names[m]} · LS (net)", S["LS_net"]),
                  row(f"{names[m]} · long-only 상위 10% (net)", S["LO10_net"]), row(f"{names[m]} · long-only 상위 {TOP_N} (gross)", S["LO50"]),
                  row(f"{names[m]} · 상위 10% − EW (net)", S["LO10_xEW_net"])]
    lines += ["", "연도별 기간 평균(net): LS · 상위10%−EW", ""]
    for m in models:
        S = {k: pd.Series(v, idx) for k, v in res[m].items()}
        parts = [f"{y}: {S['LS_net'][S['LS_net'].index.year == y].mean()*100:+.2f}% · {S['LO10_xEW_net'][S['LO10_xEW_net'].index.year == y].mean()*100:+.2f}%"
                 for y in sorted(set(idx.year))]
        lines.append(f"- {names[m]}: " + "; ".join(parts))
    s_ls, s_x = stats(pd.Series(res["ours"]["LS_net"], idx)), stats(pd.Series(res["ours"]["LO10_xEW_net"], idx))
    lines += ["", "## 사전 등록 판정 (kleb28 recipe, net)", "",
              f"- LS: Sharpe {s_ls['sharpe']:.2f}, t {s_ls['t']:+.2f} → 기준(Sharpe ≥ 0.5 이고 t ≥ 2) {'통과' if s_ls['sharpe'] >= 0.5 and s_ls['t'] >= 2 else '미달'}",
              f"- long-only 상위 10% − EW: 기간 평균 {s_x['mean']*100:+.2f}%, t {s_x['t']:+.2f} → 기준(평균 > 0 이고 t ≥ 2) {'통과' if s_x['mean'] > 0 and s_x['t'] >= 2 else '미달'}",
              "- 한계: yfinance에 상장폐지 종목 없음(survivorship), ticker 재사용 오매칭 가능, 미국만, 대여비 0"]
    OUT.mkdir(exist_ok=True)
    (OUT / "numerai_real_backtest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
