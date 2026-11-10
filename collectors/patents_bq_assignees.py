"""Sim E data: for a fixed list of bigrams (simulation/sim_e_bigrams.csv), count US applications per
(bigram, year, harmonized assignee) in Google Patents, plus each assignee's total US applications per year.
Year basis from BQ_DATE_BASIS (publication = earliest publication date per application; filing). Same text
pipeline as collectors/patents_bq_bigrams.py (title + abstract, English, dedup by application_number).
Output: data/external/assignee_bigram_year.csv.gz (bigram, year, assignee, n) and data/external/assignee_totals.csv.gz
(assignee, year, n_total). Protocol: simulation/protocol.md (Sim E). Scans ~240 GB — run after the monthly free tier resets.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
from pathlib import Path

from collectors.common import env, log
from collectors.patents_bq_bigrams import STOP, TABLE, Y0, Y1

ROOT = Path(__file__).resolve().parents[1]
LIST = ROOT / "simulation" / "sim_e_bigrams.csv"
OUT_BG = ROOT / "data" / "external" / "assignee_bigram_year.csv.gz"
OUT_TOT = ROOT / "data" / "external" / "assignee_totals.csv.gz"


def build_sql(bigrams: list[str], basis: str) -> str:
    stop = ", ".join(f"'{w}'" for w in sorted(set(STOP)))
    date_col = "filing_date" if basis == "filing" else "publication_date"
    yr_expr = ("CAST(FLOOR(filing_date / 10000) AS INT64)" if basis == "filing"
               else "CAST(FLOOR(MIN(publication_date) OVER (PARTITION BY application_number) / 10000) AS INT64)")
    lst = ", ".join("'" + b.replace("'", "") + "'" for b in bigrams)
    return f"""
WITH docs AS (
  SELECT application_number,
         {yr_expr} AS yr,
         IFNULL((SELECT name FROM UNNEST(assignee_harmonized) LIMIT 1), '') AS asg,
         LOWER(CONCAT(
           IFNULL((SELECT text FROM UNNEST(title_localized) WHERE language = 'en' LIMIT 1), ''), ' ',
           IFNULL((SELECT text FROM UNNEST(abstract_localized) WHERE language = 'en' LIMIT 1), ''))) AS txt
  FROM {TABLE}
  WHERE country_code = 'US' AND {date_col} BETWEEN {Y0}0101 AND {Y1}1231
),
docs1 AS (
  SELECT application_number, yr, asg, txt FROM docs
  QUALIFY ROW_NUMBER() OVER (PARTITION BY application_number ORDER BY LENGTH(txt) DESC) = 1
),
toks AS (SELECT yr, asg, REGEXP_EXTRACT_ALL(txt, r'[a-z0-9]+') AS w FROM docs1),
bg AS (
  SELECT yr, asg, g
  FROM toks, UNNEST(ARRAY(
    SELECT DISTINCT CONCAT(w[OFFSET(i)], ' ', w[OFFSET(i + 1)])
    FROM UNNEST(GENERATE_ARRAY(0, ARRAY_LENGTH(w) - 2)) AS i
    WHERE w[OFFSET(i)] NOT IN ({stop}) AND w[OFFSET(i + 1)] NOT IN ({stop}))) AS g
  WHERE ARRAY_LENGTH(w) >= 2 AND asg != ''
),
wanted AS (SELECT g FROM UNNEST([{lst}]) AS g)
SELECT 'bg' AS kind, b.g AS bigram, b.yr, b.asg, COUNT(*) AS n
FROM bg b JOIN wanted USING (g) GROUP BY b.g, b.yr, b.asg
UNION ALL
SELECT 'tot' AS kind, '' AS bigram, yr, asg, COUNT(*) AS n FROM docs1 WHERE asg != '' GROUP BY yr, asg
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    key, project = env("GCP_SA_KEY"), env("GCP_PROJECT_ID")
    if not key or not project:
        log("assignees: skipped (GCP_SA_KEY / GCP_PROJECT_ID missing)"); return
    bigrams = sorted({r["bigram"].strip() for r in csv.DictReader(open(LIST, encoding="utf-8")) if r["bigram"].strip()})
    basis = env("BQ_DATE_BASIS", "publication")
    log(f"assignees: {len(bigrams)} bigrams; date basis = {basis}")
    from google.cloud import bigquery
    from google.oauth2 import service_account
    creds = service_account.Credentials.from_service_account_info(json.loads(key))
    client = bigquery.Client(project=project, credentials=creds)
    sql = build_sql(bigrams, basis)
    est = client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False))
    gb = est.total_bytes_processed / 1e9
    log(f"assignees: dry run — {gb:.1f} GB would be scanned")
    if a.dry_run:
        return
    max_gb = float(env("BQ_MAX_GB", "400"))
    if gb > max_gb:
        raise SystemExit(f"assignees: estimate {gb:.0f} GB exceeds BQ_MAX_GB={max_gb:g}; not running")
    job = client.query(sql)
    it = job.result(page_size=100_000)
    log(f"assignees: query done; billed {job.total_bytes_billed/1e9:.1f} GB; downloading")
    OUT_BG.parent.mkdir(parents=True, exist_ok=True)
    n_bg = n_tot = 0
    with gzip.open(OUT_BG, "wt", newline="", encoding="utf-8") as fb, gzip.open(OUT_TOT, "wt", newline="", encoding="utf-8") as ft:
        wb, wt = csv.writer(fb), csv.writer(ft)
        wb.writerow(["bigram", "year", "assignee", "n"]); wt.writerow(["assignee", "year", "n_total"])
        for r in it:
            if r["kind"] == "bg":
                wb.writerow([r["bigram"], int(r["yr"]), r["asg"], int(r["n"])]); n_bg += 1
            else:
                wt.writerow([r["asg"], int(r["yr"]), int(r["n"])]); n_tot += 1
    log(f"assignees: wrote {n_bg:,} bigram-year-assignee rows and {n_tot:,} assignee-year totals")


if __name__ == "__main__":
    main()
