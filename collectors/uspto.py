"""USPTO patent-application yearly counts via the Open Data Portal (ODP) search API.

PatentsView's search.patentsview.org stopped resolving after the 2026-03-20 migration to ODP.
Verified 2026-11-04 on the Actions runner:
  POST https://api.uspto.gov/api/v1/patent/applications/search   header X-API-KEY
  body {"q": '<lucene>', "pagination": {"offset": 0, "limit": 1}}  -> {"count": N, ...}
  Searchable text field: applicationMetaData.inventionTitle (abstract is NOT exposed -> 404).
  Date fields: applicationMetaData.filingDate / grantDate, range syntax [YYYY-MM-DD TO YYYY-MM-DD].

We count by FILING year (what Kalyani et al. use; grants lag filings by 2-3 years). Applications
become visible at publication (~18 months after filing), so the last ~2 years are undercounted;
settings.years.refresh_last_n re-collects them weekly. Utility applications only.
Denominator (__all): all utility applications filed that year.
"""
from __future__ import annotations

import time

import requests

from collectors.common import (ALL, env, load_counts, load_settings, load_technologies, log,
                               needs_collection, save_counts, upsert, year_range)

SOURCE = "uspto"
DEFAULT_BASE = "https://api.uspto.gov/api/v1/patent/applications/search"
TITLE = "applicationMetaData.inventionTitle"
DATE = "applicationMetaData.filingDate"
UTILITY = 'applicationMetaData.applicationTypeLabelName:Utility'


def build_q(keywords: list[str] | None, year: int) -> str:
    parts = [UTILITY, f"{DATE}:[{year}-01-01 TO {year}-12-31]"]
    if keywords:
        parts.append("(" + " OR ".join(f'{TITLE}:"{k}"' for k in keywords) + ")")
    return " AND ".join(parts)


def query(base: str, key: str, keywords: list[str] | None, year: int) -> int:
    body = {"q": build_q(keywords, year), "pagination": {"offset": 0, "limit": 1}}
    headers = {"X-API-KEY": key, "Accept": "application/json", "Content-Type": "application/json"}
    for attempt in range(6):
        r = requests.post(base, json=body, headers=headers, timeout=90)
        if r.status_code == 429 or r.status_code >= 500:
            wait = 30 * (2 ** attempt)
            log(f"  uspto {r.status_code}; sleeping {wait}s"); time.sleep(wait); continue
        if r.status_code == 404:
            # ODP returns 404 "No matching records found" for a zero-hit query (verified 2026-11-04);
            # an unknown field name is also a 404, so distinguish by message.
            msg = ""
            try:
                msg = str(r.json().get("detailedMessage") or r.json().get("message") or "")
            except Exception:  # noqa: BLE001
                pass
            if "No matching records" in msg:
                return 0
            raise RuntimeError(f"uspto 404: {msg[:200]} :: q={body['q'][:120]}")
        r.raise_for_status()
        return int(r.json().get("count", 0))
    raise RuntimeError("uspto: repeated 429/5xx")


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
    save_counts(existing)
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
