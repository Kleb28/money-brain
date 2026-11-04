"""Out-of-sample evaluation of the Rule G detector on the techdiffusion.net technology set.

Arithmetic only. Inputs (all produced by workflows, never hand-edited):
  data/external/oos_technologies.csv          1,286 Wikipedia-title technologies (Kalyani et al. 2023 release)
  data/external/oos_counts_uspto_*.csv        USPTO title-phrase filing counts 2002-2019 (sharded)
  data/external/oos_counts_edgar_*.csv        10-K full-text hit counts 2002-2019 (sharded)
  data/external/jobs_by_tech_year.csv         Burning Glass postings per bigram-year 2010-2019 (location file aggregate)
  data/counts.csv                             denominators (__all rows) for uspto / edgar_10k
Three tests, each reported for every rule in settings.detector.grid:
  A  hiring timing   — does the USPTO signal precede the job-posting emergence year (10% of max, 2010-19)?
                       controls = technologies whose posting share was flat (never +50% over 2010).
  B  cross-section   — using counts up to 2009 only, does a USPTO signal separate technologies that were
                       widely discussed on earnings calls 2002-19 (disruptive, >100 transcripts) from those
                       never discussed (<10)?  Reported within patent-size quartiles.
  C  10-K timing     — does the USPTO signal precede the 10-K emergence year (10% of max, 2002-19)?
                       controls = flat 10-K share (same validity rule as config/settings.yml) and
                       technologies that never reached 10 filings/yr.
Writes outputs/oos_report.md and outputs/oos_details.csv.
"""
from __future__ import annotations

import csv
import glob
import statistics
from collections import defaultdict
from pathlib import Path

import yaml

from detector.detector import _rule_g

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "data" / "external"
OUT = ROOT / "outputs"
YEARS = list(range(2002, 2020))
SIGNAL_WINDOW = (2004, 2017)   # first fire must fall here to count (leaves room for an outcome by 2019)


def read_csv(p: Path) -> list[dict]:
    with open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_counts(pattern: str) -> dict[str, dict[int, int]]:
    out: dict[str, dict[int, int]] = defaultdict(dict)
    for p in sorted(glob.glob(str(EXT / pattern))):
        for r in read_csv(Path(p)):
            out[r["technology_id"]][int(r["year"])] = int(r["count"])
    return out


def denominators() -> dict[str, dict[int, int]]:
    d: dict[str, dict[int, int]] = defaultdict(dict)
    for r in read_csv(ROOT / "data" / "counts.csv"):
        if r["technology_id"] == "__all":
            d[r["source"]][int(r["year"])] = int(r["count"])
    return d


def shares(raw: dict[int, int], den: dict[int, int], upto: int = 2019) -> dict[int, float]:
    return {y: raw[y] / den[y] * 1e6 for y in raw if y in den and den[y] > 0 and y <= upto}


def emergence(sh: dict[int, float], raw: dict[int, int], min_peak: int) -> tuple[int | None, str]:
    """First year share >= 10% of its max. Returns (year, status): status 'censored' when the first
    observed year already qualifies, 'weak' when the peak raw count is below min_peak, 'ok' otherwise."""
    if not sh or max(raw.values(), default=0) < min_peak:
        return None, "weak"
    m = max(sh.values())
    ys = sorted(sh)
    for y in ys:
        if sh[y] >= 0.1 * m:
            return y, ("censored" if y == ys[0] else "ok")
    return None, "weak"


def first_fire(sh: dict[int, float], raw: dict[int, int], rule: dict, upto: int = 2019) -> int | None:
    sh2 = {y: v for y, v in sh.items() if y <= upto}
    y = _rule_g(sh2, raw, rule["w"], rule["g"], rule["hits"], rule["mc"])
    if y is None or not (SIGNAL_WINDOW[0] <= y <= SIGNAL_WINDOW[1]):
        return None
    return y


