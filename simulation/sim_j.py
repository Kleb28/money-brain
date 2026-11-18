"""Sim J (simulation/protocol.md): do economically motivated factors, combined or optimized
walk-forward, beat naive benchmarks out of sample?

J1 index timing (French market, FRED predictors), J2 US equity factor combination (French),
J3 cross-asset ETF cross-section (yfinance). Writes outputs/sim_j.md.
Network: French Data Library, FRED, Yahoo. Run in GitHub Actions (sim-j.yml).
"""
from __future__ import annotations

import io
import os
import sys
import time
import zipfile

import numpy as np
import pandas as pd
import requests

UA = {"User-Agent": "Mozilla/5.0 (research script)"}
FRENCH = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
CACHE = "data/external"
OUT = "outputs/sim_j.md"
ETFS = ["SPY", "IWM", "EFA", "EEM", "EWJ", "TLT", "IEF", "SHY", "LQD", "HYG", "TIP", "EMB",
        "GLD", "SLV", "DBC", "USO", "DBA", "VNQ", "UUP", "FXE", "FXY"]
T_PASS = 2.5


# ---------------------------------------------------------------- data
def get(url: str, tries: int = 4) -> bytes:
    for i in range(tries):
        try:
            r = requests.get(url, headers=UA, timeout=60)
            r.raise_for_status()
            return r.content
        except Exception as e:  # noqa: BLE001
            print(f"  retry {i + 1} {url}: {e}", flush=True)
            time.sleep(5 * (i + 1))
    raise RuntimeError(f"download failed: {url}")


def parse_french(raw: bytes) -> pd.DataFrame:
    """First monthly block of a French CSV zip (YYYYMM rows), values in decimal."""
    z = zipfile.ZipFile(io.BytesIO(raw))
    text = z.read(z.namelist()[0]).decode("latin-1")
    rows, header = [], None
    for line in text.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if header is None:
            if len(parts) > 1 and parts[0] == "" and any(p for p in parts[1:]):
                header = parts[1:]
            continue
        if len(parts[0]) == 6 and parts[0].isdigit():
            rows.append(parts)
        elif rows:
            break  # end of monthly block
    df = pd.DataFrame([r[1:len(header) + 1] for r in rows], columns=header,
                      index=pd.PeriodIndex([r[0] for r in rows], freq="M").to_timestamp("M"))
    df = df.apply(pd.to_numeric, errors="coerce") / 100.0
    df[df <= -0.9999] = np.nan  # -99.99 missing code
    return df


def french() -> pd.DataFrame:
    ff3 = parse_french(get(FRENCH + "F-F_Research_Data_Factors_CSV.zip"))
    ff5 = parse_french(get(FRENCH + "F-F_Research_Data_5_Factors_2x3_CSV.zip"))
    mom = parse_french(get(FRENCH + "F-F_Momentum_Factor_CSV.zip"))
    st = parse_french(get(FRENCH + "F-F_ST_Reversal_Factor_CSV.zip"))
    lt = parse_french(get(FRENCH + "F-F_LT_Reversal_Factor_CSV.zip"))
    out = ff3[["Mkt-RF", "RF"]].copy()
    for c in ["SMB", "HML", "RMW", "CMA"]:
        out[c] = ff5[c]
    out["Mom"] = mom.iloc[:, 0]
    out["ST_Rev"] = st.iloc[:, 0]
    out["LT_Rev"] = lt.iloc[:, 0]
    return out


CHROME = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
          "Chrome/130.0 Safari/537.36", "Accept": "text/csv,text/plain,*/*"}


