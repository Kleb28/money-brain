"""Diagnostics run on the Actions runner. Current target: USPTO Open Data Portal search API
(PatentsView's search.patentsview.org stopped resolving after the 2026-03-20 migration)."""
from __future__ import annotations

import json
import os

import requests

KEY = os.environ.get("USPTO_API_KEY", "")
H = {"X-API-KEY": KEY, "Accept": "application/json", "Content-Type": "application/json"}
BASE = "https://api.uspto.gov/api/v1/patent/applications/search"
print("key present:", bool(KEY), "len", len(KEY))


def show(label, r):
    print(f"--- {label}: status={r.status_code}")
    try:
        d = r.json()
        print("  keys:", list(d.keys())[:12])
        for k in ("count", "total", "totalCount", "numFound"):
            if k in d:
                print(f"  {k} =", d[k])
        recs = d.get("patentFileWrapperDataBag") or d.get("patents") or d.get("results") or []
        if recs:
            rec = recs[0]
            print("  first record keys:", list(rec.keys())[:20])
            meta = rec.get("applicationMetaData", {})
            if meta:
                print("  applicationMetaData keys:", list(meta.keys())[:40])
                print("  sample:", json.dumps({k: meta.get(k) for k in ("inventionTitle", "grantDate", "filingDate", "cpcClassificationBag", "patentNumber")}, default=str)[:400])
    except Exception as e:  # noqa: BLE001
        print("  non-json:", r.text[:600].replace("\n", " "), e)


# D: bare search (schema discovery)
show("GET bare", requests.get(BASE, headers=H, params={"limit": 1}, timeout=60))
# A: GET with title phrase
show("GET title phrase", requests.get(BASE, headers=H, params={"q": 'applicationMetaData.inventionTitle:"additive manufacturing"', "limit": 1}, timeout=60))
# C: POST with range in q
body = {"q": 'applicationMetaData.inventionTitle:"additive manufacturing" AND applicationMetaData.grantDate:[2018-01-01 TO 2018-12-31]',
        "pagination": {"offset": 0, "limit": 1}}
show("POST q with grantDate range", requests.post(BASE, headers=H, json=body, timeout=60))
# B: POST with rangeFilters
body = {"q": 'applicationMetaData.inventionTitle:"additive manufacturing"',
        "rangeFilters": [{"field": "applicationMetaData.grantDate", "valueFrom": "2018-01-01", "valueTo": "2018-12-31"}],
        "pagination": {"offset": 0, "limit": 1}}
show("POST rangeFilters", requests.post(BASE, headers=H, json=body, timeout=60))
# E: abstract field guess
body = {"q": 'abstractText:"additive manufacturing" AND applicationMetaData.grantDate:[2018-01-01 TO 2018-12-31]',
        "pagination": {"offset": 0, "limit": 1}}
show("POST abstract guess", requests.post(BASE, headers=H, json=body, timeout=60))
# F: all granted in 2018 (denominator candidate)
body = {"q": 'applicationMetaData.grantDate:[2018-01-01 TO 2018-12-31]', "pagination": {"offset": 0, "limit": 1}}
show("POST denominator 2018", requests.post(BASE, headers=H, json=body, timeout=60))
# G: does search.patentsview.org resolve at all?
try:
    r = requests.get("https://search.patentsview.org/api/v1/patent/", headers={"X-Api-Key": KEY}, timeout=20)
    print("patentsview status", r.status_code, r.text[:200])
except Exception as e:  # noqa: BLE001
    print("patentsview EXC", str(e)[:200])
