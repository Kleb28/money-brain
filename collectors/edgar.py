"""SEC EDGAR full-text search (EFTS) yearly counts of 10-K filings mentioning a technology.

Endpoint: https://efts.sec.gov/LATEST/search-index  (undocumented but public; 2001+ only)
Returns hits.total.value; relation may be "gte" when capped at 10,000 -> stored as-is and
flagged in the log. SEC requires a descriptive User-Agent with contact info:
set repository variable EDGAR_USER_AGENT, e.g. "money-brain research you@example.com".
Rate limit: < 10 req/s across sec.gov.
"""
from __future__ import annotations

from collectors.common import (ALL, RateLimiter, env, get_json, load_counts, load_settings,
                               load_technologies, log, needs_collection, save_counts, upsert,
                               year_range)

SOURCE = "edgar_10k"
EFTS = "https://efts.sec.gov/LATEST/search-index"


def build_query(keywords: list[str]) -> str:
    return " OR ".join(f'"{k}"' for k in keywords)


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
            c = hits(cfg["denominator_query"], forms, y, headers, rl)
            upsert(existing, ALL, SOURCE, y, c); n += 1
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
