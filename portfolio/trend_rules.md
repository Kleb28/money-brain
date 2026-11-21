# 추세추종 혼합 paper portfolio — 사전 등록 규칙 (2026-11-18)

목적: Sim K(1972-2002)에서 통과하고 2003-2026 탐색에서 60/40의 변동성·낙폭을 줄였던 추세추종(TSMOM)이, 규칙을 고정한 뒤의 실제 미래 구간에서도 같은 역할을 하는지 forward test로 확인함. 실제 매매가 아닌 paper portfolio이고, 기존 portfolio/rules.md 실험과는 별개임(그쪽 종목·규칙은 건드리지 않음). 근거: simulation/protocol.md Sim J·Sim K·탐색적 혼합 기록.

## 설계
- Inception: 2026-11-30 종가(11월 말 신호로 12월 수익부터 기록). 측정 24개월, 읽기 2027-11-30(12개월)·2028-11-30(24개월)
- 기준 B: SPY 60 / IEF 40, 매월 말 재조정
- 혼합 T: B 80% + 추세추종 sleeve 20%, 매월 말 재조정
- 추세추종 sleeve: ETF 21개(SPY·IWM·EFA·EEM·EWJ·TLT·IEF·SHY·LQD·HYG·TIP·EMB·GLD·SLV·DBC·USO·DBA·VNQ·UUP·FXE·FXY). 월말 t에 각 ETF의 12개월 수익 − 현금(BIL) 12개월 수익의 부호로 long/short, 비중 = 부호 × (10%/σ_i) ÷ N(σ_i = 63거래일 일수익 표준편차 연율화). sleeve 월수익 = 현금(BIL) + 2 × Σ w_i(r_i − 현금) − 2 × 5 bp × turnover
- Sim J·탐색 계산과 다른 점 하나: 무위험 수익을 French RF 대신 BIL ETF 수익으로 씀(French 자료는 2개월쯤 늦게 나옴)
- 참고용(판정에 안 씀): managed futures ETF DBMF·KMLM의 같은 달 수익과 sleeve의 상관 — 실제로 살 수 있는 상품이 우리 계산과 비슷하게 움직이는지 봄
- 이 파일 작성 이후 ETF 목록·비중 규칙·혼합 비율은 바꾸지 않음. ETF가 상장폐지되면 그 달부터 N에서 빠짐

## 측정
- 매주 토요일 04:30 UTC(GitHub Actions `portfolio-trend`): yfinance 조정 종가로 inception 이후 전체를 다시 계산해 outputs/portfolio_trend.md 갱신(완결된 달만)
- 지표: 누적 수익, 월수익 변동성(연율), 최대낙폭(월말 기준), Sharpe(현금 초과)

## 판정 (24개월, 2028-11-30)
- H1: T의 변동성이 B보다 낮음. H2: T의 최대낙폭이 B보다 얕음(같으면 미충족). H3: T의 Sharpe가 B 이상
- H1·H2가 이 실험의 주장(덜 잃는 도구)이고 H3는 같이 봄. H1·H2 둘 다 미충족이면 "분산 효과가 규칙 고정 후에는 나타나지 않았음"으로 기록하고 닫음

## 미리 적어 두는 한계
- 24개월은 통계적 검정력이 없음(pilot). 그 기간에 60/40이 크게 빠지는 구간이 없으면 H2는 판단 재료가 안 됨
- 2× 레버리지 sleeve와 short 포지션은 개인 계좌에서 그대로 구현하기 어려움 — 실제 편입 수단은 managed futures ETF가 될 텐데, 그 상품과의 유사성은 아직 측정하지 않았음(위 참고용 상관으로 쌓음)
- 조정 종가는 배당 재투자를 가정하고 세금·환전 비용은 다루지 않았음