def fred(series: str) -> pd.Series:
    """FRED monthly series; tries the csv graph endpoint, then the plain-text data endpoint."""
    for i in range(3):
        for kind, url in [("csv", f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"),
                          ("txt", f"https://fred.stlouisfed.org/data/{series}.txt")]:
            try:
                r = requests.get(url, headers=CHROME, timeout=(10, 30))
                r.raise_for_status()
                if kind == "csv":
                    df = pd.read_csv(io.BytesIO(r.content))
                    dates, vals = df.iloc[:, 0], df.iloc[:, 1]
                else:
                    rows = [ln.split() for ln in r.text.splitlines()]
                    rows = [x for x in rows if len(x) == 2 and x[0][:4].isdigit() and "-" in x[0]]
                    dates, vals = [x[0] for x in rows], [x[1] for x in rows]
                s = pd.Series(pd.to_numeric(pd.Series(list(vals)), errors="coerce").values,
                              index=pd.to_datetime(pd.Series(list(dates))) + pd.offsets.MonthEnd(0))
                if s.notna().sum() > 100:
                    return s
            except Exception as e:  # noqa: BLE001
                print(f"  FRED {series} {kind} try {i + 1}: {e}", flush=True)
        time.sleep(10 * (i + 1))
    raise RuntimeError(f"FRED download failed: {series}")


def etf_prices() -> pd.DataFrame:
    path = os.path.join(CACHE, "sim_j_etf.csv.gz")
    import yfinance as yf
    frames = {}
    for t in ETFS:
        for i in range(4):
            try:
                d = yf.download(t, start="1993-01-01", auto_adjust=True, progress=False, threads=False)
                if len(d):
                    c = d["Close"]
                    frames[t] = (c.iloc[:, 0] if isinstance(c, pd.DataFrame) else c).rename(t)
                    break
            except Exception as e:  # noqa: BLE001
                print(f"  yf retry {t}: {e}", flush=True)
            time.sleep(10 * (i + 1))
        time.sleep(2)
        print(f"  {t}: {len(frames.get(t, []))} days", flush=True)
    px = pd.DataFrame(frames).sort_index()
    if px.shape[1] >= 15:
        px.to_csv(path, compression="gzip")
    elif os.path.exists(path):
        print("  yfinance incomplete, using cache", flush=True)
        px = pd.read_csv(path, index_col=0, parse_dates=True)
    return px


# ---------------------------------------------------------------- stats
def nw_t(x, lags: int = 3) -> tuple[float, float]:
    x = np.asarray(pd.Series(x).dropna(), float)
    n = len(x)
    if n < 10:
        return float("nan"), float("nan")
    m = x.mean()
    e = x - m
    v = e @ e / n
    for L in range(1, lags + 1):
        v += 2 * (1 - L / (lags + 1)) * (e[L:] @ e[:-L]) / n
    return m, m / np.sqrt(v / n)


def sharpe(r) -> float:
    r = pd.Series(r).dropna()
    return float(r.mean() / r.std() * np.sqrt(12)) if len(r) > 2 else float("nan")


def paired_scaled(a: pd.Series, b: pd.Series) -> tuple[float, float, int]:
    df = pd.concat([a, b], axis=1).dropna()
    d = df.iloc[:, 0] / df.iloc[:, 0].std() - df.iloc[:, 1] / df.iloc[:, 1].std()
    m, t = nw_t(d)
    return m, t, len(d)


def ols_fit_predict(X: np.ndarray, y: np.ndarray, x_new: np.ndarray) -> float:
    A = np.column_stack([np.ones(len(X)), X])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    return float(np.r_[1.0, x_new] @ beta)


# ---------------------------------------------------------------- J1
def j1(ff: pd.DataFrame, fr: dict[str, pd.Series], lines: list[str]) -> dict:
    mkt = ff["Mkt-RF"] + ff["RF"]
    idx = (1 + mkt).cumprod()
    P = pd.DataFrame(index=ff.index)
    P["tbl"] = fr["TB3MS"]
    P["term"] = fr["GS10"] - fr["TB3MS"]
    P["dfy"] = fr["BAA"] - fr["AAA"]
    cpi = fr["CPIAUCSL"].reindex(ff.index)
    P["infl"] = np.log(cpi.shift(1) / cpi.shift(13))
    P["mom12"] = mkt.rolling(12).sum()
    P["trend"] = (idx > idx.rolling(10).mean()).astype(float)
    P["svar"] = (mkt ** 2).rolling(12).sum()
    y = ff["Mkt-RF"].shift(-1)  # return of t+1 aligned to predictors at t
    data = pd.concat([P, y.rename("y")], axis=1).loc["1954-01-31":]
    data = data.dropna(subset=list(P.columns))
    preds = list(P.columns)
    oos_dates = data.index[(data.index >= "1979-12-31") & data["y"].notna()]
    rows = []
    for t in oos_dates:
        tr = data.loc[:t].iloc[:-1].dropna()  # y known up to month t (row t-1 holds r_t)
        f = {"HM": tr["y"].mean()}
        uni = []
        for p in preds:
            v = ols_fit_predict(tr[[p]].values, tr["y"].values, data.loc[t, [p]].values)
            f[p] = v
            uni.append(v)
        f["COMB"] = float(np.mean(uni))
        f["KS"] = ols_fit_predict(tr[preds].values, tr["y"].values, data.loc[t, preds].values)
        f["var60"] = tr["y"].iloc[-60:].var()
        f["y"] = data.loc[t, "y"]
        f["rf_next"] = ff["RF"].shift(-1).loc[t]
        rows.append(pd.Series(f, name=t + pd.offsets.MonthEnd(1)))
    R = pd.DataFrame(rows)

    def r2os(col, sub=R):
        return 1 - ((sub["y"] - sub[col]) ** 2).sum() / ((sub["y"] - sub["HM"]) ** 2).sum()

    def cw(col, sub=R):
        adj = (sub["y"] - sub["HM"]) ** 2 - ((sub["y"] - sub[col]) ** 2 - (sub["HM"] - sub[col]) ** 2)
        return nw_t(adj)[1]

    def timing(col, sub=R):
        w = (sub[col] / (3 * sub["var60"])).clip(0, 1.5)
        return sub["rf_next"] + w * sub["y"]

    bh = R["rf_next"] + R["y"]
    res = {"r2": r2os("COMB"), "cw": cw("COMB"), "n": len(R), "start": R.index[0], "end": R.index[-1]}
    res["pass"] = res["r2"] > 0 and res["cw"] >= T_PASS
    lines += ["## J1 — 지수 타이밍 (French 시장 초과수익, 1980-01 이후 표본 밖)", "",
              f"- 표본 밖 {res['start']:%Y-%m} ~ {res['end']:%Y-%m}, {res['n']}개월",
              "", "| 예측 | R²_OS(%) | CW t | 2000- R²_OS(%) | 타이밍 Sharpe | 2000- Sharpe |", "|---|---|---|---|---|---|"]
    sub = R.loc["2000-01-31":]
    for col in ["COMB", "KS"] + preds + ["HM"]:
        r2 = r2os(col) * 100 if col != "HM" else 0.0
        t = cw(col) if col != "HM" else float("nan")
        lines.append(f"| {col} | {r2:+.2f} | {t:.2f} | {(r2os(col, sub) * 100 if col != 'HM' else 0):+.2f} | "
                     f"{sharpe(timing(col)):.2f} | {sharpe(timing(col, sub)):.2f} |")
    lines.append(f"| buy-and-hold | | | | {sharpe(bh):.2f} | {sharpe(bh.loc['2000-01-31':]):.2f} |")
    lines += ["", f"- 판정(COMB R²_OS > 0 이고 CW t ≥ {T_PASS}): R²_OS {res['r2'] * 100:+.2f}%, t {res['cw']:.2f} → "
              + ("통과" if res["pass"] else "미달"), ""]
    return res


# ---------------------------------------------------------------- J2
FACTORS = ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom", "ST_Rev", "LT_Rev"]


def j2(ff: pd.DataFrame, lines: list[str]) -> dict:
    F = ff[FACTORS].loc["1963-07-31":].dropna()
    oos = F.index[F.index >= "1990-01-31"]
    out = {k: {} for k in ["1/N", "MV", "InvVol", "FacMom"]}
    for t in oos:
        hist = F.loc[F.index < t]
        r = F.loc[t]
        mu = hist.mean().values
        S = hist.cov().values
        S = 0.5 * S + 0.5 * np.diag(np.diag(S))
        w = np.linalg.solve(S, mu)
        w = w / np.abs(w).sum()
        out["MV"][t] = float(w @ r.values)
        out["1/N"][t] = float(r.mean())
        iv = 1 / hist.std().values
        out["InvVol"][t] = float((iv / iv.sum()) @ r.values)
        on = (hist.iloc[-12:].sum() > 0).values.astype(float)
        out["FacMom"][t] = float((on / on.sum()) @ r.values) if on.sum() else 0.0
    S = pd.DataFrame(out)
    S["Mkt-RF"] = F.loc[oos, "Mkt-RF"]
    m, t, n = paired_scaled(S["MV"], S["1/N"])
    res = {"m": m, "t": t, "n": n, "pass": m > 0 and t >= T_PASS}
    lines += ["## J2 — 미국 주식 팩터 8개 조합 (1990-01 이후 표본 밖, paper long-short, 비용 없음)", "",
              "| 전략 | 연 수익(%) | Sharpe | 2010- Sharpe | vs 1/N 차이 t |", "|---|---|---|---|---|"]
    for c in ["1/N", "MV", "InvVol", "FacMom", "Mkt-RF"]:
        tt = paired_scaled(S[c], S["1/N"])[1] if c != "1/N" else float("nan")
        lines.append(f"| {c} | {S[c].mean() * 1200:.2f} | {sharpe(S[c]):.2f} | {sharpe(S[c].loc['2010-01-31':]):.2f} | {tt:.2f} |")
    lines.append("")
    lines.append("- 팩터별 표본 밖 Sharpe: " + ", ".join(f"{c} {sharpe(F.loc[oos, c]):.2f}" for c in FACTORS))
    lines += [f"- 판정(MV − 1/N 표준화 차이 평균 > 0 이고 t ≥ {T_PASS}, n {n}): 평균 {m:+.4f}, t {t:.2f} → "
              + ("통과" if res["pass"] else "미달"), ""]
    return res


# ---------------------------------------------------------------- J3
def zcs(df: pd.DataFrame) -> pd.DataFrame:
    z = df.sub(df.mean(axis=1), axis=0).div(df.std(axis=1), axis=0)
    return z.clip(-3, 3)


def ls_weights(score: pd.Series, vol: pd.Series) -> pd.Series:
    s = score.dropna()
    v = vol.reindex(s.index)
    ok = v.notna() & (v > 0)
    s, v = s[ok], v[ok]
    if len(s) < 8:
        return pd.Series(dtype=float)
    raw = (s - s.mean()) / v
    return raw / raw.abs().sum()


def j3(px: pd.DataFrame, rf: pd.Series, lines: list[str]) -> dict:
    px = px.dropna(how="all")
    dret = px.pct_change(fill_method=None)
    vol = (dret.rolling(63, min_periods=50).std() * np.sqrt(252)).resample("ME").last()
    M = px.resample("ME").last()
    # drop first partial month per ETF: require a full prior month of data
    first = px.apply(lambda s: s.first_valid_index())
    for c in M.columns:
        if first[c] is not None:
            M.loc[M.index <= first[c] + pd.offsets.MonthEnd(0), c] = np.nan
    R = M.pct_change(fill_method=None)
    sig = {
        "MOM": M.shift(1) / M.shift(12) - 1,
        "TREND": M / M.rolling(10).mean() - 1,
        "REV": -R,
        "LOWVOL": -vol,
        "VAL": -(M / M.shift(60) - 1),
    }
    Z = {k: zcs(v) for k, v in sig.items()}
    comp = sum(z.fillna(0) for z in Z.values()) / sum(z.notna().astype(int) for z in Z.values()).replace(0, np.nan)
    comp = comp.where(sum(z.notna().astype(int) for z in Z.values()) > 0)
    rf = rf.reindex(M.index).ffill()
    nxt = R.shift(-1)
    dates = [d for d in M.index[:-1] if comp.loc[d].notna().sum() >= 8 and vol.loc[d].notna().sum() >= 8]

    def run(score_fn):
        rets, prev = {}, pd.Series(dtype=float)
        for d in dates:
            sc = score_fn(d)
            if sc is None:
                continue
            w = ls_weights(sc, vol.loc[d])
            if w.empty:
                continue
            r = nxt.loc[d].reindex(w.index)
            ok = r.notna()
            gross = float((w[ok] * r[ok]).sum())
            turn = float(w.sub(prev, fill_value=0).abs().sum())
            rets[d + pd.offsets.MonthEnd(1)] = gross - 0.0005 * turn
            prev = w
        return pd.Series(rets)

    comp_r = run(lambda d: comp.loc[d])

    # ridge: panel of (z-scores at t, vol-scaled return t+1), train strictly before d
    panel = []
    for d in M.index[:-1]:
        X = pd.DataFrame({k: Z[k].loc[d] for k in Z}).fillna(0)
        yy = nxt.loc[d] / vol.loc[d]
        ok = comp.loc[d].notna() & yy.notna()
        if ok.sum():
            panel.append((d, X[ok].values, yy[ok].values))

    def ridge_score(d):
        tr = [(x, y) for (dd, x, y) in panel if dd + pd.offsets.MonthEnd(1) <= d]
        months = len(tr)
        if months < 36:
            return None
        X = np.vstack([x for x, _ in tr])
        y = np.concatenate([y for _, y in tr])
        Xc = np.column_stack([np.ones(len(X)), X])
        lam = 0.05 * len(X) * np.eye(Xc.shape[1])
        lam[0, 0] = 0
        beta = np.linalg.solve(Xc.T @ Xc + lam, Xc.T @ y)
        Xd = pd.DataFrame({k: Z[k].loc[d] for k in Z}).fillna(0)
        s = pd.Series(np.column_stack([np.ones(len(Xd)), Xd.values]) @ beta, index=Xd.index)
        return s.where(comp.loc[d].notna())

    ridge_r = run(ridge_score)

    # TSMOM and long-only references
    ts, lo, ew, b6040 = {}, {}, {}, {}
    rf12 = (1 + rf).rolling(12).apply(np.prod, raw=True) - 1
    for d in dates:
        nd = d + pd.offsets.MonthEnd(1)
        r = nxt.loc[d]
        ex12 = (M.loc[d] / M.shift(12).loc[d] - 1) - rf12.loc[d]
        v = vol.loc[d]
        ok = ex12.notna() & v.notna() & r.notna()
        if ok.sum():
            w = np.sign(ex12[ok]) * (0.10 / v[ok]) / ok.sum()
            ts[nd] = float((w * (r[ok] - rf.shift(-1).loc[d])).sum())
        c = comp.loc[d].dropna()
        c = c[r.reindex(c.index).notna()]
        top = c[c >= c.quantile(2 / 3)].index
        lo[nd] = float(r[top].mean())
        avail = r.dropna()
        ew[nd] = float(avail[avail.index.isin(c.index)].mean())
        if pd.notna(r.get("SPY")) and pd.notna(r.get("IEF")):
            b6040[nd] = 0.6 * r["SPY"] + 0.4 * r["IEF"]
    ts, lo, ew, b6040 = map(pd.Series, (ts, lo, ew, b6040))

    ma, ta = nw_t(comp_r)
    mb, tb, nb = paired_scaled(ridge_r, comp_r.reindex(ridge_r.index))
    res = {"a_m": ma, "a_t": ta, "a_pass": ma > 0 and ta >= T_PASS,
           "b_m": mb, "b_t": tb, "b_n": nb, "b_pass": mb > 0 and tb >= T_PASS,
           "start": comp_r.index[0], "end": comp_r.index[-1], "n_etf": int(M.notna().any().sum())}
    lines += [f"## J3 — 자산군 ETF {res['n_etf']}개 cross-section (표본 밖 {res['start']:%Y-%m} ~ {res['end']:%Y-%m})", "",
              "| 전략 | 연 수익(%) | 연 변동성(%) | Sharpe | t |", "|---|---|---|---|---|"]
    for name, s, excess in [("COMP long-short(비용 후)", comp_r, False), ("RIDGE long-short(비용 후)", ridge_r, False),
                            ("COMP 구간 맞춤(RIDGE 기간)", comp_r.reindex(ridge_r.index), False),
                            ("TSMOM", ts, False), ("COMP 상위 1/3 long-only", lo, True),
                            ("ETF 1/N long-only", ew, True), ("SPY 60 / IEF 40", b6040, True)]:
        x = s - rf.reindex(s.index).values if excess else s
        lines.append(f"| {name} | {s.mean() * 1200:.2f} | {s.std() * np.sqrt(12) * 100:.2f} | {sharpe(x):.2f} | {nw_t(x)[1]:.2f} |")
    lines.append("")
    lines.append("- 신호별 단독 long-short Sharpe(비용 후): " + ", ".join(
        f"{k} {sharpe(run(lambda d, k=k: Z[k].loc[d])):.2f}" for k in Z))
    lines += [f"- J3a 판정(COMP long-short 평균 > 0 이고 t ≥ {T_PASS}): 연 {ma * 1200:+.2f}%, t {ta:.2f} → "
              + ("통과" if res["a_pass"] else "미달"),
              f"- J3b 판정(RIDGE − COMP 표준화 차이 평균 > 0 이고 t ≥ {T_PASS}, n {nb}): 평균 {mb:+.4f}, t {tb:.2f} → "
              + ("통과" if res["b_pass"] else "미달"),
              "- long-only 행의 Sharpe·t는 무위험 수익 차감 후, long-short·TSMOM은 그대로(자기 자금 조달)", ""]
    return res


def main() -> None:
    os.makedirs("outputs", exist_ok=True)
    lines = ["# Sim J — 팩터 조합·최적화 walk-forward (simulation/protocol.md 사전 등록 2026-11-18)", "",
             f"실행 {pd.Timestamp.utcnow():%Y-%m-%d} UTC. 모든 가중치·예측은 t월 말까지의 데이터로 만들고 t+1월에 적용.", ""]
    print("French...", flush=True)
    ff = french()
    lines.append(f"- 데이터: French 월간 {ff.index[0]:%Y-%m} ~ {ff.index[-1]:%Y-%m}")
    summary = []
    try:
        print("FRED...", flush=True)
        fr = {s: fred(s) for s in ["TB3MS", "GS10", "BAA", "AAA", "CPIAUCSL"]}
        fr = {k: v.reindex(ff.index) / (100.0 if k != "CPIAUCSL" else 1.0) for k, v in fr.items()}
        r1 = j1(ff, fr, lines)
        summary.append(f"- J1 지수 타이밍: R²_OS {r1['r2'] * 100:+.2f}%, CW t {r1['cw']:.2f} → {'통과' if r1['pass'] else '미달'}")
    except Exception as e:  # noqa: BLE001
        summary.append(f"- J1 실행 실패: {e}")
    try:
        r2 = j2(ff, lines)
        summary.append(f"- J2 팩터 MV vs 1/N: t {r2['t']:.2f} → {'통과' if r2['pass'] else '미달'}")
    except Exception as e:  # noqa: BLE001
        summary.append(f"- J2 실행 실패: {e}")
    try:
        print("ETF prices...", flush=True)
        px = etf_prices()
        r3 = j3(px, ff["RF"], lines)
        summary.append(f"- J3a ETF COMP long-short: t {r3['a_t']:.2f} → {'통과' if r3['a_pass'] else '미달'}")
        summary.append(f"- J3b ETF RIDGE vs COMP: t {r3['b_t']:.2f} → {'통과' if r3['b_pass'] else '미달'}")
    except Exception as e:  # noqa: BLE001
        summary.append(f"- J3 실행 실패: {e}")
    text = "\n".join(lines[:4] + ["## 요약", ""] + summary + [""] + lines[4:]) + "\n"
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text)
    print(text)


if __name__ == "__main__":
    sys.exit(main())
