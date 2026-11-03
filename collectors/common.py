"""Shared helpers for all collectors.

Data contract (data/counts.csv):
    technology_id, source, year, count, collected_at
One row per (technology_id, source, year). A source named "<source>__all" holds the
per-year denominator (all documents in that source), used to normalise counts to shares.
"""
from __future__ import annotations

import csv
import datetime as dt
import os
import sys
import time
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"
DATA = ROOT / "data"
COUNTS_PATH = DATA / "counts.csv"
COUNTS_FIELDS = ["technology_id", "source", "year", "count", "collected_at"]

ALL = "__all"  # denominator technology_id


def log(msg: str) -> None:
    print(f"[{dt.datetime.utcnow():%H:%M:%S}] {msg}", file=sys.stderr, flush=True)


def load_settings() -> dict:
    with open(CONFIG / "settings.yml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_technologies() -> list[dict]:
    rows = []
    with open(CONFIG / "technologies.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            r["keywords"] = [k.strip() for k in r["keywords"].split(";") if k.strip()]
            r["ec_year"] = int(r["ec_year"]) if r.get("ec_year") else None
            rows.append(r)
    return rows


def year_range(settings: dict) -> list[int]:
    y0 = int(settings["years"]["start"])
    y1 = settings["years"]["end"] or dt.date.today().year
    return list(range(y0, int(y1) + 1))


def load_counts() -> dict[tuple[str, str, int], dict]:
    out = {}
    if COUNTS_PATH.exists():
        with open(COUNTS_PATH, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                r["year"] = int(r["year"])
                r["count"] = int(r["count"])
                out[(r["technology_id"], r["source"], r["year"])] = r
    return out


def save_counts(rows: dict[tuple[str, str, int], dict]) -> None:
    DATA.mkdir(exist_ok=True)
    with open(COUNTS_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COUNTS_FIELDS)
        w.writeheader()
        for key in sorted(rows):
            w.writerow({k: rows[key][k] for k in COUNTS_FIELDS})


def needs_collection(existing: dict, tech_id: str, source: str, year: int, settings: dict) -> bool:
    """Skip (tech, source, year) already present unless it is within the refresh window."""
    if (tech_id, source, year) not in existing:
        return True
    refresh_from = dt.date.today().year - int(settings["years"]["refresh_last_n"])
    return year >= refresh_from


def upsert(existing: dict, tech_id: str, source: str, year: int, count: int) -> None:
    existing[(tech_id, source, year)] = {
        "technology_id": tech_id,
        "source": source,
        "year": year,
        "count": int(count),
        "collected_at": dt.date.today().isoformat(),
    }


def get_json(url: str, params: dict | None = None, headers: dict | None = None,
             retries: int = 4, backoff: float = 2.0, timeout: int = 60):
    """GET with simple retry/backoff. Returns parsed JSON (or raw text when not JSON)."""
    last_err = None
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=timeout)
            if r.status_code == 429 or r.status_code >= 500:
                raise requests.HTTPError(f"{r.status_code} {r.reason}", response=r)
            r.raise_for_status()
            ctype = r.headers.get("content-type", "")
            return r.json() if "json" in ctype else r.text
        except Exception as e:  # noqa: BLE001
            last_err = e
            wait = backoff ** attempt
            log(f"  retry {attempt + 1}/{retries} after error: {e} (sleep {wait:.0f}s)")
            time.sleep(wait)
    raise RuntimeError(f"GET failed after {retries} attempts: {url} :: {last_err}")


class RateLimiter:
    def __init__(self, per_second: float):
        self.interval = 1.0 / per_second if per_second > 0 else 0
        self._last = 0.0

    def wait(self) -> None:
        now = time.monotonic()
        delta = now - self._last
        if delta < self.interval:
            time.sleep(self.interval - delta)
        self._last = time.monotonic()


def env(name: str, default: str | None = None) -> str | None:
    v = os.environ.get(name)
    return v if v else default
