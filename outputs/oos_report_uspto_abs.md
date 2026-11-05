# Out-of-sample evaluation — techdiffusion.net technology set (patent series: uspto_abs)

USPTO series complete for 1286 / 1286 technologies; 10-K series for 1286; job-posting series for 1147.

Rule G: share[y] / share[y−2] ≥ 1+g, raw count ≥ min_count, for N consecutive windows; first fire counted only if in 2004–2017.

## A. Hiring timing (Burning Glass postings 2010–2019; outcome independent of patents)
Positives: posting share < 10% of its 2010–19 max in 2010 and ≥ 1,000 postings → emergence year = first year ≥ 10% of max (n = 25). Controls: share already ≥ 10% of max in 2010 and never +50% above the 2010 level (n = 286).

| rule | n pos | eligible (peak ≥ min_count) | signal | led | same | lagged | lead rate (all / eligible) | lead 1–5y | median lead | n ctl (eligible) | fire rate (all / eligible) | lead − fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 10 / +30% / 1w | 25 | 25 | 13 | 13 | 0 | 0 | 0.52 / 0.52 | 0.08 | 7 | 286 (274) | 0.45 / 0.47 | 0.07 |
| 10 / +30% / 2w | 25 | 25 | 17 | 13 | 3 | 1 | 0.52 / 0.52 | 0.16 | 6 | 286 (274) | 0.33 / 0.35 | 0.19 |
| 10 / +50% / 1w | 25 | 25 | 12 | 11 | 0 | 1 | 0.44 / 0.44 | 0.20 | 7 | 286 (274) | 0.42 / 0.44 | 0.02 |
| 10 / +50% / 2w | 25 | 25 | 13 | 8 | 3 | 2 | 0.32 / 0.32 | 0.12 | 6.00 | 286 (274) | 0.16 / 0.17 | 0.16 |
| 30 / +30% / 1w | 25 | 19 | 13 | 11 | 1 | 1 | 0.44 / 0.58 | 0.12 | 7 | 286 (233) | 0.39 / 0.48 | 0.05 |
| 30 / +30% / 2w | 25 | 19 | 11 | 7 | 2 | 2 | 0.28 / 0.37 | 0.20 | 3 | 286 (233) | 0.26 / 0.31 | 0.02 |
| 30 / +50% / 1w | 25 | 19 | 10 | 8 | 1 | 1 | 0.32 / 0.42 | 0.16 | 6.00 | 286 (233) | 0.31 / 0.39 | 0.01 |
| 30 / +50% / 2w | 25 | 19 | 9 | 5 | 1 | 3 | 0.20 / 0.26 | 0.16 | 2 | 286 (233) | 0.12 / 0.15 | 0.08 |

Positives and their emergence years: Binder material 2011, Default effect 2011, Highdensity polyethylene 2011, Google Search 2011, Smartphone 2011, Touchpad 2011, Augmented reality 2012, Autonomous system Internet 2012, Tree data structure 2012, PC game 2012, Machine learning 2012, Pager 2012, Push technology 2012, SMS 2012, Softwaredefined radio 2013, Adenoassociated virus 2014, Dataspaces 2014, Notification LED 2014, Power inverter 2014, Harvard architecture 2014, Selfdriving car 2015, Artificial neural network 2016, Antireflective coating 2016, Contact region 2017, Superoxide dismutase 2018

## B. Cross-section, signal computed from 2002–2009 counts only
Outcome = earnings-call class over 2002–19 (Kalyani et al.: disruptive > 100 transcripts, non-disruptive < 10). The transcript total includes years before 2009, so this measures association, not strict prediction. Quartiles are by total patents mentioning the technology (size control).

