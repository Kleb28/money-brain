# Sim I — lower Meta Model correlation for MMC (v6.0, medium 351 features, target `target`, every 4th era)

MM proxy: validation_benchmark_models [lgbm_jupiter_60] (benchmark, not the real Meta Model). Validation eras with MM proxy and neutralizer: 100. Auxiliary targets (H1): target_eleven_4, target_raw_return_20 (train per-era corr with target 0.16, 0.33). MLP epochs 18.

Per-era means. Columns: MMC proxy | NCORR | raw corr | corr with MM proxy | n eras

| variant | MMC proxy | NCORR | corr | corr w/ MM | n |
|---|---|---|---|---|---|
| A | +0.0006 | +0.0307 | +0.0275 | 0.675 | 100 |
| H1 | +0.0005 | +0.0263 | +0.0208 | 0.560 | 100 |
| H2 | +0.0002 | +0.0237 | +0.0217 | 0.574 | 100 |
| H3 | +0.0008 | +0.0207 | +0.0189 | 0.423 | 100 |
| MLP alone | -0.0002 | +0.0065 | +0.0061 | 0.217 | 100 |
| aux1 alone | +0.0005 | +0.0131 | +0.0117 | 0.271 | 100 |
| MM proxy itself | +nan | +nan | +0.0359 | 1.000 | 100 |

Paired difference vs A (per era). Columns: mean | std | sharpe | t | max dd | pos | n

| variant | metric | mean | std | sharpe | t | max dd | pos | n | verdict |
|---|---|---|---|---|---|---|---|---|---|
| H1 | MMC proxy | -0.0002 | 0.0020 | -0.08 | -0.8 | 0.018 | 0.48 | 100 | fail |
| H1 | NCORR | -0.0044 | 0.0114 | -0.38 | -3.8 | 0.385 | 0.35 | 100 | bar ≥ -0.003 |
| H2 | MMC proxy | -0.0004 | 0.0027 | -0.16 | -1.6 | 0.075 | 0.40 | 100 | fail |
| H2 | NCORR | -0.0070 | 0.0137 | -0.51 | -5.1 | 0.780 | 0.23 | 100 | bar ≥ -0.003 |
| H3 | MMC proxy | +0.0002 | 0.0008 | 0.20 | +2.0 | 0.006 | 0.54 | 100 | fail |
| H3 | NCORR | -0.0100 | 0.0068 | -1.47 | -14.7 | 1.002 | 0.05 | 100 | bar ≥ -0.003 |

Pass rule (pre-registered): MMC-proxy diff mean > 0 and t ≥ 2.4, and NCORR diff mean ≥ -0.003.
