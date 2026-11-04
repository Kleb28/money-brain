"""Build the out-of-sample technology list from the techdiffusion.net release (tech_summary).

One row per Wikipedia title (1,286 from 1,899 bigrams); bigrams of the same title are OR-ed as
keywords, like the 29-technology keyword groups. Deterministic; no judgement calls.
Output: data/external/oos_technologies.csv  (id, title, keywords, start_year, transcript_counts,
num_patents, total_postings, ec_class)
ec_class follows Kalyani et al. (NBER w28999 rev2): disruptive > 100 earnings-call transcripts,
intermediate 10-100, non_disruptive < 10. transcript_counts is per bigram in the source and
identical for singular/plural variants, so the title-level value is the max, not the sum.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "external" / "tech_summary.csv.gz"
OUT = ROOT / "data" / "external" / "oos_technologies.csv"


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:60]


def main() -> None:
    ts = pd.read_csv(SRC)
    g = ts.groupby("title").agg(
        keywords=("tech", lambda x: "; ".join(sorted(set(x)))),
        start_year=("start_year", "min"),
        transcript_counts=("transcript_counts", "max"),
        num_patents=("num_patents", "sum"),
        total_postings=("total_postings", "sum"),
    ).reset_index()
    g["id"] = "oos_" + g["title"].map(slug)
    assert g["id"].is_unique
    g["ec_class"] = pd.cut(g["transcript_counts"], [-1, 9, 100, 10**9],
                           labels=["non_disruptive", "intermediate", "disruptive"]).astype(str)
    g = g.sort_values("id")[["id", "title", "keywords", "start_year", "transcript_counts",
                             "num_patents", "total_postings", "ec_class"]]
    g.to_csv(OUT, index=False)
    print(len(g), "titles;", g.ec_class.value_counts().to_dict())


if __name__ == "__main__":
    main()
