# Numerai baseline — v6.0, LightGBM on 'medium' (351 features), target target, every 4th era

Train: 209 of 835 eras; validation: 100 of 397 eras (2019-01-04 .. 2026-08-07). Columns: mean per-era numerai_corr | std | sharpe (mean/std) | t (sharpe·√n) | max drawdown (cum corr) | share of eras > 0 | n eras.

| model | target | mean | std | sharpe | t | max dd | pos | n | note |
|---|---|---|---|---|---|---|---|---|---|
| ours, raw | target | +0.0275 | 0.0203 | 1.35 | +13.5 | 0.036 | 0.89 | 100 | feature exposure max 0.24, mean 0.065 |
| ours, feature-neutralized (100%) | target | +0.0266 | 0.0225 | 1.19 | +11.9 | 0.028 | 0.93 | 100 | FNC-style |
| ours, NCORR (Numerai neutralizer) | target | +0.0307 | 0.0230 | 1.34 | +13.4 | 0.037 | 0.89 | 100 | payout metric |
| ours, raw | target_jupiter_20 | +0.0181 | 0.0212 | 0.85 | +8.5 | 0.057 | 0.83 | 100 | feature exposure max 0.24, mean 0.065 |
| ours, feature-neutralized (100%) | target_jupiter_20 | +0.0180 | 0.0206 | 0.87 | +8.7 | 0.043 | 0.82 | 100 | FNC-style |
| ours, NCORR (Numerai neutralizer) | target_jupiter_20 | +0.0208 | 0.0234 | 0.89 | +8.9 | 0.058 | 0.83 | 100 | payout metric |
| ours, raw | target_jupiter_60 | +0.0275 | 0.0203 | 1.35 | +13.5 | 0.036 | 0.89 | 100 | feature exposure max 0.24, mean 0.065 |
| ours, feature-neutralized (100%) | target_jupiter_60 | +0.0266 | 0.0225 | 1.19 | +11.9 | 0.028 | 0.93 | 100 | FNC-style |
| ours, NCORR (Numerai neutralizer) | target_jupiter_60 | +0.0307 | 0.0230 | 1.34 | +13.4 | 0.037 | 0.89 | 100 | payout metric |
| benchmark lgbm_jupiter_60 | target | +0.0359 | 0.0195 | 1.83 | +18.3 | 0.003 | 0.99 | 100 | corr with our preds 0.67 |
| benchmark lgbm_jupiter_60 | target_jupiter_20 | +0.0250 | 0.0216 | 1.16 | +11.6 | 0.019 | 0.87 | 100 | corr with our preds 0.67 |
| benchmark lgbm_jupiter_60 | target_jupiter_60 | +0.0359 | 0.0195 | 1.83 | +18.3 | 0.003 | 0.99 | 100 | corr with our preds 0.67 |
| (same-era check) ours NCORR vs this benchmark raw | target | +0.0307 | 0.0230 | 1.34 | +13.4 | 0.037 | 0.89 | 100 | eras with benchmark coverage |

Per-era corr (raw), by year of era index:

- eras 0–48: mean +0.0393, pos 0.92, n 13
- eras 52–100: mean +0.0150, pos 0.69, n 13
- eras 104–152: mean +0.0424, pos 1.00, n 13
- eras 156–204: mean +0.0280, pos 1.00, n 13
- eras 208–256: mean +0.0341, pos 1.00, n 13
- eras 260–308: mean +0.0258, pos 0.92, n 13
- eras 312–360: mean +0.0090, pos 0.62, n 13
- eras 364–396: mean +0.0258, pos 1.00, n 9
