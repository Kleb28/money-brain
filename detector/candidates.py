"""Candidate discovery, stage 2: apply the pre-registered Rule G (config/settings.yml) to every bigram
in data/external/bigram_counts.csv.gz and list the ones whose signal is recent.

Arithmetic only — no scoring by an LLM. Steps:
  1. share = count / (__all documents that year) * 1e6, years >= settings.years.start
  2. Rule G exactly as detector.detector (min_count, +growth over window, consecutive windows)
  3. keep bigrams whose first signal year >= --since (default: latest complete year − 6) and whose
     latest complete-year share is still >= its share two years earlier (not already fading)
  4. drop non-term bigrams deterministically: a token that WordNet knows only as a finite verb or an
     adverb (enhances, ensures, obtain, gradually), or a function word missed by the SQL stoplist;
     participles and gerunds are kept (machine learning, distributed ledger)
  5. drop bigrams used by fewer than settings.candidates.min_assignees distinct applicants in the
     latest complete year (one applicant's continuation family is not a technology), when the counts
     file carries n_assignees
  6. collapse plural/singular variants (same token stems) and identical count series (same family)
  7. optional: merge 10-K counts (data/external/cand_counts_edgar_*.csv) to assign the provisional Tier
Outputs: outputs/candidates_bigrams.csv (all survivors), outputs/candidates.md (summary) and
data/external/cand_technologies.csv (id, keywords — input for the 10-K collector).
The latest complete filing year is the last year whose __all count is >= 90% of the year before
(applications publish ~18 months after filing, so the most recent years are undercounted).
"""
from __future__ import annotations

import argparse
import csv
import glob
import gzip
import re
from collections import defaultdict
from pathlib import Path

import yaml

from detector.detector import _rule_g

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "data" / "external"
OUT = ROOT / "outputs"
ALL = "__all"


EXTRA_STOP = set("""across around along toward towards against beyond behind until since whether because although
though however therefore thus hence whereas unless whereby wherever whenever every either neither own like
unlike near far away back forth together apart instead rather quite rather almost already still yet
ever never often always usually typically generally particularly especially preferably optionally
""".split())


def _wordnet():
    try:
        from nltk.corpus import wordnet as wn
        wn.synsets("test")
        return wn
    except LookupError:
        import nltk
        nltk.download("wordnet", quiet=True)
        from nltk.corpus import wordnet as wn
        return wn
    except ImportError:
        return None


def is_term(bigram: str, wn) -> bool:
    """Deterministic non-term filter. Keeps a bigram unless a token is a function word, an adverb-only
    word, or a finite-verb-only word (WordNet has no noun/adjective sense for it and it is not a
    participle/gerund). Unknown tokens (new jargon, acronyms) are kept."""
    for t in bigram.split():
        if t in EXTRA_STOP:
            return False
        if wn is None or t.endswith("ing") or t.endswith("ed"):
            continue
        pos = {s.pos() for s in wn.synsets(t)}
        if not pos:
            continue
        if pos <= {"r"}:
            return False
        if pos <= {"v"}:
            return False
        if "n" not in pos and "a" not in pos and "s" not in pos and t.endswith("s"):
            base = {s.pos() for s in wn.synsets(t[:-1])} | {s.pos() for s in wn.synsets(t[:-2])}
            if base and base <= {"v"}:
                return False
    return True


