# Rule selection (2026-11-04)

Positives: 16 validation technologies with ec_year > 2002. Controls: 13 valid of 18 (valid = max 10-K share 2005-19 / mean 2002-04 < 3.0).

Valid controls: ctl_ball_bearing (0.98), ctl_hydraulic_cylinder (0.91), ctl_heat_exchanger (1.51), ctl_centrifugal_pump (1.1), ctl_circuit_breaker (2.15), ctl_power_transformer (2.13), ctl_epoxy_resin (1.2), ctl_polyurethane_foam (1.07), ctl_zeolite_catalyst (2.85), ctl_catheter (1.09), ctl_dental_implant (2.07), ctl_syringe (1.31), ctl_toothbrush (1.15)

Rejected controls (10-K share rose): ctl_carbon_nanotube (18.29), ctl_rna_interference (4.65), ctl_stem_cell (4.56), ctl_razor (4.88)

Unchecked (no EDGAR data yet): ctl_graphene

score = lead_rate − fire_rate; fired = Rule G signal year ≤ 2019 on a control.

## arxiv

| min_count | growth | windows | n_pos | led | lead_rate | n_ctl | fired | fire_rate | score |
|---|---|---|---|---|---|---|---|---|---|
| 10 | +30% | 1 | 14 | 5 | 0.36 | 10 | 3 | 0.30 | +0.06 |
| 10 | +30% | 2 | 14 | 3 | 0.21 | 10 | 2 | 0.20 | +0.01 |
| 10 | +50% | 1 | 14 | 4 | 0.29 | 10 | 2 | 0.20 | +0.09 |
| 10 | +50% | 2 | 14 | 3 | 0.21 | 10 | 1 | 0.10 | +0.11 |
| 30 | +30% | 1 | 14 | 2 | 0.14 | 10 | 1 | 0.10 | +0.04 |
| 30 | +30% | 2 | 14 | 1 | 0.07 | 10 | 0 | 0.00 | +0.07 |
| 30 | +50% | 1 | 14 | 2 | 0.14 | 10 | 0 | 0.00 | +0.14 |
| 30 | +50% | 2 | 14 | 1 | 0.07 | 10 | 0 | 0.00 | +0.07 |

## clinicaltrials

| min_count | growth | windows | n_pos | led | lead_rate | n_ctl | fired | fire_rate | score |
|---|---|---|---|---|---|---|---|---|---|
| 10 | +30% | 1 | 2 | 0 | 0.00 | 3 | 2 | 0.67 | -0.67 |
| 10 | +30% | 2 | 2 | 0 | 0.00 | 3 | 2 | 0.67 | -0.67 |
| 10 | +50% | 1 | 2 | 0 | 0.00 | 3 | 2 | 0.67 | -0.67 |
| 10 | +50% | 2 | 2 | 0 | 0.00 | 3 | 0 | 0.00 | +0.00 |
| 30 | +30% | 1 | 2 | 0 | 0.00 | 3 | 2 | 0.67 | -0.67 |
| 30 | +30% | 2 | 2 | 0 | 0.00 | 3 | 2 | 0.67 | -0.67 |
| 30 | +50% | 1 | 2 | 0 | 0.00 | 3 | 2 | 0.67 | -0.67 |
| 30 | +50% | 2 | 2 | 0 | 0.00 | 3 | 0 | 0.00 | +0.00 |

## edgar_10k

| min_count | growth | windows | n_pos | led | lead_rate | n_ctl | fired | fire_rate | score |
|---|---|---|---|---|---|---|---|---|---|
| 10 | +30% | 1 | 16 | 6 | 0.38 | 13 | 8 | 0.62 | -0.24 |
| 10 | +30% | 2 | 16 | 3 | 0.19 | 13 | 5 | 0.38 | -0.20 |
| 10 | +50% | 1 | 16 | 3 | 0.19 | 13 | 7 | 0.54 | -0.35 |
| 10 | +50% | 2 | 16 | 1 | 0.06 | 13 | 1 | 0.08 | -0.01 |
| 30 | +30% | 1 | 16 | 1 | 0.06 | 13 | 1 | 0.08 | -0.01 |
| 30 | +30% | 2 | 16 | 1 | 0.06 | 13 | 1 | 0.08 | -0.01 |
| 30 | +50% | 1 | 16 | 0 | 0.00 | 13 | 1 | 0.08 | -0.08 |
| 30 | +50% | 2 | 16 | 0 | 0.00 | 13 | 0 | 0.00 | +0.00 |

## pubmed

| min_count | growth | windows | n_pos | led | lead_rate | n_ctl | fired | fire_rate | score |
|---|---|---|---|---|---|---|---|---|---|
| 10 | +30% | 1 | 16 | 5 | 0.31 | 13 | 8 | 0.62 | -0.30 |
| 10 | +30% | 2 | 16 | 3 | 0.19 | 13 | 4 | 0.31 | -0.12 |
| 10 | +50% | 1 | 16 | 4 | 0.25 | 13 | 5 | 0.38 | -0.13 |
| 10 | +50% | 2 | 16 | 2 | 0.12 | 13 | 1 | 0.08 | +0.05 |
| 30 | +30% | 1 | 16 | 3 | 0.19 | 13 | 6 | 0.46 | -0.27 |
| 30 | +30% | 2 | 16 | 1 | 0.06 | 13 | 4 | 0.31 | -0.25 |
| 30 | +50% | 1 | 16 | 2 | 0.12 | 13 | 3 | 0.23 | -0.11 |
| 30 | +50% | 2 | 16 | 0 | 0.00 | 13 | 1 | 0.08 | -0.08 |

## uspto

| min_count | growth | windows | n_pos | led | lead_rate | n_ctl | fired | fire_rate | score |
|---|---|---|---|---|---|---|---|---|---|
| 10 | +30% | 1 | 16 | 10 | 0.62 | 13 | 8 | 0.62 | +0.01 |
| 10 | +30% | 2 | 16 | 5 | 0.31 | 13 | 5 | 0.38 | -0.07 |
| 10 | +50% | 1 | 16 | 10 | 0.62 | 13 | 4 | 0.31 | +0.32 |
| 10 | +50% | 2 | 16 | 4 | 0.25 | 13 | 3 | 0.23 | +0.02 |
| 30 | +30% | 1 | 16 | 8 | 0.50 | 13 | 7 | 0.54 | -0.04 |
| 30 | +30% | 2 | 16 | 4 | 0.25 | 13 | 3 | 0.23 | +0.02 |
| 30 | +50% | 1 | 16 | 8 | 0.50 | 13 | 3 | 0.23 | +0.27 |
| 30 | +50% | 2 | 16 | 3 | 0.19 | 13 | 1 | 0.08 | +0.11 |

## Best score per source (arithmetic only — freezing a rule is a human decision)

- arxiv: min_count 30, +50%, 1 window(s) → lead 0.14, fire 0.00, score +0.14
- clinicaltrials: min_count 10, +50%, 2 window(s) → lead 0.00, fire 0.00, score +0.00
- edgar_10k: min_count 30, +50%, 2 window(s) → lead 0.00, fire 0.00, score +0.00
- pubmed: min_count 10, +50%, 2 window(s) → lead 0.12, fire 0.08, score +0.05
- uspto: min_count 10, +50%, 1 window(s) → lead 0.62, fire 0.31, score +0.32
