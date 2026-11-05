# Out-of-sample evaluation — techdiffusion.net technology set

USPTO series complete for 1286 / 1286 technologies; 10-K series for 1286; job-posting series for 1147.

Rule G: share[y] / share[y−2] ≥ 1+g, raw count ≥ min_count, for N consecutive windows; first fire counted only if in 2004–2017.

## A. Hiring timing (Burning Glass postings 2010–2019; outcome independent of patents)
Positives: posting share < 10% of its 2010–19 max in 2010 and ≥ 1,000 postings → emergence year = first year ≥ 10% of max (n = 25). Controls: share already ≥ 10% of max in 2010 and never +50% above the 2010 level (n = 286).

| rule | n pos | eligible (peak ≥ min_count) | signal | led | same | lagged | lead rate (all / eligible) | lead 1–5y | median lead | n ctl (eligible) | fire rate (all / eligible) | lead − fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 10 / +30% / 1w | 25 | 20 | 20 | 18 | 0 | 2 | 0.72 / 0.90 | 0.28 | 7.00 | 286 (213) | 0.63 / 0.85 | 0.09 |
| 10 / +30% / 2w | 25 | 20 | 12 | 7 | 1 | 4 | 0.28 / 0.35 | 0.16 | 5 | 286 (213) | 0.36 / 0.49 | -0.08 |
| 10 / +50% / 1w | 25 | 20 | 18 | 16 | 0 | 2 | 0.64 / 0.80 | 0.32 | 6.00 | 286 (213) | 0.53 / 0.72 | 0.11 |
| 10 / +50% / 2w | 25 | 20 | 8 | 6 | 1 | 1 | 0.24 / 0.30 | 0.12 | 4.50 | 286 (213) | 0.18 / 0.24 | 0.06 |
| 30 / +30% / 1w | 25 | 9 | 8 | 4 | 2 | 2 | 0.16 / 0.44 | 0.12 | 3.00 | 286 (120) | 0.29 / 0.70 | -0.13 |
| 30 / +30% / 2w | 25 | 9 | 5 | 2 | 1 | 2 | 0.08 / 0.22 | 0.08 | 1.00 | 286 (120) | 0.15 / 0.35 | -0.07 |
| 30 / +50% / 1w | 25 | 9 | 8 | 3 | 2 | 3 | 0.12 / 0.33 | 0.12 | 2 | 286 (120) | 0.21 / 0.51 | -0.09 |
| 30 / +50% / 2w | 25 | 9 | 5 | 2 | 1 | 2 | 0.08 / 0.22 | 0.08 | 1.00 | 286 (120) | 0.06 / 0.15 | 0.02 |

Positives and their emergence years: Binder material 2011, Default effect 2011, Highdensity polyethylene 2011, Google Search 2011, Smartphone 2011, Touchpad 2011, Augmented reality 2012, Autonomous system Internet 2012, Tree data structure 2012, PC game 2012, Machine learning 2012, Pager 2012, Push technology 2012, SMS 2012, Softwaredefined radio 2013, Adenoassociated virus 2014, Dataspaces 2014, Notification LED 2014, Power inverter 2014, Harvard architecture 2014, Selfdriving car 2015, Artificial neural network 2016, Antireflective coating 2016, Contact region 2017, Superoxide dismutase 2018

## B. Cross-section, signal computed from 2002–2009 counts only
Outcome = earnings-call class over 2002–19 (Kalyani et al.: disruptive > 100 transcripts, non-disruptive < 10). The transcript total includes years before 2009, so this measures association, not strict prediction. Quartiles are by total patents mentioning the technology (size control).

