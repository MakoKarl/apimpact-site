#!/usr/bin/env python3
"""
Re-fetch all blog post pages as full HTML (not AMP) and run asset/font/cleanup fixes on them.
"""
import re, time, requests, subprocess
from pathlib import Path
from bs4 import BeautifulSoup

SITE    = Path("site")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"}
DELAY   = 0.5

session = requests.Session()
session.headers.update(HEADERS)

BLOG_POSTS = [
    "https://www.apimpact.com/ap-impact-llc-blog/importance-of-annual-account-payable-audits",
    "https://www.apimpact.com/ap-impact-llc-blog/why-is-an-a/p-recovery-audit-considered-a-best-practice",
    "https://www.apimpact.com/ap-impact-llc-blog/the-importance-of-a-vendor-master-file-in-accounts-payable-recovery-audits",
    "https://www.apimpact.com/ap-impact-llc-blog/how-to-choose-the-right-ap-recovery-audit-partner",
    "https://www.apimpact.com/ap-impact-llc-blog/how-much-work-is-involved-in-an-a/p-audit",
    "https://www.apimpact.com/ap-impact-llc-blog/accounts-payable-recovery-audits-a-path-to-financial-recovery",
]

def url_to_local(url):
    path = url.replace("https://www.apimpact.com/", "").rstrip("/")
    return SITE / path / "index.html"

def normalize_links(soup, base_url):
    """Fix internal links to use local paths."""
    import urllib.parse
    base_domain = "https://www.apimpact.com"

    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        if href.startswith("/") or href.startswith(base_domain):
            abs_href = href if href.startswith("http") else base_domain + href
            rel = abs_href.replace(base_domain, "")
            if rel and not rel.endswith(".html"):
                path = Path(rel.lstrip("/"))
                if not path.suffix:
                    rel = rel.rstrip("/") + "/index.html"
            tag["href"] = rel

    for tag in soup.find_all(src=True):
        src = tag["src"]
        if src.startswith("/hs-fs/") or src.startswith("/hubfs/"):
            pass  # already relative
        elif src.startswith(base_domain + "/hs-fs/") or src.startswith(base_domain + "/hubfs/"):
            tag["src"] = src.replace(base_domain, "")

    return soup

LINK_TAG = '<link href="/fonts/inter.css" rel="stylesheet"/>'

for url in BLOG_POSTS:
    print(f"\nFetching: {url}")
    try:
        r = session.get(url, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"  ERROR: {e}")
        continue

    soup = BeautifulSoup(r.content, "lxml")

    # Remove HubSpot scripts and analytics
    HS_SCRIPT_SRCS = ["hs-script-loader", "scriptloader", "HubspotToolsMenu",
                      "hsforms.net", "content-cwv-embed", "cos-i18n", "keyboard-accessible-menu"]
    HS_INLINE_PATS = [r'_hsq\s*=', r'hsVars\s*=', r'HubSpotFormsV4', r'__ptq\.gif',
                      r'setContentType', r'setCanonicalUrl', r'var newIslands\s*=',
                      r'hs-form-event', r'_hcms/forms/embed']

    for tag in soup.find_all("script"):
        src = tag.get("src", "")
        content = tag.string or ""
        if any(p in src for p in HS_SCRIPT_SRCS) or any(re.search(p, content) for p in HS_INLINE_PATS):
            tag.decompose()
    for tag in soup.find_all("noscript"):
        if "hubspot" in str(tag).lower():
            tag.decompose()

    # Fix internal links
    soup = normalize_links(soup, url)

    # Add Inter font link
    html = str(soup)
    if "/fonts/inter.css" not in html:
        html = html.replace("<head>", "<head>\n" + LINK_TAG, 1)
        if LINK_TAG not in html:
            html = re.sub(r'(<head[^>]*>)', r'\1\n' + LINK_TAG, html, count=1)

    # Replace /_hcms/googlefonts src with local() fallback
    html = re.sub(
        r'src:\s*url\("/_hcms/googlefonts/[^"]+"\)[^;]*;',
        'src: local("Inter");',
        html
    )

    # Download and localize hubspotusercontent CDN assets
    import urllib.parse, hashlib
    def localize(url_match):
        asset_url = url_match.group(1).rstrip("\\")
        p = urllib.parse.urlparse(asset_url)
        host_slug = p.netloc.replace(".", "_")
        path = p.path.lstrip("/")
        if p.query:
            qs_hash = hashlib.md5(p.query.encode()).hexdigest()[:6]
            stem = Path(path).stem + "_" + qs_hash
            path = str(Path(path).parent / (stem + (Path(path).suffix or "")))
        local = SITE / "ext" / host_slug / path
        if not local.exists():
            try:
                resp = session.get(asset_url, timeout=15)
                resp.raise_for_status()
                local.parent.mkdir(parents=True, exist_ok=True)
                local.write_bytes(resp.content)
                print(f"  saved {p.path}")
                time.sleep(0.1)
            except:
                return asset_url
        return "/" + str(local.relative_to(SITE))

    import re as _re
    for pat in [
        r'(https://[a-zA-Z0-9.-]+\.hubspotusercontent-na[12]\.net/[^\s"\')\]>]+)',
        r'(https://(?:www\.)?apimpact\.com/hub(?:fs|[^/]*)/[^\s"\')\]>]*)',
    ]:
        html = _re.sub(pat, localize, html)

    local_path = url_to_local(url)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(html, encoding="utf-8")
    print(f"  saved to {local_path}")
    time.sleep(DELAY)

print("\nAll blog posts re-fetched.")
