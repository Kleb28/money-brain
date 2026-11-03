"""SEC EDGAR full-text search (EFTS) yearly counts of 10-K filings mentioning a technology.

Endpoint: https://efts.sec.gov/LATEST/search-index  (undocumented but public; 2001+ only)
Returns hits.total.value; relation may be "gte" when capped at 10,000 -> stored as-is and
flagged in the log. Boolean semantics verified 2026-11-03: `"a" OR "b"` = union,
`"a" "b"` = intersection. SEC requires a descriptive User-Agent with contact info:
set repository variable EDGAR_USER_AGENT, e.g. "money-brain research you@example.com".
Rate limit: < 10 req/s across sec.gov.

Denominator (__all): number of form-type "10-K" entries in the quarterly master index
https://www.sec.gov/Archives/edgar/full-index/<year>/QTR<n>/form.gz (exact "10-K", matching
the EFTS forms=10-K filter). EFTS itself caps totals at 10,000 so it cannot be the denominator.
"""
from __future__ import annotations

import gzip
import io

import requests

from collectors.common import (ALL, RateLimiter, env, get_json, load_counts, load_settings,
                               load_technologies, log, needs_collection, save_counts, upsert,
                               year_range)

SOURCE = "edgar_10k"
EFTS = "https://efts.sec.gov/LATEST/search-index"
FULL_INDEX = "https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{q}/form.gz"


def build_query(keywords: list[str]) -> str:
    return " OR ".join(f'"{k}"' for k in keywords)


def count_10k_in_index(year: int, headers: dict, rl: RateLimiter) -> int | None:
    """Exact '10-K' rows summed over the year's quarters; None if the year is not yet indexed."""
    total, found = 0, False
    for q in (1, 2, 3, 4):
        rl.wait()
        r = requests.get(FULL_INDEX.format(year=year, q=q), headers=headers, timeout=180)
        if r.status_code == 404:
            continue
        r.raise_for_status()
        found = True
        with gzip.open(io.BytesIO(r.content), "rt", encoding="latin-1") as f:
            for line in f:
                if line.startswith("10-K "):
                    total += 1
    return total if found else None


def hits(query: str, forms: str, year: int, headers: dict, rl: RateLimiter) -> int:
    rl.wait()
    params = {"q": query, "forms": forms, "dateRange": "custom",
              "startdt": f"{year}-01-01", "enddt": f"{year}-12-31"}
    data = get_json(EFTS, params=params, headers=headers)
    total = data.get("hits", {}).get("total", {})
    if total.get("relation") == "gte":
        log(f"  edgar: count capped (>= {total.get('value')}) for {query[:40]}… {year}")
    return int(total.get("value", 0))


def main() -> None:
    settings = load_settings()
    cfg = settings["sources"][SOURCE.split("_")[0]]
    if not cfg.get("enabled", True):
        log(f"{SOURCE}: disabled"); return
    ua = env("EDGAR_USER_AGENT")
    if not ua:
        log(f"{SOURCE}: EDGAR_USER_AGENT not set; SEC may reject with 403. Using generic UA.")
        ua = "money-brain-collector (set EDGAR_USER_AGENT)"
    headers = {"User-Agent": ua, "Accept": "application/json"}
    rl = RateLimiter(5.0)
    forms = cfg.get("forms", "10-K")
    techs = [t for t in load_technologies() if t["arm"] in cfg["arms"]]
    years = year_range(settings)
    existing = load_counts()
    n = 0
    for y in years:
        if needs_collection(existing, ALL, SOURCE, y, settings):
            c = count_10k_in_index(y, headers, rl)
            if c is not None:
                upsert(existing, ALL, SOURCE, y, c); n += 1
    save_counts(existing)
    for t in techs:
        for y in years:
            if not needs_collection(existing, t["id"], SOURCE, y, settings):
                continue
            c = hits(build_query(t["keywords"]), forms, y, headers, rl)
            upsert(existing, t["id"], SOURCE, y, c); n += 1
        log(f"{SOURCE}: {t['id']} done")
        save_counts(existing)
    save_counts(existing)
    log(f"{SOURCE}: {n} rows collected/refreshed")


if __name__ == "__main__":
    main()