### as of 2009
| rule | fire rate disruptive (n) | fire rate intermediate (n) | fire rate non_disruptive (n) | lift disruptive/non | Q1 disr/non | Q2 disr/non | Q3 disr/non | Q4 disr/non |
|---|---|---|---|---|---|---|---|---|
| 10 / +30% / 1w | 0.39 (275) | 0.34 (414) | 0.33 (597) | 1.18 | 0.63/0.32 (51/182) | 0.52/0.37 (48/175) | 0.38/0.33 (60/147) | 0.22/0.25 (116/93) |
| 10 / +30% / 2w | 0.29 (275) | 0.19 (414) | 0.16 (597) | 1.87 | 0.35/0.19 (51/182) | 0.46/0.15 (48/175) | 0.27/0.18 (60/147) | 0.21/0.08 (116/93) |
| 10 / +50% / 1w | 0.31 (275) | 0.27 (414) | 0.27 (597) | 1.11 | 0.59/0.34 (51/182) | 0.38/0.27 (48/175) | 0.30/0.27 (60/147) | 0.16/0.16 (116/93) |
| 10 / +50% / 2w | 0.17 (275) | 0.09 (414) | 0.08 (597) | 2.17 | 0.27/0.12 (51/182) | 0.27/0.06 (48/175) | 0.10/0.08 (60/147) | 0.13/0.04 (116/93) |
| 30 / +30% / 1w | 0.32 (275) | 0.25 (414) | 0.14 (597) | 2.25 | 0.22/0.07 (51/182) | 0.48/0.15 (48/175) | 0.47/0.23 (60/147) | 0.22/0.12 (116/93) |
| 30 / +30% / 2w | 0.21 (275) | 0.13 (414) | 0.06 (597) | 3.82 | 0.10/0.03 (51/182) | 0.29/0.06 (48/175) | 0.30/0.09 (60/147) | 0.18/0.04 (116/93) |
| 30 / +50% / 1w | 0.25 (275) | 0.18 (414) | 0.11 (597) | 2.41 | 0.24/0.07 (51/182) | 0.40/0.11 (48/175) | 0.37/0.16 (60/147) | 0.15/0.09 (116/93) |
| 30 / +50% / 2w | 0.12 (275) | 0.06 (414) | 0.02 (597) | 4.96 | 0.10/0.01 (51/182) | 0.17/0.03 (48/175) | 0.10/0.04 (60/147) | 0.11/0.02 (116/93) |

### as of 2019 (all years)
| rule | fire rate disruptive (n) | fire rate intermediate (n) | fire rate non_disruptive (n) | lift disruptive/non | Q1 disr/non | Q2 disr/non | Q3 disr/non | Q4 disr/non |
|---|---|---|---|---|---|---|---|---|
| 10 / +30% / 1w | 0.47 (275) | 0.48 (414) | 0.44 (597) | 1.07 | 0.71/0.38 (51/182) | 0.54/0.47 (48/175) | 0.47/0.46 (60/147) | 0.34/0.44 (116/93) |
| 10 / +30% / 2w | 0.43 (275) | 0.36 (414) | 0.28 (597) | 1.54 | 0.63/0.32 (51/182) | 0.58/0.29 (48/175) | 0.40/0.26 (60/147) | 0.29/0.22 (116/93) |
| 10 / +50% / 1w | 0.42 (275) | 0.42 (414) | 0.42 (597) | 1.01 | 0.71/0.41 (51/182) | 0.56/0.47 (48/175) | 0.43/0.41 (60/147) | 0.23/0.34 (116/93) |
| 10 / +50% / 2w | 0.26 (275) | 0.18 (414) | 0.15 (597) | 1.68 | 0.49/0.21 (51/182) | 0.31/0.15 (48/175) | 0.17/0.14 (60/147) | 0.18/0.08 (116/93) |
| 30 / +30% / 1w | 0.48 (275) | 0.39 (414) | 0.25 (597) | 1.91 | 0.43/0.15 (51/182) | 0.69/0.29 (48/175) | 0.62/0.32 (60/147) | 0.34/0.26 (116/93) |
| 30 / +30% / 2w | 0.35 (275) | 0.22 (414) | 0.10 (597) | 3.38 | 0.27/0.08 (51/182) | 0.46/0.10 (48/175) | 0.43/0.12 (60/147) | 0.28/0.12 (116/93) |
| 30 / +50% / 1w | 0.39 (275) | 0.29 (414) | 0.20 (597) | 1.97 | 0.41/0.14 (51/182) | 0.60/0.23 (48/175) | 0.52/0.26 (60/147) | 0.22/0.16 (116/93) |
| 30 / +50% / 2w | 0.20 (275) | 0.10 (414) | 0.05 (597) | 4.34 | 0.22/0.03 (51/182) | 0.25/0.06 (48/175) | 0.18/0.05 (60/147) | 0.17/0.03 (116/93) |

