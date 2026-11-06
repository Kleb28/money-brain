"""Sim A — did Tier-1 bigrams (patent signal at T, 10-K quiet) become 10-K topics by T+3 / T+5?
Protocol: simulation/protocol.md. Arithmetic only. Writes outputs/sim_a.md.

Inputs: simulation/events_sampled.json (rule -> bigram -> T), simulation/controls.json (bigram -> pseudo T),
data/external/sim_counts_edgar_*.csv (10-K filings per bigram-year).
Tier at T uses max(count[T-1], count[T]) < low  (T1) / >= high (T2) / between (mid).
Outcomes: reach = count[T+k] >= 30 filings; triple = count[T+k] >= max(3 * level_T, 10).
"""
from __future__ import annotations

import csv
import glob
import json
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIM = ROOT / "simulation"
OUT = ROOT / "outputs"
LOWS = (10, 50)
HIGH = 200
PRE = "30/0.5/2"
LAST_EDGAR_YEAR = 2026  # FY2025 10-Ks are filed Jan-Mar 2026; treated as complete, flagged in the report


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, c - h, c + h


def fmt_rate(k, n):
    p, lo, hi = wilson(k, n)
    return "–" if n == 0 else f"{p:.2f} [{lo:.2f}, {hi:.2f}] (n={n})"


def main() -> None:
    counts: dict[str, dict[int, int]] = defaultdict(dict)
    for p in glob.glob(str(ROOT / "data" / "external" / "sim_counts_edgar_*.csv")):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            counts[r["technology_id"].replace("_", " ")][int(r["year"])] = int(r["count"])
    events = json.load(open(SIM / "events_sampled.json"))
    controls = json.load(open(SIM / "controls.json"))

    def level(bg, T):
        c = counts.get(bg, {})
        if (T - 1) not in c and T not in c:
            return None
        return max(c.get(T - 1, 0), c.get(T, 0))

    def outcome(bg, T, k, lvl):
        y = T + k
        c = counts.get(bg, {})
        if y > LAST_EDGAR_YEAR or y not in c:
            return None
        return c[y] >= 30, c[y] >= max(3 * lvl, 10)

    lines = ["# Sim A — Tier-1 bigrams becoming 10-K topics (protocol: simulation/protocol.md)", "",
             f"10-K counts by filing year; years up to {LAST_EDGAR_YEAR} used (2026 = FY2025 reports, mostly filed by March 2026). "
             "Rates are Wilson 95% intervals. Controls = bigrams with no Rule G signal under any grid rule, pseudo-T drawn from the pre-registered rule's T distribution, "
             "classified by the same 10-K level at T.", ""]
    for low in LOWS:
        lines += [f"## 10-K low threshold {low} (T1 = fewer than {low} filings in T−1/T; T2 = {HIGH}+)", "",
                  "| rule | group | n | reach ≥30 at T+3 | reach ≥30 at T+5 | ≥3× level at T+3 | ≥3× level at T+5 |", "|---|---|---|---|---|---|---|"]
        ctl_stats = {}
        for name, mapping, is_ctl in [("no-signal control", controls, True)] + [(r, ev, False) for r, ev in events.items()]:
            groups = defaultdict(lambda: {"n": 0, "r3": [0, 0], "r5": [0, 0], "t3": [0, 0], "t5": [0, 0]})
            for bg, T in mapping.items():
                lvl = level(bg, T)
                if lvl is None:
                    continue
                g = "T1" if lvl < low else ("T2" if lvl >= HIGH else "mid")
                s = groups[g]; s["n"] += 1
                for k, key in ((3, "r3"), (5, "r5")):
                    o = outcome(bg, T, k, lvl)
                    if o is not None:
                        s[key][1] += 1; s[key][0] += int(o[0])
                        tk = "t3" if k == 3 else "t5"
                        s[tk][1] += 1; s[tk][0] += int(o[1])
            for g in ("T1", "mid", "T2"):
                s = groups.get(g)
                if not s:
                    continue
                label = f"{'**' if name == PRE else ''}{name}{'**' if name == PRE else ''}"
                lines.append(f"| {label} | {g} | {s['n']} | {fmt_rate(*s['r3'])} | {fmt_rate(*s['r5'])} | {fmt_rate(*s['t3'])} | {fmt_rate(*s['t5'])} |")
                if is_ctl:
                    ctl_stats[g] = s
        # lift table for T1 vs control T1
        lines += ["", f"Lift (T1 rate ÷ no-signal T1 rate), low {low}:", "", "| rule | reach T+3 | reach T+5 | 3× T+3 | 3× T+5 |", "|---|---|---|---|---|"]
        c1 = ctl_stats.get("T1")
        for name, ev in events.items():
            s = {"r3": [0, 0], "r5": [0, 0], "t3": [0, 0], "t5": [0, 0]}
            for bg, T in ev.items():
                lvl = level(bg, T)
                if lvl is None or lvl >= low:
                    continue
                for k, rk, tk in ((3, "r3", "t3"), (5, "r5", "t5")):
                    o = outcome(bg, T, k, lvl)
                    if o is not None:
                        s[rk][1] += 1; s[rk][0] += int(o[0]); s[tk][1] += 1; s[tk][0] += int(o[1])
            def lift(key):
                if not c1 or c1[key][1] == 0 or s[key][1] == 0 or c1[key][0] == 0:
                    return "–"
                return f"{(s[key][0]/s[key][1]) / (c1[key][0]/c1[key][1]):.1f}×"
            lines.append(f"| {name} | {lift('r3')} | {lift('r5')} | {lift('t3')} | {lift('t5')} |")
        lines.append("")

    # pre-registered rule by T bucket, low 50
    lines += [f"## Pre-registered rule {PRE}, T1 (low 50) by signal-year bucket", "",
              "| T | n T1 | reach ≥30 at T+3 | reach ≥30 at T+5 | control T1 reach T+5 |", "|---|---|---|---|---|"]
    buckets = [(2008, 2011), (2012, 2015), (2016, 2019), (2020, 2023)]
    for a, b in buckets:
        s = {"n": 0, "r3": [0, 0], "r5": [0, 0]}
        c = {"r5": [0, 0]}
        for bg, T in events[PRE].items():
            lvl = level(bg, T)
            if lvl is None or lvl >= 50 or not (a <= T <= b):
                continue
            s["n"] += 1
            for k, key in ((3, "r3"), (5, "r5")):
                o = outcome(bg, T, k, lvl)
                if o is not None:
                    s[key][1] += 1; s[key][0] += int(o[0])
        for bg, T in controls.items():
            lvl = level(bg, T)
            if lvl is None or lvl >= 50 or not (a <= T <= b):
                continue
            o = outcome(bg, T, 5, lvl)
            if o is not None:
                c["r5"][1] += 1; c["r5"][0] += int(o[0])
        lines.append(f"| {a}–{b} | {s['n']} | {fmt_rate(*s['r3'])} | {fmt_rate(*s['r5'])} | {fmt_rate(*c['r5'])} |")
    OUT.mkdir(exist_ok=True)
    (OUT / "sim_a.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
