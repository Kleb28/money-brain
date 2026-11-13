# money-brain 인수인계 (2026-11-13 기준)

이 파일은 money-brain(투자 thesis 탐색 파이프라인 + Numerai 트랙)을 "$$$" 프로젝트로 분리하면서 새 세션이 처음 읽는 문서임. 규칙은 CLAUDE.md, 실험 규약과 판정은 simulation/protocol.md가 원본이고, 여기는 상태·운영·다음 할 일만 적음. 모든 숫자의 출처는 outputs/ 아래 파일임.

## 1. 한 줄 상태
- 테마 탐지는 작동이 확인됐고(독립 세트 lift 1.5-5×), 회사 선정의 arithmetic 연결은 10-K 언급 방식으로는 실패했으며(사후 전환을 알아도 null), 특허 출원인 방식(Sim E)이 12월 2일 실행 대기 중임. Numerai 트랙은 Unity v6.0으로 baseline 제출을 시작했고(round 1397, 모델 kleb28, unstaked), 우리 feature를 더한 1차 검정(Sim G)은 실패함.

## 2. 지금 돌아가는 것 (GitHub Actions, 리포는 public — 로그도 public)
- `collect.yml` 매주 월 03:17 UTC — PubMed·arXiv·EDGAR 등 수집 → detector → outputs/tiers.csv·signals.csv·validation_report.md
- `portfolio.yml` 매주 토 04:00 UTC — paper portfolio 가격 누적 → outputs/portfolio.md (inception 2026-11-06, 24개월, 읽기 2027-05-06·2027-11-06·2028-05-06; 규칙 portfolio/rules.md, 종목 변경 금지)
- `bq.yml` 매월 2일 — Google Patents BigQuery 키워드 count(uspto_abs). 1회 약 236 GB, 무료 한도 1 TB/월
- `numerai.yml` 매주 토 20:00 UTC — Unity v6.0 다운로드 → LightGBM(medium 351 feature, 4 era마다) → validation 진단 → live 예측 제출(모델 kleb28) → outputs/numerai_baseline.md
- 수동 실행만: `bq-bigrams`(전체 bigram count, ~254 GB), `bq-assignees`(Sim E 출원인, ~240 GB), `numerai-test`(Sim F), `dealflow`, `filers`, `prices`, `companyfacts`, `theme-market`, `probe`, `oos`

## 3. 비밀·변수 (값은 절대 코드·로그·커밋에 쓰지 않음)
- Repository secrets: NCBI_API_KEY, USPTO_API_KEY, GCP_SA_KEY, NUMERAI_PUBLIC_ID, NUMERAI_SECRET_KEY
- Repository variables: EDGAR_USER_AGENT(Caleb 연락처), GCP_PROJECT_ID = money-brain-513811, BQ_MAX_GB(기본 400)
- NUMERAI_MODEL_NAME 변수는 없음 — 계정에 슬롯이 하나(kleb28)라 코드가 자동 선택함. 슬롯을 늘리면 변수로 지정해야 함
- Claude 세션의 proxy는 GitHub secrets/variables 쓰기를 403으로 막음 → 키 추가·교체는 Caleb이 GitHub 화면에서 함. Numerai 키는 2026-11-13 대화 스크린샷에 노출됐으므로 원하면 재발급 후 secret 값만 교체
- Claude 세션 sandbox는 numer.ai·sec.gov·stooq·arXiv에 직접 접속 못 함 → 네트워크 작업은 전부 Actions에서 돌림. BigQuery 11월 사용량 약 980 GB(한도 근접), 12월 2일 갱신

## 4. 확정된 판정 (전부 protocol.md에 기록, 사전 등록 기준으로 판정)
- Sim A: T1 bigram이 10-K 토픽이 되는 비율은 낮지만(3년 내 30건 이상 5%) 무신호 대비 lift 1.5-5×; 전환 목록은 실제 파동과 시점이 맞음(machine learning 2015, deep learning 2017, quantum computing 2018, language models 2023)
- Sim B·B2: 10-K 언급 회사 basket은 SPY·대조군 대비 edge 없음(T1−control ≈ −1 pp, t −0.2; 변형 V1-V3 모두 t < 2.5). 복기에서 사후 전환을 알고 골라도 null → "언급 ≠ 노출"로 경로 닫음
- Sim D: 테마 ETF 출시 후 수익, 생존 ETF 42개로는 결론 불가 → 닫음, Ben-David et al.(RFS 2023)을 prior로 씀
- Theory 3: 10-K 10-49건 구간이 신호의 유효 구간(Kalyani 세트 disruptive 69% vs 1-9건 21%) → 2026-11-11 settings `edgar_low_min: 10` 추가, 신호 있고 10-K < 10이면 tier TW(watch)
- 타이밍 결함: 특허 count가 filing 연도 기준이라 약 1-1.5년 look-ahead가 있었음. 수집기에 publication 연도 basis 추가(기본값), 12월부터 적용. 기존 결론은 null이라 안 바뀜
- Sim F(Numerai Signals 오프라인): 추적 bigram 언급 feature 3종, 중립화 corr 전부 기준 미달(F2 +0.0071, t 1.07) → 닫음, validation 구간 봉인 유지
- Sim G 1차: Unity base NCORR +0.0307 → 우리 feature 4개 추가 시 +0.0277, paired 차이 −0.0030(t ≈ −4.5) → 현재 feature는 해침. 원인 후보는 커버리지 불균형(train 9.8%·validation 18.2%)과 "목록에 없음 = NaN" 처리
- 탐색적(사전 등록 아님, 가설용): 소형주(매출 하위 1/3)의 추적 bigram 언급 수가 많을수록 1y 수익 저조(IC −0.061, t −3.7). Lazy Prices(Cohen·Malloy·Nguyen, J. Finance 2020, 초록 기준) 계열