def stem(tok: str) -> str:
    for suf in ("ies", "es", "s"):
        if tok.endswith(suf) and len(tok) - len(suf) >= 3:
            return tok[: -len(suf)] + ("y" if suf == "ies" else "")
    return tok


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", type=int, default=None, help="earliest signal year to keep")
    ap.add_argument("--top", type=int, default=300, help="rows in the markdown summary")
    a = ap.parse_args()
    settings = yaml.safe_load(open(ROOT / "config" / "settings.yml", encoding="utf-8"))
    d = settings["detector"]
    w, g, hits, mc = int(d["growth_window_years"]), float(d["growth_threshold"]), int(d["consecutive_hits"]), int(d["min_count"])
    y_start = int(settings["years"]["start"])
    lo, hi = int(d["tier"]["edgar_low_max"]), int(d["tier"]["edgar_high_min"])
    min_asg = int(settings.get("candidates", {}).get("min_assignees", 10))

    raw: dict[str, dict[int, int]] = defaultdict(dict)
    asg: dict[str, dict[int, int]] = defaultdict(dict)
    with gzip.open(EXT / "bigram_counts.csv.gz", "rt", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            y = int(r["year"])
            if y >= y_start:
                raw[r["bigram"]][y] = int(r["count"])
                if r.get("n_assignees"):
                    asg[r["bigram"]][y] = int(r["n_assignees"])
    den = raw.pop(ALL)
    asg.pop(ALL, None)
    years = sorted(den)
    complete = [y for i, y in enumerate(years) if i == 0 or den[y] >= 0.9 * den[years[i - 1]]]
    latest = max(complete)
    since = a.since or latest - 6
    print(f"bigrams: {len(raw):,}; denominators {years[0]}-{years[-1]}; latest complete filing year {latest}; keeping signals >= {since}")

    wn = _wordnet()
    dropped = {"rule": 0, "fading": 0, "non_term": 0, "few_assignees": 0}
    rows = []
    for bg, counts in raw.items():
        sh = {y: counts.get(y, 0) / den[y] * 1e6 for y in years if den[y] and y <= latest}
        sig = _rule_g(sh, counts, w, g, hits, mc)
        if sig is None or sig < since:
            dropped["rule"] += 1; continue
        if (latest - 2) in sh and sh[latest - 2] > 0 and sh[latest] < sh[latest - 2]:
            dropped["fading"] += 1; continue
        if not is_term(bg, wn):
            dropped["non_term"] += 1; continue
        n_asg = asg.get(bg, {}).get(latest)
        if n_asg is not None and n_asg < min_asg:
            dropped["few_assignees"] += 1; continue
        g3 = (sh[latest] / sh[latest - 3] - 1) if sh.get(latest - 3, 0) > 0 else None
        rows.append({"bigram": bg, "signal_year": sig, "latest_year": latest, "latest_count": counts.get(latest, 0),
                     "latest_share_ppm": round(sh[latest], 1), "growth_3y": None if g3 is None else round(g3, 2),
                     "n_assignees": n_asg,
                     "count_series": " ".join(str(counts.get(y, 0)) for y in years if y <= latest)})
    print("dropped:", dropped)

    # collapse plural/singular variants and identical count series (same patent family)
    best: dict[str, dict] = {}
    for r in sorted(rows, key=lambda r: r["bigram"]):
        key = " ".join(stem(t) for t in r["bigram"].split())
        key2 = "series:" + r["count_series"] if r["latest_count"] >= 30 else key
        k = key if key in best else (key2 if key2 in best else key)
        if k not in best or r["latest_count"] > best[k]["latest_count"]:
            r["variants"] = sorted({r["bigram"], *(best.get(k, {}).get("variants", []))})
            best[k] = r
            best[key2] = r
        else:
            best[k]["variants"] = sorted({*best[k]["variants"], r["bigram"]})
    seen, uniq = set(), []
    for r in best.values():
        if id(r) not in seen:
            seen.add(id(r)); uniq.append(r)
    rows = sorted(uniq, key=lambda r: (-r["signal_year"], -(r["growth_3y"] or 0)))

    # optional 10-K counts → provisional tier
    ed: dict[str, dict[int, int]] = defaultdict(dict)
    for p in glob.glob(str(EXT / "cand_counts_edgar_*.csv")):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            ed[r["technology_id"]][int(r["year"])] = int(r["count"])
    for r in rows:
        e = ed.get(re.sub(r"[^a-z0-9]+", "_", r["bigram"]))
        if e:
            ly = max(y for y in e if y <= latest + 1)
            r["edgar_latest"] = e[ly]
            r["tier"] = "T2" if e[ly] >= hi else ("T0" if e[ly] < lo else "T1")
        else:
            r["edgar_latest"], r["tier"] = None, None

    OUT.mkdir(exist_ok=True)
    fields = ["bigram", "variants", "signal_year", "latest_year", "latest_count", "latest_share_ppm", "growth_3y",
              "n_assignees", "edgar_latest", "tier", "count_series"]
    with open(OUT / "candidates_bigrams.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=fields); wr.writeheader()
        for r in rows:
            wr.writerow({**r, "variants": "; ".join(r["variants"])})
    with open(EXT / "cand_technologies.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f); wr.writerow(["id", "keywords"])
        for r in rows:
            wr.writerow([re.sub(r"[^a-z0-9]+", "_", r["bigram"]), "; ".join(r["variants"])])
    by_year = defaultdict(int)
    for r in rows:
        by_year[r["signal_year"]] += 1
    lines = [f"# Candidate bigrams — Rule G ({mc} / +{int(g*100)}% / {hits} consecutive) on all US patent title+abstract bigrams",
             "", f"Latest complete filing year {latest}; signals since {since}; {len(rows)} bigrams after collapsing plural variants.",
             "Signals per year: " + ", ".join(f"{y}: {n}" for y, n in sorted(by_year.items())), "",
             f"Top {a.top} by signal recency, then 3-year growth:", "",
             "| bigram | signal | latest count | assignees | share ppm | growth 3y | 10-K latest | tier |", "|---|---|---|---|---|---|---|---|"]
    for r in rows[: a.top]:
        lines.append(f"| {r['bigram']} | {r['signal_year']} | {r['latest_count']} | {r['n_assignees'] if r['n_assignees'] is not None else '–'} | {r['latest_share_ppm']} | "
                     f"{r['growth_3y'] if r['growth_3y'] is not None else '–'} | {r['edgar_latest'] if r['edgar_latest'] is not None else '–'} | {r['tier'] or '–'} |")
    (OUT / "candidates.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"candidates: {len(rows)} bigrams; by signal year {dict(sorted(by_year.items()))}")


if __name__ == "__main__":
    main()
