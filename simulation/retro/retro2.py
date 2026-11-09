"""Retro 2: equal-weight universe benchmark; cross-sectional rank IC of firm-level features (Numerai-Signals style)."""
from pathlib import Path
import csv, glob, gzip, json, math, bisect, datetime as dt, sys, random
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from simulation.sim_b import load_prices, price_on_or_after, MIN_ENTRY_PRICE, MAX_TICKER_RETURN

ROOT = Path(__file__).resolve().parents[2]; EXT = ROOT / "data/external"; SIM = ROOT / "simulation"; OUT = ROOT / "outputs"
PRE = "30/0.5/2"
prices = load_prices(); spy = prices["SPY"]
print("tickers with prices", len(prices))

roles = {}
for r in csv.DictReader(open(SIM / "filer_queries.csv")):
    roles[(r["bigram"], int(r["year"]))] = r["roles"].split(";")
filers = defaultdict(set)
for p in glob.glob(str(EXT / "sim_filers_*.csv")):
    for r in csv.DictReader(open(p)):
        t = r["ticker"].strip().upper()
        if t:
            filers[(r["bigram"], int(r["year"]))].add(t)

edgar = defaultdict(dict)
for p in glob.glob(str(EXT / "sim_counts_edgar_*.csv")):
    for r in csv.DictReader(open(p)):
        edgar[r["technology_id"].replace("_", " ")][int(r["year"])] = int(r["count"])

def ret(t, y1, k):
    s = prices.get(t)
    if not s: return None
    p0, p1 = price_on_or_after(s, dt.date(y1, 7, 1)), price_on_or_after(s, dt.date(y1 + k, 7, 1))
    if p0 and p1 and p0 >= MIN_ENTRY_PRICE:
        return min(p1 / p0 - 1, MAX_TICKER_RETURN)
    return None

# universe per year = all tickers appearing in any filer list that year
universe = defaultdict(set)
for (bg, y1), tk in filers.items():
    universe[y1] |= tk

print("\n== equal-weight universe vs SPY (all 10-K filers in our lists that year)")
for y1 in sorted(universe):
    for k in (1, 2):
        if dt.date(y1 + k, 7, 1) > max(spy[0]): continue
        rs = [r for r in (ret(t, y1, k) for t in universe[y1]) if r is not None]
        s0, s1 = price_on_or_after(spy, dt.date(y1, 7, 1)), price_on_or_after(spy, dt.date(y1 + k, 7, 1))
        if rs and k == 2:
            print(f"  entry {y1}: n={len(rs)} EW {k}y {sum(rs)/len(rs)*100:+.1f}%  SPY {(s1/s0-1)*100:+.1f}%  median {sorted(rs)[len(rs)//2]*100:+.1f}%")

# ---- firm-level features per year
def spearman(x, y):
    n = len(x)
    if n < 10: return None
    def rank(v):
        order = sorted(range(n), key=lambda i: v[i]); r = [0]*n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[order[j+1]] == v[order[i]]: j += 1
            for m in range(i, j+1): r[order[m]] = (i + j) / 2
            i = j + 1
        return r
    rx, ry = rank(x), rank(y)
    mx, my = sum(rx)/n, sum(ry)/n
    cov = sum((a-mx)*(b-my) for a, b in zip(rx, ry)); vx = sum((a-mx)**2 for a in rx); vy = sum((b-my)**2 for b in ry)
    return cov / math.sqrt(vx*vy) if vx and vy else None

def ic_series(feature_fn, label, k=1, min_n=100):
    ics = []
    for y1 in sorted(universe):
        if dt.date(y1 + k, 7, 1) > max(spy[0]): continue
        xs, ys = [], []
        for t in universe[y1]:
            r = ret(t, y1, k)
            f = feature_fn(t, y1)
            if r is None or f is None: continue
            xs.append(f); ys.append(r)
        if len(xs) < min_n: continue
        ic = spearman(xs, ys)
        if ic is not None: ics.append((y1, ic, len(xs), sum(1 for x in xs if x > 0)))
    if not ics: print(f"  {label}: no data"); return
    m = sum(i for _, i, _, _ in ics) / len(ics); sd = math.sqrt(sum((i - m)**2 for _, i, _, _ in ics) / max(1, len(ics)-1))
    print(f"  {label} ({k}y): mean IC {m:+.4f}  t {m/(sd/math.sqrt(len(ics))):+.2f}  years {len(ics)}  pos {sum(1 for _, i, _, _ in ics if i > 0)}  | per-year: " + " ".join(f"{y}:{i:+.3f}" for y, i, _, _ in ics))

# feature 1: number of PRE T1 signal bigrams the firm mentioned in year y1
t1_by_firm = defaultdict(lambda: defaultdict(int)); mid_by_firm = defaultdict(lambda: defaultdict(int)); t2_by_firm = defaultdict(lambda: defaultdict(int))
ctl_by_firm = defaultdict(lambda: defaultdict(int)); any_by_firm = defaultdict(lambda: defaultdict(int))
for (bg, y1), tk in filers.items():
    rs = roles.get((bg, y1), [])
    for t in tk:
        any_by_firm[y1][t] += 1
        if f"{PRE}:T1" in rs: t1_by_firm[y1][t] += 1
        if f"{PRE}:mid" in rs: mid_by_firm[y1][t] += 1
        if f"{PRE}:T2" in rs: t2_by_firm[y1][t] += 1
        if "control:T1" in rs: ctl_by_firm[y1][t] += 1

print("\n== cross-sectional rank IC (feature vs forward return, all firms in that year's universe)")
for k in (1, 2):
    ic_series(lambda t, y: t1_by_firm[y].get(t, 0), "n T1 signal bigrams", k)
    ic_series(lambda t, y: t1_by_firm[y].get(t, 0) / max(1, any_by_firm[y].get(t, 0)), "share T1 among all mentioned", k)
    ic_series(lambda t, y: t2_by_firm[y].get(t, 0), "n T2 (already-hot) bigrams", k)
    ic_series(lambda t, y: mid_by_firm[y].get(t, 0), "n mid bigrams", k)
    ic_series(lambda t, y: ctl_by_firm[y].get(t, 0), "n control (no-signal) bigrams", k)
    ic_series(lambda t, y: any_by_firm[y].get(t, 0), "n any tracked bigrams (verbosity)", k)
    ic_series(lambda t, y: (t1_by_firm[y].get(t, 0) > 0) - (t2_by_firm[y].get(t, 0) > 0), "T1-mentioner minus T2-mentioner", k)

# feature 2 (ex-post diagnostic): number of T1 bigrams the firm mentioned that later converted (>=30 by T+3)
def conv_count(t, y1):
    T = y1 - 1; n = 0
    for (bg, yy), tk in filers.items():
        pass
    return None
# cheaper: precompute converted set
conv_set = set()
for (bg, y1), rs in roles.items():
    if f"{PRE}:T1" in rs:
        T = y1 - 1; c = edgar.get(bg, {})
        if (T + 3) in c and c[T + 3] >= 30 and c[T+3] >= 3 * max(c.get(T-1, 0), c.get(T, 0), 3):
            conv_set.add((bg, y1))
convf = defaultdict(lambda: defaultdict(int))
for (bg, y1), tk in filers.items():
    if (bg, y1) in conv_set:
        for t in tk: convf[y1][t] += 1
print("\n== ex-post diagnostic (not tradable): n T1 bigrams that later tripled & reached 30")
for k in (1, 2):
    ic_series(lambda t, y: convf[y].get(t, 0), "n later-converted T1 bigrams", k)
print("converted T1 events:", len(conv_set))
