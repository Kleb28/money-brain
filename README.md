# money-brain

투자 thesis 자동 탐색 파이프라인. 문헌·공시·임상·특허 건수의 연도별 시계열에서 "근거는 쌓이는데 시장은 아직 말하지 않는" 기술을 찾는다.

## 설계 근거
- 후보 생성·확산 단계: Kalyani·Bloom·Carvalho·Hassan·Lerner·Tahoun, *The Diffusion of New Technologies*, QJE 2025 (특허 → 실적 콜 → 채용공고)
- 근거 지표: Rotolo·Hicks·Martin, Research Policy 2015; Carley et al., Scientometrics 2018 (emergence 속성)
- 늦었음 신호: Ben-David·Franzoni·Kim·Moussawi, RFS 2023 (테마 ETF는 관심 정점에 출시되고 5년간 위험조정 −30%)
- 10-K 문구 지연 반응: Cohen·Malloy·Nguyen, *Lazy Prices*, JF 2020
- LLM 역할 제한: Si·Yang·Hashimoto 2024 (LLM 자기평가는 사람과 53% 일치) → 점수는 전부 산술, LLM은 연결 판정·카드 작성만

## 구조
```
config/technologies.csv   추적 기술 목록 (id, arm, status, ec_year, keywords)
config/settings.yml       연도 범위·소스별 설정·탐지 임계값
collectors/               소스별 수집기 — 연도별 건수만 받음 (pubmed, arxiv, edgar, clinicaltrials, uspto)
data/counts.csv           technology_id, source, year, count, collected_at  (__all = 분모)
data/validation_set.csv   Kalyani 29개 기술·돌파 연도·키워드 (검증 라벨)
detector/detector.py      정규화 → 성장률 규칙 → Tier → 검증 리포트
outputs/                  shares.csv, signals.csv, tiers.csv, validation_report.md (Actions가 커밋)
theses/                   thesis 카드 (md, _template.md 참고)
```

## 탐지 규칙 (settings.yml)
- share = count / 그 소스의 해당 연도 전체 문서 수 × 1e6
- Rule G: count ≥ min_count(30) 이고 2년 성장률 ≥ +50%가 2회 연속인 첫 해 — 사전 등록 규칙 그대로 유지. 1,286개 세트 out-of-sample 테스트에서 가장 보수적이면서 네 테스트 모두 양의 구분력을 보임 (validation_notes addendum 4)
- Rule K: 2002~2019 최대 share의 10%에 처음 도달한 해 (Kalyani 방식, 비교용)
- Tier: 신호 = settings.detector.signal_sources(현재 uspto_abs, 특허 제목+초록)의 Rule G. T0 신호만(10-K 언급 거의 없음) / T1 신호 + 10-K 언급 낮음 (후보) / T2 10-K 언급 높음 (늦음) / T- 신호 없음 — Tier 임계값(edgar_low_max·high_min)은 잠정

## 실행
- Actions: 매주 월요일 자동, 또는 Actions 탭 → collect-and-detect → Run workflow (sources 입력으로 일부만 실행 가능)
- 로컬 (터미널, 리포 루트에서):
  ```
  pip install -r requirements.txt
  python -m collectors.run_all pubmed        # 소스 하나만
  python -m detector.detector
  ```

## 필요한 설정 (Settings → Secrets and variables → Actions)
| 종류 | 이름 | 값 |
|---|---|---|
| Secret | NCBI_API_KEY | NCBI 계정에서 발급 |
| Secret | USPTO_API_KEY | data.uspto.gov 발급 (없으면 uspto 수집기는 자동 건너뜀) |
| Variable | EDGAR_USER_AGENT | `money-brain research <연락 이메일>` — SEC 요구사항, 없으면 403 가능 |
| Variable | USPTO_API_BASE | (선택) 엔드포인트가 바뀐 경우만 |
| Secret | GCP_SA_KEY | GCP service account JSON 키 전체 (BigQuery Job User 권한) — patents-bq 워크플로용 |
| Variable | GCP_PROJECT_ID | 그 service account가 속한 GCP 프로젝트 ID |
| Variable | BQ_MAX_GB | (선택) BigQuery 1회 스캔 상한 GB, 기본 400 (무료 tier 월 1 TB) |

## 운영 주기
- 수집 주 1회 (Actions) → 탐지·Tier 갱신 자동
- thesis 카드 갱신 주 1회 (Claude 예약 작업: tiers.csv의 T1 후보에 찬반 판정 → theses/ 갱신)
- thesis 3개 선정 분기 1회 (사람이 결정)

## 알려진 한계
- EDGAR 전문검색은 2001년 이후만 있고 건수 10,000에서 상한 (relation=gte)
- 10-K 분모는 EDGAR 분기 마스터 인덱스(form.gz)의 정확한 "10-K" 행 수; EFTS 총계는 10,000에서 상한이라 분모로 못 씀
- uspto는 ODP 검색 API(api.uspto.gov)로 제목(inventionTitle) 구절만 검색 가능 — 초록은 노출되지 않음; 출원 연도 기준이라 최근 2년은 미공개분만큼 과소 집계. 제목만으로는 연간 peak count 중앙값 9건으로 너무 희소함 (validation_notes addendum 3) → uspto_abs(제목+초록, Google Patents 공개 데이터셋/BigQuery, collectors/patents_bq.py, Actions: patents-bq)로 대체 검증 중
- 키워드 OR 검색이라 동음이의 잡음 포함 — Kalyani는 사람 감사로 80% 정확도 기준을 썼고 여기서는 아직 안 함

## Paper portfolio (model-ETF 실험)
- `portfolio/rules.md`: 2026-11-06 사전 등록 — treatment = selected thesis 3개 basket(동일 비중, basket당 1/3), control = 관심 정점 테마 ETF(FOTO·DRAM)·SPY·SMH·QQQ, 24개월, 종목 변경은 카드 retire로만
- `portfolio/holdings.csv`: 종목·비중; `portfolio/track.py`: Stooq 종가 → `data/prices.csv`, `outputs/portfolio.md` (매주 토요일 04:00 UTC, Actions `portfolio`)
