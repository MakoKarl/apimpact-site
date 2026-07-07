#!/usr/bin/env python3
"""
Post-processor: find every external CSS/image/font URL still referenced
in the scraped HTML files, download it, and rewrite the references.

Targets:
  - hubspotusercontent-na2.net  (theme CSS/JS)
  - hubspotusercontent-na1.net  (video module CSS/JS)
  - www.apimpact.com/hubfs/     (background images, fonts in CSS url())
"""

import os, re, time, urllib.parse
import requests
from pathlib import Path

SITE      = Path("site")
HEADERS   = {"User-Agent": "Mozilla/5.0"}
DELAY     = 0.2

session = requests.Session()
session.headers.update(HEADERS)

downloaded = {}   # original_url -> local_abs_path

def fetch_bytes(url):
    try:
        r = session.get(url, timeout=20)
        r.raise_for_status()
        return r.content
    except Exception as e:
        print(f"  FAIL {url}: {e}")
        return None

def url_to_local(url, prefix="ext"):
    """Map an external URL to a deterministic local path."""
    p = urllib.parse.urlparse(url)
    # Build a path: ext/<host>/<path>
    host_slug = p.netloc.replace(".", "_")
    path = p.path.lstrip("/")
    if not path:
        path = "index"
    # Strip query from path for saved filename, but incorporate it as suffix if needed
    qs = p.query
    if qs:
        # use a short hash of the query so files are unique
        import hashlib
        qs_hash = hashlib.md5(qs.encode()).hexdigest()[:6]
        stem = Path(path).stem + "_" + qs_hash
        suffix = Path(path).suffix or ""
        path = str(Path(path).parent / (stem + suffix))
    local = SITE / prefix / host_slug / path
    return local

def download(url):
    """Download url, save locally, return root-relative path."""
    if url in downloaded:
        return downloaded[url]
    local = url_to_local(url)
    if local.exists():
        rel = "/" + str(local.relative_to(SITE))
        downloaded[url] = rel
        return rel
    data = fetch_bytes(url)
    if data is None:
        downloaded[url] = url   # keep original if we can't get it
        return url
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_bytes(data)
    rel = "/" + str(local.relative_to(SITE))
    downloaded[url] = rel
    print(f"  saved {rel}")
    time.sleep(DELAY)
    return rel

# ── Patterns to match external URLs we want to localize ──────────────────────

# Matches https://anything.hubspotusercontent-na1.net/... or na2
HS_CDN = re.compile(
    r'(https://[a-zA-Z0-9.-]+\.hubspotusercontent-na[12]\.net/[^\s"\')\]>]+)'
)

# Matches https://www.apimpact.com/hubfs/... (not already local)
APIMPACT_HUBFS = re.compile(
    r'(https://(?:www\.)?apimpact\.com/hub(?:fs|[^/]*)/[^\s"\')\]>]*)'
)

# Google Fonts – leave as-is (external is fine, always accessible)

def process_file(html_path):
    text = html_path.read_text(encoding="utf-8", errors="replace")
    changed = False

    for pattern in [HS_CDN, APIMPACT_HUBFS]:
        def replace_url(m):
            url = m.group(1).rstrip("\\")
            local = download(url)
            return local
        new_text, n = pattern.subn(replace_url, text)
        if n:
            text = new_text
            changed = True

    if changed:
        html_path.write_text(text, encoding="utf-8")
        print(f"patched: {html_path}")

def main():
    html_files = list(SITE.rglob("*.html"))
    print(f"Processing {len(html_files)} HTML files...\n")
    for f in html_files:
        process_file(f)

    # Also process downloaded CSS files for nested url() references
    css_files = list(SITE.rglob("*.css"))
    ext_css = [f for f in css_files if "ext" in str(f)]
    for f in ext_css:
        text = f.read_text(encoding="utf-8", errors="replace")
        changed = False
        for pattern in [HS_CDN, APIMPACT_HUBFS]:
            new_text, n = pattern.subn(lambda m: download(m.group(1).rstrip("\\")), text)
            if n:
                text = new_text
                changed = True
        if changed:
            f.write_text(text, encoding="utf-8")
            print(f"patched CSS: {f}")

    print(f"\nDone. {len(downloaded)} URLs processed.")

if __name__ == "__main__":
    main()
