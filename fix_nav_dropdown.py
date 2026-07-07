#!/usr/bin/env python3
"""
Inject dropdown nav fix into all site HTML files.
Replaces the HubSpot keyboard-accessible-menu JS that was removed.
"""
from pathlib import Path

SITE = Path("site")

NAV_CSS = """<style id="nav-dropdown-fix">
.hs-elevate-menu--desktop .hs-elevate-menu--has-children{position:relative}
.hs-elevate-menu--desktop .hs-elevate-menu__submenu{
  position:absolute;top:calc(100% + 4px);left:0;
  background:#fff;box-shadow:0 4px 16px rgba(0,0,0,.12);
  border-radius:8px;padding:8px 0;z-index:9999;min-width:180px
}
.hs-elevate-menu--desktop .hs-elevate-menu__submenu li{list-style:none;padding:0;margin:0}
.hs-elevate-menu--desktop .hs-elevate-menu__submenu a{
  display:block;padding:10px 20px;color:#09152b;
  text-decoration:none;font-size:14px;white-space:nowrap
}
.hs-elevate-menu--desktop .hs-elevate-menu__submenu a:hover{background:#f7f9fc;color:#e8792a}
</style>"""

NAV_JS = """<script id="nav-dropdown-js">
(function(){
  // Desktop: show submenu on hover
  document.querySelectorAll('.hs-elevate-menu--desktop .hs-elevate-menu--has-children').forEach(function(li){
    var sub=li.querySelector('ul.hs-elevate-menu__submenu');
    if(!sub)return;
    li.addEventListener('mouseenter',function(){sub.style.display='block';});
    li.addEventListener('mouseleave',function(){sub.style.display='none';});
  });
  // Mobile: toggle submenu on span click
  document.querySelectorAll('.hs-elevate-menu--mobile .hs-elevate-menu--has-children').forEach(function(li){
    var sub=li.querySelector('ul');
    var trigger=li.querySelector('.hs-elevate-menu__menu-item-link-container');
    if(!sub||!trigger)return;
    sub.style.display='none';
    trigger.style.cursor='pointer';
    trigger.addEventListener('click',function(){
      sub.style.display=(sub.style.display==='none')?'block':'none';
    });
  });
  // Mobile hamburger toggle
  var ham=document.querySelector('.hs-elevate-site-header__hamburger-menu');
  var menuWrap=document.querySelector('.hs-elevate-site-header__menu-container');
  if(ham&&menuWrap){
    ham.style.cursor='pointer';
    ham.addEventListener('click',function(){
      var hidden=menuWrap.style.display==='none'||menuWrap.classList.contains('_hs-elevate-site-header__menu-container--is-hidden_1ke6g_109');
      if(hidden){
        menuWrap.style.display='block';
        menuWrap.classList.remove('_hs-elevate-site-header__menu-container--is-hidden_1ke6g_109');
      }else{
        menuWrap.style.display='none';
      }
    });
  }
})();
</script>"""


def process(path):
    html = path.read_text(encoding="utf-8", errors="replace")
    changed = False

    if "nav-dropdown-fix" not in html:
        html = html.replace("</head>", NAV_CSS + "\n</head>", 1)
        changed = True

    if "nav-dropdown-js" not in html:
        html = html.replace("</body>", NAV_JS + "\n</body>", 1)
        changed = True

    if changed:
        path.write_text(html, encoding="utf-8")
        print(f"  patched: {path}")


files = list(SITE.rglob("*.html"))
print(f"Processing {len(files)} files...")
for f in files:
    process(f)
print("Done.")
