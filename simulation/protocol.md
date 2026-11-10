# Historical simulation protocol — pre-registered 2026-11-06

목적: money-brain의 선정 규칙(특허 Rule G + 10-K Tier)이 과거에 적용됐다면 (A) 시장 화제가 될 기술을 골랐는지, (B) 그 기술을 10-K에 먼저 쓴 회사 basket이 초과수익을 냈는지 검정하고, (C) 그 결과로 규칙 하나를 고르되 다중검정 낙관을 통제함. 이 파일은 결과를 보기 전에 쓰며, 이후 변경은 날짜와 이유를 아래 변경 기록에 남김.

## 데이터 (전부 리포에 있거나 workflow로 수집)
- 특허: Google Patents 미국 출원 제목+초록 bigram 연도별 문서 수·출원인 수, 2005-2026 (data/external/bigram_counts.csv.gz; 2026-11-06 재집계본 — 미래 정보 사전 필터 없음)
- 시장 대화: EDGAR 10-K 전문검색 연도별 언급 수(filing 연도 기준)와 filer 목록(티커 포함)
- 가격: Stooq 일별 종가 (현재 상장 종목만 → 상장폐지 종목 누락 = survivorship bias, 결과에 명시)
- 벤치마크: SPY, 그리고 같은 연도에 무작위로 뽑은 같은 수의 10-K filer basket (아래)

## 사건 정의
- 시점 T = 2008 … 2023 (filing 연도 기준 10-K는 T+1년에 나오는 FY T 보고서까지 사용 가능)
- 후보 bigram at T: T년까지의 특허 count만으로 Rule G(settings.yml: 30 / +50% / 2회 연속) 첫 신호가 [T−2, T]에 있고, 비용어 필터(detector/candidates.is_term)를 통과하고, T년 출원인 ≥ 10
- Tier at T: 10-K 언급 수(T−1, T 두 해 최대) < low → T1, ≥ high → T2, 사이 → T1.5 (보고용). low·high는 아래 탐색 공간
- 한 bigram은 첫 후보 연도 한 번만 사건으로 셈 (중복 제거)

## Sim A — 시장 화제 전환 (예측력)
- 결과 변수: T+3년과 T+5년 10-K 언급 수가 (i) ≥ 30건 (ii) T 시점의 3배 이상
- 비교: T1 사건 vs 같은 T에 Rule G 신호 없이 10-K 언급만 같은 구간인 bigram (신호 없음 대조군; 무작위 표본 사건 수의 3배)
- 보고: 전환율, 비율(lift), Wilson 95% CI, T별 분해

## Sim B — 수익률
- basket(T): T+1년에 제출된 10-K에 그 bigram을 쓴 미국 상장사 전부, 동일 비중, Stooq에 가격이 있는 종목만; 종목 수 < 3이면 사건 제외(기록)
- 진입: T+1년 7월 1일 이후 첫 거래일 종가 (10-K 대부분이 제출된 뒤), 보유 {1, 2, 3}년, 배당 미반영
- 초과수익: basket − SPY (가격 수익률); 두 번째 대조군: 같은 T+1년 10-K filer 전체에서 같은 종목 수를 무작위로 뽑은 basket 100회 평균 ("10-K에 새 단어를 쓰는 회사" 효과 제거)
- 보고: 사건별 초과수익 분포(평균·중앙값·t·히트율), T1 vs T2 vs 신호 없음, 보유기간별, T별; 같은 T·같은 bigram 군집을 고려해 표준오차는 T 단위 cluster로 계산
- 가설: H_B1 T1 basket 초과수익 > 0; H_B2 T1 > T2 (일찍 들어가는 게 낫다)

