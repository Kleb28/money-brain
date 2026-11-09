"""Retro 4: does the negative 'verbosity' IC survive a size control (revenue terciles from companyfacts)?"""
from pathlib import Path
import csv, glob, math, datetime as dt, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from simulation.sim_b import load_prices, price_on_or_after, MIN_ENTRY_PRICE, MAX_TICKER_RETURN
ROOT = Path(__file__).resolve().parents[2]; EXT = ROOT / "data/external"; SIM = ROOT / "simulation"
PRE = "30/0.5/2"
roles = {}
for r in csv.DictReader(open(SIM / "filer_queries.csv")):
    roles[(r["bigram"], int(r["year"]))] = r["roles"].split(";")
filers = defaultdict(set)
for p in glob.glob(str(EXT / "sim_filers_*.csv")):
    for r in csv.DictReader(open(p)):
        t = r["ticker"].strip().upper()
        if t: filers[(r["bigram"], int(r["year"]))].add(t)
prices = load_prices(); spy = prices["SPY"]
universe = defaultdict(set)
for (bg, y1), tk in filers.items(): universe[y1] |= tk
any_by_firm = defaultdict(lambda: defaultdict(int)); ctl_by_firm = defaultdict(lambda: defaultdict(int)); t1_by_firm = defaultdict(lambda: defaultdict(int))
for (bg, y1), tk in filers.items():
    rs = roles.get((bg, y1), [])
    for t in tk:
        any_by_firm[y1][t] += 1
        if "control:T1" in rs: ctl_by_firm[y1][t] += 1
        if f"{PRE}:T1" in rs: t1_by_firm[y1][t] += 1
rev = {}
for r in csv.DictReader(open(EXT / "sim_financials.csv")):
    try:
        if r["revenue"]: rev[(r["ticker"], int(r["fy"]))] = float(r["revenue"])
    except ValueError: pass
print("revenue rows", len(rev))

def ret(t, y1, k):
    s = prices.get(t)
    if not s: return None
    p0, p1 = price_on_or_after(s, dt.date(y1, 7, 1)), price_on_or_after(s, dt.date(y1 + k, 7, 1))
    if p0 and p1 and p0 >= MIN_ENTRY_PRICE: return min(p1 / p0 - 1, MAX_TICKER_RETURN)
    return None

def spearman(x, y):
    n = len(x)
    def rank(v):
        order = sorted(range(n), key=lambda i: v[i]); r = [0]*n; i = 0
        while i < n:
            j = i
            while j + 1 < n and v[order[j+1]] == v[order[i]]: j += 1
            for m in range(i, j+1): r[order[m]] = (i + j) / 2
            i = j + 1
        return r
    rx, ry = rank(x), rank(y); mx, my = sum(rx)/n, sum(ry)/n
    cov = sum((a-mx)*(b-my) for a, b in zip(rx, ry)); vx = sum((a-mx)**2 for a in rx); vy = sum((b-my)**2 for b in ry)
    return cov / math.sqrt(vx*vy) if vx and vy else None

for label, feat in (("verbosity (n any tracked bigrams)", any_by_firm), ("n T1 bigrams", t1_by_firm)):
    print(f"\n== {label}, 1y IC within revenue terciles (fy = y1-1)")
    per_terc = defaultdict(list); ic_rev = []
    for y1 in sorted(universe):
        if dt.date(y1 + 1, 7, 1) > max(spy[0]): continue
        rows = []
        for t in universe[y1]:
            r = ret(t, y1, 1); rv = rev.get((t, y1 - 1))
            if r is None or rv is None or rv <= 0: continue
            rows.append((feat[y1].get(t, 0), r, rv))
        if len(rows) < 150: continue
        ic_rev.append(spearman([x[0] for x in rows], [x[2] for x in rows]))
        rows.sort(key=lambda x: x[2]); n = len(rows)
        for ti, name in enumerate(("small", "mid", "large")):
            sub = rows[ti*n//3:(ti+1)*n//3]
            ic = spearman([x[0] for x in sub], [x[1] for x in sub])
            if ic is not None: per_terc[name].append((y1, ic))
    print(f"  corr(feature, revenue) mean {sum(ic_rev)/len(ic_rev):+.3f}")
    for name, v in per_terc.items():
        m = sum(i for _, i in v)/len(v); sd = math.sqrt(sum((i-m)**2 for _, i in v)/(len(v)-1))
        print(f"  {name}: mean IC {m:+.4f} t {m/(sd/math.sqrt(len(v))):+.2f} years {len(v)} pos {sum(1 for _, i in v if i>0)}")
