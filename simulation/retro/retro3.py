"""Retro 3: which T1 bigrams converted, and can patent-side features at T predict conversion (train 2008-2015, test 2016-2021)?"""
import csv, glob, gzip, json, math, sys
from collections import defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; EXT = ROOT / "data/external"; SIM = ROOT / "simulation"
PRE = "30/0.5/2"

edgar = defaultdict(dict)
for p in glob.glob(str(EXT / "sim_counts_edgar_*.csv")):
    for r in csv.DictReader(open(p)):
        edgar[r["technology_id"].replace("_", " ")][int(r["year"])] = int(r["count"])
events = json.load(open(SIM / "events_sampled.json"))[PRE]
controls = json.load(open(SIM / "controls.json"))
need = set(events) | set(controls)
pat = defaultdict(dict)
with gzip.open(EXT / "bigram_counts.csv.gz", "rt") as f:
    for r in csv.DictReader(f):
        if r["bigram"] in need:
            pat[r["bigram"]][int(r["year"])] = (int(r["count"]), int(r["n_assignees"]), int(r["n_cpc"]))
# patent denominators (total docs per year) approximated by sum over all bigrams is not available here; use raw counts

def level10k(bg, T):
    c = edgar.get(bg, {})
    if (T-1) not in c and T not in c: return None
    return max(c.get(T-1, 0), c.get(T, 0))

def outcome(bg, T, k=3):
    c = edgar.get(bg, {}); y = T + k
    if y > 2026 or y not in c: return None
    lvl = level10k(bg, T)
    return int(c[y] >= 30), int(c[y] >= max(3 * lvl, 10)), c[y]

rows = []
for src, mapping in (("T1", events), ("ctl", controls)):
    for bg, T in mapping.items():
        lvl = level10k(bg, T)
        if lvl is None or lvl >= 50: continue
        o = outcome(bg, T, 3)
        if o is None: continue
        p = pat.get(bg, {})
        cT = p.get(T, (0, 0, 0)); c2 = p.get(T-2, (0, 0, 0)); c5 = p.get(T-5, (0, 0, 0))
        e = edgar.get(bg, {})
        rows.append(dict(src=src, bg=bg, T=T, lvl=lvl, reach=o[0], triple=o[1], c3=o[2],
                         pc=cT[0], asg=cT[1], cpc=cT[2], g2=(cT[0]+1)/(c2[0]+1), g5=(cT[0]+1)/(c5[0]+1),
                         asg_per_doc=cT[1]/max(1, cT[0]), e_trend=(e.get(T, 0)+1)/(e.get(T-2, 0)+1), e0=e.get(T, 0)))
print("rows", len(rows), "T1", sum(r["src"]=="T1" for r in rows))

# converted list
conv = [r for r in rows if r["src"] == "T1" and r["triple"] and r["reach"]]
print(f"\nT1 bigrams that reached >=30 AND tripled by T+3: {len(conv)}")
for r in sorted(conv, key=lambda r: r["T"]):
    print(f"  {r['T']} {r['bg']:28s} 10-K {r['lvl']:>3}->{r['c3']:>4}  patents {r['pc']:>4} asg {r['asg']:>3} cpc {r['cpc']:>3}")
reach_only = [r for r in rows if r["src"] == "T1" and r["reach"] and not r["triple"]]
print(f"\nT1 reached >=30 without tripling (were already 10-49): {len(reach_only)}; examples:", ", ".join(r['bg'] for r in reach_only[:25]))

# univariate AUC for predicting reach (T1 arm only), by era
def auc(xs, ys):
    pos = [x for x, y in zip(xs, ys) if y]; neg = [x for x, y in zip(xs, ys) if not y]
    if not pos or not neg: return None
    # rank-based
    allv = sorted(set(xs)); rk = {v: i for i, v in enumerate(allv)}
    import bisect
    s = 0.0
    sn = sorted(neg)
    for p in pos:
        s += bisect.bisect_left(sn, p) + 0.5 * (bisect.bisect_right(sn, p) - bisect.bisect_left(sn, p))
    return s / (len(pos) * len(neg))

print("\n== univariate AUC for 'reach >=30 at T+3' among T1 events (higher feature -> more conversion if AUC>0.5)")
for era, (a, b) in (("2008-2015", (2008, 2015)), ("2016-2023", (2016, 2023))):
    sub = [r for r in rows if r["src"] == "T1" and a <= r["T"] <= b]
    ys = [r["reach"] for r in sub]
    print(f"  era {era}: n={len(sub)} base rate {sum(ys)/len(ys):.3f}")
    for f in ("lvl", "e0", "e_trend", "pc", "asg", "cpc", "g2", "g5", "asg_per_doc"):
        print(f"    {f:12s} AUC {auc([r[f] for r in sub], ys):.3f}")

# conversion rate by 10-K level at T (0, 1-9, 10-29, 30-49) for T1 vs control
print("\n== reach rate by 10-K level at T")
for src in ("T1", "ctl"):
    for lo, hi in ((0, 0), (1, 9), (10, 29), (30, 49)):
        sub = [r for r in rows if r["src"] == src and lo <= r["lvl"] <= hi]
        if sub:
            print(f"  {src} lvl {lo}-{hi}: n={len(sub)} reach {sum(r['reach'] for r in sub)/len(sub):.3f} triple {sum(r['triple'] for r in sub)/len(sub):.3f}")

# simple 2-feature score: 10-K level in 10-49 AND assignees high
print("\n== reach rate, T1 only, by assignee count at T (lvl 10-49 vs 0-9)")
for lo, hi in ((0, 9), (10, 49)):
    for alo, ahi in ((10, 19), (20, 49), (50, 99), (100, 10**6)):
        sub = [r for r in rows if r["src"] == "T1" and lo <= r["lvl"] <= hi and alo <= r["asg"] <= ahi]
        if len(sub) >= 20:
            print(f"  lvl {lo}-{hi} asg {alo}-{ahi}: n={len(sub)} reach {sum(r['reach'] for r in sub)/len(sub):.3f}")