## C. 10-K timing (EDGAR full-text, 2002–2019; 10-K lags earnings calls by ~4 years on the 29-technology set, so leads here overstate leads vs. the market)
Positives: 10-K share < 10% of max in 2002, peak ≥ 30 filings → emergence = first year ≥ 10% of max (n = 26). Controls: flat 10-K share (max 2005–19 / mean 2002–04 < 3; n = 205) and never ≥ 10 filings in any year (n = 736).

| rule | n pos | eligible | signal | led | same | lagged | lead rate (all / eligible) | lead 1–5y | median lead | fire rate flat (all / eligible) | fire rate never (all / eligible) | lead − fire(flat) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 10 / +30% / 1w | 26 | 26 | 11 | 8 | 0 | 3 | 0.31 / 0.31 | 0.27 | 2.50 | 0.39 / 0.40 (n=200) | 0.44 / 0.56 (n=587) | -0.08 |
| 10 / +30% / 2w | 26 | 26 | 18 | 10 | 2 | 6 | 0.38 / 0.38 | 0.31 | 3.00 | 0.26 / 0.27 (n=200) | 0.32 / 0.40 (n=587) | 0.12 |
| 10 / +50% / 1w | 26 | 26 | 14 | 9 | 1 | 4 | 0.35 / 0.35 | 0.31 | 3 | 0.30 / 0.31 (n=200) | 0.42 / 0.53 (n=587) | 0.04 |
| 10 / +50% / 2w | 26 | 26 | 16 | 10 | 1 | 5 | 0.38 / 0.38 | 0.31 | 2.50 | 0.14 / 0.14 (n=200) | 0.17 / 0.22 (n=587) | 0.25 |
| 30 / +30% / 1w | 26 | 26 | 19 | 7 | 3 | 9 | 0.27 / 0.27 | 0.23 | 1 | 0.37 / 0.41 (n=184) | 0.28 / 0.60 (n=339) | -0.10 |
| 30 / +30% / 2w | 26 | 26 | 22 | 5 | 4 | 13 | 0.19 / 0.19 | 0.15 | 3 | 0.21 / 0.24 (n=184) | 0.13 / 0.29 (n=339) | -0.02 |
| 30 / +50% / 1w | 26 | 26 | 19 | 6 | 3 | 10 | 0.23 / 0.23 | 0.19 | 2.00 | 0.26 / 0.29 (n=184) | 0.22 / 0.47 (n=339) | -0.03 |
| 30 / +50% / 2w | 26 | 26 | 20 | 5 | 4 | 11 | 0.19 / 0.19 | 0.15 | 2 | 0.08 / 0.09 (n=184) | 0.06 / 0.13 (n=339) | 0.11 |

## D. Pseudo-prospective Tier logic, as of 2009 (uses only 2002–2009 data for the decision)
Tier 1 = USPTO signal by 2009 AND 10-K filings 2007–09 peak < 10; Tier 2 = signal AND 10-K ≥ 10; baselines = no signal with the same 10-K split. Outcomes 2010–19: ≥ 30 10-K filings in some year; 10-K share 2015–19 mean ≥ 3× 2007–09 mean.