def timing_table(rows: list[tuple[int | None, int, bool]]) -> dict:
    """rows = (signal_year or None, emergence_year, eligible). Lead = emergence - signal.
    eligible = the technology's peak raw count reaches the rule's min_count at all (title-phrase
    counts are sparse, so many technologies can never fire under a rule)."""
    n = len(rows)
    elig = sum(1 for r in rows if r[2])
    leads = [e - s for s, e, _ in rows if s is not None]
    led = sum(1 for x in leads if x > 0); same = sum(1 for x in leads if x == 0); lag = sum(1 for x in leads if x < 0)
    useful = sum(1 for x in leads if 1 <= x <= 5)
    return {"n": n, "eligible": elig, "signal": len(leads), "led": led, "same": same, "lagged": lag, "no_signal": n - len(leads),
            "lead_rate": led / n if n else float("nan"), "lead_rate_elig": led / elig if elig else float("nan"),
            "useful_lead_rate": useful / n if n else float("nan"),
            "median_lead": statistics.median([x for x in leads if x > 0]) if led else None}


def eligible(raw: dict[int, int], rule: dict) -> bool:
    return max(raw.values(), default=0) >= rule["mc"]


def fmt(x) -> str:
    if x is None:
        return "–"
    if isinstance(x, float):
        return f"{x:.2f}"
    return str(x)