### as of 2009
| rule | fire rate disruptive (n) | fire rate intermediate (n) | fire rate non_disruptive (n) | lift disruptive/non | Q1 disr/non | Q2 disr/non | Q3 disr/non | Q4 disr/non |
|---|---|---|---|---|---|---|---|---|
| 10 / +30% / 1w | 0.60 (275) | 0.46 (414) | 0.14 (597) | 4.45 | 0.43/0.08 (51/182) | 0.73/0.09 (48/175) | 0.75/0.19 (60/147) | 0.55/0.26 (116/93) |
| 10 / +30% / 2w | 0.27 (275) | 0.18 (414) | 0.06 (597) | 4.72 | 0.16/0.03 (51/182) | 0.35/0.03 (48/175) | 0.25/0.10 (60/147) | 0.29/0.11 (116/93) |
| 10 / +50% / 1w | 0.47 (275) | 0.37 (414) | 0.11 (597) | 4.41 | 0.43/0.06 (51/182) | 0.62/0.08 (48/175) | 0.65/0.16 (60/147) | 0.34/0.16 (116/93) |
| 10 / +50% / 2w | 0.16 (275) | 0.10 (414) | 0.03 (597) | 5.31 | 0.12/0.02 (51/182) | 0.23/0.02 (48/175) | 0.15/0.05 (60/147) | 0.16/0.04 (116/93) |
| 30 / +30% / 1w | 0.29 (275) | 0.15 (414) | 0.03 (597) | 10.09 | 0.06/0.02 (51/182) | 0.15/0.02 (48/175) | 0.32/0.05 (60/147) | 0.43/0.04 (116/93) |
| 30 / +30% / 2w | 0.11 (275) | 0.06 (414) | 0.01 (597) | 9.30 | 0.00/0.00 (51/182) | 0.06/0.01 (48/175) | 0.12/0.02 (60/147) | 0.17/0.03 (116/93) |
| 30 / +50% / 1w | 0.18 (275) | 0.11 (414) | 0.02 (597) | 8.35 | 0.04/0.02 (51/182) | 0.12/0.01 (48/175) | 0.22/0.04 (60/147) | 0.25/0.02 (116/93) |
| 30 / +50% / 2w | 0.05 (275) | 0.03 (414) | 0.01 (597) | 8.14 | 0.00/0.00 (51/182) | 0.04/0.00 (48/175) | 0.03/0.01 (60/147) | 0.09/0.02 (116/93) |

### as of 2019 (all years)
| rule | fire rate disruptive (n) | fire rate intermediate (n) | fire rate non_disruptive (n) | lift disruptive/non | Q1 disr/non | Q2 disr/non | Q3 disr/non | Q4 disr/non |
|---|---|---|---|---|---|---|---|---|
| 10 / +30% / 1w | 0.75 (275) | 0.62 (414) | 0.24 (597) | 3.19 | 0.59/0.17 (51/182) | 0.79/0.20 (48/175) | 0.88/0.29 (60/147) | 0.74/0.35 (116/93) |
| 10 / +30% / 2w | 0.46 (275) | 0.32 (414) | 0.10 (597) | 4.41 | 0.47/0.07 (51/182) | 0.60/0.06 (48/175) | 0.47/0.12 (60/147) | 0.39/0.22 (116/93) |
| 10 / +50% / 1w | 0.63 (275) | 0.56 (414) | 0.22 (597) | 2.89 | 0.57/0.16 (51/182) | 0.75/0.18 (48/175) | 0.77/0.26 (60/147) | 0.53/0.32 (116/93) |
| 10 / +50% / 2w | 0.30 (275) | 0.20 (414) | 0.06 (597) | 5.15 | 0.29/0.06 (51/182) | 0.46/0.03 (48/175) | 0.28/0.07 (60/147) | 0.25/0.09 (116/93) |
| 30 / +30% / 1w | 0.45 (275) | 0.25 (414) | 0.05 (597) | 8.75 | 0.18/0.04 (51/182) | 0.35/0.05 (48/175) | 0.52/0.07 (60/147) | 0.59/0.06 (116/93) |
| 30 / +30% / 2w | 0.23 (275) | 0.11 (414) | 0.02 (597) | 10.35 | 0.14/0.01 (51/182) | 0.17/0.01 (48/175) | 0.28/0.03 (60/147) | 0.26/0.04 (116/93) |
| 30 / +50% / 1w | 0.34 (275) | 0.19 (414) | 0.05 (597) | 7.29 | 0.16/0.04 (51/182) | 0.33/0.04 (48/175) | 0.38/0.05 (60/147) | 0.41/0.06 (116/93) |
| 30 / +50% / 2w | 0.15 (275) | 0.06 (414) | 0.01 (597) | 14.47 | 0.10/0.01 (51/182) | 0.12/0.00 (48/175) | 0.17/0.01 (60/147) | 0.16/0.02 (116/93) |

