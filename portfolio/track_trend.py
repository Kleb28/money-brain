"""Trend-following blend paper portfolio (portfolio/trend_rules.md) -> outputs/portfolio_trend.md.

Recomputes everything from adjusted closes each run; completed months only.
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
import pandas as pd

ETFS = ["SPY", "IWM", "EFA", "EEM", "EWJ", "TLT", "IEF", "SHY", "LQD", "HYG", "TIP", "EMB",
        "GLD", "SLV", "DBC", "USO", "DBA", "VNQ", "UUP", "FXE", "FXY"]
CASH, REF = "BIL", ["DBMF", "KMLM"]
INCEPTION = pd.Timestamp(os.environ.get("TREND_INCEPTION", "2026-11-30"))
OUT = "outputs/portfolio_trend.md"


def download(tickers: list[str], start: str) -> pd.DataFrame:
    import yfinance as yf
    frames = {}
    for t in tickers:
        for i in range(4):
            try:
                d = yf.download(t, start=start, auto_adjust=True, progress=False, threads=False)
                if len(d):
                    c = d["Close"]
                    frames[t] = (c.iloc[:, 0] if isinstance(c, pd.DataFrame) else c).rename(t)
                    break
            except Exception as e:  # noqa: BLE001
                print(f"  retry {t}: {e}", flush=True)
            time.sleep(10 * (i + 1))
        time.sleep(2)
    return pd.DataFrame(frames).sort_index()


def compute(px: pd.DataFrame, today: pd.Timestamp) -> tuple[pd.DataFrame, pd.Series, pd.Timestamp | None]:
    """Monthly returns per holding month from INCEPTION, plus the latest month-end weights."""
    px = px.loc[px.index < today.normalize().replace(day=1)].dropna(how="all")
    etfs = [c for c in ETFS if c in px.columns]
    vol = (px[etfs].pct_change(fill_method=None).rolling(63, min_periods=50).std() * np.sqrt(252)).resample("ME").last()
    M = px.resample("ME").last()
    R = M.pct_change(fill_method=None)
    rows, prev, last_w, last_d = {}, pd.Series(dtype=float), pd.Series(dtype=float), None
    for i, d in enumerate(M.index):
        if d < INCEPTION + pd.offsets.MonthEnd(0) or i < 12:
            continue
        ex12 = (M.loc[d, etfs] / M[etfs].iloc[i - 12] - 1) - (M.loc[d, CASH] / M[CASH].iloc[i - 12] - 1)
        v = vol.loc[d]
        ok = ex12.notna() & v.notna() & (v > 0)
        if ok.sum() < 8:
            continue
        w = np.sign(ex12[ok]) * (0.10 / v[ok]) / ok.sum()
        turn = float(w.sub(prev, fill_value=0).abs().sum())
        last_w, last_d = w, d
        if i + 1 < len(M.index):
            nd = M.index[i + 1]
            r, cash = R.loc[nd], R.loc[nd, CASH]
            held = w[r.reindex(w.index).notna()]
            ts = float((held * (r[held.index] - cash)).sum())
            sleeve = cash + 2 * ts - 2 * 0.0005 * turn
            b = 0.6 * r["SPY"] + 0.4 * r["IEF"]
            rows[nd] = {"B": b, "T": 0.8 * b + 0.2 * sleeve, "sleeve": sleeve, "cash": cash,
                        **{k: r.get(k, np.nan) for k in REF}}
        prev = w
    return pd.DataFrame(rows).T, last_w, last_d


def stats(r: pd.Series, cash: pd.Series) -> str:
    cum = (1 + r).prod() - 1
    w = (1 + r).cumprod()
    mdd = min(0.0, float((w / w.cummax().clip(lower=1.0) - 1).min()))
    if len(r) < 3:
        return f"{cum * 100:+.2f}% | – | {mdd * 100:.1f}% | –"
    ex = r - cash
    return f"{cum * 100:+.2f}% | {r.std() * np.sqrt(12) * 100:.2f}% | {mdd * 100:.1f}% | {ex.mean() / ex.std() * np.sqrt(12):.2f}"


def render(S: pd.DataFrame, w: pd.Series, wd, today: pd.Timestamp) -> str:
    L = [f"# 추세추종 혼합 paper portfolio — inception {INCEPTION:%Y-%m-%d}, {today:%Y-%m-%d} 기준", "",
         "규칙: portfolio/trend_rules.md. 완결된 달만 기록. B = SPY 60/IEF 40, T = B 80% + 추세추종 sleeve 20%.", ""]
    if S.empty:
        L += ["- 아직 완결된 보유 달이 없음(첫 기록은 inception 다음 달 말 이후)", ""]
    else:
        L += [f"- 기록 {len(S)}개월 ({S.index[0]:%Y-%m} ~ {S.index[-1]:%Y-%m})", "",
              "| 포트폴리오 | 누적 수익 | 변동성(연) | 최대낙폭(월말) | Sharpe |", "|---|---|---|---|---|"]
        for k, name in [("B", "B 60/40"), ("T", "T 혼합"), ("sleeve", "추세추종 sleeve"), ("DBMF", "DBMF(참고)"), ("KMLM", "KMLM(참고)")]:
            if S[k].notna().all():
                L.append(f"| {name} | {stats(S[k].astype(float), S['cash'].astype(float))} |")
        if len(S) >= 6:
            L += ["", "- sleeve 상관: " + ", ".join(f"{k} {S['sleeve'].astype(float).corr(S[k].astype(float)):.2f}" for k in ["B"] + REF)]
        L += ["", "| 달 | B | T | sleeve | DBMF | KMLM |", "|---|---|---|---|---|---|"]
        for d, r in S.iterrows():
            L.append(f"| {d:%Y-%m} | " + " | ".join(f"{r[k] * 100:+.2f}%" if pd.notna(r[k]) else "–" for k in ["B", "T", "sleeve", "DBMF", "KMLM"]) + " |")
        L.append("")
    if wd is not None and len(w):
        L += [f"## {wd:%Y-%m} 말 신호로 정한 sleeve 포지션 (2× 적용 전 비중)", "",
              "- long: " + ", ".join(f"{k} {v * 100:.1f}%" for k, v in w[w > 0].sort_values(ascending=False).items()),
              "- short: " + (", ".join(f"{k} {v * 100:.1f}%" for k, v in w[w < 0].sort_values().items()) or "없음"), ""]
    return "\n".join(L) + "\n"


def main() -> None:
    today = pd.Timestamp.now(tz="UTC").tz_localize(None)
    start = f"{INCEPTION - pd.DateOffset(months=16):%Y-%m-%d}"
    px = download(ETFS + [CASH] + REF, start)
    missing = [t for t in ["SPY", "IEF", CASH] if t not in px.columns]
    if missing or px.shape[1] < 15:
        print(f"download incomplete ({px.shape[1]} tickers, missing {missing}); keeping previous output")
        sys.exit(1)
    S, w, wd = compute(px, today)
    text = render(S, w, wd, today)
    os.makedirs("outputs", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text)
    print(text)


if __name__ == "__main__":
    main()