def main() -> None:
    settings = yaml.safe_load(open(ROOT / "config" / "settings.yml", encoding="utf-8"))
    d = settings["detector"]
    w = int(d["growth_window_years"])
    grid = d["grid"]
    rules = [{"mc": mc, "g": g, "hits": h, "w": w, "name": f"{mc} / +{int(g*100)}% / {h}w"}
             for mc in grid["min_count"] for g in grid["growth_threshold"] for h in grid["consecutive_hits"]]
    techs = {r["id"]: r for r in read_csv(EXT / "oos_technologies.csv")}
    bigram_to_id = {}
    for tid, t in techs.items():
        for k in t["keywords"].split(";"):
            bigram_to_id[k.strip()] = tid
    den = denominators()
    us_raw = load_counts("oos_counts_uspto_*.csv")
    ed_raw = load_counts("oos_counts_edgar_*.csv")
    us_sh = {tid: shares(r, den["uspto"]) for tid, r in us_raw.items() if len(r) >= len(YEARS)}
    ed_sh = {tid: shares(r, den["edgar_10k"]) for tid, r in ed_raw.items() if len(r) >= len(YEARS)}

    # ---- job-posting series per technology (sum over its bigrams) ----
    jobs_h: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    jobs_t: dict[int, int] = {}
    jp = EXT / "jobs_by_tech_year.csv"
    if jp.exists():
        for r in read_csv(jp):
            tid = bigram_to_id.get(r["tech"])
            if not tid:
                continue
            y = int(r["year"])
            jobs_h[tid][y] += int(r["tech_hiring"])
            jobs_t[y] = max(jobs_t.get(y, 0), int(r["total_jobs"]))
    job_sh = {tid: {y: h[y] / jobs_t[y] * 1e6 for y in h if jobs_t.get(y)} for tid, h in jobs_h.items()}

    lines = ["# Out-of-sample evaluation — techdiffusion.net technology set", "",
             f"USPTO series complete for {len(us_sh)} / {len(techs)} technologies; 10-K series for {len(ed_sh)}; "
             f"job-posting series for {len(job_sh)}.", "",
             "Rule G: share[y] / share[y−2] ≥ 1+g, raw count ≥ min_count, for N consecutive windows; "
             f"first fire counted only if in {SIGNAL_WINDOW[0]}–{SIGNAL_WINDOW[1]}.", ""]
    details = []

    # ---- Test A: hiring timing ----
    pos_A, ctl_A = {}, []
    for tid, sh in job_sh.items():
        if tid not in us_sh:
            continue
        h = jobs_h[tid]
        if sum(h.values()) < 1000 or max(h.values()) < 100:
            continue
        em, status = emergence(sh, h, 100)
        if status == "ok" and em and em >= 2011:
            pos_A[tid] = em
        elif status == "censored":
            base = sh.get(2010, 0)
            later = [sh[y] for y in sh if y >= 2011]
            if base > 0 and later and max(later) / base < 1.5:
                ctl_A.append(tid)
    lines += ["## A. Hiring timing (Burning Glass postings 2010–2019; outcome independent of patents)",
              f"Positives: posting share < 10% of its 2010–19 max in 2010 and ≥ 1,000 postings → emergence year = first year ≥ 10% of max (n = {len(pos_A)}). "
              f"Controls: share already ≥ 10% of max in 2010 and never +50% above the 2010 level (n = {len(ctl_A)}).", "",
              "| rule | n pos | eligible (peak ≥ min_count) | signal | led | same | lagged | lead rate (all / eligible) | lead 1–5y | median lead | n ctl (eligible) | fire rate (all / eligible) | lead − fire |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for rule in rules:
        rows = [(first_fire(us_sh[tid], us_raw[tid], rule), em, eligible(us_raw[tid], rule)) for tid, em in pos_A.items()]
        t = timing_table(rows)
        ctl_e = [tid for tid in ctl_A if eligible(us_raw[tid], rule)]
        fires = sum(1 for tid in ctl_A if first_fire(us_sh[tid], us_raw[tid], rule) is not None)
        fr = fires / len(ctl_A) if ctl_A else float("nan")
        fr_e = fires / len(ctl_e) if ctl_e else float("nan")
        lines.append(f"| {rule['name']} | {t['n']} | {t['eligible']} | {t['signal']} | {t['led']} | {t['same']} | {t['lagged']} | {fmt(t['lead_rate'])} / {fmt(t['lead_rate_elig'])} | "
                     f"{fmt(t['useful_lead_rate'])} | {fmt(t['median_lead'])} | {len(ctl_A)} ({len(ctl_e)}) | {fmt(fr)} / {fmt(fr_e)} | {fmt(t['lead_rate'] - fr) if ctl_A else '–'} |")
        for tid, em in pos_A.items():
            details.append({"test": "A", "rule": rule["name"], "technology": techs[tid]["title"], "role": "positive",
                            "emergence": em, "signal": first_fire(us_sh[tid], us_raw[tid], rule)})
        for tid in ctl_A:
            details.append({"test": "A", "rule": rule["name"], "technology": techs[tid]["title"], "role": "control",
                            "emergence": "", "signal": first_fire(us_sh[tid], us_raw[tid], rule)})
    if pos_A:
        lines += ["", "Positives and their emergence years: " +
                  ", ".join(f"{techs[t]['title']} {e}" for t, e in sorted(pos_A.items(), key=lambda x: x[1]))]
    lines.append("")

    # ---- Test B: cross-section as of 2009 ----
    lines += ["## B. Cross-section, signal computed from 2002–2009 counts only",
              "Outcome = earnings-call class over 2002–19 (Kalyani et al.: disruptive > 100 transcripts, non-disruptive < 10). "
              "The transcript total includes years before 2009, so this measures association, not strict prediction. "
              "Quartiles are by total patents mentioning the technology (size control).", ""]
    classes = ["disruptive", "intermediate", "non_disruptive"]
    sizes = sorted((int(techs[t]["num_patents"]), t) for t in us_sh)
    q = {}
    for i, (_, t) in enumerate(sizes):
        q[t] = min(4, i * 4 // max(1, len(sizes)) + 1)
    for upto, label in ((2009, "as of 2009"), (2019, "as of 2019 (all years)")):
        lines += [f"### {label}", "| rule | " + " | ".join(f"fire rate {c} (n)" for c in classes) + " | lift disruptive/non | " +
                  " | ".join(f"Q{k} disr/non" for k in (1, 2, 3, 4)) + " |",
                  "|---|" + "---|" * (len(classes) + 5)]
        for rule in rules:
            fired = {t: first_fire(us_sh[t], us_raw[t], rule, upto=upto) is not None for t in us_sh}
            cells, rates = [], {}
            for c in classes:
                ids = [t for t in us_sh if techs[t]["ec_class"] == c]
                r = sum(fired[t] for t in ids) / len(ids) if ids else float("nan")
                rates[c] = r
                cells.append(f"{fmt(r)} ({len(ids)})")
            lift = rates["disruptive"] / rates["non_disruptive"] if rates.get("non_disruptive") else None
            qcells = []
            for k in (1, 2, 3, 4):
                a = [t for t in us_sh if q[t] == k and techs[t]["ec_class"] == "disruptive"]
                b = [t for t in us_sh if q[t] == k and techs[t]["ec_class"] == "non_disruptive"]
                ra = sum(fired[t] for t in a) / len(a) if a else None
                rb = sum(fired[t] for t in b) / len(b) if b else None
                qcells.append(f"{fmt(ra)}/{fmt(rb)} ({len(a)}/{len(b)})")
            lines.append(f"| {rule['name']} | " + " | ".join(cells) + f" | {fmt(lift)} | " + " | ".join(qcells) + " |")
        lines.append("")

    # ---- Test C: 10-K timing ----
    pos_C, ctl_flat, ctl_never = {}, [], []
    max_ratio = float(d.get("control_edgar_max_ratio", 3.0))
    for tid, sh in ed_sh.items():
        if tid not in us_sh:
            continue
        raw = ed_raw[tid]
        if max(raw.values()) < 10:
            ctl_never.append(tid); continue
        em, status = emergence(sh, raw, 30)
        if status == "ok" and em:
            pos_C[tid] = em
        elif status == "censored":
            base = [sh[y] for y in (2002, 2003, 2004) if sh.get(y, 0) > 0]
            later = [sh[y] for y in sh if 2005 <= y <= 2019]
            if base and later and max(later) / (sum(base) / len(base)) < max_ratio:
                ctl_flat.append(tid)
    lines += ["## C. 10-K timing (EDGAR full-text, 2002–2019; 10-K lags earnings calls by ~4 years on the 29-technology set, so leads here overstate leads vs. the market)",
              f"Positives: 10-K share < 10% of max in 2002, peak ≥ 30 filings → emergence = first year ≥ 10% of max (n = {len(pos_C)}). "
              f"Controls: flat 10-K share (max 2005–19 / mean 2002–04 < {max_ratio:g}; n = {len(ctl_flat)}) and never ≥ 10 filings in any year (n = {len(ctl_never)}).", "",
              "| rule | n pos | eligible | signal | led | same | lagged | lead rate (all / eligible) | lead 1–5y | median lead | fire rate flat (all / eligible) | fire rate never (all / eligible) | lead − fire(flat) |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for rule in rules:
        rows = [(first_fire(us_sh[tid], us_raw[tid], rule), em, eligible(us_raw[tid], rule)) for tid, em in pos_C.items()]
        t = timing_table(rows)

        def fire_rates(ids):
            e = [tid for tid in ids if eligible(us_raw[tid], rule)]
            f = sum(1 for tid in ids if first_fire(us_sh[tid], us_raw[tid], rule) is not None)
            return (f / len(ids) if ids else float("nan")), (f / len(e) if e else float("nan")), len(e)
        f_flat, f_flat_e, n_flat_e = fire_rates(ctl_flat)
        f_never, f_never_e, n_never_e = fire_rates(ctl_never)
        lines.append(f"| {rule['name']} | {t['n']} | {t['eligible']} | {t['signal']} | {t['led']} | {t['same']} | {t['lagged']} | {fmt(t['lead_rate'])} / {fmt(t['lead_rate_elig'])} | "
                     f"{fmt(t['useful_lead_rate'])} | {fmt(t['median_lead'])} | {fmt(f_flat)} / {fmt(f_flat_e)} (n={n_flat_e}) | {fmt(f_never)} / {fmt(f_never_e)} (n={n_never_e}) | {fmt(t['lead_rate'] - f_flat) if ctl_flat else '–'} |")
        for tid, em in pos_C.items():
            details.append({"test": "C", "rule": rule["name"], "technology": techs[tid]["title"], "role": "positive",
                            "emergence": em, "signal": first_fire(us_sh[tid], us_raw[tid], rule)})
    lines.append("")

    OUT.mkdir(exist_ok=True)
    (OUT / "oos_report.md").write_text("\n".join(lines), encoding="utf-8")
    with open(OUT / "oos_details.csv", "w", newline="", encoding="utf-8") as f:
        wri = csv.DictWriter(f, fieldnames=["test", "rule", "technology", "role", "emergence", "signal"])
        wri.writeheader(); wri.writerows(details)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
