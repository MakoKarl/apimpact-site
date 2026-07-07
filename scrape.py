#!/usr/bin/env python3
"""
Mirror apimpact.com to a local static folder.
Usage: python3 scrape.py
Output: ./site/ directory ready to deploy to Azure Static Web Apps
"""

import os, re, time, urllib.parse
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from collections import deque

BASE_URL   = "https://www.apimpact.com"
OUT_DIR    = Path("site")
DELAY      = 0.3
MAX_PAGES  = 2000
HEADERS    = {"User-Agent": "Mozilla/5.0 (compatible; SiteMirror/1.0)"}

visited   = set()
queue     = deque([BASE_URL + "/"])

session = requests.Session()
session.headers.update(HEADERS)

ASSET_EXTS = {
    ".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp",
    ".ico", ".woff", ".woff2", ".ttf", ".eot", ".otf", ".pdf",
    ".mp4", ".mp3", ".xml", ".json", ".txt", ".map", ".rss"
}

def normalize(url: str, base: str) -> str:
    url = urllib.parse.urljoin(base, url)
    url = url.split("#")[0].rstrip("?&").rstrip("&").rstrip("?")
    return url

def is_internal(url: str) -> bool:
    p = urllib.parse.urlparse(url)
    return p.netloc in ("", "www.apimpact.com", "apimpact.com")

def is_asset(url: str) -> bool:
    ext = Path(urllib.parse.urlparse(url).path).suffix.lower()
    return ext in ASSET_EXTS

def url_to_local(url: str) -> Path:
    """URL → local file path. Pages without extension get /index.html."""
    p = urllib.parse.urlparse(url)
    path = p.path.lstrip("/")
    if not path:
        path = "index.html"
    elif not Path(path).suffix:
        path = path.rstrip("/") + "/index.html"
    # For assets with query strings, use just the path
    return OUT_DIR / path

def fetch(url: str):
    try:
        r = session.get(url, timeout=20, allow_redirects=True)
        r.raise_for_status()
        return r
    except Exception as e:
        print(f"  SKIP {url}  ({e})")
        return None

def save(local: Path, data: bytes):
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_bytes(data)

def path_for_url(url: str) -> str:
    """Return the root-relative local path for a URL (for href/src rewriting)."""
    p = urllib.parse.urlparse(url)
    path = p.path
    if not path or path == "/":
        return "/"
    if not Path(path).suffix:
        path = path.rstrip("/") + "/index.html"
    return path

def process_page(url: str, content: bytes):
    soup = BeautifulSoup(content, "lxml")

    # Collect and rewrite <a href>
    for tag in soup.find_all("a", href=True):
        abs_url = normalize(tag["href"], url)
        if is_internal(abs_url):
            p = urllib.parse.urlparse(abs_url)
            if p.scheme not in ("mailto", "tel", "javascript"):
                if abs_url not in visited:
                    queue.append(abs_url)
                tag["href"] = path_for_url(abs_url)

    # Collect and rewrite src (img, script, iframe, etc.)
    for tag in soup.find_all(src=True):
        abs_url = normalize(tag["src"], url)
        if is_internal(abs_url) and abs_url not in visited:
            queue.append(abs_url)
        if is_internal(abs_url):
            tag["src"] = urllib.parse.urlparse(abs_url).path

    # Collect and rewrite <link href> (CSS, fonts)
    for tag in soup.find_all("link", href=True):
        abs_url = normalize(tag["href"], url)
        if is_internal(abs_url):
            if abs_url not in visited:
                queue.append(abs_url)
            tag["href"] = urllib.parse.urlparse(abs_url).path

    # Handle srcset
    for tag in soup.find_all(srcset=True):
        parts = []
        for part in tag["srcset"].split(","):
            part = part.strip()
            tokens = part.split()
            if tokens:
                abs_url = normalize(tokens[0], url)
                if is_internal(abs_url):
                    if abs_url not in visited:
                        queue.append(abs_url)
                    tokens[0] = urllib.parse.urlparse(abs_url).path
            parts.append(" ".join(tokens))
        tag["srcset"] = ", ".join(parts)

    local = url_to_local(url)
    save(local, soup.encode("utf-8", formatter="minimal"))

page_count = 0

def main():
    global page_count
    OUT_DIR.mkdir(exist_ok=True)
    print(f"Mirroring {BASE_URL} → {OUT_DIR}/\n")

    while queue:
        url = queue.popleft()

        # Normalize
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            continue
        if not is_internal(url):
            continue
        if url in visited:
            continue
        visited.add(url)

        r = fetch(url)
        if r is None:
            continue

        ct = r.headers.get("Content-Type", "")

        if "text/html" in ct:
            if page_count >= MAX_PAGES:
                continue
            print(f"[page {page_count+1}] {url}")
            process_page(url, r.content)
            page_count += 1
        else:
            local = url_to_local(url)
            if not local.exists():
                print(f"  [asset] {urllib.parse.urlparse(url).path}")
                save(local, r.content)

        time.sleep(DELAY)

    print(f"\nDone. Pages: {page_count}, Total URLs processed: {len(visited)}")
    print(f"Output: {OUT_DIR.resolve()}")

if __name__ == "__main__":
    main()
