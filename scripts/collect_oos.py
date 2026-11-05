"""Collect yearly counts for the out-of-sample technology list (data/external/oos_technologies.csv).

Usage:  python -m scripts.collect_oos --source uspto|edgar --shard K --nshards N [--years 2002-2019]
Writes data/external/oos_counts_<source>_<K>.csv (technology_id, source, year, count); resumable —
existing rows are skipped. Commits progress every COMMIT_EVERY technologies when run in Actions
(GIT_COMMIT=1) so a killed runner loses little. Query functions are the same ones the weekly
collectors use (collectors/uspto.py, collectors/edgar.py), so counts are comparable with counts.csv.
"""
from __future__ import annotations

import argparse
import csv
import subprocess
import time
from pathlib import Path

from collectors import edgar, uspto
from collectors.common import RateLimiter, env, log

ROOT = Path(__file__).resolve().parents[1]
LIST = ROOT / "data" / "external" / "oos_technologies.csv"
COMMIT_EVERY = 60


def load_list(path: Path = LIST) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["keywords"] = [k.strip() for k in r["keywords"].split(";") if k.strip()]
    return rows


def load_done(path: Path) -> dict[tuple[str, int], int]:
    out = {}
    if path.exists():
        with open(path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                out[(r["technology_id"], int(r["year"]))] = int(r["count"])
    return out


def save(path: Path, source: str, done: dict) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["technology_id", "source", "year", "count"])
        for (tid, y) in sorted(done):
            w.writerow([tid, source, y, done[(tid, y)]])


def git_commit(path: Path, msg: str) -> None:
    if env("GIT_COMMIT") != "1":
        return
    try:
        subprocess.run(["git", "add", str(path)], cwd=ROOT, check=True)
        if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
            return
        subprocess.run(["git", "commit", "-q", "-m", msg], cwd=ROOT, check=True)
        for attempt in range(5):
            subprocess.run(["git", "pull", "-q", "--rebase", "origin", "main"], cwd=ROOT, check=False)
            if subprocess.run(["git", "push", "-q", "origin", "HEAD:main"], cwd=ROOT).returncode == 0:
                return
            time.sleep(10 + 10 * attempt)
        log("git push failed repeatedly; continuing (file is still on disk)")
    except Exception as e:  # noqa: BLE001
        log(f"git step failed: {e!r}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, choices=["uspto", "edgar"])
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    ap.add_argument("--years", default="2002-2019")
    ap.add_argument("--max-minutes", type=float, default=330)
    ap.add_argument("--list", default=str(LIST), help="CSV with id,keywords columns")
    ap.add_argument("--prefix", default="oos", help="output file prefix: data/external/<prefix>_counts_<source>_<shard>.csv")
    a = ap.parse_args()
    y0, y1 = (int(x) for x in a.years.split("-"))
    years = list(range(y0, y1 + 1))
    techs = [t for i, t in enumerate(load_list(Path(a.list))) if i % a.nshards == a.shard]
    src_name = "uspto" if a.source == "uspto" else edgar.SOURCE
    out = ROOT / "data" / "external" / f"{a.prefix}_counts_{a.source}_{a.shard}.csv"
    done = load_done(out)
    log(f"{a.source} shard {a.shard}/{a.nshards}: {len(techs)} technologies, {len(done)} rows already done")

    if a.source == "uspto":
        key = env("USPTO_API_KEY")
        if not key:
            raise SystemExit("USPTO_API_KEY missing")
        base = env("USPTO_API_BASE", uspto.DEFAULT_BASE)

        def count(t, y):
            c = uspto.query(base, key, t["keywords"], y); time.sleep(1.2); return c
    else:
        ua = env("EDGAR_USER_AGENT") or "money-brain-collector (set EDGAR_USER_AGENT)"
        headers = {"User-Agent": ua, "Accept": "application/json"}
        rl = RateLimiter(4.0)

        def count(t, y):
            return edgar.hits(edgar.build_query(t["keywords"]), "10-K", y, headers, rl)

    t_start = time.time()
    n_new, since_commit = 0, 0
    for i, t in enumerate(techs):
        todo = [y for y in years if (t["id"], y) not in done]
        for y in todo:
            try:
                done[(t["id"], y)] = count(t, y); n_new += 1
            except Exception as e:  # noqa: BLE001
                log(f"  {t['id']} {y}: {e!r}"[:300]); time.sleep(5)
        if todo:
            since_commit += 1
        if since_commit >= COMMIT_EVERY or (time.time() - t_start) / 60 > a.max_minutes:
            save(out, src_name, done)
            git_commit(out, f"data: oos {a.source} shard {a.shard} progress ({i + 1}/{len(techs)})")
            since_commit = 0
            if (time.time() - t_start) / 60 > a.max_minutes:
                log("time budget reached; exiting (resumable)"); break
    save(out, src_name, done)
    git_commit(out, f"data: oos {a.source} shard {a.shard} done ({len(done)} rows)")
    log(f"{a.source} shard {a.shard}: {n_new} new rows, {len(done)} total, {(time.time()-t_start)/60:.0f} min")


if __name__ == "__main__":
    main()
