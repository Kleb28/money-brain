"""Sim I — does lowering our correlation with the Meta Model raise MMC? (pre-registered in simulation/protocol.md)

A  = baseline LightGBM (same recipe as train_baseline.py: medium features, every 4th era, `target`)
H1 = rank mean of A and LightGBMs on the 2 auxiliary targets least correlated with `target` in train eras
H2 = rank 50/50 of A and an sklearn MLP (256-64)
H3 = A orthogonalized 50% against the Meta Model proxy
MM proxy = meta_model file of the dataset if one exists, else benchmark lgbm_jupiter_60 (else first benchmark column).
Per validation era: MMC proxy, NCORR (Numerai neutralizer), raw corr, correlation with the MM proxy.
Verdict: variant − A paired per era; pass = MMC-proxy mean > 0 and t ≥ 2.4 and NCORR mean diff ≥ −0.003.
Writes outputs/sim_i.md. Runs on GitHub Actions (numer.ai is not reachable from the sandbox).
"""
from __future__ import annotations

import json
import math
import os
import time

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.stats import norm

from numerai.train_baseline import DATA, ERA_STEP, OUT, PARAMS, era_stats, log, numerai_corr, pick_version

FEATURE_SET = "medium"
T_PASS, NCORR_TOL = 2.4, -0.003


def gauss(x: np.ndarray) -> np.ndarray:
    r = (pd.Series(x).rank(method="average").to_numpy() - 0.5) / len(x)
    g = norm.ppf(r)
    return g - g.mean()


def dkey(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s.astype(str)).dt.strftime("%Y-%m-%d")