## Sim C — 규칙 선택 (한 번만)
- 탐색 공간 (고정): Rule G grid 8개 {min_count 10·30} × {+30%·+50%} × {1·2회 연속}; 10-K low {10, 50}, high {100, 200}; 보유 {1, 2, 3년}; basket 구성 1가지 → 총 8 × 4 × 3 = 96 조합
- 분할: 선택 구간 T = 2008-2014, 검증 구간 T = 2015-2019, 봉인 구간 T = 2020-2023 (봉인은 최종 규칙 하나에 대해 한 번만 열고, 그 결과로 다시 고르지 않음)
- 선택 지표: 검증 구간 T1 basket 초과수익(대 SPY)의 평균을 cluster SE로 나눈 t; 다중검정은 96회 시도를 반영한 deflated Sharpe(Bailey·López de Prado, J. Portfolio Management 2014)로 보고
- 선택 규칙: 1등이 아니라 1등과 SE 1개 안에 드는 조합 중 가장 단순한 것(파라미터가 사전 등록값에 가까운 것). 기본값(30/+50%/2회, low 50, high 200, 2년)이 그 안에 들면 기본값 유지
- 통과 기준: 검증 구간 t ≥ 2 그리고 무작위 filer 대조군 대비 초과수익 > 0 → forward test 유지; 미달이면 "이 데이터에 edge 없음"으로 기록하고 portfolio 실험은 그대로 두되 추가 투자 판단에 쓰지 않음

## Sim D — Ben-David 대조군 확인
- 테마 ETF 출시일 이후 12·24개월 ETF 수익률 − SPY, 출시일은 Stooq 첫 가격일로 정의; 대상 ETF는 2010년 이후 출시된 테마 ETF 중 Stooq에 있는 것 (목록은 수집 전에 고정, simulation/etf_list.csv)

## 미리 적는 한계
- Survivorship bias(가격): 상장폐지 종목 누락 → basket 수익률이 위로 치우침; T1·T2·무작위 대조군이 같은 편향을 받으므로 상대 비교로 판단
- 10-K filing 연도 ≈ FY+1이므로 "T년에 알 수 있었던 정보"는 T+1년 상반기까지 제출된 10-K로 한정함(진입을 7월 이후로 둔 이유)
- 2009-2021 단일 체제 편향; 검증·봉인 구간이 모두 강세장임
- bigram ≠ 테마: 같은 기술의 여러 표현이 각각 사건이 돼 유효 표본이 줄어듦 (cluster SE로 일부 보정)
- EDGAR 전문검색은 2001년 이후 문서만 색인함

## 변경 기록
- 2026-11-06: 최초 작성 (결과 미확인 상태)
- 2026-11-07 (Sim B 첫 실행 후, 결과 표를 본 뒤의 변경 — 결과 방향은 바꾸지 않는 데이터 정제): (1) 가격을 미조정 종가에서 분할·배당 조정 종가로 교체 (yfinance auto_adjust) — 미조정 가격에서 OTC 주식의 역분할이 +10만% 수익으로 잡혀 평균이 무의미해짐 (2y 평균 +938% ± 896 등); (2) 진입일 가격 $1 미만 종목 제외; (3) 종목 보유수익 +500% 상한. 중앙값·히트율은 이 변경 전에도 같은 방향이었음(T1 ≈ 대조군 < T2)을 기록해 둠.

## 결과 기록 (2026-11-07)
- Sim A (outputs/sim_a.md): 사전 등록 rule T1 bigram이 T+5년에 10-K 30건 이상이 될 확률 5% vs 대조군 3% (lift 1.6×); 3배 증가 기준 3% vs 1% (5.1×). 통계적으로 양이나 절대 수준이 낮고 2016년 이후 lift 소멸.
- Sim B (outputs/sim_b.md, 조정 종가·$1 하한·+500% 상한 적용본): T1 basket 초과수익 1/2/3년 −2.4 / −7.1 / −17.6% (t −0.5 / −1.3 / −3.1), 대조군 −1.0 / −6.2 / −16.3%; T1 − 대조군 ≈ −1 pp (t ≈ −0.2); T1 − T2 ≈ 0 (t 0.0-0.5). grid 8개 rule 중 검증 기준(t ≥ 2이고 대조군 대비 양)을 만족하는 조합 없음.
- 판정: H_B1·H_B2 기각. "특허 신호 bigram을 다음 해 10-K에 쓴 회사 전부"로 만든 basket에는 edge가 없음. Sim C(규칙 선택)는 통과 후보가 없어 실행하지 않음(규약대로). Portfolio 실험은 사전 등록대로 24개월 유지하되 추가 투자 판단에 쓰지 않음.
- 해석 한계: basket 정의가 "언급한 회사 전부"(부수적 언급 포함)라 카드의 for/against 수혜주 선별과 다름; survivorship bias는 모든 arm에 같은 방향; 2009-2024 대형주 우위 구간이라 동일 비중 basket 전체가 SPY에 뒤짐(대조군 포함).

