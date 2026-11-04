"""Reduce the techdiffusion.net firm-level file (15 GB .dta, 49.9M rows) to the rows usable for a
returns backtest: Compustat-matched firms (gvkey not null) with at least one technology posting in
the year. Output data/external/firm_tech_year.csv.gz (gvkey, cluster_id, poster_name, tech, year,
tech_hiring, total_jobs). Streams in chunks; nothing else is kept in memory."""
from __future__ import annotations

import os
import time

import pandas as pd
import pyreadstat
import requests

URL = "https://www.dropbox.com/scl/fi/d9zs9d9ibmcz9qzf0d484/firm_data.dta?rlkey=7t16qwoyiqpjs2hh01py3ohtv&dl=1"
H = {"User-Agent": "Mozilla/5.0 (money-brain research probe)"}
TMP = "/tmp/dnt/firm_data.dta"
OUT = "data/external/firm_tech_year.csv.gz"
os.makedirs("/tmp/dnt", exist_ok=True)
os.makedirs("data/external", exist_ok=True)

t0 = time.time()
with requests.get(URL, headers=H, timeout=900, stream=True) as r:
    r.raise_for_status()
    with open(TMP, "wb") as f:
        for chunk in r.iter_content(1 << 22):
            f.write(chunk)
print(f"downloaded {os.path.getsize(TMP)/1e6:.0f} MB in {time.time()-t0:.0f}s", flush=True)

parts, n, kept, firms_total = [], 0, 0, 0
for df, _ in pyreadstat.read_file_in_chunks(pyreadstat.read_dta, TMP, chunksize=3_000_000,
                                             usecols=["year", "tech", "cluster_id", "total_jobs", "tech_hiring", "gvkey", "poster_name"]):
    sub = df[df["gvkey"].notna() & (df["tech_hiring"] > 0)]
    parts.append(sub)
    n += len(df); kept += len(sub)
    print(f"  {n:,} rows read; {kept:,} kept; {time.time()-t0:.0f}s", flush=True)
out = pd.concat(parts, ignore_index=True)
out["gvkey"] = out["gvkey"].astype(int)
out = out[["gvkey", "cluster_id", "poster_name", "tech", "year", "tech_hiring", "total_jobs"]].sort_values(["gvkey", "tech", "year"])
out.to_csv(OUT, index=False, compression="gzip")
print("rows", len(out), "firms", out.gvkey.nunique(), "techs", out.tech.nunique(), "size MB", os.path.getsize(OUT) / 1e6, flush=True)
if os.path.getsize(OUT) > 90e6:
    os.remove(OUT); print("too large to commit; removed", flush=True)
os.remove(TMP)