def main() -> None:
    from numerapi import NumerAPI
    napi = NumerAPI()
    ver = pick_version(napi)
    names = napi.list_datasets()
    mine = [n for n in names if n.startswith(ver + "/")]
    log(f"dataset {ver}; files: {mine}")
    DATA.mkdir(exist_ok=True)
    mm_files = [n for n in mine if "meta_model" in n and n.endswith(".parquet")]
    files = ["features.json", "train.parquet", "validation.parquet", "validation_benchmark_models.parquet", "validation_neutralizer.parquet"]
    files += [n.split("/", 1)[1] for n in mm_files]
    for f in files:
        if not (DATA / f).exists():
            napi.download_dataset(f"{ver}/{f}", dest_path=str(DATA / f))
        log(f"have {f}: {os.path.getsize(DATA / f)/1e6:.0f} MB")

    meta = json.load(open(DATA / "features.json"))
    feats = meta["feature_sets"][FEATURE_SET]
    schema = pq.read_schema(DATA / "train.parquet").names
    era_col = "date" if "date" in schema else "era"
    target = "target"
    tcols = [c for c in schema if c.startswith("target")]
    log(f"{len(feats)} features; target columns: {tcols}")

    def load(path: str, cols: list[str]) -> pd.DataFrame:
        df = pq.read_table(DATA / path, columns=[era_col, "numerai_ticker"] + [c for c in ("data_type",) if c in schema] + cols + feats).to_pandas()
        if "data_type" in df.columns and path.startswith("validation"):
            df = df[df["data_type"] == "validation"]
        df = df.dropna(subset=[target])
        codes, _ = pd.factorize(df[era_col], sort=True)
        df["era"] = codes
        return df[df["era"] % ERA_STEP == 0].copy()

    train = load("train.parquet", tcols)
    log(f"train {len(train):,} rows, {train['era'].nunique()} eras")
    str_feats = [f for f in feats if not pd.api.types.is_numeric_dtype(train[f])]
    vocab = {}
    for f in str_feats:
        vals = set()
        for p in ("train.parquet", "validation.parquet"):
            vals |= {str(v) for v in pq.read_table(DATA / p, columns=[f]).column(0).to_pylist() if v is not None}
        vocab[f] = {v: i for i, v in enumerate(sorted(vals))}

    def encode(df):
        for f, m in vocab.items():
            df[f] = df[f].astype(str).map(m).fillna(-1).astype(np.int32)
        return df
    train = encode(train)
    cat = [feats.index(f) for f in str_feats] or "auto"

    # --- H1 auxiliary target choice: train eras only
    aux_cand = [c for c in tcols if c != target and "jupiter" not in c and train[c].notna().mean() >= 0.5]
    cand_corr = {}
    for c in aux_cand:
        sub = train[["era", target, c]].dropna()
        if (sub[target] == sub[c]).mean() > 0.99:
            continue
        cand_corr[c] = sub.groupby("era").apply(lambda g: np.corrcoef(g[target], g[c])[0, 1]).mean()
    aux = sorted(cand_corr, key=cand_corr.get)[:2]
    log(f"aux target correlation with target (train): {dict(sorted(cand_corr.items(), key=lambda kv: kv[1]))}; chosen {aux}")

    import lightgbm as lgb
    models = {}
    for tgt in [target] + aux:
        sub = train.dropna(subset=[tgt])
        t0 = time.time()
        m = lgb.LGBMRegressor(**PARAMS)
        m.fit(sub[feats].astype(np.float32), sub[tgt], categorical_feature=cat)
        models[tgt] = m
        log(f"LightGBM on {tgt}: {(time.time()-t0)/60:.1f} min")

    # --- H2 MLP on numeric features
    from sklearn.neural_network import MLPRegressor
    num = [f for f in feats if f not in str_feats]
    Xtr = train[num].astype(np.float32)
    med = Xtr.median(); Xtr = Xtr.fillna(med)
    mu, sd = Xtr.mean(), Xtr.std().replace(0, 1)
    Xtr = ((Xtr - mu) / sd).to_numpy(np.float32)
    t0 = time.time()
    mlp = MLPRegressor(hidden_layer_sizes=(256, 64), batch_size=2048, learning_rate_init=1e-3, max_iter=20,
                       early_stopping=True, n_iter_no_change=3, random_state=0)
    mlp.fit(Xtr, train[target].to_numpy(np.float32))
    log(f"MLP: {(time.time()-t0)/60:.1f} min, {mlp.n_iter_} epochs")
    del train, Xtr

    val = encode(load("validation.parquet", [target]))
    val["_d"] = dkey(val[era_col])
    Xv = val[feats].astype(np.float32)
    val["A"] = models[target].predict(Xv)
    for i, t in enumerate(aux):
        val[f"aux{i+1}"] = models[t].predict(Xv)
    Xm = ((val[num].astype(np.float32).fillna(med) - mu) / sd).to_numpy(np.float32)
    val["mlp"] = mlp.predict(Xm)
    del Xv, Xm
    log(f"validation {len(val):,} rows, {val['era'].nunique()} eras")

    # --- MM proxy
    mm_src = None
    for f in mm_files:
        mmdf = pq.read_table(DATA / f.split("/", 1)[1]).to_pandas()
        if "numerai_ticker" not in mmdf.columns:
            mmdf = mmdf.reset_index()
        mcol = [c for c in mmdf.columns if "meta" in c.lower() and pd.api.types.is_numeric_dtype(mmdf[c])]
        dcol = next((c for c in ("date", "era") if c in mmdf.columns), None)
        log(f"{f}: columns {list(mmdf.columns)[:10]}, rows {len(mmdf):,}")
        if mcol and dcol and "numerai_ticker" in mmdf.columns:
            mm = mmdf[["numerai_ticker", dcol, mcol[0]]].rename(columns={mcol[0]: "mm"}); mm["_d"] = dkey(mm[dcol])
            if mm.merge(val[["numerai_ticker", "_d"]], on=["numerai_ticker", "_d"]).shape[0] > 10_000:
                mm_src = f"{f} [{mcol[0]}]"; break
    if mm_src is None:
        bm = pq.read_table(DATA / "validation_benchmark_models.parquet").to_pandas()
        if "numerai_ticker" not in bm.columns:
            bm = bm.reset_index()
        bcols = [c for c in bm.columns if c not in ("numerai_ticker", "composite_figi", "date", "data_type", "era", "id") and pd.api.types.is_numeric_dtype(bm[c])]
        c = "lgbm_jupiter_60" if "lgbm_jupiter_60" in bcols else bcols[0]
        log(f"no usable meta_model file; benchmark columns {bcols}; using {c}")
        mm = bm[["numerai_ticker", era_col, c]].rename(columns={c: "mm"}); mm["_d"] = dkey(mm[era_col])
        mm_src = f"validation_benchmark_models [{c}] (benchmark, not the real Meta Model)"
    val = val.merge(mm[["numerai_ticker", "_d", "mm"]], on=["numerai_ticker", "_d"], how="inner").dropna(subset=["mm"])
    log(f"rows with MM proxy: {len(val):,}, eras {val['era'].nunique()}; source {mm_src}")

    # --- variants (per era, rank/gauss space)
    def per_era(g: pd.DataFrame) -> pd.DataFrame:
        r = lambda c: g[c].rank(pct=True)
        out = pd.DataFrame(index=g.index)
        out["A"] = r("A")
        out["H1"] = (r("A") + r("aux1") + (r("aux2") if "aux2" in g else 0)) / (3 if "aux2" in g else 2)
        out["H2"] = (r("A") + r("mlp")) / 2
        p, m = gauss(g["A"].to_numpy()), gauss(g["mm"].to_numpy())
        out["H3"] = p - 0.5 * m * (p @ m) / (m @ m)
        out["MLP alone"] = r("mlp")
        out["aux1 alone"] = r("aux1")
        return out
    V = pd.concat([per_era(g) for _, g in val.groupby("era", sort=False)])
    variants = list(V.columns)
    val = val.join(V.add_prefix("v_"))

    def mmc(g: pd.DataFrame, c: str) -> float:
        p, m = gauss(g[c].to_numpy()), gauss(g["mm"].to_numpy())
        pn = p - m * (p @ m) / (m @ m)
        t = g[target].to_numpy(float); t = t - t.mean()
        return float(t @ pn / len(t))

    # --- NCORR via Numerai neutralizer (streamed, our dates only)
    pf = pq.ParquetFile(DATA / "validation_neutralizer.parquet")
    ncols = [c for c in pf.schema_arrow.names if c not in ("numerai_ticker", "composite_figi", "date", "data_type", "era") and not c.startswith("__")]
    want = set(val["_d"]); parts = []
    for b in pf.iter_batches(batch_size=250_000):
        b = b.to_pandas(); dc = "date" if "date" in b.columns else "era"
        b["_d"] = dkey(b[dc]); b = b[b["_d"].isin(want)]
        if len(b):
            b = b[["numerai_ticker", "_d"] + ncols].copy(); b[ncols] = b[ncols].astype("float32"); parts.append(b)
    neut = pd.concat(parts, ignore_index=True)
    log(f"neutralizer rows {len(neut):,}, {len(ncols)} columns")
    vn = val[["numerai_ticker", "_d", "era", target, "mm"] + ["v_" + v for v in variants]].merge(neut, on=["numerai_ticker", "_d"], how="inner")
    del neut

    rows = []
    for e, g in vn.groupby("era", sort=True):
        M = np.nan_to_num(g[ncols].to_numpy(float)); M = M - M.mean(axis=0)
        for v in variants:
            c = "v_" + v
            gz = gauss(g[c].to_numpy())
            beta, *_ = np.linalg.lstsq(M, gz, rcond=None)
            rows.append({"era": e, "variant": v,
                         "ncorr": numerai_corr(pd.Series(gz - M @ beta), g[target]),
                         "corr": numerai_corr(g[c], g[target]),
                         "mmc": mmc(g, c),
                         "corr_mm": float(np.corrcoef(g[c].rank(), g["mm"].rank())[0, 1])})
        rows.append({"era": e, "variant": "MM proxy itself", "ncorr": np.nan, "corr": numerai_corr(g["mm"], g[target]), "mmc": np.nan, "corr_mm": 1.0})
    R = pd.DataFrame(rows)
    piv = {k: R.pivot(index="era", columns="variant", values=k) for k in ("ncorr", "corr", "mmc", "corr_mm")}
    n = piv["mmc"]["A"].notna().sum()

    L = [f"# Sim I — lower Meta Model correlation for MMC ({ver}, {FEATURE_SET} {len(feats)} features, target `{target}`, every {ERA_STEP}th era)", "",
         f"MM proxy: {mm_src}. Validation eras with MM proxy and neutralizer: {n}. Auxiliary targets (H1): {', '.join(aux)} "
         f"(train per-era corr with target {', '.join(f'{cand_corr[a]:.2f}' for a in aux)}). MLP epochs {mlp.n_iter_}.", "",
         "Per-era means. Columns: MMC proxy | NCORR | raw corr | corr with MM proxy | n eras", "",
         "| variant | MMC proxy | NCORR | corr | corr w/ MM | n |", "|---|---|---|---|---|---|"]
    for v in variants + ["MM proxy itself"]:
        f = lambda k: piv[k][v].mean()
        L.append(f"| {v} | {f('mmc'):+.4f} | {f('ncorr'):+.4f} | {f('corr'):+.4f} | {f('corr_mm'):.3f} | {piv['corr'][v].notna().sum()} |")
    L += ["", "Paired difference vs A (per era). Columns: mean | std | sharpe | t | max dd | pos | n", "",
          "| variant | metric | mean | std | sharpe | t | max dd | pos | n | verdict |", "|---|---|---|---|---|---|---|---|---|---|"]
    for v in ("H1", "H2", "H3"):
        dm = (piv["mmc"][v] - piv["mmc"]["A"]).dropna(); dn = (piv["ncorr"][v] - piv["ncorr"]["A"]).dropna()
        sm, sn = era_stats(dm), era_stats(dn)
        ok = sm["mean"] > 0 and sm["t"] >= T_PASS and sn["mean"] >= NCORR_TOL
        fm = lambda s: f"{s['mean']:+.4f} | {s['std']:.4f} | {s['sharpe']:.2f} | {s['t']:+.1f} | {s['max_dd']:.3f} | {s['pos']:.2f} | {s['n']}"
        L.append(f"| {v} | MMC proxy | {fm(sm)} | {'PASS' if ok else 'fail'} |")
        L.append(f"| {v} | NCORR | {fm(sn)} | bar ≥ {NCORR_TOL} |")
    L += ["", f"Pass rule (pre-registered): MMC-proxy diff mean > 0 and t ≥ {T_PASS}, and NCORR diff mean ≥ {NCORR_TOL}."]
    OUT.mkdir(exist_ok=True)
    (OUT / "sim_i.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    R.to_csv(OUT / "sim_i_eras.csv", index=False, float_format="%.6f")
    print("\n".join(L))


if __name__ == "__main__":
    main()
