#!/usr/bin/env python3
"""
Clean up blog post formatting:
- Standardize h5/h6/h4 section headers to h2
- Remove <br/> tags (use paragraph breaks instead)
- Remove empty paragraphs
- Strip transparent background-color spans
- Convert bold-span fake headings to h2
- Add blog-body CSS and class
"""
import re
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString, Tag

BLOG_DIR = Path("site/ap-impact-llc-blog")

BLOG_CSS = """<style>
.blog-body h2{font-size:1.2rem;font-weight:700;color:#002d62;margin-top:2rem;margin-bottom:.5rem;line-height:1.3}
.blog-body p{margin-bottom:1rem;line-height:1.7;color:#2d3748}
.blog-body ul,.blog-body ol{margin:0 0 1rem 1.5rem}
.blog-body li{margin-bottom:.4rem;line-height:1.6;color:#2d3748}
.blog-body strong{color:#002d62}
</style>"""

POSTS = [
    "importance-of-annual-account-payable-audits",
    "why-is-an-a/p-recovery-audit-considered-a-best-practice",
    "the-importance-of-a-vendor-master-file-in-accounts-payable-recovery-audits",
    "how-to-choose-the-right-ap-recovery-audit-partner",
    "how-much-work-is-involved-in-an-a/p-audit",
    "accounts-payable-recovery-audits-a-path-to-financial-recovery",
]


def clean_span_content(span):
    """Reformat the content of the post body span."""

    # 1. Upgrade h4/h5/h6 to h2
    for tag in span.find_all(["h4", "h5", "h6"]):
        tag.name = "h2"

    # 2. Convert bold-span headings to h2
    #    Pattern: <p><span style="font-weight: bold;">TEXT</span></p>
    for p in list(span.find_all("p")):
        children = [c for c in p.children if not (isinstance(c, NavigableString) and not c.strip())]
        if len(children) == 1 and isinstance(children[0], Tag) and children[0].name == "span":
            child = children[0]
            style = child.get("style", "")
            if "font-weight" in style and ("bold" in style or "700" in style):
                text = child.get_text(strip=True)
                if text:
                    new_tag = span.find_parent("html").new_tag("h2")
                    new_tag.string = text
                    p.replace_with(new_tag)

    # 3. Remove <br> tags — replace with nothing (paragraph breaks exist already)
    for br in span.find_all("br"):
        br.decompose()

    # 4. Unwrap transparent background-color spans
    for s in span.find_all("span"):
        style = s.get("style", "")
        if "background-color: transparent" in style or "background-color:transparent" in style:
            s.unwrap()

    # 5. Remove empty <p> tags
    for p in list(span.find_all("p")):
        if not p.get_text(strip=True):
            p.decompose()

    # 6. Strip <!--more--> comment nodes
    for child in list(span.children):
        if isinstance(child, NavigableString) and child.strip() == "":
            continue

    # Remove HTML comments like <!--more-->
    from bs4 import Comment
    for comment in span.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()

    return span


def process_file(post_slug):
    path = BLOG_DIR / post_slug / "index.html"
    if not path.exists():
        print(f"  MISSING: {path}")
        return

    html = path.read_text(encoding="utf-8", errors="replace")

    # Add blog-body CSS before </head> if not already there
    if "blog-body" not in html:
        html = html.replace("</head>", BLOG_CSS + "\n</head>", 1)

    soup = BeautifulSoup(html, "lxml")

    # Find the post body span
    span = soup.find("span", id="hs_cos_wrapper_post_body")
    if not span:
        print(f"  No post body span found in {path}")
        return

    # Add blog-body class
    existing_classes = span.get("class", [])
    if "blog-body" not in existing_classes:
        existing_classes.append("blog-body")
        span["class"] = existing_classes

    # Clean content
    clean_span_content(span)

    path.write_text(str(soup), encoding="utf-8")
    print(f"  Formatted: {path}")


def main():
    for slug in POSTS:
        process_file(slug)
    print("\nDone.")


if __name__ == "__main__":
    main()
