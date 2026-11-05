"""Full-text patent counts from the Google Patents public dataset on BigQuery.

Source id: uspto_abs  — US applications (deduplicated by application_number) whose English title or
abstract contains a technology phrase, by FILING year. Replaces the title-only `uspto` series as the
patent layer once validated (title-only counts were too sparse: median peak 9 titles/yr, see
outputs/validation_notes_2026-11-03.md addendum 3).

Table: patents-public-data.patents.publications (public). One query tokenises every US title+abstract
once, generates 1–4-grams and joins them to the phrase table, so cost is independent of the number
of phrases (bytes scanned ≈ title + abstract columns of the whole table). The script dry-runs first and
refuses to run if the estimate exceeds BQ_MAX_GB (default 400; the BigQuery free tier is 1 TB/month).

Env: GCP_SA_KEY (service-account JSON, repository secret), GCP_PROJECT_ID (repository variable).
Phrases: config/technologies.csv keywords (all rows) + data/external/oos_technologies.csv keywords.
Outputs: data/counts.csv rows (source uspto_abs) for config technologies and the __all denominator;
         data/external/oos_counts_uspto_abs_0.csv for the out-of-sample set.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
from pathlib import Path

from collectors.common import ALL, COUNTS_PATH, env, load_counts, load_technologies, log, save_counts, upsert

SOURCE = "uspto_abs"
ROOT = Path(__file__).resolve().parents[1]
OOS_LIST = ROOT / "data" / "external" / "oos_technologies.csv"
OOS_OUT = ROOT / "data" / "external" / f"oos_counts_{SOURCE}_0.csv"
TABLE = "`patents-public-data.patents.publications`"
Y0, Y1 = 2000, dt.date.today().year
MAX_N = 4


def norm(phrase: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", phrase.lower()))


def phrase_pairs() -> list[tuple[str, str]]:
    pairs = set()
    for t in load_technologies():
        for k in t["keywords"]:
            pairs.add((norm(k), t["id"]))
    if OOS_LIST.exists():
        with open(OOS_LIST, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                for k in r["keywords"].split(";"):
                    if k.strip():
                        pairs.add((norm(k), r["id"]))
    bad = [p for p, _ in pairs if not p or len(p.split()) > MAX_N]
    if bad:
        log(f"{SOURCE}: {len(bad)} phrases dropped (empty or > {MAX_N} tokens): {bad[:10]}")
    return sorted(p for p in pairs if p[0] and len(p[0].split()) <= MAX_N)


def build_sql(pairs: list[tuple[str, str]]) -> str:
    rows = ",\n".join(f"STRUCT('{p}' AS phrase, '{t}' AS tech)" for p, t in pairs)
    return f"""
WITH phrases AS (
  SELECT phrase, tech, ARRAY_LENGTH(SPLIT(phrase, ' ')) AS n FROM UNNEST([{rows}])
),
docs AS (
  SELECT application_number,
         CAST(FLOOR(filing_date / 10000) AS INT64) AS yr,
         LOWER(CONCAT(
           IFNULL((SELECT text FROM UNNEST(title_localized) WHERE language = 'en' LIMIT 1), ''), ' ',
           IFNULL((SELECT text FROM UNNEST(abstract_localized) WHERE language = 'en' LIMIT 1), ''))) AS txt
  FROM {TABLE}
  WHERE country_code = 'US' AND filing_date BETWEEN {Y0}0101 AND {Y1}1231
),
docs1 AS (
  SELECT application_number, yr, txt FROM docs
  QUALIFY ROW_NUMBER() OVER (PARTITION BY application_number ORDER BY LENGTH(txt) DESC) = 1
),
toks AS (
  SELECT application_number, yr, REGEXP_EXTRACT_ALL(txt, r'[a-z0-9]+') AS w FROM docs1
),
grams AS (
  SELECT application_number, yr, n,
         ARRAY_TO_STRING(ARRAY(SELECT w[OFFSET(j)] FROM UNNEST(GENERATE_ARRAY(i, i + n - 1)) AS j ORDER BY j), ' ') AS g
  FROM toks, UNNEST(GENERATE_ARRAY(1, {MAX_N})) AS n, UNNEST(GENERATE_ARRAY(0, ARRAY_LENGTH(w) - n)) AS i
  WHERE ARRAY_LENGTH(w) >= n
),
hits AS (
  SELECT DISTINCT g.application_number, g.yr, p.tech
  FROM grams g JOIN phrases p ON p.n = g.n AND p.phrase = g.g
)
SELECT tech, yr, COUNT(*) AS n FROM hits GROUP BY tech, yr
UNION ALL
SELECT '{ALL}' AS tech, yr, COUNT(*) AS n FROM docs1 GROUP BY yr
ORDER BY tech, yr
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="estimate bytes only")
    a = ap.parse_args()
    key, project = env("GCP_SA_KEY"), env("GCP_PROJECT_ID")
    if not key or not project:
        log(f"{SOURCE}: skipped (GCP_SA_KEY / GCP_PROJECT_ID missing)"); return
    from google.cloud import bigquery  # noqa: WPS433  (installed only in the bq workflow)
    from google.oauth2 import service_account

    creds = service_account.Credentials.from_service_account_info(json.loads(key))
    client = bigquery.Client(project=project, credentials=creds)
    pairs = phrase_pairs()
    sql = build_sql(pairs)
    log(f"{SOURCE}: {len(pairs)} phrase→technology pairs, years {Y0}-{Y1}, query {len(sql)/1e3:.0f} kB")
    est = client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False))
    gb = est.total_bytes_processed / 1e9
    log(f"{SOURCE}: dry run — {gb:.1f} GB would be scanned")
    max_gb = float(env("BQ_MAX_GB", "400"))
    if a.dry_run:
        return
    if gb > max_gb:
        raise SystemExit(f"{SOURCE}: estimate {gb:.0f} GB exceeds BQ_MAX_GB={max_gb:g}; not running")
    job = client.query(sql)
    rows = list(job.result())
    log(f"{SOURCE}: {len(rows)} rows; billed {job.total_bytes_billed/1e9:.1f} GB; slot {job.slot_millis/6e4:.1f} min")

    config_ids = {t["id"] for t in load_technologies()}
    existing = load_counts()
    oos_rows = []
    n_cfg = 0
    for r in rows:
        tech, y, n = r["tech"], int(r["yr"]), int(r["n"])
        if tech == ALL or tech in config_ids:
            upsert(existing, tech, SOURCE, y, n); n_cfg += 1
        else:
            oos_rows.append((tech, y, n))
    # zero-fill: a technology with no hit in a year is a 0, not a missing row
    years = range(Y0, Y1 + 1)
    for tid in config_ids:
        for y in years:
            if (tid, SOURCE, y) not in existing:
                upsert(existing, tid, SOURCE, y, 0)
    save_counts(existing)
    if OOS_LIST.exists():
        with open(OOS_LIST, encoding="utf-8") as f:
            oos_ids = [r["id"] for r in csv.DictReader(f)]
        got = {(t, y): n for t, y, n in oos_rows}
        with open(OOS_OUT, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["technology_id", "source", "year", "count"])
            for tid in oos_ids:
                for y in years:
                    w.writerow([tid, SOURCE, y, got.get((tid, y), 0)])
        log(f"{SOURCE}: wrote {OOS_OUT.name} ({len(oos_ids)} technologies)")
    log(f"{SOURCE}: {n_cfg} config rows upserted into {COUNTS_PATH.name}")


if __name__ == "__main__":
    main()
