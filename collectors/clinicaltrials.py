"""ClinicalTrials.gov API v2 yearly counts of studies (by start date) matching a technology.

query.term searches title/intervention/keywords; countTotal=true returns totalCount.
Bio arm only. Denominator = all studies starting that year.
"""
from __future__ import annotations

from collectors.common import (ALL, RateLimiter, get_json, load_counts, load_settings,
                               load_technologies, log, needs_collection, save_counts, upsert,
                               year_range)

SOURCE = "clinicaltrials"
API = "https://clinicaltrials.gov/api/v2/studies"


def total(term: str | None, year: int, rl: RateLimiter) -> int:
    rl.wait()
    params = {"filter.advanced": f"AREA[StartDate]RANGE[{year}-01-01,{year}-12-31]",
              "countTotal": "true", "pageSize": 1, "fields": "NCTId"}
    if term:
        params["query.term"] = term
    data = get_json(API, params=params, headers={"Accept": "application/json"})
    return int(data.get("totalCount", 0))


def build_term(keywords: list[str]) -> str:
    return " OR ".join(f'"{k}"' for k in keywords)


def main() -> None:
    settings = load_settings()
    cfg = settings["sources"][SOURCE]
    if not cfg.get("enabled", True):
        log(f"{SOURCE}: disabled"); return
    rl = RateLimiter(3.0)
    techs = [t for t in load_technologies() if t["arm"] in cfg["arms"]]
    years = year_range(settings)
    existing = load_counts()
    n = 0
    for y in years:
        if needs_collection(existing, ALL, SOURCE, y, settings):
            upsert(existing, ALL, SOURCE, y, total(None, y, rl)); n += 1
    for t in techs:
        for y in years:
            if not needs_collection(existing, t["id"], SOURCE, y, settings):
                continue
            upsert(existing, t["id"], SOURCE, y, total(build_term(t["keywords"]), y, rl)); n += 1
        log(f"{SOURCE}: {t['id']} done")
        save_counts(existing)
    save_counts(existing)
    log(f"{SOURCE}: {n} rows collected/refreshed")


if __name__ == "__main__":
    main()
