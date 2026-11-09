"""Retrospective diagnostics on Sim A/B data (exploratory, not pre-registered)."""
from pathlib import Path
import csv, glob, gzip, json, math, bisect, datetime as dt, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from simulation.sim_b import load_prices, price_on_or_after, cluster_stats, fmt, MIN_ENTRY_PRICE, MAX_TICKER_RETURN, MIN_TICKERS

ROOT = Path(__file__).resolve().parents[2]
EXT = ROOT / "data/external"; SIM = ROOT / "simulation"; OUT = ROOT / "outputs"
PRE = "30/0.5/2"

# 10-K counts per bigram-year
edgar = defaultdict(dict)
for p in glob.glob(str(EXT / "sim_counts_edgar_*.csv")):
    for r in csv.DictReader(open(p)):
        edgar[r["technology_id"].replace("_", " ")][int(r["year"])] = int(r["count"])

# events
events = list(csv.DictReader(open(OUT / "sim_b_events.csv")))
print("events", len(events))

def conv(bg, T, k=5, thr=30):
    c = edgar.get(bg, {})
    y = T + k
    if y > 2026 or y not in c:
        return None
    lvl = max(c.get(T - 1, 0), c.get(T, 0))
    return c[y] >= thr, c[y] >= max(3 * lvl, 10), c[y]

# ---- A. conversion x returns for PRE T1 and control T1
def arm_rows(prefix, suffix):
    return [e for e in events if f"{prefix}:{suffix}" in e["roles"].split(";")]

for name, rows in (("PRE T1", arm_rows(PRE, "T1")), ("control T1", arm_rows("control", "T1")), ("PRE T2", arm_rows(PRE, "T2")), ("PRE mid", arm_rows(PRE, "mid"))):
    print(f"\n== {name}: n={len(rows)}")
    for k in (1, 2, 3):
        for horizon in (3, 5):
            groups = defaultdict(lambda: ([], []))
            for e in rows:
                if not e[f"ex{k}y"]:
                    continue
                cv = conv(e["bigram"], int(e["T"]), horizon)
                if cv is None:
                    continue
                g = "converted(>=30)" if cv[0] else ("tripled" if cv[1] else "no")
                groups[g][0].append(float(e[f"ex{k}y"])); groups[g][1].append(int(e["T"]))
            for g, (v, c) in sorted(groups.items()):
                s = cluster_stats(v, c)
                print(f"  hold {k}y, conv@T+{horizon} {g:16s} {fmt(s)}")

# ---- D. tails
print("\n== tails (2y excess)")
for name, rows in (("PRE T1", arm_rows(PRE, "T1")), ("control T1", arm_rows("control", "T1")), ("PRE T2", arm_rows(PRE, "T2"))):
    v = [float(e["ex2y"]) for e in rows if e["ex2y"]]
    n = len(v)
    print(f"  {name}: n={n} >+50%: {sum(x>0.5 for x in v)/n:.3f}  >+100%: {sum(x>1 for x in v)/n:.3f}  <-50%: {sum(x<-0.5 for x in v)/n:.3f}  p90 {sorted(v)[int(n*0.9)]:+.2f} p10 {sorted(v)[int(n*0.1)]:+.2f}")

# ---- by n_tickers buckets (basket size) for PRE T1 and control
print("\n== by basket size (2y), PRE T1 vs control")
for name, rows in (("PRE T1", arm_rows(PRE, "T1")), ("control T1", arm_rows("control", "T1"))):
    for lo, hi in ((3, 5), (6, 10), (11, 20), (21, 50), (51, 10000)):
        v = [float(e["ex2y"]) for e in rows if e["ex2y"] and lo <= int(e["n_tickers"]) <= hi]
        c = [int(e["T"]) for e in rows if e["ex2y"] and lo <= int(e["n_tickers"]) <= hi]
        if v:
            print(f"  {name} size {lo}-{hi}: {fmt(cluster_stats(v, c))}")
