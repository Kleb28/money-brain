"""PubMed yearly counts via NCBI E-utilities esearch (rettype=count).

One call per (technology, year) + one denominator call per year.
Uses NCBI_API_KEY if present (10 req/s) else 3 req/s.
"""
from __future__ import annotations

from collectors.common import (ALL, RateLimiter, env, get_json, load_counts, load_settings,
                               load_technologies, log, needs_collection, save_counts, upsert,
                               year_range)

SOURCE = "pubmed"
ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"


def build_query(keywords: list[str], field: str, year: int) -> str:
    terms = " OR ".join(f'"{k}"[{field}]' for k in keywords)
    return f"({terms}) AND {year}[dp]"


def count(query: str, key: str | None, rl: RateLimiter) -> int:
    rl.wait()
    params = {"db": "pubmed", "term": query, "rettype": "count", "retmode": "json"}
    if key:
        params["api_key"] = key
    data = get_json(ESEARCH, params=params)
    return int(data["esearchresult"]["count"])


def main() -> None:
    settings = load_settings()
    cfg = settings["sources"][SOURCE]
    if not cfg.get("enabled", True):
        log(f"{SOURCE}: disabled"); return
    key = env("NCBI_API_KEY")
    rl = RateLimiter(9.0 if key else 2.5)
    techs = [t for t in load_technologies() if t["arm"] in cfg["arms"]]
    years = year_range(settings)
    existing = load_counts()
    n = 0
    for y in years:
        if needs_collection(existing, ALL, SOURCE, y, settings):
            c = count(f"journal article[pt] AND {y}[dp]", key, rl)
            upsert(existing, ALL, SOURCE, y, c); n += 1
    for t in techs:
        for y in years:
            if not needs_collection(existing, t["id"], SOURCE, y, settings):
                continue
            c = count(build_query(t["keywords"], cfg["field"], y), key, rl)
            upsert(existing, t["id"], SOURCE, y, c); n += 1
        log(f"{SOURCE}: {t['id']} done")
        save_counts(existing)
    save_counts(existing)
    log(f"{SOURCE}: {n} rows collected/refreshed")


if __name__ == "__main__":
    main()
