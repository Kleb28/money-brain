# Numerai track (separate from the thesis pipeline)

Purpose: learn the measurement and modelling layer the thesis pipeline lacks (point-in-time data, era-wise validation,
feature neutralization, corr/sharpe as Numerai scores them) in an environment where Numerai supplies the data and
does the scoring. Nothing here uses money-brain data; it does not validate the thesis pipeline.
The arithmetic-only rule of CLAUDE.md governs thesis scoring; here ML is the point and no LLM is involved.

- `train_baseline.py` — Numerai example-model recipe (LightGBM, `medium` feature set, every 4th era) + validation
  diagnostics vs Numerai's published benchmark models → `outputs/numerai_baseline.md`; submits live predictions when keys exist.
- Workflow `.github/workflows/numerai.yml` — manual run, and Saturdays 20:00 UTC after the weekend round opens.

Yardstick: on the same validation eras, our per-era numerai_corr mean and sharpe vs the benchmark model.
Staking: none until the model has live rounds behind it; unstaked submissions still appear on the leaderboard.

Setup that only the account owner can do: numer.ai account → create a model slot → Settings → API keys with
"upload submissions" → repository secrets `NUMERAI_PUBLIC_ID`, `NUMERAI_SECRET_KEY`, repository variable `NUMERAI_MODEL_NAME`.
Until then the workflow runs with `--no-submit` behaviour automatically (keys absent).
