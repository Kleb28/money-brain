"""Sim K (simulation/protocol.md): time-series momentum on 1972-01..2002-10 (before Sim J's ETF sample).

Assets from FRED monthly series (8 countries): equity price-index excess returns, 10y bond excess returns
approximated from yields, and 7 USD currency pairs with interest differentials. Writes outputs/sim_k.md.
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
import pandas as pd

from simulation.sim_j import fred, nw_t, sharpe

OUT = "outputs/sim_k.md"
CC = ["US", "JP", "GB", "DE", "FR", "CA", "AU", "CH"]
# FX: (country, series, True if quoted as USD per foreign unit)
FX = [("JP", "EXJPUS", False), ("GB", "EXUSUK", True), ("DE", "EXGEUS", False), ("FR", "EXFRUS", False),
      ("CA", "EXCAUS", False), ("AU", "EXUSAL", True), ("CH", "EXSZUS", False)]
START, END = "1972-01-31", "2002-10-31"
T_PASS = 2.5


def try_fred(sid: str) -> pd.Series | None:
    try:
        s = fred(sid)
        time.sleep(1)
        return s.groupby(level=0).last()
    except Exception as e:  # noqa: BLE001
        print(f"  missing {sid}: {e}", flush=True)
        return None


def build() -> tuple[pd.DataFrame, dict[str, str], list[str]]:
    notes = []
    short = {}
    for c in CC:
        if c == "US":
            s = try_fred("TB3MS")
        else:
            a, b = try_fred(f"IR3TIB01{c}M156N"), try_fred(f"IRSTCI01{c}M156N")
            s = a.combine_first(b) if a is not None and b is not None else (a if a is not None else b)
        if s is not None:
            short[c] = s / 100.0
    rets, cls = {}, {}
    for c in CC:
        rs = short.get(c)
        if rs is None:
            notes.append(f"{c}: 단기금리 없음 → 주식·국채 제외")
            continue
        p = try_fred(f"SPASTT01{c}M661N")
        if p is not None:
            rets[f"EQ_{c}"] = np.log(p / p.shift(1)) - rs.shift(1) / 12
            cls[f"EQ_{c}"] = "주식"
        y = try_fred(f"IRLTLT01{c}M156N")
        if y is not None:
            y = y / 100.0
            y0 = y.shift(1)
            dur = (1 - (1 + y0 / 2) ** -20) / y0
            rets[f"BD_{c}"] = y0 / 12 - dur * (y - y0) - rs.shift(1) / 12
            cls[f"BD_{c}"] = "국채"
    for c, sid, usd_per in FX:
        s = try_fred(sid)
        if s is None or c not in short or "US" not in short:
            notes.append(f"{sid}: 자료 없음 → 제외")
            continue
        usd_per_f = s if usd_per else 1.0 / s
        rets[f"FX_{c}"] = np.log(usd_per_f / usd_per_f.shift(1)) + (short[c].shift(1) - short["US"].shift(1)) / 12
        cls[f"FX_{c}"] = "통화"
    R = pd.DataFrame(rets).sort_index()
    return R, cls, notes


def tsmom(R: pd.DataFrame, skip: int = 1) -> tuple[pd.Series, pd.Series, pd.DataFrame]:
    """Returns (TSMOM net, always-long same risk, per-asset contributions) on holding months."""
    sig = np.sign(R.shift(skip).rolling(12, min_periods=12).sum())
    vol = R.rolling(24, min_periods=24).std() * np.sqrt(12)
    ok = sig.notna() & vol.notna() & (vol > 0)
    n = ok.sum(axis=1)
    base = (0.10 / vol).where(ok).div(n.where(n >= 4), axis=0)
    w = (sig * base)  # weight decided at end of month t
    nxt = R.shift(-1)
    contrib = (w * nxt)
    gross = contrib.sum(axis=1, min_count=1)
    turn = w.fillna(0).diff().abs().sum(axis=1)
    net = (gross - 0.0005 * turn).where(n >= 4)
    longonly = (base * nxt).sum(axis=1, min_count=1).where(n >= 4)
    # index by holding month
    shift = lambda s: s.set_axis(s.index + pd.offsets.MonthEnd(1))  # noqa: E731
    return shift(net).dropna(), shift(longonly).dropna(), shift(contrib)


def main() -> None:
    os.makedirs("outputs", exist_ok=True)
    R, cls, notes = build()
    net, lo, contrib = tsmom(R)
    net, lo = net.loc[START:END], lo.loc[START:END]
    m, t = nw_t(net)
    passed = m > 0 and t >= T_PASS
    first = R.apply(lambda s: s.first_valid_index())
    L = ["# Sim K — TSMOM 재검정, 1972-01 ~ 2002-10 (simulation/protocol.md 사전 등록 2026-11-18)", "",
         f"실행 {pd.Timestamp.utcnow():%Y-%m-%d} UTC. 신호는 t−12~t−1월(최근 1개월 제외), t+1월 보유, 비용 5 bp × turnover.", "",
         "## 판정", "",
         f"- TSMOM 연 {m * 1200:+.2f}%, Sharpe {sharpe(net):.2f}, Newey-West t {t:.2f}, {len(net)}개월 "
         f"({net.index[0]:%Y-%m} ~ {net.index[-1]:%Y-%m}) → " + ("통과" if passed else "미달") + f" (기준 평균 > 0 이고 t ≥ {T_PASS})", "",
         "## 같이 보고 (판정에 안 씀)", "",
         "| 구분 | 연 수익(%) | Sharpe | t |", "|---|---|---|---|"]

    def row(name, s):
        s = s.dropna()
        L.append(f"| {name} | {s.mean() * 1200:+.2f} | {sharpe(s):.2f} | {nw_t(s)[1]:.2f} |")

    row("TSMOM 전체", net)
    row("TSMOM 1972-1986", net.loc[:"1986-12-31"])
    row("TSMOM 1987-2002", net.loc["1987-01-31":])
    for k in ["주식", "국채", "통화"]:
        cols = [c for c in contrib.columns if cls[c] == k]
        row(f"TSMOM {k}만(전체 N 기준 비중)", contrib[cols].sum(axis=1, min_count=1).loc[START:END])
    row("같은 위험 비중 항상 long", lo)
    net0 = tsmom(R, skip=0)[0].loc[START:END]
    row("최근 월 포함 원 정의(월평균 자료라 부풀 수 있음)", net0)
    L += ["", f"- 상관(TSMOM, 항상 long): {pd.concat([net, lo], axis=1).dropna().corr().iloc[0, 1]:.2f}",
          "- 자산별 첫 달: " + ", ".join(f"{c} {first[c]:%Y-%m}" for c in R.columns if first[c] is not None)]
    if notes:
        L.append("- 제외: " + "; ".join(notes))
    L.append("")
    text = "\n".join(L) + "\n"
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text)
    print(text)


if __name__ == "__main__":
    sys.exit(main())
