"""Sim G feature file: money-brain 10-K text features per (ticker, filing year) for joining to Numerai Unity rows.
Source: data/external/sim_filers_*.csv (which firms mentioned which tracked bigrams in 10-Ks filed in year y1) and
simulation/filer_queries.csv (bigram roles). Valid for Numerai dates 1 July y1 .. 30 June y1+1 (10-K season over).
Columns: ticker, y1, mb_n_any (tracked bigrams mentioned), mb_n_t1 (pre-registered-rule T1 signal bigrams),
mb_n_t2 (already-hot bigrams), mb_n_ctl (no-signal control bigrams). Output: numerai/extra_features.csv.
Arithmetic only. Usage: python -m numerai.build_extra_features
"""
from __future__ import annotations

import csv
import glob
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "data" / "external"
SIM = ROOT / "simulation"
PRE = "30/0.5/2"


def main() -> None:
    roles = {}
    for r in csv.DictReader(open(SIM / "filer_queries.csv", encoding="utf-8")):
        roles[(r["bigram"], int(r["year"]))] = set(r["roles"].split(";"))
    agg: dict[tuple[str, int], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for p in glob.glob(str(EXT / "sim_filers_*.csv")):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            t = r["ticker"].strip().upper()
            if not t:
                continue
            key = (r["bigram"], int(r["year"]))
            rs = roles.get(key, set())
            a = agg[(t, key[1])]
            a["mb_n_any"] += 1
            a["mb_n_t1"] += f"{PRE}:T1" in rs
            a["mb_n_t2"] += f"{PRE}:T2" in rs
            a["mb_n_ctl"] += "control:T1" in rs
    out = ROOT / "numerai" / "extra_features.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ticker", "y1", "mb_n_any", "mb_n_t1", "mb_n_t2", "mb_n_ctl"])
        for (t, y), a in sorted(agg.items()):
            w.writerow([t, y, a["mb_n_any"], a["mb_n_t1"], a["mb_n_t2"], a["mb_n_ctl"]])
    print(f"wrote {out} with {len(agg):,} ticker-years, {len({t for t, _ in agg})} tickers, years {min(y for _, y in agg)}-{max(y for _, y in agg)}")


if __name__ == "__main__":
    main()
