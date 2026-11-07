"""Sim B2 (V3): annual revenue and R&D expense per filer from EDGAR companyfacts (XBRL), for the
CIKs that appear in data/external/sim_filers_*.csv with a ticker. Output: data/external/sim_financials.csv
(cik, ticker, fy, revenue, rd). Runs on the Actions runner (sec.gov). Resumable."""
from __future__ import annotations

import csv
import glob
import time
from pathlib import Path

import requests

from collectors.common import RateLimiter, env, log

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "data" / "external"
OUT = EXT / "sim_financials.csv"
REV_TAGS = ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet", "RevenueFromContractWithCustomerIncludingAssessedTax"]
RD_TAGS = ["ResearchAndDevelopmentExpense", "ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost"]


def annual(facts: dict, tags: list[str]) -> dict[int, float]:
    out: dict[int, float] = {}
    gaap = facts.get("facts", {}).get("us-gaap", {})
    for tag in tags:
        for u in gaap.get(tag, {}).get("units", {}).get("USD", []):
            if u.get("form") in ("10-K", "10-K/A", "20-F", "40-F") and u.get("fp") == "FY" and u.get("fy"):
                fy = int(u["fy"])
                # keep the latest-filed value per fiscal year, prefer full-year durations
                if fy not in out:
                    out[fy] = float(u["val"])
        if out:
            break
    return out


def main() -> None:
    ciks: dict[str, str] = {}
    for p in glob.glob(str(EXT / "sim_filers_*.csv")):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            if r["ticker"].strip() and r["cik"].strip():
                ciks.setdefault(r["cik"].strip().lstrip("0") or "0", r["ticker"].strip().upper())
    done = set()
    rows = []
    if OUT.exists():
        for r in csv.DictReader(open(OUT, encoding="utf-8")):
            done.add(r["cik"]); rows.append([r["cik"], r["ticker"], r["fy"], r["revenue"], r["rd"]])
    headers = {"User-Agent": env("EDGAR_USER_AGENT") or "money-brain-collector (set EDGAR_USER_AGENT)", "Accept": "application/json"}
    rl = RateLimiter(8.0)
    todo = [c for c in ciks if c not in done]
    log(f"companyfacts: {len(ciks)} CIKs, {len(todo)} to fetch")
    t0 = time.time()
    for i, cik in enumerate(todo):
        rl.wait()
        try:
            r = requests.get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cik):010d}.json", headers=headers, timeout=60)
        except requests.RequestException as e:
            log(f"  {cik}: {e.__class__.__name__}"); time.sleep(5); continue
        if r.status_code != 200:
            rows.append([cik, ciks[cik], "", "", ""]); done.add(cik); continue
        try:
            facts = r.json()
        except ValueError:
            continue
        rev, rd = annual(facts, REV_TAGS), annual(facts, RD_TAGS)
        years = sorted(set(rev) | set(rd))
        if not years:
            rows.append([cik, ciks[cik], "", "", ""])
        for fy in years:
            rows.append([cik, ciks[cik], fy, rev.get(fy, ""), rd.get(fy, "")])
        done.add(cik)
        if i % 300 == 0:
            log(f"  {i}/{len(todo)} ({(time.time()-t0)/60:.0f} min)")
            with open(OUT, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f); w.writerow(["cik", "ticker", "fy", "revenue", "rd"]); w.writerows(rows)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["cik", "ticker", "fy", "revenue", "rd"]); w.writerows(rows)
    log(f"companyfacts: wrote {len(rows)} rows for {len(done)} CIKs in {(time.time()-t0)/60:.0f} min")


if __name__ == "__main__":
    main()
