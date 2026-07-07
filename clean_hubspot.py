#!/usr/bin/env python3
"""
Remove all HubSpot-specific scripts, analytics, tracking, and broken font refs from HTML files.
Keep: content, images, CSS theme (already downloaded locally), fonts (now local).
"""
import re
from pathlib import Path
from bs4 import BeautifulSoup

SITE = Path("site")

# Script src patterns to completely remove
REMOVE_SCRIPT_SRCS = [
    "hs-script-loader",           # HubSpot analytics loader
    "scriptloader",               # HubSpot script loader
    "HubspotToolsMenu",           # HubSpot toolbar
    "hsforms.net",                # HubSpot forms embed JS
    "content-cwv-embed",          # HubSpot Core Web Vitals
    "cos-i18n",                   # HubSpot i18n
    "keyboard-accessible-menu",   # HubSpot menu flyouts
]

# Inline script content patterns to remove entire <script> block
REMOVE_SCRIPT_PATTERNS = [
    r'_hsq\s*=',                  # HubSpot analytics queue
    r'hsVars\s*=',                # HubSpot vars config
    r'hsVars\[',                  # HubSpot vars assignment
    r'HubSpotFormsV4',            # HubSpot forms v4
    r'hs-form-event',             # HubSpot form events
    r'_hcms/forms/embed',         # HubSpot form loader
    r'__ptq\.gif',                # HubSpot tracking pixel
    r'setContentType.*standard',  # HubSpot analytics push
    r'setCanonicalUrl',           # HubSpot analytics push
    r'setPageId',                 # HubSpot analytics push
    r'hs_form_target',            # HubSpot form target init
    r'var newIslands\s*=',        # HubSpot Islands (React hydration)
]

# <noscript> / <img> tracking pixel patterns
REMOVE_NOSCRIPT_PATTERNS = [
    r'track-na\d+\.hubspot\.com',
    r'__ptq\.gif',
]

def should_remove_script(tag) -> bool:
    src = tag.get("src", "")
    if any(p in src for p in REMOVE_SCRIPT_SRCS):
        return True
    content = tag.string or ""
    if any(re.search(p, content) for p in REMOVE_SCRIPT_PATTERNS):
        return True
    return False

def process_file(path: Path):
    html = path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "lxml")

    removed = 0

    # Remove <script> tags
    for tag in soup.find_all("script"):
        if should_remove_script(tag):
            tag.decompose()
            removed += 1

    # Remove HubSpot tracking <noscript> blocks
    for tag in soup.find_all("noscript"):
        content = str(tag)
        if any(re.search(p, content) for p in REMOVE_NOSCRIPT_PATTERNS):
            tag.decompose()
            removed += 1

    # Remove HubSpot <link> tags that are broken (hs-script-loader type)
    for tag in soup.find_all("link"):
        href = tag.get("href", "")
        if "hubspot.com" in href and "fonts.googleapis" not in href:
            tag.decompose()
            removed += 1

    # Fix remaining /_hcms/googlefonts/Inter/ woff references in <style> tags
    for style in soup.find_all("style"):
        if style.string and "/_hcms/googlefonts/Inter/" in style.string:
            # Replace all /_hcms/googlefonts/Inter/XXX.woffX src() with empty placeholder
            cleaned = re.sub(
                r'src:\s*url\("/_hcms/googlefonts/Inter/[^"]+"\) format\([^)]+\)(?:,\s*url\("[^"]+"\) format\([^)]+\))*;',
                'src: local("Inter");',
                style.string
            )
            style.string.replace_with(cleaned)
            removed += 1

    if removed:
        path.write_text(str(soup), encoding="utf-8")
        print(f"  [{removed} removed] {path}")

def main():
    files = list(SITE.rglob("*.html"))
    print(f"Cleaning {len(files)} HTML files...\n")
    for f in files:
        process_file(f)
    print("\nDone.")

if __name__ == "__main__":
    main()
