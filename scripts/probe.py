"""Diagnostics run on the Actions runner (this sandbox cannot reach arxiv.org / sec.gov).
Prints raw API behaviour so query syntax and denominators can be fixed from the log.
"""
from __future__ import annotations

import json
import os
import re
import time

import requests

UA = os.environ.get("EDGAR_USER_AGENT", "money-brain probe")


def show(label, r):
    body = r.text[:600].replace("\n", " ")
    print(f"--- {label}\n  status={r.status_code} ctype={r.headers.get('content-type')}\n  body={body}\n")


# ---------- arXiv ----------
for base in ("https://export.arxiv.org/api/query", "http://export.arxiv.org/api/query"):
    for q in ['abs:"additive manufacturing"',
              '(abs:"3d printing" OR abs:"additive manufacturing")',
              'abs:"additive manufacturing" AND submittedDate:[201201010000 TO 201212312359]',
              '(abs:"3d printing" OR abs:"additive manufacturing") AND submittedDate:[201201010000 TO 201212312359]',
              'abs:%22additive%20manufacturing%22+AND+submittedDate:[201201010000+TO+201212312359]']:
        time.sleep(3)
        try:
            if "%22" in q:
                r = requests.get(f"{base}?search_query={q}&max_results=0", timeout=60)
            else:
                r = requests.get(base, params={"search_query": q, "max_results": 0}, timeout=60)
            m = re.search(r"<opensearch:totalResults[^>]*>(\d+)<", r.text)
            print(f"ARXIV {base[:5]} | {q} -> status {r.status_code} total={m.group(1) if m else None} url={r.url}")
            if r.status_code != 200:
                show("arxiv error body", r)
        except Exception as e:  # noqa: BLE001
            print(f"ARXIV {q} -> EXC {e}")
    break  # https only unless it fails entirely

for url in ("https://arxiv.org/stats/get_monthly_submissions", "https://arxiv.org/stats/monthly_submissions"):
    try:
        r = requests.get(url, timeout=60, headers={"User-Agent": "money-brain probe"})
        show(f"arxiv stats {url}", r)
    except Exception as e:  # noqa: BLE001
        print(f"arxiv stats {url} EXC {e}")

# ---------- EDGAR ----------
H = {"User-Agent": UA, "Accept": "application/json"}
EFTS = "https://efts.sec.gov/LATEST/search-index"
tests = [
    ('"cloud computing"', "single phrase"),
    ('"cloud computing" OR "cloud services"', "OR two phrases"),
    ('"cloud computing" "cloud services"', "two phrases, space"),
    ('"cloud computing" | "cloud services"', "pipe"),
    ('"cloud services"', "second phrase alone"),
]
for q, label in tests:
    time.sleep(0.3)
    r = requests.get(EFTS, params={"q": q, "forms": "10-K", "dateRange": "custom",
                                   "startdt": "2018-01-01", "enddt": "2018-12-31"}, headers=H, timeout=60)
    try:
        d = r.json(); tot = d["hits"]["total"]
        print(f"EDGAR 2018 [{label}] q={q} -> {tot}")
        if label == "single phrase":
            h = d["hits"]["hits"][0]["_source"]
            print("  first hit keys:", sorted(h.keys()))
            print("  first hit sample:", json.dumps({k: h[k] for k in ("form", "file_type", "file_date", "display_names") if k in h})[:300])
            print("  aggregations keys:", list(d.get("aggregations", {}).keys()))
            ft = d.get("aggregations", {}).get("form_filter", {}).get("buckets", [])[:5]
            print("  form_filter buckets:", ft)
    except Exception as e:  # noqa: BLE001
        show(f"EDGAR [{label}] parse fail {e}", r)

# denominator candidate: full-index form.idx
r = requests.get("https://www.sec.gov/Archives/edgar/full-index/2018/QTR1/form.idx", headers={"User-Agent": UA}, timeout=120)
print(f"form.idx status={r.status_code} len={len(r.text)}")
lines = r.text.splitlines()
n10k = sum(1 for ln in lines if ln.startswith("10-K ") )
n10k_all = sum(1 for ln in lines if ln.split("  ")[0].strip() in ("10-K", "10-K405", "10-KSB", "10-K/A"))
print(f"form.idx 2018 QTR1: lines={len(lines)} 10-K exact={n10k} 10-K family={n10k_all}")
print("form.idx header sample:", lines[:12])
