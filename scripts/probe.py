"""Read the techdiffusion.net site text (data documentation) and list the three Dropbox folders."""
from __future__ import annotations

import html
import re

import requests

H = {"User-Agent": "Mozilla/5.0 (money-brain research probe)"}


def text_of(url):
    r = requests.get(url, headers=H, timeout=120)
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", r.text, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", "\n", t)
    t = html.unescape(t)
    t = re.sub(r"\n\s*\n+", "\n", t)
    return r.status_code, t


def log(*a):
    print(*a, flush=True)


base = "https://www.techdiffusion.net"
r = requests.get(base, headers=H, timeout=120)
links = sorted(set(re.findall(r'href="(/[^"#?]*)"', r.text)))
log("site pages:", links)
for p in [""] + [l for l in links if l not in ("/",)]:
    code, t = text_of(base + p)
    log(f"\n######## PAGE {p or '/'} status {code}")
    log(t[:6000])

for name, url in {
    "folder1": "https://www.dropbox.com/sh/kml262k1l381mw6/AAA5A6YjQPz6ATLlXr5l49Ana?dl=0",
    "folder2": "https://www.dropbox.com/scl/fo/hnmj9svolva18ca88vixk/AKjuI1MXiojRkdxgO6XR5rw?rlkey=evdkmt0ywad3vohf71jb1naqo&st=iqoaoudk&dl=0",
    "folder3": "https://www.dropbox.com/scl/fo/q8qem553r8qflgx127wi1/AAo-LwqkR5zWFud3z2uIVGk?rlkey=ozlw34nmmdh0uy5ab74ga09ba&dl=0",
}.items():
    log(f"\n######## {name}")
    try:
        r = requests.get(url, headers=H, timeout=120)
        log("status", r.status_code, "bytes", len(r.text))
        m = re.search(r"<title>(.*?)</title>", r.text, flags=re.S)
        log("title:", html.unescape(m.group(1)).strip() if m else None)
        names = sorted(set(re.findall(r'"(?:filename|name)"\s*:\s*"([^"]{1,120}\.(?:dta|csv|xlsx|xls|pdf|txt|zip|do|R|py|md|docx)(?:\.gz)?)"', r.text)))
        log("file names in page json:", names[:100])
        words = sorted(set(re.findall(r'[\w\-]+\.(?:dta|csv|xlsx|pdf|zip|txt|do)\b', html.unescape(r.text))))
        log("file-like tokens:", words[:100])
        for pat in ("rlkey", "sharing_modal", "folder"):
            pass
    except Exception as e:  # noqa: BLE001
        log("EXC", repr(e)[:300])
