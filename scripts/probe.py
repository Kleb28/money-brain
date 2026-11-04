"""Inspect the techdiffusion.net data release (Dropbox, public links). Downloads each .dta,
prints shape / columns / head / key ranges, and saves a gzipped CSV under data/external/
when the file is small enough to commit (< 80 MB)."""
from __future__ import annotations

import io
import os
import sys

import pandas as pd
import requests

FILES = {
    "tech_summary": "https://www.dropbox.com/scl/fi/fy91fcnt1x1867metwejb/tech_summary.dta?rlkey=8uylqptj9hvm67hsdvyci2ao1&st=lrxn1wgx&dl=1",
    "firm_data": "https://www.dropbox.com/scl/fi/d9zs9d9ibmcz9qzf0d484/firm_data.dta?rlkey=7t16qwoyiqpjs2hh01py3ohtv&dl=1",
    "industry_data": "https://www.dropbox.com/scl/fi/fj8uahro39824k4uzplt9/industry_data.dta?rlkey=z5x1zrn0uf8ob4an9qjs1otdk&dl=1",
    "Compustat_clusters": "https://www.dropbox.com/scl/fi/c2rr6y2dobtv2orxoh0cs/Compustat_clusters.dta?rlkey=02rab8bkjb1ezcvf6tvyxa62w&dl=1",
    "location_data": "https://www.dropbox.com/scl/fi/dy1yhzp3padagsvg2189t/location_data.dta?rlkey=5r9xyvlsn2h5dqbh1u20tm12r&dl=1",
    "occupation_data": "https://www.dropbox.com/scl/fi/0bzr9u25bg03w641y4qup/occupation_data.dta?rlkey=l5nvur3utam4bbun4p0sz6p68&dl=1",
}
H = {"User-Agent": "Mozilla/5.0 (money-brain research probe)"}
os.makedirs("data/external", exist_ok=True)
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)

for name, url in FILES.items():
    print(f"\n==================== {name}")
    try:
        r = requests.get(url, headers=H, timeout=600, allow_redirects=True)
        print("status", r.status_code, "bytes", len(r.content), "ctype", r.headers.get("content-type"))
        if r.status_code != 200 or len(r.content) < 1000:
            print("body head:", r.text[:300]); continue
        df = pd.read_stata(io.BytesIO(r.content))
        print("shape", df.shape)
        print("columns", list(df.columns))
        print(df.dtypes.to_string())
        print(df.head(8).to_string())
        for c in df.columns:
            if "year" in c.lower() or c.lower() in ("fyear", "yr"):
                print(f"  {c}: min {df[c].min()} max {df[c].max()}")
            if df[c].dtype == object and df[c].nunique() < 5000:
                print(f"  {c}: {df[c].nunique()} unique; sample {list(df[c].dropna().unique()[:8])}")
        out = f"data/external/{name}.csv.gz"
        df.to_csv(out, index=False, compression="gzip")
        sz = os.path.getsize(out)
        print("saved", out, sz, "bytes")
        if sz > 80 * 1024 * 1024:
            os.remove(out); print("  too large to commit; removed")
    except Exception as e:  # noqa: BLE001
        print("EXC", repr(e)[:400])
sys.stdout.flush()
