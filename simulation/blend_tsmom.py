"""Exploratory (not pre-registered, 2026-11-18): does adding TSMOM to SPY 60 / IEF 40 help on 2002-2026?

TSMOM is the Sim J reference definition (21 ETFs, sign of 12m excess return, 10%/vol/N, monthly).
As a fund sleeve it is levered 2x (~9% vol, typical managed-futures level) on top of cash:
sleeve = rf + 2 x TSMOM excess - 5 bp x turnover. Blend = (1-x) 60/40 + x sleeve, rebalanced monthly.
Writes outputs/blend_tsmom.md.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from simulation.sim_j import french, nw_t, sharpe

OUT = "outputs/blend_tsmom.md"


def series() -> pd.DataFrame:
    px = pd.read_csv("data/external/sim_j_etf.csv.gz", index_col=0, parse_dates=True).dropna(how="all")
    px = px.loc[px.index < pd.Timestamp.today().normalize().replace(day=1)]
    dret = px.pct_change(fill_method=None)
    vol = (dret.rolling(63, min_periods=50).std() * np.sqrt(252)).resample("ME").last()
    M = px.resample("ME").last()
    first = px.apply(lambda s: s.first_valid_index())
    for c in M.columns:
        M.loc[M.index <= first[c] + pd.offsets.MonthEnd(0), c] = np.nan
    R = M.pct_change(fill_method=None)
    rf = french()["RF"].reindex(M.index).ffill()
    rf12 = (1 + rf).rolling(12).apply(np.prod, raw=True) - 1
    nxt = R.shift(-1)
    out, prev = {}, pd.Series(dtype=float)
    for d in M.index[:-1]:
        ex12 = (M.loc[d] / M.shift(12).loc[d] - 1) - rf12.loc[d]
        v, r = vol.loc[d], nxt.loc[d]
        ok = ex12.notna() & v.notna() & r.notna()
        if ok.sum() < 8 or pd.isna(r.get("SPY")) or pd.isna(r.get("IEF")):
            continue
        w = np.sign(ex12[ok]) * (0.10 / v[ok]) / ok.sum()
        nd = d + pd.offsets.MonthEnd(1)
        rfn = rf.shift(-1).loc[d]
        ts = float((w * (r[ok] - rfn)).sum())
        turn = float(w.sub(prev, fill_value=0).abs().sum())
        prev = w
        out[nd] = {"tsmom": ts, "sleeve": rfn + 2 * ts - 2 * 0.0005 * turn, "rf": rfn,
                   "b6040": 0.6 * r["SPY"] + 0.4 * r["IEF"], "spy": r["SPY"]}
    return pd.DataFrame(out).T


def mdd(r: pd.Series) -> float:
    w = (1 + r).cumprod()
    return float((w / w.cummax() - 1).min())


def main() -> None:
    S = series()
    L = ["# 60/40 + 추세추종 혼합 (탐색적, 사전 등록 아님; Sim J와 같은 2002-2026 구간)", "",
         f"- 구간 {S.index[0]:%Y-%m} ~ {S.index[-1]:%Y-%m}, {len(S)}개월. 추세추종 sleeve = 무위험 + 2 × Sim J TSMOM 초과수익(비용 5 bp × turnover × 2)",
         f"- 상관: TSMOM vs 60/40 {S['tsmom'].corr(S['b6040']):.2f}, vs SPY {S['tsmom'].corr(S['spy']):.2f}; "
         f"60/40이 손실인 달의 TSMOM 평균 {S.loc[S['b6040'] < 0, 'tsmom'].mean() * 100:+.2f}%/월", "",
         "| 포트폴리오 | 연 수익(%) | 연 변동성(%) | Sharpe | 최대낙폭(%) | 2008(%) | 2022(%) |", "|---|---|---|---|---|---|---|"]
    ports = {"SPY": S["spy"], "추세추종 sleeve 단독": S["sleeve"]}
    for x in [0.0, 0.1, 0.2, 0.3]:
        ports[f"60/40 {int(x * 100)}% → 추세추종"] = (1 - x) * S["b6040"] + x * S["sleeve"]
    base = ports["60/40 0% → 추세추종"]
    for name, r in ports.items():
        yr = lambda y: float((1 + r.loc[str(y)]).prod() - 1) * 100  # noqa: E731
        L.append(f"| {name} | {((1 + r).prod() ** (12 / len(r)) - 1) * 100:.2f} | {r.std() * np.sqrt(12) * 100:.2f} | "
                 f"{sharpe(r - S['rf']):.2f} | {mdd(r) * 100:.1f} | {yr(2008):+.1f} | {yr(2022):+.1f} |")
    L.append("")
    for x in [0.1, 0.2, 0.3]:
        b = ports[f"60/40 {int(x * 100)}% → 추세추종"]
        d = (b - S["rf"]) / (b - S["rf"]).std() - (base - S["rf"]) / (base - S["rf"]).std()
        m, t = nw_t(d)
        L.append(f"- {int(x * 100)}% 혼합 vs 60/40 Sharpe 차이 검정(표준화 차이 NW t): {t:.2f}")
    L += ["", "- 해석 주의: 같은 구간을 다시 본 탐색적 결과이고 2× 레버리지·비용 가정은 결과를 보기 전에 정했지만 사전 등록은 아님", ""]
    text = "\n".join(L) + "\n"
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text)
    print(text)


if __name__ == "__main__":
    sys.exit(main())
