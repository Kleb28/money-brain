# Rule selection (2026-11-04)

Positives: 16 validation technologies with ec_year > 2002. Controls: 0 valid of 18 (valid = max 10-K share 2005-19 / mean 2002-04 < 3.0).

Valid controls: 

Rejected controls (10-K share rose): none

Unchecked (no EDGAR data yet): ctl_ball_bearing, ctl_hydraulic_cylinder, ctl_heat_exchanger, ctl_centrifugal_pump, ctl_circuit_breaker, ctl_power_transformer, ctl_epoxy_resin, ctl_polyurethane_foam, ctl_carbon_nanotube, ctl_graphene, ctl_zeolite_catalyst, ctl_catheter, ctl_dental_implant, ctl_syringe, ctl_rna_interference, ctl_stem_cell, ctl_toothbrush, ctl_razor

score = lead_rate − fire_rate; fired = Rule G signal year ≤ 2019 on a control.

## arxiv

| min_count | growth | windows | n_pos | led | lead_rate | n_ctl | fired | fire_rate | score |
|---|---|---|---|---|---|---|---|---|---|
| 10 | +30% | 1 | 14 | 5 | 0.36 | 0 | 0 | 0.00 | +0.36 |
| 10 | +30% | 2 | 14 | 3 | 0.21 | 0 | 0 | 0.00 | +0.21 |
| 10 | +50% | 1 | 14 | 4 | 0.29 | 0 | 0 | 0.00 | +0.29 |
| 10 | +50% | 2 | 14 | 3 | 0.21 | 0 | 0 | 0.00 | +0.21 |
| 30 | +30% | 1 | 14 | 2 | 0.14 | 0 | 0 | 0.00 | +0.14 |
| 30 | +30% | 2 | 14 | 1 | 0.07 | 0 | 0 | 0.00 | +0.07 |
| 30 | +50% | 1 | 14 | 2 | 0.14 | 0 | 0 | 0.00 | +0.14 |
| 30 | +50% | 2 | 14 | 1 | 0.07 | 0 | 0 | 0.00 | +0.07 |

## clinicaltrials

| min_count | growth | windows | n_pos | led | lead_rate | n_ctl | fired | fire_rate | score |
|---|---|---|---|---|---|---|---|---|---|
| 10 | +30% | 1 | 2 | 0 | 0.00 | 0 | 0 | 0.00 | +0.00 |
| 10 | +30% | 2 | 2 | 0 | 0.00 | 0 | 0 | 0.00 | +0.00 |
| 10 | +50% | 1 | 2 | 0 | 0.00 | 0 | 0 | 0.00 | +0.00 |
| 10 | +50% | 2 | 2 | 0 | 0.00 | 0 | 0 | 0.00 | +0.00 |
| 30 | +30% | 1 | 2 | 0 | 0.00 | 0 | 0 | 0.00 | +0.00 |
| 30 | +30% | 2 | 2 | 0 | 0.00 | 0 | 0 | 0.00 | +0.00 |
| 30 | +50% | 1 | 2 | 0 | 0.00 | 0 | 0 | 0.00 | +0.00 |
| 30 | +50% | 2 | 2 | 0 | 0.00 | 0 | 0 | 0.00 | +0.00 |

## edgar_10k

| min_count | growth | windows | n_pos | led | lead_rate | n_ctl | fired | fire_rate | score |
|---|---|---|---|---|---|---|---|---|---|
| 10 | +30% | 1 | 16 | 6 | 0.38 | 0 | 0 | 0.00 | +0.38 |
| 10 | +30% | 2 | 16 | 3 | 0.19 | 0 | 0 | 0.00 | +0.19 |
| 10 | +50% | 1 | 16 | 3 | 0.19 | 0 | 0 | 0.00 | +0.19 |
| 10 | +50% | 2 | 16 | 1 | 0.06 | 0 | 0 | 0.00 | +0.06 |
| 30 | +30% | 1 | 16 | 1 | 0.06 | 0 | 0 | 0.00 | +0.06 |
| 30 | +30% | 2 | 16 | 1 | 0.06 | 0 | 0 | 0.00 | +0.06 |
| 30 | +50% | 1 | 16 | 0 | 0.00 | 0 | 0 | 0.00 | +0.00 |
| 30 | +50% | 2 | 16 | 0 | 0.00 | 0 | 0 | 0.00 | +0.00 |

## pubmed

| min_count | growth | windows | n_pos | led | lead_rate | n_ctl | fired | fire_rate | score |
|---|---|---|---|---|---|---|---|---|---|
| 10 | +30% | 1 | 16 | 5 | 0.31 | 0 | 0 | 0.00 | +0.31 |
| 10 | +30% | 2 | 16 | 3 | 0.19 | 0 | 0 | 0.00 | +0.19 |
| 10 | +50% | 1 | 16 | 4 | 0.25 | 0 | 0 | 0.00 | +0.25 |
| 10 | +50% | 2 | 16 | 2 | 0.12 | 0 | 0 | 0.00 | +0.12 |
| 30 | +30% | 1 | 16 | 3 | 0.19 | 0 | 0 | 0.00 | +0.19 |
| 30 | +30% | 2 | 16 | 1 | 0.06 | 0 | 0 | 0.00 | +0.06 |
| 30 | +50% | 1 | 16 | 2 | 0.12 | 0 | 0 | 0.00 | +0.12 |
| 30 | +50% | 2 | 16 | 0 | 0.00 | 0 | 0 | 0.00 | +0.00 |

## uspto

| min_count | growth | windows | n_pos | led | lead_rate | n_ctl | fired | fire_rate | score |
|---|---|---|---|---|---|---|---|---|---|
| 10 | +30% | 1 | 16 | 10 | 0.62 | 0 | 0 | 0.00 | +0.62 |
| 10 | +30% | 2 | 16 | 5 | 0.31 | 0 | 0 | 0.00 | +0.31 |
| 10 | +50% | 1 | 16 | 10 | 0.62 | 0 | 0 | 0.00 | +0.62 |
| 10 | +50% | 2 | 16 | 4 | 0.25 | 0 | 0 | 0.00 | +0.25 |
| 30 | +30% | 1 | 16 | 8 | 0.50 | 0 | 0 | 0.00 | +0.50 |
| 30 | +30% | 2 | 16 | 4 | 0.25 | 0 | 0 | 0.00 | +0.25 |
| 30 | +50% | 1 | 16 | 8 | 0.50 | 0 | 0 | 0.00 | +0.50 |
| 30 | +50% | 2 | 16 | 3 | 0.19 | 0 | 0 | 0.00 | +0.19 |

## Best score per source (arithmetic only — freezing a rule is a human decision)

