"""VC deal sourcing from the theme signal: applicants (assignees) behind recent US patent applications
whose title matches a theme's phrases (USPTO Open Data Portal search; title-only, so precision over
recall). Public companies are identified by name match against the SEC registrant list
(company_tickers.json); everything else is 'not SEC-registered' = private, foreign, or academic.
Output: outputs/dealflow.md and outputs/dealflow.csv. Runs on the Actions runner (api.uspto.gov, sec.gov).
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

import requests
import yaml

from collectors.common import env, log
from collectors.uspto import DEFAULT_BASE, TITLE, DATE, UTILITY

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
Y0, Y1 = 2022, dt.date.today().year
PAGE = 100
MAX_PAGES = 30
ACADEMIC = re.compile(r"\b(universit|institute|college|school|foundation|hospital|research council|academy|national lab|cnrs|fraunhofer|csic|riken)\b", re.I)


def norm(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\b(inc|corp|corporation|co|company|ltd|limited|llc|plc|sa|ag|nv|se|gmbh|kk|kabushiki kaisha|holdings?|group|technologies|technology|international|the)\b", " ", s)
    return " ".join(s.split())


def sec_registrants(headers) -> dict[str, tuple[str, str]]:
    r = requests.get("https://www.sec.gov/files/company_tickers.json", headers=headers, timeout=60)
    r.raise_for_status()
    out = {}
    for v in r.json().values():
        out[norm(v["title"])] = (v["ticker"], v["title"])
    return out


def search(base, key, phrases, page) -> dict:
    kw = " OR ".join(f'{TITLE}:"{p}"' for p in phrases)
    q = f"({kw}) AND {DATE}:[{Y0}-01-01 TO {Y1}-12-31] AND {UTILITY}"
    body = {"q": q, "pagination": {"offset": page * PAGE, "limit": PAGE}}
    for attempt in range(4):
        r = requests.post(base, json=body, headers={"X-API-KEY": key, "Content-Type": "application/json"}, timeout=90)
        if r.status_code == 200:
            return r.json()
        if r.status_code == 404:
            return {"count": 0, "patentFileWrapperDataBag": []}
        time.sleep(15 * (attempt + 1))
    return {}


def applicant_names(rec: dict) -> list[str]:
    md = rec.get("applicationMetaData", {})
    names = []
    for k in ("firstApplicantName",):
        if md.get(k):
            names.append(md[k])
    for a in md.get("applicantBag", []) or rec.get("applicantBag", []) or []:
        n = a.get("applicantNameText") or a.get("name")
        if n:
            names.append(n)
    for a in rec.get("assignmentBag", []) or []:
        for ae in a.get("assigneeBag", []) or []:
            n = ae.get("assigneeNameText")
            if n:
                names.append(n)
    return list(dict.fromkeys(names))


def main() -> None:
    key = env("USPTO_API_KEY")
    if not key:
        raise SystemExit("USPTO_API_KEY missing")
    base = env("USPTO_API_BASE", DEFAULT_BASE)
    headers = {"User-Agent": env("EDGAR_USER_AGENT") or "money-brain (set EDGAR_USER_AGENT)"}
    sec = sec_registrants(headers)
    themes = yaml.safe_load(open(ROOT / "config" / "themes.yml", encoding="utf-8"))["themes"]
    selected = [t.strip() for t in (env("DEALFLOW_THEMES") or "adv_packaging,ntn_wifi7_oran,battery_chem_mfg").split(",")]
    rows, md = [], ["# Deal flow — applicants behind recent US patent applications in the selected themes", "",
                    f"Title-phrase search on the USPTO ODP API, filings {Y0}-{Y1}; applicant/assignee names from the application record. "
                    "'SEC' = name matches an SEC registrant (public filer); 'academic' = university/institute pattern; 'other' = private, foreign, or unmatched. "
                    "Arithmetic listing only — no ranking by judgement. Name matching is approximate (verify before use).", ""]
    first_rec_printed = False
    for tid in selected:
        t = themes[tid]
        phrases = t["patent_keywords"] + t.get("market_phrases", [])
        counter: Counter = Counter(); sample_titles: dict[str, list[str]] = defaultdict(list)
        total = None
        for page in range(MAX_PAGES):
            res = search(base, key, phrases, page)
            if not res:
                break
            total = res.get("count", total)
            recs = res.get("patentFileWrapperDataBag", []) or []
            if not recs:
                break
            if not first_rec_printed:
                log("sample record keys: " + ", ".join(sorted(recs[0].keys())))
                log("sample metadata keys: " + ", ".join(sorted(recs[0].get("applicationMetaData", {}).keys())))
                first_rec_printed = True
            for rec in recs:
                names = applicant_names(rec)
                title = rec.get("applicationMetaData", {}).get("inventionTitle", "")
                for n in names[:1]:
                    counter[n] += 1
                    if len(sample_titles[n]) < 2:
                        sample_titles[n].append(title)
            time.sleep(1.2)
            if len(recs) < PAGE:
                break
        log(f"{tid}: {total} applications matched, {len(counter)} applicants collected")
        md += [f"## {t['name']} ({tid}) — {total} applications {Y0}-{Y1}, {len(counter)} applicants", "",
               "| applicant | applications | class | ticker | sample title |", "|---|---|---|---|---|"]
        for name, n in counter.most_common(80):
            key_n = norm(name)
            cls, tick = "other", ""
            if ACADEMIC.search(name):
                cls = "academic"
            elif key_n in sec:
                cls, tick = "SEC", sec[key_n][0]
            else:
                for k, (tk, _) in sec.items():
                    if len(k) >= 6 and (key_n.startswith(k) or k.startswith(key_n)):
                        cls, tick = "SEC?", tk; break
            rows.append([tid, name, n, cls, tick, sample_titles[name][0] if sample_titles[name] else ""])
            md.append(f"| {name} | {n} | {cls} | {tick} | {(sample_titles[name][0] if sample_titles[name] else '')[:80]} |")
        md.append("")
    OUT.mkdir(exist_ok=True)
    (OUT / "dealflow.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    with open(OUT / "dealflow.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["theme", "applicant", "applications", "class", "ticker", "sample_title"]); w.writerows(rows)
    log(f"wrote {len(rows)} applicant rows")


if __name__ == "__main__":
    main()
