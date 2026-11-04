"""Aggregate the techdiffusion.net location-level file (1.7 GB .dta, 14.4M rows) to one job-posting
share series per technology bigram and year, 2010-2019. Written to data/external/jobs_by_tech_year.csv
(tech, title, start_year, year, tech_hiring, total_jobs). Streams the file in chunks; nothing is held
in memory beyond the running sums."""
from __future__ import annotations

import os
import time
from collections import defaultdict

import pandas as pd
import pyreadstat
import requests

URL = "https://www.dropbox.com/scl/fi/dy1yhzp3padagsvg2189t/location_data.dta?rlkey=5r9xyvlsn2h5dqbh1u20tm12r&dl=1"
H = {"User-Agent": "Mozilla/5.0 (money-brain research probe)"}
TMP = "/tmp/dnt/location_data.dta"
OUT = "data/external/jobs_by_tech_year.csv"
os.makedirs("/tmp/dnt", exist_ok=True)
os.makedirs("data/external", exist_ok=True)

t0 = time.time()
with requests.get(URL, headers=H, timeout=600, stream=True) as r:
    r.raise_for_status()
    with open(TMP, "wb") as f:
        for chunk in r.iter_content(1 << 22):
            f.write(chunk)
print(f"downloaded {os.path.getsize(TMP)/1e6:.0f} MB in {time.time()-t0:.0f}s", flush=True)

hiring = defaultdict(int)
jobs = defaultdict(int)
meta_rows = {}
n = 0
for df, _ in pyreadstat.read_file_in_chunks(pyreadstat.read_dta, TMP, chunksize=2_000_000):
    g = df.groupby(["tech", "year"], as_index=False).agg(h=("tech_hiring", "sum"), t=("total_jobs", "sum"))
    for row in g.itertuples(index=False):
        hiring[(row.tech, int(row.year))] += int(row.h)
        jobs[(row.tech, int(row.year))] += int(row.t)
    m = df.drop_duplicates("tech")[["tech", "title", "start_year"]]
    for row in m.itertuples(index=False):
        meta_rows.setdefault(row.tech, (row.title, int(row.start_year)))
    n += len(df)
    print(f"  {n:,} rows; {len(hiring):,} tech-years; {time.time()-t0:.0f}s", flush=True)

rows = [{"tech": k[0], "title": meta_rows[k[0]][0], "start_year": meta_rows[k[0]][1], "year": k[1],
         "tech_hiring": hiring[k], "total_jobs": jobs[k]} for k in sorted(hiring)]
out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)
print("techs", out.tech.nunique(), "years", sorted(out.year.unique()), "rows", len(out), flush=True)
print(out.groupby("year").total_jobs.max().to_string(), flush=True)
os.remove(TMP)