| rule | group | n | reach ≥30 10-K | 10-K share 3× | disruptive (EC) |
|---|---|---|---|---|---|
| 10 / +30% / 1w | T1 signal & 10-K low | 290 | 0.00 | 0.09 | 0.07 |
| 10 / +30% / 1w | T2 signal & 10-K high | 150 | 0.46 | 0.05 | 0.58 |
| 10 / +30% / 1w | no signal & 10-K low | 547 | 0.01 | 0.06 | 0.03 |
| 10 / +30% / 1w | no signal & 10-K high | 299 | 0.51 | 0.03 | 0.51 |
| 10 / +30% / 2w | T1 signal & 10-K low | 154 | 0.01 | 0.08 | 0.08 |
| 10 / +30% / 2w | T2 signal & 10-K high | 99 | 0.55 | 0.09 | 0.68 |
| 10 / +30% / 2w | no signal & 10-K low | 683 | 0.01 | 0.07 | 0.04 |
| 10 / +30% / 2w | no signal & 10-K high | 350 | 0.48 | 0.02 | 0.49 |
| 10 / +50% / 1w | T1 signal & 10-K low | 234 | 0.00 | 0.10 | 0.06 |
| 10 / +50% / 1w | T2 signal & 10-K high | 126 | 0.50 | 0.06 | 0.55 |
| 10 / +50% / 1w | no signal & 10-K low | 603 | 0.01 | 0.06 | 0.04 |
| 10 / +50% / 1w | no signal & 10-K high | 323 | 0.49 | 0.02 | 0.52 |
| 10 / +50% / 2w | T1 signal & 10-K low | 79 | 0.03 | 0.11 | 0.13 |
| 10 / +50% / 2w | T2 signal & 10-K high | 55 | 0.58 | 0.13 | 0.69 |
| 10 / +50% / 2w | no signal & 10-K low | 758 | 0.01 | 0.06 | 0.04 |
| 10 / +50% / 2w | no signal & 10-K high | 394 | 0.48 | 0.02 | 0.51 |
| 30 / +30% / 1w | T1 signal & 10-K low | 154 | 0.01 | 0.08 | 0.08 |
| 30 / +30% / 1w | T2 signal & 10-K high | 124 | 0.52 | 0.07 | 0.61 |
| 30 / +30% / 1w | no signal & 10-K low | 683 | 0.01 | 0.07 | 0.04 |
| 30 / +30% / 1w | no signal & 10-K high | 325 | 0.49 | 0.02 | 0.50 |
| 30 / +30% / 2w | T1 signal & 10-K low | 67 | 0.00 | 0.04 | 0.09 |
| 30 / +30% / 2w | T2 signal & 10-K high | 77 | 0.57 | 0.09 | 0.68 |
| 30 / +30% / 2w | no signal & 10-K low | 770 | 0.01 | 0.07 | 0.04 |
| 30 / +30% / 2w | no signal & 10-K high | 372 | 0.48 | 0.02 | 0.50 |
| 30 / +50% / 1w | T1 signal & 10-K low | 106 | 0.02 | 0.09 | 0.09 |
| 30 / +50% / 1w | T2 signal & 10-K high | 101 | 0.55 | 0.09 | 0.59 |
| 30 / +50% / 1w | no signal & 10-K low | 731 | 0.01 | 0.07 | 0.04 |
| 30 / +50% / 1w | no signal & 10-K high | 348 | 0.48 | 0.02 | 0.51 |
| 30 / +50% / 2w | T1 signal & 10-K low | 28 | 0.00 | 0.07 | 0.18 |
| 30 / +50% / 2w | T2 signal & 10-K high | 41 | 0.61 | 0.15 | 0.66 |
| 30 / +50% / 2w | no signal & 10-K low | 809 | 0.01 | 0.07 | 0.04 |
| 30 / +50% / 2w | no signal & 10-K high | 408 | 0.48 | 0.02 | 0.52 |
