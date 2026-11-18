# Sim J — 팩터 조합·최적화 walk-forward (simulation/protocol.md 사전 등록 2026-11-18)

실행 2026-11-18 UTC. 모든 가중치·예측은 t월 말까지의 데이터로 만들고 t+1월에 적용.

## 요약

- J1 실행 실패: FRED download failed: TB3MS
- J2 팩터 MV vs 1/N: t -0.99 → 미달
- J3a ETF COMP long-short: t 0.63 → 미달
- J3b ETF RIDGE vs COMP: t 1.07 → 미달

- 데이터: French 월간 1926-07 ~ 2026-09
## J2 — 미국 주식 팩터 8개 조합 (1990-01 이후 표본 밖, paper long-short, 비용 없음)

| 전략 | 연 수익(%) | Sharpe | 2010- Sharpe | vs 1/N 차이 t |
|---|---|---|---|---|
| 1/N | 3.31 | 0.78 | 0.43 | nan |
| MV | 2.98 | 0.71 | 0.45 | -0.99 |
| InvVol | 2.90 | 0.68 | 0.28 | -2.11 |
| FacMom | 4.83 | 0.74 | 0.49 | -0.33 |
| Mkt-RF | 8.94 | 0.59 | 0.87 | -0.90 |

- 팩터별 표본 밖 Sharpe: Mkt-RF 0.59, SMB 0.08, HML 0.17, RMW 0.39, CMA 0.27, Mom 0.34, ST_Rev 0.13, LT_Rev 0.22
- 판정(MV − 1/N 표준화 차이 평균 > 0 이고 t ≥ 2.5, n 441): 평균 -0.0225, t -0.99 → 미달

## J3 — 자산군 ETF 21개 cross-section (표본 밖 2002-11 ~ 2026-11)

| 전략 | 연 수익(%) | 연 변동성(%) | Sharpe | t |
|---|---|---|---|---|
| COMP long-short(비용 후) | 0.39 | 3.19 | 0.12 | 0.63 |
| RIDGE long-short(비용 후) | 1.36 | 3.52 | 0.39 | 1.87 |
| COMP 구간 맞춤(RIDGE 기간) | 0.39 | 3.19 | 0.12 | 0.63 |
| TSMOM | 2.20 | 4.63 | 0.48 | 2.29 |
| COMP 상위 1/3 long-only | 5.38 | 8.25 | 0.45 | 2.16 |
| ETF 1/N long-only | 6.47 | 8.62 | 0.56 | 2.62 |
| SPY 60 / IEF 40 | 8.36 | 8.88 | 0.75 | 3.96 |

- 신호별 단독 long-short Sharpe(비용 후): MOM 0.25, TREND 0.38, REV -0.62, LOWVOL 0.37, VAL -0.24
- J3a 판정(COMP long-short 평균 > 0 이고 t ≥ 2.5): 연 +0.39%, t 0.63 → 미달
- J3b 판정(RIDGE − COMP 표준화 차이 평균 > 0 이고 t ≥ 2.5, n 289): 평균 +0.0763, t 1.07 → 미달
- long-only 행의 Sharpe·t는 무위험 수익 차감 후, long-short·TSMOM은 그대로(자기 자금 조달)

