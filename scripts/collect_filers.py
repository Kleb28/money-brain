"""Sim B input: for each (bigram, filing year) in simulation/filer_queries.csv, list the 10-K filers
(EDGAR full-text search display_names → entity, ticker, CIK). Output data/external/sim_filers_<shard>.csv.
Resumable; commits progress like scripts/collect_oos.py. Up to MAX_PAGES × 100 filings per query."""
from __future__ import annotations

import argparse
import csv
import re
import time
from pathlib import Path

import requests

from collectors.common import RateLimiter, env, log
from collectors.edgar import EFTS
from scripts.collect_oos import git_commit

ROOT = Path(__file__).resolve().parents[1]
MAX_PAGES = 5
COMMIT_EVERY = 150


def filers(phrase: str, year: int, headers: dict, rl: RateLimiter) -> list[tuple[str, str, str, int]]:
    seen: dict[str, int] = {}
    for page in range(1, MAX_PAGES + 1):
        rl.wait()
        params = {"q": f'"{phrase}"', "forms": "10-K", "dateRange": "custom",
                  "startdt": f"{year}-01-01", "enddt": f"{year}-12-31", "page": page, "from": (page - 1) * 100}
        for attempt in range(4):
            r = requests.get(EFTS, params=params, headers=headers, timeout=60)
            if r.status_code == 200:
                break
            time.sleep(10 * (attempt + 1))
        else:
            log(f"  {phrase} {year} p{page}: HTTP {r.status_code}"); break
        hs = r.json().get("hits", {}).get("hits", [])
        for h in hs:
            for name in h.get("_source", {}).get("display_names", []):
                seen[name] = seen.get(name, 0) + 1
        if len(hs) < 100:
            break
    out = []
    for name, n in seen.items():
        m = re.match(r"^(.*?)\s+\((\S+)\)\s+\(CIK (\d+)\)", name)
        if m:
            out.append((m.group(1).strip(), m.group(2), m.group(3), n))
        else:
            m2 = re.match(r"^(.*?)\s+\(CIK (\d+)\)", name)
            if m2:
                out.append((m2.group(1).strip(), "", m2.group(2), n))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", default="simulation/filer_queries.csv")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    ap.add_argument("--max-minutes", type=float, default=330)
    a = ap.parse_args()
    rows = [r for i, r in enumerate(csv.DictReader(open(ROOT / a.list, encoding="utf-8"))) if i % a.nshards == a.shard]
    out = ROOT / "data" / "external" / f"sim_filers_{a.shard}.csv"
    # keep everything in memory and rewrite the file before each commit: an open append handle
    # survives `git pull --rebase` on a stale inode and its later writes never reach the repo
    rows_out: list[list] = []
    done = set()
    if out.exists():
        for r in csv.DictReader(open(out, encoding="utf-8")):
            rows_out.append([r["bigram"], r["year"], r["entity"], r["ticker"], r["cik"], r["n_filings"]])
            done.add((r["bigram"], int(r["year"])))

    def save():
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["bigram", "year", "entity", "ticker", "cik", "n_filings"]); w.writerows(rows_out)

    headers = {"User-Agent": env("EDGAR_USER_AGENT") or "money-brain-collector (set EDGAR_USER_AGENT)", "Accept": "application/json"}
    rl = RateLimiter(4.0)
    t0 = time.time(); n_since = 0
    for i, r in enumerate(rows):
        key = (r["bigram"], int(r["year"]))
        if key in done:
            continue
        try:
            fl = filers(r["bigram"], int(r["year"]), headers, rl)
        except Exception as e:  # noqa: BLE001
            log(f"  {key}: {e!r}"[:200]); time.sleep(5); continue
        if not fl:
            rows_out.append([r["bigram"], r["year"], "", "", "", 0])
        for ent, tick, cik, n in fl:
            rows_out.append([r["bigram"], r["year"], ent, tick, cik, n])
        done.add(key); n_since += 1
        if n_since >= COMMIT_EVERY or (time.time() - t0) / 60 > a.max_minutes:
            save(); git_commit(out, f"data: sim filers shard {a.shard} progress ({i + 1}/{len(rows)})"); n_since = 0
            if (time.time() - t0) / 60 > a.max_minutes:
                log("time budget reached; exiting (resumable)"); break
    save()
    git_commit(out, f"data: sim filers shard {a.shard} ({len(done)} queries)")
    log(f"filers shard {a.shard}: {len(done)} queries done, {(time.time()-t0)/60:.0f} min")


if __name__ == "__main__":
    main()
