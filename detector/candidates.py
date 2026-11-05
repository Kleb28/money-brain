"""Candidate discovery, stage 2: apply the pre-registered Rule G (config/settings.yml) to every bigram
in data/external/bigram_counts.csv.gz and list the ones whose signal is recent.

Arithmetic only — no scoring by an LLM. Steps:
  1. share = count / (__all documents that year) * 1e6, years >= settings.years.start
  2. Rule G exactly as detector.detector (min_count, +growth over window, consecutive windows)
  3. keep bigrams whose first signal year >= --since (default: latest complete year − 6) and whose
     latest complete-year share is still >= its share two years earlier (not already fading)
  4. collapse plural/singular variants (same token stems) into one row, keeping the larger series
  5. optional: merge 10-K counts (data/external/cand_counts_edgar_*.csv) to assign the provisional Tier
Outputs: outputs/candidates_bigrams.csv (all survivors, one per row) and outputs/candidates.md (summary).
The latest complete filing year is the last year whose __all count is >= 70% of the year before
(applications publish ~18 months after filing, so the most recent years are undercounted).
"""
from __future__ import annotations

import argparse
import csv
import glob
import gzip
import re
from collections import defaultdict
from pathlib import Path

import yaml

from detector.detector import _rule_g

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "data" / "external"
OUT = ROOT / "outputs"
ALL = "__all"


def stem(tok: str) -> str:
    for suf in ("ies", "es", "s"):
        if tok.endswith(suf) and len(tok) - len(suf) >= 3:
            return tok[: -len(suf)] + ("y" if suf == "ies" else "")
    return tok


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", type=int, default=None, help="earliest signal year to keep")
    ap.add_argument("--top", type=int, default=300, help="rows in the markdown summary")
    a = ap.parse_args()
    settings = yaml.safe_load(open(ROOT / "config" / "settings.yml", encoding="utf-8"))
    d = settings["detector"]
    w, g, hits, mc = int(d["growth_window_years"]), float(d["growth_threshold"]), int(d["consecutive_hits"]), int(d["min_count"])
    y_start = int(settings["years"]["start"])
    lo, hi = int(d["tier"]["edgar_low_max"]), int(d["tier"]["edgar_high_min"])

    raw: dict[str, dict[int, int]] = defaultdict(dict)
    with gzip.open(EXT / "bigram_counts.csv.gz", "rt", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            y = int(r["year"])
            if y >= y_start:
                raw[r["bigram"]][y] = int(r["count"])
    den = raw.pop(ALL)
    years = sorted(den)
    complete = [y for i, y in enumerate(years) if i == 0 or den[y] >= 0.7 * den[years[i - 1]]]
    latest = max(complete)
    since = a.since or latest - 6
    print(f"bigrams: {len(raw):,}; denominators {years[0]}-{years[-1]}; latest complete filing year {latest}; keeping signals >= {since}")

    rows = []
    for bg, counts in raw.items():
        sh = {y: counts.get(y, 0) / den[y] * 1e6 for y in years if den[y] and y <= latest}
        sig = _rule_g(sh, counts, w, g, hits, mc)
        if sig is None or sig < since:
            continue
        if (latest - 2) in sh and sh[latest - 2] > 0 and sh[latest] < sh[latest - 2]:
            continue  # already fading
        g3 = (sh[latest] / sh[latest - 3] - 1) if sh.get(latest - 3, 0) > 0 else None
        rows.append({"bigram": bg, "signal_year": sig, "latest_year": latest, "latest_count": counts.get(latest, 0),
                     "latest_share_ppm": round(sh[latest], 1), "growth_3y": None if g3 is None else round(g3, 2),
                     "count_series": " ".join(str(counts.get(y, 0)) for y in years if y <= latest)})

    # collapse plural/singular variants
    best: dict[str, dict] = {}
    for r in rows:
        key = " ".join(stem(t) for t in r["bigram"].split())
        if key not in best or r["latest_count"] > best[key]["latest_count"]:
            r["variants"] = sorted({r["bigram"], *(best.get(key, {}).get("variants", []))})
            best[key] = r
        else:
            best[key]["variants"] = sorted({*best[key]["variants"], r["bigram"]})
    rows = sorted(best.values(), key=lambda r: (-r["signal_year"], -(r["growth_3y"] or 0)))

    # optional 10-K counts → provisional tier
    ed: dict[str, dict[int, int]] = defaultdict(dict)
    for p in glob.glob(str(EXT / "cand_counts_edgar_*.csv")):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            ed[r["technology_id"]][int(r["year"])] = int(r["count"])
    for r in rows:
        e = ed.get(re.sub(r"[^a-z0-9]+", "_", r["bigram"]))
        if e:
            ly = max(y for y in e if y <= latest + 1)
            r["edgar_latest"] = e[ly]
            r["tier"] = "T2" if e[ly] >= hi else ("T0" if e[ly] < lo else "T1")
        else:
            r["edgar_latest"], r["tier"] = None, None

    OUT.mkdir(exist_ok=True)
    fields = ["bigram", "variants", "signal_year", "latest_year", "latest_count", "latest_share_ppm", "growth_3y",
              "edgar_latest", "tier", "count_series"]
    with open(OUT / "candidates_bigrams.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=fields); wr.writeheader()
        for r in rows:
            wr.writerow({**r, "variants": "; ".join(r["variants"])})
    by_year = defaultdict(int)
    for r in rows:
        by_year[r["signal_year"]] += 1
    lines = [f"# Candidate bigrams — Rule G ({mc} / +{int(g*100)}% / {hits} consecutive) on all US patent title+abstract bigrams",
             "", f"Latest complete filing year {latest}; signals since {since}; {len(rows)} bigrams after collapsing plural variants.",
             "Signals per year: " + ", ".join(f"{y}: {n}" for y, n in sorted(by_year.items())), "",
             f"Top {a.top} by signal recency, then 3-year growth:", "",
             "| bigram | signal | latest count | share ppm | growth 3y | 10-K latest | tier |", "|---|---|---|---|---|---|---|"]
    for r in rows[: a.top]:
        lines.append(f"| {r['bigram']} | {r['signal_year']} | {r['latest_count']} | {r['latest_share_ppm']} | "
                     f"{r['growth_3y'] if r['growth_3y'] is not None else '–'} | {r['edgar_latest'] if r['edgar_latest'] is not None else '–'} | {r['tier'] or '–'} |")
    (OUT / "candidates.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"candidates: {len(rows)} bigrams; by signal year {dict(sorted(by_year.items()))}")


if __name__ == "__main__":
    main()
