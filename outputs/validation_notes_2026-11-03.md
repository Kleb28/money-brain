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

---

# Addendum 2026-11-04 (2) — Negative controls and rule selection

Controls: 18 candidates; 13 valid by their own 10-K trajectory (max share 2005-19 / mean 2002-04 < 3). Rejected: carbon nanotube (18.3×), razor (4.9×), RNA interference (4.7×), stem cell (4.6×); graphene unchecked (no 2002-04 EDGAR base).

## Discrimination (lead rate on 16 positives − fire rate on 13 controls), from outputs/rule_selection.md
| source | best rule | lead | fire | score |
|---|---|---|---|---|
| uspto | 10 / +50% / 1 window | 0.62 | 0.31 | +0.32 |
| uspto | 30 / +50% / 1 window | 0.50 | 0.23 | +0.27 |
| uspto | 30 / +50% / 2 windows (pre-registered baseline) | 0.19 | 0.08 | +0.11 |
| arxiv | 30 / +50% / 1 window | 0.14 | 0.00 | +0.14 |
| pubmed | best | 0.12 | 0.08 | +0.05 |
| edgar_10k | best | 0.00 | 0.00 | 0.00 |

Text sources do not discriminate: with loose rules PubMed and EDGAR fire on controls more often than they lead on positives (PubMed 0.31 vs 0.62; EDGAR 0.38 vs 0.62).
USPTO false positives under the 1-window rules are small-count jumps (hydraulic cylinder 15→27, centrifugal pump 22→40, power transformer 5→15) plus one real mini-surge (circuit breaker 63→111 in 2008).

## Decision proposed (not yet frozen)
Change exactly one parameter from the pre-registered baseline: consecutive windows 2 → 1, keeping min_count 30 and +50%. Rationale: the second window costs 1–2 years of lead on positives and controls alike (it delays rather than discriminates); min_count 30 was set a priori as the noise floor and removes the 5→15-type false positives.
Resulting USPTO rule: min_count 30, +50% over 2 years, 1 window → lead 8/16, fire 3/13.
Uncertainty: with n = 16 / 13 the standard error on each rate is ≈ ±0.12; the difference between the two 1-window rules is not resolvable on this set.

## Role of each source after validation
- uspto (title phrase, filing year): the leading signal.
- arxiv: weak secondary for CS/physics themes; pubmed: no leading value; both still useful as denominators of "science volume" in cards.
- edgar_10k: lagging by ~4 years → use as the "already in the market" (Tier 2) marker, not as evidence.
- clinicaltrials: downstream (lags 11 years on bispecific) → card context only.

---

# Addendum 2026-11-04 (3) — Out-of-sample test on the techdiffusion.net set (1,286 technologies)

Data: Kalyani·Bloom·Carvalho·Hassan·Lerner·Tahoun public release (techdiffusion.net, Nov 2023; paper NBER w28999 rev2 / QJE 2025): 1,899 patent bigrams grouped into 1,286 Wikipedia titles, earnings-call transcript totals 2002-19 (disruptive > 100 / intermediate 10-100 / non-disruptive < 10), Burning Glass postings 2010-19, patent-based emergence year. No per-year earnings-call series is public, so the 29-set EC label cannot be reproduced; three substitute labels were used. New series collected: USPTO title-phrase filings 2002-19 and 10-K full-text hits 2002-19 for all 1,286 (data/external/). Full tables: outputs/oos_report.md.

## Results
- A. Hiring timing (n = 25 positives emerging in postings after 2010, 286 flat controls): lead − fire between −0.13 and +0.11 for every rule; the loose rule fires on 63% of controls. No timing discrimination.
- C. 10-K timing (n = 26 positives, 205 flat controls): lead − fire between −0.21 and +0.04. No timing discrimination.
- B. Cross-section (signal from 2002-09 counts only): fire rate disruptive 0.29 vs non-disruptive 0.03 under 30/+30%/1w (lift 10×), holding within patent-size quartiles. The signal picks commercially relevant technologies, but B does not separate "before" from "contemporaneous".
- D. Tier-1 logic as of 2009 (signal AND < 10 10-K filings 2007-09): over all 1,286, Tier-1 technologies became disruptive at 3-11% vs 3-5% for no-signal/low-10-K — no lift; the technologies that became disruptive were already in 10-Ks by 2007-09 (Tier 2: 59-67%). Restricted to young technologies (patent emergence ≥ 2000, n = 114): Tier 1 under 10/+50%/1w has n = 13, of which 5 became disruptive (38% vs 6% base; augmented reality 2007, self-driving car 2008, fingerprint 2004, LED circuit 2005, USB flash drive 2007). Under min_count 30 the Tier-1 group is nearly empty (n = 3).

## Reading
- Timing power of the USPTO growth rule, found on the 29-set in-sample (lead 0.50-0.62 vs fire 0.23-0.31), does not replicate on hiring- or 10-K-based labels. Treat the 29-set result as in-sample optimism until a per-year earnings-call series is available.
- What survives: cross-sectional selection (B) and, among young technologies only, the Tier-1 combination (D, n = 13). The set is dominated by 1980s-90s technologies, which is the wrong population for a "new technology" screen; the young subset is the relevant analog and it is small.
- Title-only counts are the binding constraint: median peak count 9 titles/yr; only 25% of technologies ever reach min_count 30, so the pre-registered floor silences most of the universe. Full-text patent counts (abstract/claims) are needed before the floor can be judged.

## Decisions proposed (not frozen)
- Do not use the detector as a timing trigger; use it as a screen (signal AND 10-K low) restricted to technologies whose patent history starts recently.
- Replace title-only USPTO counts with full-text counts before re-running rule selection (candidate: Google Patents public dataset on BigQuery, free tier; needs a GCP project).
- Keep settings.yml unchanged until the full-text series exists.
