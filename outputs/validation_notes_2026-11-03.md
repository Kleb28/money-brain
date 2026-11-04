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

---

# Addendum 2026-11-04 — USPTO (Open Data Portal, title phrase, filing year)

## Baseline rule (min_count 30, +50% / 2y, 2 consecutive), n = 14 non-imputed
led 3 (autonomous cars +1, ML/AI +2, virtual reality +2), same 2 (smart devices, wireless charging), lagged 9, median −2.
Best single source under the baseline rule, still not a majority.

## Sensitivity (same grid as other sources)
| min_count | growth | windows | n | led | same | lagged | median |
|---|---|---|---|---|---|---|---|
| 10 | +30% | 1 | 16 | 10 | 5 | 1 | +2 |
| 10 | +50% | 1 | 16 | 10 | 4 | 2 | +2 |
| 30 | +30% | 1 | 16 | 8 | 1 | 7 | +1 |
| 30 | +50% | 1 | 16 | 8 | 0 | 8 | +1 |
| 10 | +30% | 2 | 16 | 5 | 2 | 9 | −1 |
| 30 | +50% | 2 | 14 | 3 | 2 | 9 | −2 |

Same loose rule (10 / +30% / 1 window) on other sources: arxiv 5/13, edgar 6/16, pubmed 5/14 → patents lead more often than any text source at equal strictness.
The second consecutive window is what removes most leads (it costs 1–2 years); min_count 30 removes the small bio/niche series (bispecific titles: 16 in 2012, 31 in 2014).

## What this does and does not show
- Shows: patent filing counts (title phrase) are the only layer here that leads the earnings-call breakthrough for a majority, and only under a single-window rule.
- Does not show: the false-positive rate of that single-window rule. The validation set has no negative controls (technologies with steady patenting that never broke through), so the loose rule's precision is unknown. Millimeter wave "+10" (signal 2004 on 18→32 titles) is the kind of early fire that may be noise.
- Title-only is narrower than Kalyani's full-text bigrams; bio terms (bispecific, ADC) under-count because the term sits in claims/abstract, not titles.

## Next step before fixing thresholds
Add 10–15 negative-control rows to technologies.csv (status `control`): patent-active topics with no earnings-call emergence 2002–2019. Measure how often each rule fires on controls; choose the rule by (lead rate on positives) − (fire rate on controls), then freeze it.
