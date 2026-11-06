"""Theme-level market check on EDGAR full-text search (runs on the Actions runner; sec.gov is not
reachable from the sandbox).

For every theme in config/themes.yml and every market phrase:
  1. yearly 10-K counts 2015-<now>  -> outputs/theme_market.md (table) + data/external/theme_market_counts.csv
  2. the filers whose 10-Ks (filed 2024-<now>) contain the phrase, with how many of their filings do
     -> outputs/theme_filers.csv  (theme, phrase, entity, ticker, cik, n_filings)
Entity names come from EFTS display_names ("NVIDIA CORP  (NVDA)  (CIK 0001045810)").
Arithmetic only; the for/against linkage judgement happens later, on this evidence.
"""
from __future__ import annotations

import csv
import datetime as dt
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

import requests
import yaml

from collectors.common import RateLimiter, env, log
from collectors.edgar import EFTS, hits

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
EXT = ROOT / "data" / "external"
Y0, Y1 = 2015, dt.date.today().year
FILER_FROM = 2024
MAX_PAGES = 10


def filers(phrase: str, headers: dict, rl: RateLimiter) -> Counter:
    c: Counter = Counter()
    for page in range(1, MAX_PAGES + 1):
        rl.wait()
        params = {"q": f'"{phrase}"', "forms": "10-K", "dateRange": "custom",
                  "startdt": f"{FILER_FROM}-01-01", "enddt": f"{Y1}-12-31", "page": page, "from": (page - 1) * 100}
        r = requests.get(EFTS, params=params, headers=headers, timeout=60)
        if r.status_code != 200:
            log(f"  filers {phrase} p{page}: HTTP {r.status_code}"); break
        hs = r.json().get("hits", {}).get("hits", [])
        if not hs:
            break
        for h in hs:
            for name in h.get("_source", {}).get("display_names", []):
                c[name] += 1
        if len(hs) < 100:
            break
    return c


def main() -> None:
    cfg = yaml.safe_load(open(ROOT / "config" / "themes.yml", encoding="utf-8"))["themes"]
    ua = env("EDGAR_USER_AGENT") or "money-brain-collector (set EDGAR_USER_AGENT)"
    headers = {"User-Agent": ua, "Accept": "application/json"}
    rl = RateLimiter(4.0)
    OUT.mkdir(exist_ok=True); EXT.mkdir(parents=True, exist_ok=True)
    years = list(range(Y0, Y1 + 1))
    count_rows, filer_rows = [], []
    md = ["# Theme-level 10-K mentions (EDGAR full-text, form 10-K, by filing year)", ""]
    for tid, t in cfg.items():
        md += [f"## {t['name']} ({tid})", "", "| phrase | " + " | ".join(str(y) for y in years) + " |", "|---|" + "---|" * len(years)]
        for ph in t["market_phrases"]:
            row = []
            for y in years:
                n = hits(f'"{ph}"', "10-K", y, headers, rl)
                row.append(n); count_rows.append([tid, ph, y, n])
            md.append(f"| {ph} | " + " | ".join(str(n) for n in row) + " |")
            fc = filers(ph, headers, rl)
            for name, n in fc.most_common():
                m = re.match(r"^(.*?)\s+\((\S+)\)\s+\(CIK (\d+)\)", name)
                if m:
                    ent, tick, cik = m.group(1).strip(), m.group(2), m.group(3)
                else:
                    m2 = re.match(r"^(.*?)\s+\(CIK (\d+)\)", name)
                    ent, tick, cik = (m2.group(1).strip(), "", m2.group(2)) if m2 else (name, "", "")
                filer_rows.append([tid, ph, ent, tick, cik, n])
            log(f"{tid}: {ph} -> {sum(row)} filings {Y0}-{Y1}; {len(fc)} filers since {FILER_FROM}")
        md.append("")
    (OUT / "theme_market.md").write_text("\n".join(md), encoding="utf-8")
    with open(EXT / "theme_market_counts.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["theme", "phrase", "year", "count"]); w.writerows(count_rows)
    with open(OUT / "theme_filers.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["theme", "phrase", "entity", "ticker", "cik", "n_filings"]); w.writerows(filer_rows)
    log(f"wrote {len(count_rows)} count rows, {len(filer_rows)} filer rows")


if __name__ == "__main__":
    main()
