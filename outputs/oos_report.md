# Out-of-sample evaluation — techdiffusion.net technology set

USPTO series complete for 180 / 1286 technologies; 10-K series for 480; job-posting series for 1147.

Rule G: share[y] / share[y−2] ≥ 1+g, raw count ≥ min_count, for N consecutive windows; first fire counted only if in 2004–2017.

## A. Hiring timing (Burning Glass postings 2010–2019; outcome independent of patents)
Positives: posting share < 10% of its 2010–19 max in 2010 and ≥ 1,000 postings → emergence year = first year ≥ 10% of max (n = 5). Controls: share already ≥ 10% of max in 2010 and never +50% above the 2010 level (n = 33).

| rule | n pos | eligible (peak ≥ min_count) | signal | led | same | lagged | lead rate (all / eligible) | lead 1–5y | median lead | n ctl (eligible) | fire rate (all / eligible) | lead − fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 10 / +30% / 1w | 5 | 4 | 4 | 3 | 0 | 1 | 0.60 / 0.75 | 0.20 | 6 | 33 (24) | 0.61 / 0.83 | -0.01 |
| 10 / +30% / 2w | 5 | 4 | 2 | 1 | 0 | 1 | 0.20 / 0.25 | 0.20 | 5 | 33 (24) | 0.33 / 0.46 | -0.13 |
| 10 / +50% / 1w | 5 | 4 | 4 | 3 | 0 | 1 | 0.60 / 0.75 | 0.40 | 5 | 33 (24) | 0.48 / 0.67 | 0.12 |
| 10 / +50% / 2w | 5 | 4 | 2 | 1 | 0 | 1 | 0.20 / 0.25 | 0.20 | 1 | 33 (24) | 0.09 / 0.12 | 0.11 |
| 30 / +30% / 1w | 5 | 2 | 2 | 1 | 0 | 1 | 0.20 / 0.50 | 0.20 | 2 | 33 (12) | 0.21 / 0.58 | -0.01 |
| 30 / +30% / 2w | 5 | 2 | 1 | 1 | 0 | 0 | 0.20 / 0.50 | 0.20 | 1 | 33 (12) | 0.09 / 0.25 | 0.11 |
| 30 / +50% / 1w | 5 | 2 | 2 | 1 | 0 | 1 | 0.20 / 0.50 | 0.20 | 2 | 33 (12) | 0.12 / 0.33 | 0.08 |
| 30 / +50% / 2w | 5 | 2 | 1 | 1 | 0 | 0 | 0.20 / 0.50 | 0.20 | 1 | 33 (12) | 0.00 / 0.00 | 0.20 |

Positives and their emergence years: Binder material 2011, Augmented reality 2012, Autonomous system Internet 2012, Adenoassociated virus 2014, Contact region 2017

## B. Cross-section, signal computed from 2002–2009 counts only
Outcome = earnings-call class over 2002–19 (Kalyani et al.: disruptive > 100 transcripts, non-disruptive < 10). The transcript total includes years before 2009, so this measures association, not strict prediction. Quartiles are by total patents mentioning the technology (size control).

### as of 2009
| rule | fire rate disruptive (n) | fire rate intermediate (n) | fire rate non_disruptive (n) | lift disruptive/non | Q1 disr/non | Q2 disr/non | Q3 disr/non | Q4 disr/non |
|---|---|---|---|---|---|---|---|---|
| 10 / +30% / 1w | 0.53 (30) | 0.41 (61) | 0.10 (89) | 5.27 | 0.29/0.08 (7/26) | 1.00/0.04 (3/27) | 0.67/0.09 (6/23) | 0.50/0.31 (14/13) |
| 10 / +30% / 2w | 0.23 (30) | 0.16 (61) | 0.04 (89) | 5.19 | 0.14/0.00 (7/26) | 0.67/0.00 (3/27) | 0.17/0.04 (6/23) | 0.21/0.23 (14/13) |
| 10 / +50% / 1w | 0.40 (30) | 0.30 (61) | 0.04 (89) | 8.90 | 0.29/0.00 (7/26) | 1.00/0.04 (3/27) | 0.67/0.04 (6/23) | 0.21/0.15 (14/13) |
| 10 / +50% / 2w | 0.13 (30) | 0.07 (61) | 0.01 (89) | 11.87 | 0.14/0.00 (7/26) | 0.33/0.00 (3/27) | 0.00/0.04 (6/23) | 0.14/0.00 (14/13) |
| 30 / +30% / 1w | 0.23 (30) | 0.15 (61) | 0.02 (89) | 10.38 | 0.00/0.00 (7/26) | 0.33/0.00 (3/27) | 0.00/0.04 (6/23) | 0.43/0.08 (14/13) |
| 30 / +30% / 2w | 0.07 (30) | 0.05 (61) | 0.02 (89) | 2.97 | 0.00/0.00 (7/26) | 0.00/0.00 (3/27) | 0.00/0.04 (6/23) | 0.14/0.08 (14/13) |
| 30 / +50% / 1w | 0.10 (30) | 0.10 (61) | 0.01 (89) | 8.90 | 0.00/0.00 (7/26) | 0.33/0.00 (3/27) | 0.00/0.04 (6/23) | 0.14/0.00 (14/13) |
| 30 / +50% / 2w | 0.07 (30) | 0.02 (61) | 0.01 (89) | 5.93 | 0.00/0.00 (7/26) | 0.00/0.00 (3/27) | 0.00/0.04 (6/23) | 0.14/0.00 (14/13) |

