"""USPTO patent yearly counts (abstract phrase match, by grant date).

STATUS: experimental. PatentsView moved under data.uspto.gov in 2025; the request
schema below follows the PatentsView Search API v1 convention (POST JSON, X-Api-Key).
If the endpoint has changed, set USPTO_API_BASE (repository variable) and adjust `query()`.
Skips silently when USPTO_API_KEY is not set so the rest of the pipeline keeps running.
"""
from __future__ import annotations

import time

import requests

from collectors.common import (ALL, env, load_counts, load_settings, load_technologies, log,
                               needs_collection, save_counts, upsert, year_range)

SOURCE = "uspto"
DEFAULT_BASE = "https://search.patentsview.org/api/v1/patent/"


def query(base: str, key: str, keywords: list[str] | None, year: int) -> int:
    clauses = [{"_gte": {"patent_date": f"{year}-01-01"}},
               {"_lte": {"patent_date": f"{year}-12-31"}}]
    if keywords:
        clauses.append({"_or": [{"_text_phrase": {"patent_abstract": k}} for k in keywords]})
    body = {"q": {"_and": clauses}, "f": ["patent_id"], "o": {"size": 1}}
    for attempt in range(4):
        r = requests.post(base, json=body, headers={"X-Api-Key": key}, timeout=60)
        if r.status_code == 429:
            time.sleep(2 ** attempt); continue
        r.raise_for_status()
        return int(r.json().get("total_hits", 0))
    raise RuntimeError("uspto: rate limited repeatedly")


def main() -> None:
    settings = load_settings()
    cfg = settings["sources"][SOURCE]
    key = env("USPTO_API_KEY")
    if not cfg.get("enabled", True) or not key:
        log(f"{SOURCE}: skipped (disabled or USPTO_API_KEY missing)"); return
    base = env("USPTO_API_BASE", DEFAULT_BASE)
    techs = [t for t in load_technologies() if t["arm"] in cfg["arms"]]
    years = year_range(settings)
    existing = load_counts()
    n = 0
    for y in years:
        if needs_collection(existing, ALL, SOURCE, y, settings):
            upsert(existing, ALL, SOURCE, y, query(base, key, None, y)); n += 1
            time.sleep(1.5)
    for t in techs:
        for y in years:
            if not needs_collection(existing, t["id"], SOURCE, y, settings):
                continue
            upsert(existing, t["id"], SOURCE, y, query(base, key, t["keywords"], y)); n += 1
            time.sleep(1.5)
        log(f"{SOURCE}: {t['id']} done")
        save_counts(existing)
    save_counts(existing)
    log(f"{SOURCE}: {n} rows collected/refreshed")


if __name__ == "__main__":
    main()
