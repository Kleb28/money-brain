"""Deterministic emergence detector.

Inputs : data/counts.csv, config/technologies.csv, config/settings.yml
Outputs: outputs/shares.csv            (share per million, per tech/source/year)
         outputs/signals.csv           (signal year per tech/source, both rules)
         outputs/tiers.csv             (Tier per tech, provisional rules)
         outputs/validation_report.md  (lead years vs. Kalyani ec_year labels)

Rules (all arithmetic, no model):
  share[y]      = count[y] / denominator[y] * 1e6
  Rule G (growth): first year y with count[y] >= min_count and
                   share[y]/share[y-w] >= 1+g for `consecutive_hits` consecutive y
  Rule K (Kalyani-style): first year share[y] >= 10% of max share over 2002-2019
  lead_years    = ec_year - signal_year   (validation rows only; positive = detector led)
"""
from __future__ import annotations

import csv
import datetime as dt
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
ALL = "__all"
K_WINDOW = (2002, 2019)


def load_csv(p: Path) -> list[dict]:
    with open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> None:
    settings = yaml.safe_load(open(ROOT / "config" / "settings.yml", encoding="utf-8"))
    d = settings["detector"]
    techs = {r["id"]: r for r in load_csv(ROOT / "config" / "technologies.csv")}
    counts = load_csv(ROOT / "data" / "counts.csv") if (ROOT / "data" / "counts.csv").exists() else []
    if not counts:
        print("no counts yet"); OUT.mkdir(exist_ok=True); return

    # counts[(tech, source)][year] = n ; denom[source][year] = N
    by = defaultdict(dict)
    denom = defaultdict(dict)
    for r in counts:
        y, n = int(r["year"]), int(r["count"])
        if r["technology_id"] == ALL:
            denom[r["source"]][y] = n
        else:
            by[(r["technology_id"], r["source"])][y] = n

    shares = {}  # (tech, source) -> {year: share}
    for (tid, src), ys in by.items():
        shares[(tid, src)] = {y: (n / denom[src][y] * 1e6) for y, n in ys.items()
                              if denom[src].get(y)}

    w, g, hits_needed, min_count = (int(d["growth_window_years"]), float(d["growth_threshold"]),
                                    int(d["consecutive_hits"]), int(d["min_count"]))

    signals = []  # rows
    sig_by_tech = defaultdict(dict)
    for (tid, src), sh in shares.items():
        years = sorted(sh)
        raw = by[(tid, src)]
        # Rule G
        rule_g = None
        streak = 0
        for y in years:
            prev = y - w
            ok = (raw.get(y, 0) >= min_count and prev in sh and sh[prev] > 0
                  and sh[y] / sh[prev] >= 1 + g)
            streak = streak + 1 if ok else 0
            if streak >= hits_needed:
                rule_g = y; break
        # Rule K
        win = {y: v for y, v in sh.items() if K_WINDOW[0] <= y <= K_WINDOW[1]}
        rule_k = None
        if win:
            thr = 0.1 * max(win.values())
            rule_k = min((y for y, v in win.items() if v >= thr), default=None)
        last_y = years[-1]
        g3 = (sh[last_y] / sh[last_y - 3] - 1) if (last_y - 3) in sh and sh[last_y - 3] > 0 else None
        signals.append({"technology_id": tid, "source": src, "rule_g_year": rule_g,
                        "rule_k_year": rule_k, "latest_year": last_y,
                        "latest_count": raw.get(last_y), "latest_share_ppm": round(sh[last_y], 2),
                        "growth_3y": None if g3 is None else round(g3, 3)})
        sig_by_tech[tid][src] = signals[-1]

    OUT.mkdir(exist_ok=True)
    with open(OUT / "shares.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f); wr.writerow(["technology_id", "source", "year", "count", "share_ppm"])
        for (tid, src), sh in sorted(shares.items()):
            for y in sorted(sh):
                wr.writerow([tid, src, y, by[(tid, src)][y], round(sh[y], 3)])
    with open(OUT / "signals.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=list(signals[0].keys())); wr.writeheader(); wr.writerows(signals)

    # Tiers (provisional; for candidates AND validation rows, so thresholds can be inspected)
    lo, hi = int(d["tier"]["edgar_low_max"]), int(d["tier"]["edgar_high_min"])
    tier_rows = []
    for tid, t in techs.items():
        s = sig_by_tech.get(tid, {})
        sci = [s[k] for k in ("pubmed", "arxiv") if k in s]
        sci_growing = any((x["growth_3y"] or 0) >= g for x in sci)
        sci_signal = any(x["rule_g_year"] for x in sci)
        ed = s.get("edgar_10k")
        ed_latest = ed["latest_count"] if ed else None
        if ed_latest is None:
            tier = "T0" if sci_signal else "T-"
        elif ed_latest >= hi:
            tier = "T2"
        elif sci_signal and ed_latest < lo:
            tier = "T0"
        elif sci_signal:
            tier = "T1"
        else:
            tier = "T-"
        tier_rows.append({"technology_id": tid, "name": t["name"], "arm": t["arm"],
                          "status": t["status"], "tier": tier,
                          "science_signal_year": min((x["rule_g_year"] for x in sci if x["rule_g_year"]), default=None),
                          "science_growth_3y": max(((x["growth_3y"] or 0) for x in sci), default=None),
                          "edgar_latest_count": ed_latest,
                          "edgar_signal_year": ed["rule_g_year"] if ed else None})
    with open(OUT / "tiers.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=list(tier_rows[0].keys())); wr.writeheader(); wr.writerows(tier_rows)

    # Validation report
    lines = [f"# Validation report ({dt.date.today().isoformat()})", "",
             f"Rule G: window {w}y, +{int(g*100)}%, {hits_needed} consecutive, min_count {min_count}. "
             "lead = ec_year - signal_year (positive = detector led the earnings-call breakthrough).", "",
             "| technology | ec_year | source | rule_g | lead_g | rule_k | lead_k |", "|---|---|---|---|---|---|---|"]
    leads = defaultdict(list)
    for tid, t in techs.items():
        if t["status"] != "validation" or not t.get("ec_year"):
            continue
        ec = int(t["ec_year"])
        for src, s in sorted(sig_by_tech.get(tid, {}).items()):
            lg = (ec - s["rule_g_year"]) if s["rule_g_year"] else None
            lk = (ec - s["rule_k_year"]) if s["rule_k_year"] else None
            if lg is not None and ec > 2002:
                leads[src].append(lg)
            lines.append(f"| {t['name']} | {ec} | {src} | {s['rule_g_year'] or '–'} | "
                         f"{lg if lg is not None else '–'} | {s['rule_k_year'] or '–'} | {lk if lk is not None else '–'} |")
    lines += ["", "## Summary (Rule G, technologies with ec_year > 2002 only)", "",
              "| source | n | led (lead>=1) | same year | lagged | median lead |", "|---|---|---|---|---|---|"]
    for src, ls in sorted(leads.items()):
        ls_sorted = sorted(ls)
        med = ls_sorted[len(ls_sorted) // 2] if ls_sorted else None
        lines.append(f"| {src} | {len(ls)} | {sum(1 for x in ls if x >= 1)} | {sum(1 for x in ls if x == 0)} | "
                     f"{sum(1 for x in ls if x < 0)} | {med} |")
    lines += ["", "Technologies imputed to 2002 by Kalyani et al. are excluded from the summary: their true breakthrough predates the earnings-call sample.", ""]
    (OUT / "validation_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"detector: {len(signals)} tech-source series, {len(tier_rows)} tier rows")


if __name__ == "__main__":
    main()
