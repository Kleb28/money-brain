# Validation notes — 2026-11-03 (first full run)

Data: 29 Kalyani technologies × 2002–2026, sources pubmed / arxiv / edgar_10k / clinicaltrials (bio only).
Labels: earnings-call emergence year (Appendix Table 11, NBER WP 2021). 14 technologies imputed to 2002 excluded from lead statistics.

## Baseline rule (min_count 30, +50% over 2y, 2 consecutive) — lead = ec_year − signal_year
| source | n | led | same | lagged | median |
|---|---|---|---|---|---|
| arxiv | 10 | 1 | 0 | 9 | −3 |
| edgar_10k | 13 | 0 | 0 | 13 | −4 |
| pubmed | 11 | 0 | 0 | 11 | −5 |
| clinicaltrials | 1 | 0 | 0 | 1 | −11 |

Only lead: Machine learning / AI on arXiv (signal 2013, EC 2015).

## Sensitivity (not a tuning — reported in full)
Loosest rule (min_count 10, +30%, 1 window): arxiv 5/13 led (median −2), edgar 6/16 led (median 0), pubmed 5/14 led (median 0).
No configuration gives a majority of leads. Loosening trades lag for noise.

## Reference point from the paper itself
Kalyani's patent-based emergence year (50% of max patent share) vs EC year, n = 16 non-imputed:
led 10 (bispecific +13, ML +10, stent graft +8, fingerprint +6, …), same 2, lagged 4 (3D printing, cloud, smart devices, social networking).
Patents are the only layer in the paper that leads the call for a majority of technologies.

## Reading
- Public text counts (PubMed / arXiv / 10-K) under a growth rule do not lead the earnings-call breakthrough for most of this set; 10-K lags by ~4 years, consistent with Cohen·Malloy·Nguyen (JF 2020) slow incorporation but in the wrong direction for a leading signal.
- The EC "breakthrough" is defined at 10% of peak call share — early in the curve — which makes it hard for any volume measure to lead.
- Patent timing is the layer worth adding (USPTO key pending). arXiv is the second-best for CS/physics-adjacent themes.
- Rule K (10% of max) is not a detector: it fires in 2002 for anything with pre-existing literature.

## Caveats
- Keyword sets are coarse OR-unions; Kalyani used a human audit (80% precision) that is not replicated here.
- EDGAR series are non-monotonic in places (cloud computing 2016: 1317 → 2018: 683); cause unverified (index coverage vs. real).
- Single run; thresholds in settings.yml are unchanged (no tuning on the validation set).
