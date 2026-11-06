"""Candidate discovery, stage 1: yearly document counts for EVERY bigram in US patent titles+abstracts.

Same table and tokenisation as collectors/patents_bq.py, but instead of counting known phrases it
counts all bigrams (adjacent token pairs, both tokens outside a function-word / patent-legalese
stoplist), by filing year, and keeps a bigram only if it reaches ≥ MIN_PEAK documents in some year
(no other prefilter: an earlier version also required the bigram not to shrink between 2010-14 and
2020-24, which used future information and would bias any historical simulation; removed 2026-11-06).
The exact Rule G is applied later by detector/candidates.py from config/settings.yml. Kalyani et al. (QJE 2025) start the same
way — technical bigrams from patent text — then keep the ones whose use rises.

Per bigram-year it also counts distinct harmonized assignees (n_assignees) and distinct 4-character
CPC subclasses (n_cpc): a technology is used by many applicants across a few classes, whereas a
single applicant's continuation family or a drafting phrase is not.
Output: data/external/bigram_counts.csv.gz  (bigram, year, count, n_assignees, n_cpc) + __all rows.
Scan ≈ 236 GB (title + abstract columns of the whole table); refuses above BQ_MAX_GB.
Env: GCP_SA_KEY, GCP_PROJECT_ID.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import json
from pathlib import Path

from collectors.common import ALL, env, log

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "external" / "bigram_counts.csv.gz"
TABLE = "`patents-public-data.patents.publications`"
Y0, Y1 = 2005, dt.date.today().year
MIN_PEAK = 30

STOP = """
the of and a an to in is are be been being for by on at or as that this these those which who whose where when
what how not no nor may can will would should could has have had was were do does did it its they their them there
here more less most least very much many some any all only so if thus hence therefore etc also further other another
same such each both either than then into onto from with without within through over under upon about after before
during while between among via per one two three four five six seven eight nine ten first second third fourth fifth
wherein thereof therein thereto thereby whereby said comprising comprises comprise comprised including includes include
included having has containing contains contain consisting consists plurality embodiment embodiments invention
inventions present disclosed disclosure disclosure exemplary example examples configured configurable adapted arranged
method methods apparatus apparatuses system systems device devices portion portions member members element elements
component components unit units assembly assemblies structure structures means step steps according accordance
substantially approximately generally respectively respective predetermined corresponding associated provided
providing provide provides based using used use uses utilizing utilized may might shall above below herein hereof
described describes describe relates related relate relating thereon thereunder therewith various certain particular
specific specifically particularly least greater less lower higher upper inner outer end ends side sides top bottom
front rear left right new improved improvement improvements mm cm nm um kg mg wt vol min max sec approx
""".split()


def build_sql() -> str:
    stop = ", ".join(f"'{w}'" for w in sorted(set(STOP)))
    return f"""
WITH docs AS (
  SELECT application_number,
         CAST(FLOOR(filing_date / 10000) AS INT64) AS yr,
         IFNULL((SELECT name FROM UNNEST(assignee_harmonized) LIMIT 1), '') AS asg,
         IFNULL((SELECT SUBSTR(code, 1, 4) FROM UNNEST(cpc) ORDER BY first DESC LIMIT 1), '') AS cpc4,
         LOWER(CONCAT(
           IFNULL((SELECT text FROM UNNEST(title_localized) WHERE language = 'en' LIMIT 1), ''), ' ',
           IFNULL((SELECT text FROM UNNEST(abstract_localized) WHERE language = 'en' LIMIT 1), ''))) AS txt
  FROM {TABLE}
  WHERE country_code = 'US' AND filing_date BETWEEN {Y0}0101 AND {Y1}1231
),
docs1 AS (
  SELECT application_number, yr, asg, cpc4, txt FROM docs
  QUALIFY ROW_NUMBER() OVER (PARTITION BY application_number ORDER BY LENGTH(txt) DESC) = 1
),
toks AS (
  SELECT yr, asg, cpc4, REGEXP_EXTRACT_ALL(txt, r'[a-z0-9]+') AS w FROM docs1
),
bg AS (
  SELECT yr, asg, cpc4, g
  FROM toks, UNNEST(ARRAY(
    SELECT DISTINCT CONCAT(w[OFFSET(i)], ' ', w[OFFSET(i + 1)])
    FROM UNNEST(GENERATE_ARRAY(0, ARRAY_LENGTH(w) - 2)) AS i
    WHERE w[OFFSET(i)] NOT IN ({stop}) AND w[OFFSET(i + 1)] NOT IN ({stop})
      AND REGEXP_CONTAINS(w[OFFSET(i)], r'^([a-z]{{2,}}|[0-9]+[a-z]+)$')
      AND REGEXP_CONTAINS(w[OFFSET(i + 1)], r'^([a-z]{{2,}}|[0-9]+[a-z]+)$'))) AS g
  WHERE ARRAY_LENGTH(w) >= 2
),
cnt AS (SELECT g, yr, COUNT(*) AS n, COUNT(DISTINCT NULLIF(asg, '')) AS n_asg, COUNT(DISTINCT NULLIF(cpc4, '')) AS n_cpc
        FROM bg GROUP BY g, yr),
keep AS (
  SELECT g FROM cnt GROUP BY g
  HAVING MAX(n) >= {MIN_PEAK}
)
SELECT c.g AS bigram, c.yr, c.n, c.n_asg, c.n_cpc FROM cnt c JOIN keep USING (g)
UNION ALL
SELECT '{ALL}' AS bigram, yr, COUNT(*) AS n, COUNT(DISTINCT NULLIF(asg, '')) AS n_asg, COUNT(DISTINCT NULLIF(cpc4, '')) AS n_cpc
FROM docs1 GROUP BY yr
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    key, project = env("GCP_SA_KEY"), env("GCP_PROJECT_ID")
    if not key or not project:
        log("bigrams: skipped (GCP_SA_KEY / GCP_PROJECT_ID missing)"); return
    from google.cloud import bigquery
    from google.oauth2 import service_account

    creds = service_account.Credentials.from_service_account_info(json.loads(key))
    client = bigquery.Client(project=project, credentials=creds)
    sql = build_sql()
    est = client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False))
    gb = est.total_bytes_processed / 1e9
    log(f"bigrams: dry run — {gb:.1f} GB would be scanned")
    if a.dry_run:
        return
    max_gb = float(env("BQ_MAX_GB", "400"))
    if gb > max_gb:
        raise SystemExit(f"bigrams: estimate {gb:.0f} GB exceeds BQ_MAX_GB={max_gb:g}; not running")
    job = client.query(sql)
    it = job.result(page_size=100_000)
    log(f"bigrams: query done; billed {job.total_bytes_billed/1e9:.1f} GB; slot {job.slot_millis/6e4:.1f} min; downloading")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with gzip.open(OUT, "wt", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["bigram", "year", "count", "n_assignees", "n_cpc"])
        for r in it:
            w.writerow([r["bigram"], int(r["yr"]), int(r["n"]), int(r["n_asg"]), int(r["n_cpc"])]); n += 1
            if n % 1_000_000 == 0:
                log(f"  {n:,} rows")
    log(f"bigrams: wrote {OUT.name} with {n:,} rows ({OUT.stat().st_size/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
