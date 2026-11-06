---
id: adv_packaging
name: Advanced packaging / backside power / HBM
arm: tech
tier: T1
status: selected
created: 2026-11-06
updated: 2026-11-06
---

## Structural driver
AI 가속기 성능이 트랜지스터 미세화보다 패키징(2.5D/3D 적층, hybrid bonding, HBM 스택, backside power delivery)에서 나오는 구간에 들어감. 특허 신호가 2021-23년에 집중됨 (backside power 2021, hybrid bonding·HBM·direct bond 2023).

## Bottleneck
hybrid bonding 장비·공정 수율, HBM 적층 수율과 검사(probe card·계측), OSAT의 2.5D 생산능력. 투자 가능한 층은 파운드리 밖의 OSAT·장비·검사·소재임.

## Beneficiaries (US-listed only)
| ticker | company | exposure (% revenue, source) | note |
|---|---|---|---|
| AMKR | Amkor Technology | advanced products 83% of FY2025 net sales ($5.56B/$6.71B; marketchameleon 2026-02-10, 10-K 기반) | AI 비중은 이보다 훨씬 낮음(확인되지 않음); 2026 capex $2.5-3.0B |
| MU | Micron | HBM 비중 확인되지 않음 | Roundhill Memory ETF(DRAM) 2026-04 출시, AUM ~$15B → attention flag |
| FORM | FormFactor | HBM probe card 비중 확인되지 않음 | 10-K "advanced packaging" 언급 8건 (2024-26) |
| ONTO | Onto Innovation | 확인되지 않음 | advanced packaging 검사·계측 |
- fail: KLIC(exposure 미입증, hybrid bonding은 BESI 선도), INTC(기술 보유가 매출로 연결 안 됨) — theses/linkage_2026-11-06.md

## Time horizon
2-4년. Breakthrough 지표 = 10-K에서 "hybrid bonding"·"backside power delivery" 언급이 연 10건 이상으로 늘고 OSAT 실적 발표에서 advanced packaging이 별도 성장 축으로 언급되는 시점.

## Evidence (deterministic, from outputs/)
- patent signal year (Rule G, uspto_abs): backside power 2021 (2023년 110건/16 출원인), power rail 2022 (156/33), hybrid bonding 2023 (95/34), direct bond 2023 (89/25), bandwidth memory 2023 (36/19), computational storage 2023 (42/10)
- EDGAR 10-K latest count / signal year: "advanced packaging" 46 (2026, FY2025) ← 40 (2023); "high bandwidth memory" 21 ← 6; "chiplet" 13 ← 8; "hybrid bonding" 3; "backside power delivery" 1 → Tier T1 (테마 표현 기준 50 근처, 세부 표현은 T0)
- clinical trials (bio only): 해당 없음
- patents (when USPTO is live): 위 bigram 합계 2023년 출원 767건 (candidates_themes.md)

## Attention (Ben-David et al. 2023 criteria)
- thematic ETF exists? (ticker, inception): advanced packaging 전용 ETF 확인되지 않음 (etfcentral 2026-06-03 기준 없음); 인접 테마 Roundhill Memory ETF(DRAM, 2026-04) ~$15B → HBM 쪽은 관심 정점 가능성
- trailing-12m return of candidate basket: 측정하지 않았음
- news volume / Google Trends: 다루지 않았음

## Falsification
12개월 내 (1) hybrid bonding·backside power 10-K 언급이 늘지 않고 (2) AMKR advanced products 매출이 역성장하면 retire. HBM 쪽은 DRAM ETF 자금 유입이 꺾이는 시점이 상단 경고.

## Review log
- 2026-11-06: status candidate → selected (Caleb, 2026-11-06); created from candidates_themes.md (2026-11-06 run) + theme_market.md; linkage in theses/linkage_2026-11-06.md
