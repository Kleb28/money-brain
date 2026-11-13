# Numerai baseline — v6.0, LightGBM on 'medium' (351 features), target target, every 4th era

Train: 209 of 835 eras; validation: 100 of 397 eras (2019-01-04 .. 2026-08-07). Columns: mean per-era numerai_corr | std | sharpe | max drawdown (cum corr) | share of eras > 0 | n eras.

| model | mean | std | sharpe | max dd | pos | n | note |
|---|---|---|---|---|---|---|---|
| ours, raw | +0.0275 | 0.0203 | 1.35 | 0.036 | 0.89 | 100 | feature exposure max 0.24, mean 0.065 |
| ours, feature-neutralized (100%) | +0.0266 | 0.0225 | 1.19 | 0.028 | 0.93 | 100 | FNC-style |
| benchmark models not loaded: TypeError("unsupported operand type(s) for /: 'str' and 'int'") |

Per-era corr (raw), by year of era index:

- eras 0–48: mean +0.0393, pos 0.92, n 13
- eras 52–100: mean +0.0150, pos 0.69, n 13
- eras 104–152: mean +0.0424, pos 1.00, n 13
- eras 156–204: mean +0.0280, pos 1.00, n 13
- eras 208–256: mean +0.0341, pos 1.00, n 13
- eras 260–308: mean +0.0258, pos 0.92, n 13
- eras 312–360: mean +0.0090, pos 0.62, n 13
- eras 364–396: mean +0.0258, pos 1.00, n 9