## Sim B2 — 회사 연결 방식 변경 재검정 (2026-11-08 사전 등록, 실행 전)
배경: Sim B의 basket("언급한 회사 전부")에는 edge가 없었음. 같은 데이터로 두 번째 검정을 하므로 변형은 아래 3개로 고정하고, 통과 기준을 Sim B보다 올림(변형 3 × 보유 3 = 9회 검정 → t ≥ 2.5 이고 대조군 대비 양). 3개 모두 미달이면 회사 연결 단계는 arithmetic으로는 닫고 카드(사람 판단)로만 둠.
- V1 niche 사건: T+1년 언급 회사가 3-10곳인 사건만(표현이 특정 회사군에 한정됨) — Sim B와 같은 basket 규칙, 사건 부분집합. 대조군도 같은 크기 조건.
- V2 회사 순위: 연도별로 각 회사가 그 해 10-K에 쓴 "T1 신호 bigram 수"를 세어 상위 10%(동일 비중) vs 나머지, 보유 1/2/3년 — 테마 basket이 아니라 "신흥 기술 어휘를 가장 많이 먼저 쓰는 회사" 순위. 대조군: 신호 없는 bigram 기준으로 같은 방식의 순위.
- V3 R&D 집약 언급 회사: 사건 basket 안에서 R&D/매출 ≥ 10%(EDGAR companyfacts XBRL, T년 회계연도)인 회사만 — 부수적 언급 제거. 대조군 basket에도 같은 필터.
- 공통: 조정 종가, $1 하한, +500% 상한, cluster SE(연도), 진입 7월 1일 — Sim B와 동일. survivorship bias 동일.
- 추가 수집: companyfacts(CIK별 RevenueFromContractWithCustomer·Revenues·ResearchAndDevelopmentExpense), 티커 4,778개 → 약 4,800 요청.

## Sim B2 결과 기록 (2026-11-08)
- V1 niche: T1 −2.9 / −5.6 / −15.7% (t −0.6 / −0.9 / −2.7) vs 대조군 +0.2 / −4.0 / −14.5% → 미달
- V2 회사 순위: 상위 10% − 나머지 +2.3 / +2.2 / −2.3 pp (t 0.5 / 0.4 / −0.5); 대조군 어휘로도 +1.1 / −0.4 / −2.5 pp → 미달
- V3 R&D 집약(≥10%): T1 −2.6 / −9.5 / −25.4% (t −0.3 / −1.0 / −3.0) vs 대조군 −9.0 / −15.4 / −33.7%; 차이 +6 / +6 / +8 pp, 결합 SE ≈ 11 → t ≈ 0.6-0.8 → 미달 (재무 데이터: companyfacts 4,775 CIK 중 매출·R&D 모두 있는 회사-연도 11,534)
- 판정: 세 변형 모두 통과 기준(t ≥ 2.5, 대조군 대비 양) 미달. 사전 등록대로 "특허 신호 → 10-K 언급 회사" arithmetic 연결은 닫음. 회사 선별은 카드(for/against)로만 두고 paper portfolio로 측정. 파이프라인의 검증된 범위는 테마 선별(Sim A·OOS)까지.

## 복기 (2026-11-09, 탐색적 — 사전 등록 아님, 가설 생성용; simulation/retro/, outputs/retro_2026-11-09.md)
- 전환(10-K 30건 이상·3배)을 사후에 알고 골라도 "언급 회사" basket은 SPY를 못 이김 (T1 전환 사건 2y −5.8% / 3y −16.5% vs 비전환 −8.3 / −18.7%; 사후 전환 bigram 수의 회사 단위 rank IC +0.006, t 0.8) → 실패 원인은 예측이 아니라 연결 방식(언급 ≠ 노출)임
- T1 사건 5,130건 중 10-K 0건인 bigram 2,235건(44%)의 전환율 0.0%; 10-29건 15%, 30-49건 79% → T1 하단(0-9건)은 noise. 변경 전 Kalyani OOS 세트로 독립 검증 필요
- 전환 bigram 37개 목록은 실제 테마 파동과 시점이 맞음 (machine learning·virtual reality·autonomous vehicles 2015, self driving 2016, deep learning 2017, edge/quantum computing 2018, multi cloud·NK 2019, language models 2023)
- 유일하게 일관된 회사 단위 신호는 음(−): 추적 bigram 언급 수가 많은 회사일수록 1y 수익 저조, 매출 하위 1/3에 집중 (IC −0.061, t −3.7, 14개 연도 중 10개 음; 중·대형은 0). 탐색적 발견이므로 OOS 확인 전까지 신호로 쓰지 않음
- T1 bigram 언급 수의 IC는 소형 −0.025(t −1.9) / 대형 +0.035(t +1.3)로 부호가 갈림 — 유의하지 않으나 "capability vs talk" 가설(특허 출원인 연결, Sim E 후보)과 방향이 맞음
- 2020-22 구간 cluster SE ±0.1은 세 해 평균이 우연히 같아서(−29.8/−30.2/−30.2%) 생긴 것, 버그 아님

