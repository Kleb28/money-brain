"""Inspect the techdiffusion.net data release (Dropbox, public links).
Streams each .dta to disk, prints metadata (rows / columns / labels) via pyreadstat without
loading the whole file, then loads only files under SIZE_FULL_MB fully and saves them as
gzipped CSV under data/external/ (committed when < 80 MB). Large files: first 200k rows only."""
from __future__ import annotations

import os
import sys
import time

import pandas as pd
import pyreadstat
import requests

FILES = {
    "tech_summary": "https://www.dropbox.com/scl/fi/fy91fcnt1x1867metwejb/tech_summary.dta?rlkey=8uylqptj9hvm67hsdvyci2ao1&st=lrxn1wgx&dl=1",
    "Compustat_clusters": "https://www.dropbox.com/scl/fi/c2rr6y2dobtv2orxoh0cs/Compustat_clusters.dta?rlkey=02rab8bkjb1ezcvf6tvyxa62w&dl=1",
    "industry_data": "https://www.dropbox.com/scl/fi/fj8uahro39824k4uzplt9/industry_data.dta?rlkey=z5x1zrn0uf8ob4an9qjs1otdk&dl=1",
    "firm_data": "https://www.dropbox.com/scl/fi/d9zs9d9ibmcz9qzf0d484/firm_data.dta?rlkey=7t16qwoyiqpjs2hh01py3ohtv&dl=1",
    "location_data": "https://www.dropbox.com/scl/fi/dy1yhzp3padagsvg2189t/location_data.dta?rlkey=5r9xyvlsn2h5dqbh1u20tm12r&dl=1",
    "occupation_data": "https://www.dropbox.com/scl/fi/0bzr9u25bg03w641y4qup/occupation_data.dta?rlkey=l5nvur3utam4bbun4p0sz6p68&dl=1",
}
H = {"User-Agent": "Mozilla/5.0 (money-brain research probe)"}
SIZE_FULL_MB = 400
TMP = "/tmp/dnt"
os.makedirs("data/external", exist_ok=True)
os.makedirs(TMP, exist_ok=True)
pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 60)


def log(*a):
    print(*a, flush=True)


for name, url in FILES.items():
    log(f"\n==================== {name}")
    path = f"{TMP}/{name}.dta"
    try:
        t0 = time.time()
        with requests.get(url, headers=H, timeout=600, stream=True, allow_redirects=True) as r:
            log("status", r.status_code, "ctype", r.headers.get("content-type"), "len", r.headers.get("content-length"))
            if r.status_code != 200:
                log("body head:", r.text[:300]); continue
            with open(path, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)
        mb = os.path.getsize(path) / 1e6
        log(f"downloaded {mb:.1f} MB in {time.time()-t0:.0f}s")
        _, meta = pyreadstat.read_dta(path, metadataonly=True)
        log("rows", meta.number_rows, "cols", meta.number_columns)
        for c in meta.column_names:
            log(f"  {c:30s} {meta.readstat_variable_types.get(c, '?'):8s} {meta.column_names_to_labels.get(c, '')}")
        if mb <= SIZE_FULL_MB:
            df = pd.read_stata(path)
        else:
            df, _ = pyreadstat.read_dta(path, row_limit=200_000)
            log("(large file: first 200k rows only)")
        log("shape", df.shape)
        log(df.head(10).to_string())
        for c in df.columns:
            lc = c.lower()
            if "year" in lc or lc in ("fyear", "yr", "date"):
                log(f"  {c}: min {df[c].min()} max {df[c].max()}")
            if df[c].dtype == object:
                n = df[c].nunique()
                log(f"  {c}: {n} unique; sample {list(df[c].dropna().unique()[:10])}")
        if mb <= SIZE_FULL_MB:
            out = f"data/external/{name}.csv.gz"
            df.to_csv(out, index=False, compression="gzip")
            sz = os.path.getsize(out) / 1e6
            log(f"saved {out} {sz:.1f} MB")
            if sz > 80:
                os.remove(out); log("  too large to commit; removed")
        del df
        os.remove(path)
    except Exception as e:  # noqa: BLE001
        log("EXC", repr(e)[:500])
sys.stdout.flush()
