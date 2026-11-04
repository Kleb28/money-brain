"""Diagnostics run on the Actions runner: find valid ODP field names for the uspto collector."""
from __future__ import annotations

import os

import requests

KEY = os.environ.get("USPTO_API_KEY", "")
H = {"X-API-KEY": KEY, "Accept": "application/json", "Content-Type": "application/json"}
BASE = "https://api.uspto.gov/api/v1/patent/applications/search"

tests = [
    'applicationMetaData.filingDate:[2002-01-01 TO 2002-12-31]',
    'applicationMetaData.effectiveFilingDate:[2002-01-01 TO 2002-12-31]',
    'applicationMetaData.grantDate:[2002-01-01 TO 2002-12-31]',
    'applicationMetaData.applicationTypeLabelName:Utility',
    'applicationMetaData.applicationTypeLabelName:"Utility"',
    'applicationMetaData.applicationTypeCategory:Utility',
    'applicationMetaData.applicationTypeCode:UTL',
    'applicationMetaData.applicationTypeLabelName:Utility AND applicationMetaData.filingDate:[2012-01-01 TO 2012-12-31]',
    '(applicationMetaData.inventionTitle:"3d printing" OR applicationMetaData.inventionTitle:"additive manufacturing") AND applicationMetaData.filingDate:[2012-01-01 TO 2012-12-31]',
    'applicationMetaData.inventionTitle:("3d printing" OR "additive manufacturing") AND applicationMetaData.filingDate:[2012-01-01 TO 2012-12-31]',
]
for q in tests:
    r = requests.post(BASE, headers=H, json={"q": q, "pagination": {"offset": 0, "limit": 1}}, timeout=90)
    try:
        d = r.json()
    except Exception:  # noqa: BLE001
        d = {}
    print(f"[{r.status_code}] count={d.get('count')} msg={str(d.get('detailedMessage') or d.get('message') or '')[:160]} | q={q}")
    if r.status_code == 200 and d.get("patentFileWrapperDataBag"):
        m = d["patentFileWrapperDataBag"][0].get("applicationMetaData", {})
        print("      sample:", {k: m.get(k) for k in ("applicationTypeLabelName", "applicationTypeCategory", "applicationTypeCode", "filingDate", "grantDate")})