## Sim F — Numerai Signals 오프라인 검정 (2026-11-11 사전 등록, 실행 전)
배경: 복기(2026-11-09)에서 "추적 bigram을 10-K에 많이 쓰는 소형사는 다음 1년 수익이 낮다"(IC −0.061, t −3.7, 매출 하위 1/3)가 사후 발견됨. 같은 가설을 다른 target(Numerai Signals v3.1 `target_jupiter_20/60`: Numerai risk factor에 중립화된 20/60일 수익)으로 검정함. 우리 수익 데이터와 기간이 겹치므로 완전 독립은 아니나, target 정의·중립화·universe가 다름.
- 데이터: `signals/v3.1/train.parquet`(~2018-12-28)·`validation.parquet`(2019-01-04~)·neutralizer parquet. 미국 티커만(`numerai_ticker` 국가 접미사 US). 우리 feature는 filing 연도 y1의 10-K 기준으로 y1년 7월 1일 ~ y1+1년 6월 30일에 유효 (sim_filers·filer_queries·sim_financials에서 계산; 매칭 안 되는 티커는 제외하고 매칭률을 보고)
- Feature (3개 고정, 전부 "높을수록 좋음" 방향으로 부호를 맞춤): F1 = −(추적 bigram 언급 수); F2 = F1을 매출 하위 1/3(그 날짜 매칭 티커 기준)에만 적용, 나머지 0; F3 = T1 bigram 언급 수에 규모로 부호 부여(하위 1/3 −, 상위 1/3 +, 중간 0)
- 지표: 날짜별 Spearman corr(feature vs target) — raw와 neutralizer 행렬에 선형 중립화한 뒤(Numerai NCORR 근사) 둘 다. 20일 target은 4주 간격, 60일 target은 12주 간격 날짜만 써서 겹침 제거. 평균·SD·t(= 평균/(SD/√n))·양의 비율·날짜 수·날짜당 티커 수
- 분할: train(~2018)에서 먼저 판정. 통과 기준: F1 또는 F2의 중립화 corr(60일 target) 평균 ≥ +0.005 이고 t ≥ 2 이고 양의 날짜 비율 ≥ 0.6. 통과 시에만 validation(2019~)을 한 번 열어 재현 여부를 기록. 미달이면 Numerai 경로는 "우리 텍스트 feature로는 edge 없음"으로 닫고 unstaked 제출도 하지 않음
- 통과 후 경로: unstaked 제출 → 라이브 라운드에서 paper trading → stake 판단은 별도
- 한계: 우리 10-K feature는 추적 bigram(5,382 bigram-연도 + 대조군)에 한정된 부분 집합이라 실제 제출 feature는 전체 10-K로 다시 만들어야 함; Numerai universe는 유동성 상위 종목이라 복기에서 효과가 있던 소형 구간과 일부만 겹침

## 타이밍 결함 기록 (2026-11-11)
- 모든 특허 count(bigram_counts, uspto_abs 시계열)는 filing 연도 기준임. 미국 출원은 최초 우선일로부터 18개월 뒤 공개되므로 T년 filing의 상당수는 T+1년 하반기~T+2년에야 보임. 따라서 "T년까지의 특허 count로 신호"는 실제 운용에서 약 1-1.5년 늦게 알게 되고, Sim A·OOS의 lead(선행 기간)는 그만큼 과대, Sim B의 7월 1일(T+1) 진입은 약 6-12개월 이름. Sim B·B2의 결과가 null이어서 결론은 바뀌지 않으나, 이후 모든 시뮬레이션과 12월 2일 재집계는 publication 연도(출원당 최초 publication_date) 기준으로 함. 운용 중인 detector는 "latest complete year = 전년 대비 denominator 90% 이상인 마지막 해"(2023) 규칙으로 불완전 연도를 피하고 있어 자체 모순은 없으나, publication 기준으로 바꾸면 2024년 데이터를 지금 쓸 수 있음

