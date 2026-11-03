# money-brain — instructions for Claude sessions

## What this repo is
Caleb's personal investment-thesis discovery pipeline. Weekly GitHub Actions collect yearly document counts per technology from PubMed / arXiv / SEC EDGAR / ClinicalTrials.gov / USPTO, a deterministic detector turns them into Tier labels, and thesis cards live in `theses/`. See README.md for the design papers and rules.

## Hard rules
- Scoring is arithmetic only. Never let an LLM assign scores, tiers, or rank candidates. LLM work is limited to: grouping keywords, company–theme linkage judgement (must pass BOTH a "for" prompt and an "against" prompt), and writing/updating thesis cards.
- Never edit `data/counts.csv` or `outputs/` by hand; they are produced by collectors and the detector and committed by the workflow.
- Adding a technology = one row in `config/technologies.csv` (status `candidate`, ec_year blank). Keywords are `;`-separated phrases; keep them unambiguous (Kalyani et al. dropped bigrams like "automated car" that matched car washes).
- Changing a threshold = edit `config/settings.yml` and note why in the commit message. Re-run the detector and check `outputs/validation_report.md` before and after.
- Validation rows (status `validation`) are the Kalyani et al. 29 technologies with their earnings-call emergence year. Do not change their ec_year; it is the label.

## Writing style for thesis cards and reports (Caleb's standing preferences)
- Korean, 음슴체 (~함/~임/~됨). Concise one-line bullets; evidence in parentheses, not separate bullets.
- English for technical terms; no Japanese-derived Sino-Korean jargon.
- Distinguish 확인되지 않음 / 측정하지 않았음 / 다루지 않았음. Match claim strength to evidence level.
- Cite sources inline (author·journal·year or outlet·date); never use cite tags or any HTML.
- Report only what failed when reviewing; do not list passed checks.

## Weekly card update (scheduled Claude task)
1. Read `outputs/tiers.csv` and `outputs/signals.csv` from the latest commit.
2. For each T1 technology without a card: run the for/against linkage prompts on 3–5 US-listed beneficiaries, then create `theses/<id>.md` from `_template.md`.
3. For existing cards: update Evidence and Review log only if a number changed; never rewrite the thesis text without a changed input.
4. Open a PR; do not push to main.
