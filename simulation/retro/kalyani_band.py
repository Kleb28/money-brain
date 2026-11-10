"""Theory 3 check on the independent Kalyani/techdiffusion set: among technologies whose patent signal (pre-registered
rule, uspto_abs) fired by 2009, does the 10-K level at the signal year (0 / 1-9 / 10-49 / 50+) separate later outcomes?
Outcomes: EC class disruptive (Kalyani et al.), and 10-K reach >= 30 in 2010-2019. Exploratory; informs whether to
pre-register a T1 band change (10-49 instead of <50). Usage: python simulation/retro/kalyani_band.py
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import yaml
from detector.oos_eval import EXT, read_csv, load_counts, denominators, shares, first_fire

settings = yaml.safe_load(open(ROOT / "config" / "settings.yml", encoding="utf-8"))
d = settings["detector"]; w = int(d["growth_window_years"])
rule = {"mc": 30, "g": 0.5, "hits": 2, "w": w, "name": "30 / +50% / 2w"}
techs = {r["id"]: r for r in read_csv(EXT / "oos_technologies.csv")}
den = denominators()
us_raw = load_counts("oos_counts_uspto_abs_*.csv"); ed_raw = load_counts("oos_counts_edgar_*.csv")
us_sh = {tid: shares(r, den["uspto_abs"]) for tid, r in us_raw.items()}

def band(level):
    return "0" if level == 0 else "1-9" if level < 10 else "10-49" if level < 50 else "50+"

from collections import defaultdict
for asof, label in ((2009, "signal by 2009; 10-K level = max of signal year and the year before; outcomes 2010-19 / EC class 2002-19"),
                    (2019, "signal by 2019 (association only); 10-K level at signal year; outcome EC class")):
    print(f"\n== {label}")
    g = defaultdict(lambda: [0, 0, 0])  # n, disruptive, reach30 later
    for tid in us_sh:
        if tid not in ed_raw: continue
        y = first_fire(us_sh[tid], us_raw[tid], rule, upto=asof)
        if y is None: continue
        lvl = max(ed_raw[tid].get(y - 1, 0), ed_raw[tid].get(y, 0))
        b = band(lvl)
        g[b][0] += 1; g[b][1] += techs[tid]["ec_class"] == "disruptive"
        g[b][2] += max(ed_raw[tid].get(yy, 0) for yy in range(y + 1, 2020)) >= 30 if y < 2019 else 0
    for b in ("0", "1-9", "10-49", "50+"):
        n, ds, rc = g[b]
        if n:
            print(f"  10-K {b:6s}: n={n:3d}  disruptive {ds/n:.2f}  reach>=30 later {rc/n:.2f}")
    # no-signal baseline by band at 2009 for reference
    if asof == 2009:
        g2 = defaultdict(lambda: [0, 0, 0])
        for tid in us_sh:
            if tid not in ed_raw or first_fire(us_sh[tid], us_raw[tid], rule, upto=2009) is not None: continue
            lvl = max(ed_raw[tid].get(yy, 0) for yy in (2008, 2009)); b = band(lvl)
            g2[b][0] += 1; g2[b][1] += techs[tid]["ec_class"] == "disruptive"; g2[b][2] += max(ed_raw[tid].get(yy, 0) for yy in range(2010, 2020)) >= 30
        print("  no-signal baseline (10-K level 2008-09):")
        for b in ("0", "1-9", "10-49", "50+"):
            n, ds, rc = g2[b]
            if n:
                print(f"  10-K {b:6s}: n={n:3d}  disruptive {ds/n:.2f}  reach>=30 later {rc/n:.2f}")
