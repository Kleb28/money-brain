"""Rebuild the as-of event lists (protocol: simulation/protocol.md, 사건 정의) from a bigram count file.

For each grid rule: a bigram's event year T (2008-2023) is the first year such that Rule G, applied to the
share series computed from counts up to T only, first fires in [T-2, T], the bigram passes detector.candidates.is_term,
and it has >= candidates.min_assignees applicants in year T. One event per bigram (first T).
Usage: python -m simulation.make_events --counts data/external/bigram_counts_pub.csv.gz --out simulation/events_by_rule_pub.json
Written 2026-11-11 to reproduce the 2026-11-06 lists (filing basis) and to re-derive them on the publication basis.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from detector.candidates import is_term, _wordnet  # noqa: E402
from detector.detector import _rule_g  # noqa: E402

ALL = "__all"
YEARS = range(2008, 2024)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--counts", default=str(ROOT / "data/external/bigram_counts.csv.gz"))
    ap.add_argument("--out", default=str(ROOT / "simulation/events_by_rule_rebuilt.json"))
    a = ap.parse_args()
    s = yaml.safe_load(open(ROOT / "config/settings.yml", encoding="utf-8"))
    d = s["detector"]; w = int(d["growth_window_years"]); grid = d["grid"]
    min_asg = int(s.get("candidates", {}).get("min_assignees", 10))
    rules = {f"{mc}/{g}/{h}": (mc, g, h) for mc in grid["min_count"] for g in grid["growth_threshold"] for h in grid["consecutive_hits"]}

    cnt: dict[str, dict[int, int]] = defaultdict(dict); asg: dict[str, dict[int, int]] = defaultdict(dict)
    with gzip.open(a.counts, "rt", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            cnt[r["bigram"]][int(r["year"])] = int(r["count"]); asg[r["bigram"]][int(r["year"])] = int(r["n_assignees"])
    den = cnt.pop(ALL)
    print(f"{len(cnt):,} bigrams; denominator years {min(den)}..{max(den)}", flush=True)

    events = {name: {} for name in rules}
    wn = _wordnet()
    n_term = 0
    for bg, c in cnt.items():
        if max(c.values()) < 30 or not is_term(bg, wn):
            continue
        n_term += 1
        sh = {y: c[y] / den[y] * 1e6 for y in c if den.get(y)}
        for name, (mc, g, h) in rules.items():
            for T in YEARS:
                if asg[bg].get(T, 0) < min_asg:
                    continue
                sh_T = {y: v for y, v in sh.items() if y <= T}
                fy = _rule_g(sh_T, c, w, g, h, mc)
                if fy is not None and T - 2 <= fy <= T:
                    events[name][bg] = T
                    break
    for name in rules:
        print(f"  rule {name}: {len(events[name]):,} events", flush=True)
    json.dump(events, open(a.out, "w"), ensure_ascii=False)
    print(f"wrote {a.out}; {n_term:,} term bigrams with peak >= 30")


if __name__ == "__main__":
    main()
