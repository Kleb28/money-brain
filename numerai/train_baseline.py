"""Numerai main tournament — baseline model, validation diagnostics and (optionally) a live submission.

Separate track from the thesis pipeline (see numerai/README.md): Numerai supplies the features and scores the
predictions, so the arithmetic-only rule of the thesis pipeline does not apply here; no LLM is involved either.

Steps: pick the newest v5.x dataset via numerapi -> download features.json, train, validation, live,
validation_benchmark_models -> LightGBM on the 'medium' feature set with every 4th era (Numerai example-model
recipe) -> per-era numerai_corr on validation (raw and feature-neutralized), sharpe, max drawdown, feature
exposure, correlation with the benchmark model -> write outputs/numerai_baseline.md -> if NUMERAI_PUBLIC_ID /
NUMERAI_SECRET_KEY / NUMERAI_MODEL_NAME are set, predict live and upload.
Run on GitHub Actions (numer.ai is not reachable from the sandbox). Usage: python -m numerai.train_baseline [--no-submit]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
DATA = Path(os.environ.get("NUMERAI_DATA_DIR", ROOT / "numerai_data"))
FEATURE_SET = os.environ.get("NUMERAI_FEATURE_SET", "medium")
ERA_STEP = int(os.environ.get("NUMERAI_ERA_STEP", "4"))      # every 4th era: 20-day targets do not overlap
PARAMS = dict(n_estimators=2000, learning_rate=0.01, max_depth=5, num_leaves=2 ** 5 - 1, colsample_bytree=0.1, verbose=-1)
NEUTRALIZE_PROP = 1.0


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def pick_version(napi) -> str:
    names = napi.list_datasets()
    log(f"{len(names)} dataset files; train files: {[n for n in names if 'train' in n][:12]}")
    vers = sorted({m.group(1) for f in names if (m := re.match(r"^(v\d+\.\d+)/train(_int8)?\.parquet$", f))},
                  key=lambda v: float(v[1:]))
    if not vers:
        raise SystemExit("no vX.Y/train.parquet dataset found")
    return vers[-1]


def numerai_corr(preds: pd.Series, target: pd.Series) -> float:
    r = (preds.rank(method="average").to_numpy() - 0.5) / len(preds)
    g = norm.ppf(r)
    t = target.to_numpy(float) - target.mean()
    g15 = np.sign(g) * np.abs(g) ** 1.5
    t15 = np.sign(t) * np.abs(t) ** 1.5
    return float(np.corrcoef(g15, t15)[0, 1])


def neutralize(df: pd.DataFrame, pred_col: str, feats: list[str], prop: float = 1.0) -> pd.Series:
    out = []
    for _, g in df.groupby("era", sort=False):
        p = g[pred_col].to_numpy(float); p = (p - p.mean())
        X = g[feats].to_numpy(np.float32); X = X - X.mean(axis=0)
        beta, *_ = np.linalg.lstsq(X, p, rcond=None)
        out.append(pd.Series(p - prop * X @ beta, index=g.index))
    return pd.concat(out).reindex(df.index)


def era_stats(per_era: pd.Series) -> dict:
    cum = per_era.cumsum(); dd = (cum.cummax() - cum).max()
    return {"mean": per_era.mean(), "std": per_era.std(), "sharpe": per_era.mean() / per_era.std() if per_era.std() else float("nan"),
            "max_dd": dd, "pos": (per_era > 0).mean(), "n": len(per_era)}


def fmt(s: dict) -> str:
    return f"{s['mean']:+.4f} | {s['std']:.4f} | {s['sharpe']:.2f} | {s['max_dd']:.3f} | {s['pos']:.2f} | {s['n']}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-submit", action="store_true")
    ap.add_argument("--no-download", action="store_true")
    a = ap.parse_args()
    from numerapi import NumerAPI
    pub, sec, model_name = os.environ.get("NUMERAI_PUBLIC_ID"), os.environ.get("NUMERAI_SECRET_KEY"), os.environ.get("NUMERAI_MODEL_NAME")
    napi = NumerAPI(pub, sec) if pub and sec else NumerAPI()
    ver = pick_version(napi)
    log(f"dataset {ver}; round {napi.get_current_round()}")
    DATA.mkdir(exist_ok=True)
    files = ["features.json", "train.parquet", "validation.parquet", "live.parquet", "validation_benchmark_models.parquet"]
    if not a.no_download:
        for f in files:
            napi.download_dataset(f"{ver}/{f}", dest_path=str(DATA / f))
            log(f"downloaded {f}: {os.path.getsize(DATA / f)/1e6:.0f} MB")

    meta = json.load(open(DATA / "features.json"))
    feats = meta["feature_sets"][FEATURE_SET]
    targets = meta.get("targets", [])
    target = "target" if "target" in targets or not targets else targets[0]
    log(f"feature set {FEATURE_SET}: {len(feats)} features; target '{target}'; {len(targets)} target columns in file")

    schema = pq.read_schema(DATA / "train.parquet").names
    non_feat = [c for c in schema if not c.startswith("feature_") and not c.startswith("target")]
    log(f"non-feature columns: {non_feat[:20]}")
    era_col = next((c for c in ("era", "date") if c in schema), None)
    if era_col is None:
        raise SystemExit(f"no era/date column; columns start {schema[:10]}")
    extra = [c for c in ("data_type",) if c in schema]
    cols = [era_col] + extra + [target] + feats

    def load(path: str, step: int) -> pd.DataFrame:
        df = pq.read_table(DATA / path, columns=cols).to_pandas()
        if "data_type" in df.columns and path.startswith("validation"):
            df = df[df["data_type"] == "validation"]
        df = df.dropna(subset=[target])
        codes, uniques = pd.factorize(df[era_col], sort=True)   # eras as ordered integers (works for 'era' strings and dates)
        df["era"] = codes
        n_eras = len(uniques)
        df = df[df["era"] % step == 0]
        return df, n_eras, uniques

    train, n_train_eras, _ = load("train.parquet", ERA_STEP)
    log(f"train: {len(train):,} rows, {train['era'].nunique()} eras (every {ERA_STEP}th of {n_train_eras})")

    import lightgbm as lgb
    model = lgb.LGBMRegressor(**PARAMS)
    t0 = time.time()
    model.fit(train[feats].astype(np.float32), train[target])
    log(f"trained in {(time.time()-t0)/60:.1f} min")
    n_train_used = train["era"].nunique()
    del train

    val, n_val_eras, val_uniques = load("validation.parquet", ERA_STEP)
    val_eras = sorted(val["era"].unique())
    val["pred"] = model.predict(val[feats].astype(np.float32))
    val["pred_neut"] = neutralize(val, "pred", feats, NEUTRALIZE_PROP)
    log(f"validation: {len(val):,} rows, {val['era'].nunique()} eras")

    per_era = val.groupby("era").apply(lambda g: numerai_corr(g["pred"], g[target]))
    per_era_n = val.groupby("era").apply(lambda g: numerai_corr(g["pred_neut"], g[target]))
    # feature exposure
    expo = pd.Series({f: np.corrcoef(val[f].astype(float), val["pred"])[0, 1] for f in feats}).abs()
    # benchmark comparison on the same eras
    bench_lines = []
    try:
        bm = pq.read_table(DATA / "validation_benchmark_models.parquet").to_pandas()
        if "id" in bm.columns:
            bm = bm.set_index("id")
        bcols = [c for c in bm.columns if c not in ("era", "data_type")]
        bm = bm.reindex(val.index)
        for c in bcols[:8]:
            s = bm[c]
            if s.notna().sum() < 1000:
                continue
            v2 = val.assign(b=s).dropna(subset=["b"])
            pe = v2.groupby("era").apply(lambda g: numerai_corr(g["b"], g[target]))
            cwith = float(np.corrcoef(v2["b"], v2["pred"])[0, 1])
            bench_lines.append(f"| benchmark {c} | {fmt(era_stats(pe))} | corr with our preds {cwith:.2f} |")
    except Exception as e:  # noqa: BLE001
        bench_lines.append(f"| benchmark models not loaded: {e!r:.120} |")

    lines = [f"# Numerai baseline — {ver}, LightGBM on '{FEATURE_SET}' ({len(feats)} features), target {target}, every {ERA_STEP}th era",
             "", f"Train: {n_train_used} of {n_train_eras} eras; validation: {val['era'].nunique()} of {n_val_eras} eras ({val_uniques[0]} .. {val_uniques[-1]}). "
             "Columns: mean per-era numerai_corr | std | sharpe | max drawdown (cum corr) | share of eras > 0 | n eras.", "",
             "| model | mean | std | sharpe | max dd | pos | n | note |", "|---|---|---|---|---|---|---|---|",
             f"| ours, raw | {fmt(era_stats(per_era))} | feature exposure max {expo.max():.2f}, mean {expo.mean():.3f} |",
             f"| ours, feature-neutralized ({NEUTRALIZE_PROP:.0%}) | {fmt(era_stats(per_era_n))} | FNC-style |"] + bench_lines
    lines += ["", "Per-era corr (raw), by year of era index:", ""]
    yr = (per_era.index.to_series() // 52)
    for k, g in per_era.groupby(yr):
        lines.append(f"- eras {g.index.min()}–{g.index.max()}: mean {g.mean():+.4f}, pos {(g > 0).mean():.2f}, n {len(g)}")
    OUT.mkdir(exist_ok=True)
    (OUT / "numerai_baseline.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))

    # live prediction + submission
    if a.no_submit or not (pub and sec and model_name):
        log("submission skipped (no keys / --no-submit)"); return
    live = pq.read_table(DATA / "live.parquet", columns=feats).to_pandas()
    live["prediction"] = model.predict(live[feats].astype(np.float32))
    live["prediction"] = live["prediction"].rank(pct=True)
    sub = live[["prediction"]].reset_index()
    sub.columns = ["id", "prediction"]
    path = DATA / "live_predictions.csv"; sub.to_csv(path, index=False)
    models = napi.get_models()
    if model_name not in models:
        raise SystemExit(f"model '{model_name}' not found in account; have {list(models)}")
    napi.upload_predictions(str(path), model_id=models[model_name])
    log(f"submitted {len(sub):,} live predictions for model {model_name}")


if __name__ == "__main__":
    main()
