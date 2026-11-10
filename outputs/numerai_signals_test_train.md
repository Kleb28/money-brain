# Sim F — Numerai Signals v3.1 offline test (train; protocol: simulation/protocol.md)

US rows 1833243 (tickers 5680); matched to money-brain 10-K features: median 909 of 2239 tickers per date. Dates 2009-07-03 .. 2018-12-28; 20d target on every 4th date, 60d on every 12th. Columns: mean corr | SD | t | share > 0 | n dates.

## target_jupiter_20

| feature | version | mean | SD | t | pos | n |
|---|---|---|---|---|---|---|
| F1 | raw | +0.0020 | 0.0375 | +0.59 | 0.56 | 124 |
| F2 | raw | +0.0038 | 0.0311 | +1.29 | 0.55 | 111 |
| F3 | raw | +0.0048 | 0.0361 | +1.39 | 0.58 | 111 |

## target_jupiter_60

| feature | version | mean | SD | t | pos | n |
|---|---|---|---|---|---|---|
| F1 | raw | -0.0034 | 0.0298 | -0.75 | 0.43 | 42 |
| F2 | raw | +0.0079 | 0.0326 | +1.47 | 0.59 | 37 |
| F3 | raw | +0.0023 | 0.0330 | +0.43 | 0.54 | 37 |

