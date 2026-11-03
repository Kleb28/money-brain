"""arXiv yearly counts via the arXiv API (max_results=0 -> opensearch:totalResults).

Denominator: monthly submission statistics from arxiv.org/stats, summed per year.
arXiv asks for >= 3 s between API requests.
"""
from __future__ import annotations

import re
import time

from collectors.common import (ALL, env, get_json, load_counts, load_settings, load_technologies,
                               log, needs_collection, save_counts, upsert, year_range)

SOURCE = "arxiv"
API = "http://export.arxiv.org/api/query"
STATS = "https://arxiv.org/stats/get_monthly_submissions"


def build_query(keywords: list[str], field: str, year: int) -> str:
    terms = " OR ".join(f'{field}:"{k}"' for k in keywords)
    return f"({terms}) AND submittedDate:[{year}01010000 TO {year}12312359]"


def total_results(query: str, sleep: float) -> int:
    time.sleep(sleep)
    text = get_json(API, params={"search_query": query, "max_results": 0})
    m = re.search(r"<opensearch:totalResults[^>]*>(\d+)<", text)
    if not m:
        raise RuntimeError("arXiv: totalResults not found in response")
    return int(m.group(1))


def yearly_totals() -> dict[int, int]:
    """CSV like: month,submissions,historical_delta  (month = YYYY-MM)."""
    text = get_json(STATS)
    out: dict[int, int] = {}
    for line in text.splitlines()[1:]:
        parts = line.split(",")
        if len(parts) < 2 or not re.match(r"\d{4}-\d{2}", parts[0]):
            continue
        out[int(parts[0][:4])] = out.get(int(parts[0][:4]), 0) + int(parts[1])
    return out


def main() -> None:
    settings = load_settings()
    cfg = settings["sources"][SOURCE]
    if not cfg.get("enabled", True):
        log(f"{SOURCE}: disabled"); return
    sleep = float(cfg.get("sleep_seconds", 3))
    techs = [t for t in load_technologies() if t["arm"] in cfg["arms"]]
    years = year_range(settings)
    existing = load_counts()
    try:
        totals = yearly_totals()
        for y in years:
            if y in totals:
                upsert(existing, ALL, SOURCE, y, totals[y])
    except Exception as e:  # noqa: BLE001
        log(f"{SOURCE}: denominator fetch failed ({e}); keeping old values")
    n = 0
    for t in techs:
        for y in years:
            if not needs_collection(existing, t["id"], SOURCE, y, settings):
                continue
            c = total_results(build_query(t["keywords"], cfg["field"], y), sleep)
            upsert(existing, t["id"], SOURCE, y, c); n += 1
        log(f"{SOURCE}: {t['id']} done")
        save_counts(existing)
    save_counts(existing)
    log(f"{SOURCE}: {n} rows collected/refreshed")


if __name__ == "__main__":
    main()
