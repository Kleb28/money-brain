# Model-ETF experiment — pre-registered rules (2026-11-06)

목적: money-brain이 고른 "특허 신호 있음 + 시장이 아직 말하지 않음" 테마 3개가, 관심 정점에서 출시된 테마 ETF와 시장 지수보다 나은 수익을 내는지 forward test로 확인함. 실제 매매가 아닌 paper portfolio임.

## 설계
- Inception: 2026-11-06 종가 (그 날 종가가 없으면 그 이후 첫 거래일 종가). 측정 기간 24개월, 중간 읽기 6·12·18개월.
- Treatment (T): 3개 thesis basket, basket 안은 동일 비중, 전체는 basket당 1/3.
  - A adv_packaging: AMKR, MU, FORM, ONTO
  - B ntn_d2d: ASTS, GSAT
  - C battery_next: QS, SLDP, ASPN, MVST
- Control:
  - K1 attention-peak 테마 ETF: FOTO (Tuttle Pure Play Photonics, 2026-05-27 출시), DRAM (Roundhill Memory, 2026-04 출시) 동일 비중 — Ben-David·Franzoni·Kim·Moussawi (RFS 2023)의 "ETF 출시 = 관심 정점" 대조군
  - K2 시장: SPY; K3 섹터: SMH, QQQ
- 종목 선정 근거는 theses/linkage_2026-11-06.md의 for/against 통과 목록 그대로이고, 이 파일 작성 이후 종목 추가·교체는 하지 않음.
- 카드가 Falsification 조건으로 retire되면 그 basket은 retire 날짜 종가로 현금화(이후 수익률 0)하고 Review log에 기록함. 카드 retire 외의 이유로는 바꾸지 않음.

## 측정
- 주간 (토요일 04:00 UTC, GitHub Actions `portfolio`): Stooq 일별 종가를 data/prices.csv에 누적, outputs/portfolio.md 갱신.
- 1차 지표: inception 이후 buy-and-hold 동일 비중 가격 수익률 (배당 미반영 — 명시). 2차: 월초 동일 비중 재조정 변형, 최대 낙폭, 종목별 기여.
- 비교: T − K1, T − SPY, basket별 − SPY.

## 미리 적어 두는 한계
- 테마 3개·종목 10개로는 통계적 검정력이 없음 — 결과는 pilot이며, 파이프라인을 계속 돌려 테마 수가 쌓여야 검정이 됨.
- B basket은 종목 2개(ASTS 변동성이 결과를 지배할 수 있음).
- 가격 수익률만 쓰므로 배당이 있는 SPY·SMH에 불리하게 비교됨 (SPY 배당수익률 약 1%대, 정확한 값은 측정하지 않았음).
- 종목 선정 시점(2026-11-06)의 정보로 골랐으므로 inception 이전 구간의 backtest는 look-ahead bias가 있어 하지 않음.

## 성공·실패 판정 (24개월)
- H1: T가 K1보다 높음. H2: T가 SPY보다 높음.
- 둘 다 아니면 "덜 explored 테마 선택"이 이 세트에서는 수익으로 연결되지 않았다고 기록하고, 선정 규칙(Tier·attention flag)을 다음 세트에서 수정함.