## 5. 12월 2일 runbook (BigQuery 한도 갱신 후, 약 730 GB)
1. `bq-bigrams` dispatch, basis=publication → data/external/bigram_counts_pub.csv.gz
2. 로컬: `python -m simulation.make_events --counts data/external/bigram_counts_pub.csv.gz --out simulation/events_by_rule_pub.json` (filing 기준 목록 5,584건을 정확히 재현함을 확인한 코드)
3. simulation/sim_e_bigrams.csv에 publication 기준 T1·대조군 bigram을 합집합으로 추가(basis 열)
4. `bq-assignees` dispatch, basis=publication → assignee_bigram_year.csv.gz, assignee_totals.csv.gz
5. `bq.yml` 월간 정기(자동, 2일)
6. Sim E 분석 스크립트 작성(아직 없음; 설계는 protocol.md Sim E: E1 건수 상위·E2 특화도 상위 basket, 대조군 C1 무작위·C2 총출원 십분위 매칭, 통과 E2−C2 2y t ≥ 2.5) → outputs/sim_e.md → 보고. 출원인→티커 매칭은 scripts/dealflow.py의 norm() + SEC company_tickers + 수동 alias
7. 통과 시 카드의 수혜주 선정에 arithmetic 입력으로 추가, 미달 시 arithmetic 회사 연결 완전 종료

## 6. 열린 일 (우선순위는 Caleb이 정함)
- Numerai 공학: feature set all(1,040)·전체 era·tree 수·target 앙상블을 하나씩 바꿔 validation NCORR/sharpe 비교(각 run 5-15분; `numerai.yml` 입력 feature_set). benchmark lgbm_jupiter_60는 같은 era에서 raw corr +0.0359·sharpe 1.83(우리 raw +0.0275·1.35, 상관 0.67)
- Sim G 2차: Unity 미국 universe 전체 10-K 본문으로 feature 재구축(전년 대비 문구 변경·신흥기술 어휘·분량; 10-K 있으면 0, 비미국만 NaN) → 같은 틀로 paired 검정. EDGAR 수집 수 주
- Paper portfolio: 자동, 첫 읽기 2027-05-06. 카드 retire 외 변경 금지
- 주간 카드 갱신(CLAUDE.md 절차)은 scheduled task로 안 걸려 있음 — 필요 시 요청
- Numerai 라운드 점수는 60일 target이라 2-3달 뒤 확정; stake는 라운드 몇 개 본 뒤 별도 결정

## 7. 파일 지도
- 규칙: CLAUDE.md, README.md, config/settings.yml(detector·tier·candidates), config/technologies.csv, config/themes.yml
- 수집: collectors/(patents_bq*.py: BigQuery), scripts/(collect_*.py: EDGAR·가격·재무; dealflow.py; theme_market.py)
- 탐지: detector/detector.py(Rule G·tier), candidates.py(bigram 후보), themes.py, oos_eval.py(Kalyani 세트 OOS)
- 시뮬레이션: simulation/protocol.md(사전 등록·판정 기록 원본), analyze.py(Sim A), sim_b.py, sim_b2.py, sim_d.py, make_events.py, retro/(복기 스크립트), sim_e_bigrams.csv
- Numerai: numerai/README.md, train_baseline.py(학습·진단·제출·Sim G), build_extra_features.py, extra_features.csv; scripts/numerai_signals_test.py(Sim F)
- 카드·포트폴리오: theses/(selected: adv_packaging·ntn_d2d·battery_next; watching: photonics_cpo·cfdna_mrd; linkage_2026-11-06.md), portfolio/
- 결과: outputs/(sim_*.md, retro_2026-11-09.md, numerai_*.md, oos_report_uspto_abs.md, validation_report.md, tiers.csv, dealflow.md)

## 8. 알려진 함정
- Actions 커밋은 항상 `git pull --rebase` 재시도 루프로; 로컬에서 push가 거부되면 봇 커밋과 충돌한 것이니 rebase 후 push
- 파일을 append 핸들로 열어 둔 채 rebase하면 쓰기가 사라짐 → 메모리에 모았다가 커밋 직전에 통째로 씀
- EDGAR 전문검색 4 req/s; Stooq는 러너에서 일일 한도로 끊김 → yfinance(auto_adjust) 우선; 가격은 조정 종가·$1 하한·+500% 상한
- Unity v6.0 스키마: `numerai_ticker`·`composite_figi`·`date`·`data_type` + feature + target 24종; `feature_country`는 문자열(범주 코드로 변환); 제출은 `numerai_ticker` key; `target` = jupiter_60; neutralizer parquet은 date가 문자열이라 batch로 스트리밍해 읽음
- outputs/는 스크립트·workflow가 만들고, 손으로 고치지 않음. 임계값 변경은 settings.yml + 커밋 메시지에 근거 + validation_report 전후 비교
- 보고 문체: 음슴체, 한 줄 불릿, 근거는 괄호, cite 태그·HTML 금지, 확인되지 않음/측정하지 않았음/다루지 않았음 구분, 검토 시 걸린 것만 보고
