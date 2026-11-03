"""Diagnostics run on the Actions runner (this sandbox cannot reach arxiv.org / sec.gov)."""
from __future__ import annotations

import re
import time

import requests

BASE = "https://export.arxiv.org/api/query"
for mr in (0, 1):
    for q in ['abs:"additive manufacturing"',
              '(abs:"3d printing" OR abs:"additive manufacturing") AND submittedDate:[201201010000 TO 201212312359]']:
        time.sleep(3)
        r = requests.get(BASE, params={"search_query": q, "max_results": mr}, timeout=60)
        m = re.search(r"<opensearch:totalResults[^>]*>(\d+)<", r.text)
        err = re.search(r"<summary>(.*?)</summary>", r.text, re.S)
        print(f"ARXIV max_results={mr} | {q} -> status {r.status_code} total={m.group(1) if m else None} "
              f"error={err.group(1).strip()[:300] if err else None}")