## C. 10-K timing (EDGAR full-text, 2002–2019; 10-K lags earnings calls by ~4 years on the 29-technology set, so leads here overstate leads vs. the market)
Positives: 10-K share < 10% of max in 2002, peak ≥ 30 filings → emergence = first year ≥ 10% of max (n = 26). Controls: flat 10-K share (max 2005–19 / mean 2002–04 < 3; n = 205) and never ≥ 10 filings in any year (n = 736).

| rule | n pos | eligible | signal | led | same | lagged | lead rate (all / eligible) | lead 1–5y | median lead | fire rate flat (all / eligible) | fire rate never (all / eligible) | lead − fire(flat) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 10 / +30% / 1w | 26 | 22 | 22 | 12 | 2 | 8 | 0.46 / 0.55 | 0.38 | 3.00 | 0.67 / 0.81 (n=171) | 0.30 / 0.88 (n=249) | -0.21 |
| 10 / +30% / 2w | 26 | 22 | 19 | 6 | 3 | 10 | 0.23 / 0.27 | 0.15 | 2.50 | 0.33 / 0.40 (n=171) | 0.14 / 0.42 (n=249) | -0.10 |
| 10 / +50% / 1w | 26 | 22 | 22 | 12 | 2 | 8 | 0.46 / 0.55 | 0.38 | 2.50 | 0.53 / 0.63 (n=171) | 0.28 / 0.82 (n=249) | -0.07 |
| 10 / +50% / 2w | 26 | 22 | 15 | 5 | 2 | 8 | 0.19 / 0.23 | 0.15 | 2 | 0.22 / 0.26 (n=171) | 0.09 / 0.26 (n=249) | -0.03 |
| 30 / +30% / 1w | 26 | 19 | 18 | 8 | 2 | 8 | 0.31 / 0.42 | 0.27 | 3.00 | 0.40 / 0.68 (n=121) | 0.08 / 0.81 (n=75) | -0.09 |
| 30 / +30% / 2w | 26 | 19 | 15 | 3 | 1 | 11 | 0.12 / 0.16 | 0.12 | 2 | 0.14 / 0.24 (n=121) | 0.04 / 0.36 (n=75) | -0.03 |
| 30 / +50% / 1w | 26 | 19 | 18 | 8 | 2 | 8 | 0.31 / 0.42 | 0.27 | 3.00 | 0.26 / 0.45 (n=121) | 0.07 / 0.68 (n=75) | 0.04 |
| 30 / +50% / 2w | 26 | 19 | 13 | 3 | 1 | 9 | 0.12 / 0.16 | 0.12 | 2 | 0.07 / 0.12 (n=121) | 0.02 / 0.20 (n=75) | 0.04 |

## D. Pseudo-prospective Tier logic, as of 2009 (uses only 2002–2009 data for the decision)
Tier 1 = USPTO signal by 2009 AND 10-K filings 2007–09 peak < 10; Tier 2 = signal AND 10-K ≥ 10; baselines = no signal with the same 10-K split. Outcomes 2010–19: ≥ 30 10-K filings in some year; 10-K share 2015–19 mean ≥ 3× 2007–09 mean.