### as of 2019 (all years)
| rule | fire rate disruptive (n) | fire rate intermediate (n) | fire rate non_disruptive (n) | lift disruptive/non | Q1 disr/non | Q2 disr/non | Q3 disr/non | Q4 disr/non |
|---|---|---|---|---|---|---|---|---|
| 10 / +30% / 1w | 0.77 (30) | 0.59 (61) | 0.20 (89) | 3.79 | 0.43/0.19 (7/26) | 1.00/0.19 (3/27) | 1.00/0.13 (6/23) | 0.79/0.38 (14/13) |
| 10 / +30% / 2w | 0.43 (30) | 0.31 (61) | 0.09 (89) | 4.82 | 0.29/0.08 (7/26) | 1.00/0.04 (3/27) | 0.50/0.04 (6/23) | 0.36/0.31 (14/13) |
| 10 / +50% / 1w | 0.63 (30) | 0.48 (61) | 0.19 (89) | 3.32 | 0.43/0.15 (7/26) | 1.00/0.19 (3/27) | 1.00/0.13 (6/23) | 0.50/0.38 (14/13) |
| 10 / +50% / 2w | 0.30 (30) | 0.15 (61) | 0.04 (89) | 6.67 | 0.29/0.08 (7/26) | 0.67/0.04 (3/27) | 0.50/0.04 (6/23) | 0.14/0.00 (14/13) |
| 30 / +30% / 1w | 0.37 (30) | 0.26 (61) | 0.04 (89) | 8.16 | 0.00/0.04 (7/26) | 0.33/0.04 (3/27) | 0.33/0.04 (6/23) | 0.57/0.08 (14/13) |
| 30 / +30% / 2w | 0.17 (30) | 0.10 (61) | 0.02 (89) | 7.42 | 0.00/0.00 (7/26) | 0.00/0.00 (3/27) | 0.33/0.04 (6/23) | 0.21/0.08 (14/13) |
| 30 / +50% / 1w | 0.27 (30) | 0.16 (61) | 0.04 (89) | 5.93 | 0.00/0.04 (7/26) | 0.33/0.04 (3/27) | 0.33/0.04 (6/23) | 0.36/0.08 (14/13) |
| 30 / +50% / 2w | 0.13 (30) | 0.03 (61) | 0.01 (89) | 11.87 | 0.00/0.00 (7/26) | 0.00/0.00 (3/27) | 0.33/0.04 (6/23) | 0.14/0.00 (14/13) |

## C. 10-K timing (EDGAR full-text, 2002–2019; 10-K lags earnings calls by ~4 years on the 29-technology set, so leads here overstate leads vs. the market)
Positives: 10-K share < 10% of max in 2002, peak ≥ 30 filings → emergence = first year ≥ 10% of max (n = 3). Controls: flat 10-K share (max 2005–19 / mean 2002–04 < 3; n = 24) and never ≥ 10 filings in any year (n = 109).

| rule | n pos | eligible | signal | led | same | lagged | lead rate (all / eligible) | lead 1–5y | median lead | fire rate flat (all / eligible) | fire rate never (all / eligible) | lead − fire(flat) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 10 / +30% / 1w | 3 | 3 | 3 | 2 | 0 | 1 | 0.67 / 0.67 | 0.33 | 6.00 | 0.71 / 0.81 (n=21) | 0.27 / 0.91 (n=32) | -0.04 |
| 10 / +30% / 2w | 3 | 3 | 3 | 2 | 0 | 1 | 0.67 / 0.67 | 0.33 | 4.00 | 0.29 / 0.33 (n=21) | 0.15 / 0.50 (n=32) | 0.37 |
| 10 / +50% / 1w | 3 | 3 | 3 | 2 | 0 | 1 | 0.67 / 0.67 | 0.33 | 5.50 | 0.50 / 0.57 (n=21) | 0.25 / 0.84 (n=32) | 0.17 |
| 10 / +50% / 2w | 3 | 3 | 3 | 2 | 0 | 1 | 0.67 / 0.67 | 0.67 | 2.00 | 0.17 / 0.19 (n=21) | 0.09 / 0.31 (n=32) | 0.50 |
| 30 / +30% / 1w | 3 | 2 | 2 | 2 | 0 | 0 | 0.67 / 1.00 | 0.67 | 3.00 | 0.38 / 0.56 (n=16) | 0.07 / 1.00 (n=8) | 0.29 |
| 30 / +30% / 2w | 3 | 2 | 2 | 2 | 0 | 0 | 0.67 / 1.00 | 0.67 | 2.00 | 0.08 / 0.12 (n=16) | 0.04 / 0.50 (n=8) | 0.58 |
| 30 / +50% / 1w | 3 | 2 | 2 | 2 | 0 | 0 | 0.67 / 1.00 | 0.67 | 3.00 | 0.21 / 0.31 (n=16) | 0.06 / 0.75 (n=8) | 0.46 |
| 30 / +50% / 2w | 3 | 2 | 2 | 2 | 0 | 0 | 0.67 / 1.00 | 0.67 | 2.00 | 0.04 / 0.06 (n=16) | 0.02 / 0.25 (n=8) | 0.62 |
