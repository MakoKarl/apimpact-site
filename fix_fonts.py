#!/usr/bin/env python3
"""
Download Inter font from Google Fonts, serve locally.
Replaces /_hcms/googlefonts/Inter/ references in all HTML files.
"""
import re, time, requests
from pathlib import Path

SITE    = Path("site")
FONT_DIR = SITE / "fonts" / "inter"
FONT_DIR.mkdir(parents=True, exist_ok=True)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
session = requests.Session()
session.headers["User-Agent"] = UA

# Fetch Inter CSS (woff2 format for modern browsers)
GFONTS_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Inter:ital,wght@0,400;0,500;0,600;0,700;0,800;1,400;1,600"
    "&display=swap&subset=latin"
)
css_text = session.get(GFONTS_URL).text

# Pull out all woff2 URLs
woff2_urls = re.findall(r'url\((https://fonts\.gstatic\.com/[^)]+\.woff2)\)', css_text)
# Deduplicate preserving order
seen = set()
unique_urls = []
for u in woff2_urls:
    if u not in seen:
        seen.add(u)
        unique_urls.append(u)

print(f"Found {len(unique_urls)} unique woff2 files")

# Download each and rewrite the CSS to use local paths
url_to_local = {}
for url in unique_urls:
    fname = url.split("/")[-1]
    local_path = FONT_DIR / fname
    if not local_path.exists():
        data = session.get(url).content
        local_path.write_bytes(data)
        print(f"  saved {fname}")
        time.sleep(0.1)
    url_to_local[url] = f"/fonts/inter/{fname}"

# Rewrite the Google Fonts CSS to point locally
local_css = css_text
for url, local in url_to_local.items():
    local_css = local_css.replace(f"url({url})", f"url({local})")

# Keep only /* latin */ blocks to reduce size
# Actually just keep full CSS - it's fine
(SITE / "fonts" / "inter.css").write_text(local_css)
print("Wrote /fonts/inter.css")

# Now patch all HTML files:
# 1. Replace /_hcms/googlefonts/Inter/xxx.woff2 with a Google-derived local equivalent
# 2. Add <link href="/fonts/inter.css"> in <head>

# Map HubSpot weight names → actual weights (for @font-face src replacement)
# The /_hcms/googlefonts/Inter/*.woff2 URLs 404 outside HubSpot
# We'll replace the entire broken @font-face src with nothing — the <link> tag will handle it

html_files = list(SITE.rglob("*.html"))
print(f"\nPatching {len(html_files)} HTML files...")

LINK_TAG = '<link href="/fonts/inter.css" rel="stylesheet"/>'

for f in html_files:
    text = f.read_text(encoding="utf-8", errors="replace")

    # Fix broken /_hcms/googlefonts src URLs — replace with empty string
    # so @font-face won't try a 404 URL
    text = re.sub(
        r'url\("/_hcms/googlefonts/Inter/[^"]+\.woff2"\) format\(\'woff2\'\),\s*url\("/_hcms/googlefonts/Inter/[^"]+\.woff"\) format\(\'woff\'\)',
        'url("/fonts/inter/placeholder")',  # placeholder — link tag overrides
        text
    )

    # Add Google Fonts link in <head> if not already present
    if '/fonts/inter.css' not in text and '<head' in text:
        text = text.replace('<head>', '<head>\n' + LINK_TAG, 1)
        # also handle <head with attributes
        if LINK_TAG not in text:
            text = re.sub(r'(<head[^>]*>)', r'\1\n' + LINK_TAG, text, count=1)

    f.write_text(text, encoding="utf-8")

print("Done.")