| rule | group | n | reach ≥30 10-K | 10-K share 3× | disruptive (EC) |
|---|---|---|---|---|---|
| 10 / +30% / 1w | T1 signal & 10-K low | 186 | 0.02 | 0.09 | 0.10 |
| 10 / +30% / 1w | T2 signal & 10-K high | 250 | 0.50 | 0.05 | 0.59 |
| 10 / +30% / 1w | no signal & 10-K low | 651 | 0.01 | 0.06 | 0.03 |
| 10 / +30% / 1w | no signal & 10-K high | 199 | 0.49 | 0.01 | 0.45 |
| 10 / +30% / 2w | T1 signal & 10-K low | 72 | 0.01 | 0.07 | 0.07 |
| 10 / +30% / 2w | T2 signal & 10-K high | 109 | 0.57 | 0.09 | 0.63 |
| 10 / +30% / 2w | no signal & 10-K low | 765 | 0.01 | 0.07 | 0.04 |
| 10 / +30% / 2w | no signal & 10-K high | 340 | 0.47 | 0.01 | 0.50 |
| 10 / +50% / 1w | T1 signal & 10-K low | 156 | 0.02 | 0.10 | 0.11 |
| 10 / +50% / 1w | T2 signal & 10-K high | 192 | 0.51 | 0.07 | 0.59 |
| 10 / +50% / 1w | no signal & 10-K low | 681 | 0.01 | 0.06 | 0.03 |
| 10 / +50% / 1w | no signal & 10-K high | 257 | 0.49 | 0.01 | 0.49 |
| 10 / +50% / 2w | T1 signal & 10-K low | 42 | 0.00 | 0.07 | 0.07 |
| 10 / +50% / 2w | T2 signal & 10-K high | 61 | 0.64 | 0.11 | 0.67 |
| 10 / +50% / 2w | no signal & 10-K low | 795 | 0.01 | 0.07 | 0.04 |
| 10 / +50% / 2w | no signal & 10-K high | 388 | 0.47 | 0.02 | 0.51 |
| 30 / +30% / 1w | T1 signal & 10-K low | 45 | 0.00 | 0.07 | 0.07 |
| 30 / +30% / 1w | T2 signal & 10-K high | 113 | 0.59 | 0.08 | 0.67 |
| 30 / +30% / 1w | no signal & 10-K low | 792 | 0.01 | 0.07 | 0.04 |
| 30 / +30% / 1w | no signal & 10-K high | 336 | 0.46 | 0.02 | 0.48 |
| 30 / +30% / 2w | T1 signal & 10-K low | 16 | 0.00 | 0.00 | 0.00 |
| 30 / +30% / 2w | T2 signal & 10-K high | 46 | 0.65 | 0.13 | 0.65 |
| 30 / +30% / 2w | no signal & 10-K low | 821 | 0.01 | 0.07 | 0.05 |
| 30 / +30% / 2w | no signal & 10-K high | 403 | 0.48 | 0.02 | 0.52 |
| 30 / +50% / 1w | T1 signal & 10-K low | 35 | 0.00 | 0.09 | 0.03 |
| 30 / +50% / 1w | T2 signal & 10-K high | 75 | 0.60 | 0.12 | 0.65 |
| 30 / +50% / 1w | no signal & 10-K low | 802 | 0.01 | 0.07 | 0.04 |
| 30 / +50% / 1w | no signal & 10-K high | 374 | 0.47 | 0.02 | 0.51 |
| 30 / +50% / 2w | T1 signal & 10-K low | 9 | 0.00 | 0.00 | 0.00 |
| 30 / +50% / 2w | T2 signal & 10-K high | 24 | 0.58 | 0.17 | 0.62 |
| 30 / +50% / 2w | no signal & 10-K low | 828 | 0.01 | 0.07 | 0.04 |
| 30 / +50% / 2w | no signal & 10-K high | 425 | 0.49 | 0.03 | 0.52 |