## Sim E — capability 연결: 특허 출원인 basket (2026-11-11 사전 등록, 12월 2일 BigQuery 무료 한도 갱신 후 실행)
가설: 테마를 10-K에 "언급한" 회사가 아니라 그 테마로 특허를 "낸" 회사가 수혜를 봄. 근거: 복기에서 사후 전환 테마의 언급 basket도 SPY를 못 이김; T1 bigram 언급 수의 IC가 대형 +/소형 −로 갈림(유의하지 않음).
- 사건: Sim B와 같은 사건(사전 등록 rule T1·대조군 T1, 2008-2023) — 단 publication 연도 count로 다시 뽑은 사건을 1차로 쓰고, filing 연도 사건으로도 같은 표를 보고함(비교용)
- 데이터(BigQuery 1회, 약 240 GB): 사건 bigram별·publication 연도 T−2…T별 harmonized 출원인 이름과 건수; 출원인별 그 해 미국 출원 총건수. 출원인→티커 매칭은 SEC company_tickers.json + scripts/dealflow.norm() + 상위 200개 출원인 수동 alias 표(IBM·Alphabet 등). 매칭률 보고
- Basket (사건당): E1 = bigram 출원 건수 상위 10개 상장 출원인(incumbent); E2 = 특화도(bigram 출원 ÷ 그 출원인 총 출원, T−2…T 합) 상위 10개, 단 bigram 출원 ≥ 3건(pure play). 동일 비중, 진입 T+1년 7월 1일, 보유 1/2/3년, 조정 종가·$1 하한·+500% 상한·cluster SE — Sim B와 동일
- 대조군: C1 = 같은 해 미국 출원 ≥ 3건인 상장 출원인 전체에서 같은 수를 무작위로 뽑은 basket(100회 평균); C2 = 총 출원 건수 십분위를 맞춘 무작위 basket(규모 효과 제거 — 이것이 주 대조군). 같은 사건의 Sim B 언급 basket도 나란히 보고
- 통과 기준: E2 − C2 (2y) t ≥ 2.5 이고 E2 − C1 > 0. E1은 보고만(규모 효과와 분리가 어려움). 검정 2변형 × 보유 3 = 6회
- 예상: E1 ≈ C2(incumbent 효과는 규모), E2 > C2이면 "capability 연결"을 카드의 수혜주 선정 규칙에 arithmetic 입력으로 추가하고 paper portfolio 다음 코호트에 적용. 미달이면 arithmetic 회사 연결은 완전히 닫음
- 한계: 상장 출원인은 미국 상장(ADR 포함)으로 한정 → 한·중·일 상장사는 빠짐; harmonized 이름의 자회사 분산; survivorship bias는 Sim B와 동일

## Sim F 결과 기록 (2026-11-11, train 구간 2009-07 ~ 2018-12)
- 매칭: Numerai US 티커 날짜당 중앙값 2,239개 중 우리 10-K feature가 있는 종목 909개(41%)
- 판정 지표(60일 Jupiter target, neutralizer 300열에 중립화): F1 −0.0014 (t −0.25), F2 +0.0071 (t +1.07, 양의 날짜 비율 0.68, n 37), F3 +0.0040 (t +0.69). raw도 같은 방향(F2 +0.0079, t 1.47). 20일 target은 셋 다 0 근처
- 판정: 통과 기준(평균 ≥ 0.005 이고 t ≥ 2 이고 양의 비율 ≥ 0.6)을 어느 feature도 충족하지 못함 — F2는 평균·비율은 넘고 t만 미달. 사전 등록대로 validation(2019~)은 열지 않고, 현재 feature로는 unstaked 제출도 하지 않음. "소형주 buzzword 과다 → 저조"는 방향이 재현됐으나 이 feature(추적 bigram 부분집합, 매칭률 41%)로는 노이즈를 못 이김. 전체 10-K 본문으로 다시 만든 feature는 별도 사전 등록 대상이며, 그때 validation 구간을 봉인된 검정으로 쓸 수 있음
- Sim E 준비: 출원인 쿼리 dry run 239.8 GB(publication 기준, 7,671 bigram) — 12월 2일 한도 갱신 후 실행
