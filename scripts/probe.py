"""Discover what www.techdiffusion.net publishes (Bloom-Hassan-Kalyani-Lerner-Tahoun data release).
Step 1: fetch the landing page(s), print title, text excerpt, and every link with its extension/size."""
from __future__ import annotations

import re
from urllib.parse import urljoin

import requests

H = {"User-Agent": "Mozilla/5.0 (money-brain research probe)"}
seen = set()


def fetch(url):
    r = requests.get(url, headers=H, timeout=60, allow_redirects=True)
    print(f"\n=== {url} -> {r.status_code} final={r.url} ctype={r.headers.get('content-type')} len={len(r.content)}")
    return r


for start in ("https://www.techdiffusion.net", "http://www.techdiffusion.net", "https://techdiffusion.net"):
    try:
        r = fetch(start)
    except Exception as e:  # noqa: BLE001
        print("EXC", e); continue
    if r.status_code != 200:
        continue
    html = r.text
    t = re.search(r"<title>(.*?)</title>", html, re.S)
    print("title:", t.group(1).strip() if t else None)
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text); text = re.sub(r"\s+", " ", text)
    print("text excerpt:", text[:1500])
    links = re.findall(r'href=["\']([^"\']+)["\']', html)
    print(f"{len(links)} links:")
    for l in links:
        full = urljoin(r.url, l)
        if full in seen:
            continue
        seen.add(full)
        print("  ", full)
    # follow same-site html links one level to find data pages
    for l in list(seen):
        if "techdiffusion" in l and not re.search(r"\.(png|jpg|css|js|ico)$", l) and l != r.url:
            try:
                r2 = fetch(l)
                if "html" in (r2.headers.get("content-type") or ""):
                    sub = re.findall(r'href=["\']([^"\']+)["\']', r2.text)
                    for s in sub:
                        fs = urljoin(r2.url, s)
                        if fs not in seen:
                            seen.add(fs); print("    sub:", fs)
            except Exception as e:  # noqa: BLE001
                print("    EXC", e)
    break
print("\nDATA-LIKE LINKS:")
for l in sorted(seen):
    if re.search(r"\.(csv|dta|zip|xlsx|xls|parquet|tsv|txt|json|gz|7z|rar|tar)(\?|$)", l, re.I) or "drive.google" in l or "dropbox" in l or "dataverse" in l or "github" in l:
        print("  ", l)
