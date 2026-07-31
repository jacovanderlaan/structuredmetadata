#!/usr/bin/env python3
"""Render W:/data/rules/mdde-metadata-areas/<slug>/<slug>.md into <site>/areas/<slug>.html.
Each area page: rich body + linked concepts + a live demo query (deep-links into
browser.html?q=<base64 sql>). Source of truth = W:. Hero optional (assets/<slug>-hero.png).

Usage: python build_areas.py <site_dir> <slug1,slug2,...> "<Sitename>" '<brand>'
"""
import os, re, sys, shutil, base64, html

SRC = "W:/data/rules/mdde-metadata-areas"
CONCEPT_TITLES = {}  # slug -> Title (built from concept folders for linking)

def load_concept_titles():
    croot = "W:/data/rules/mdde-concepts"
    for d in os.listdir(croot):
        p = os.path.join(croot, d, d + ".md")
        if os.path.isfile(p):
            CONCEPT_TITLES[d] = d.replace("-", " ").title()

def parse(path):
    raw = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S)
    fm, body = (m.group(1), m.group(2)) if m else ("", raw)
    def f(key, block=False):
        if block:
            mm = re.search(rf"^{key}:\s*\|\s*\n((?:  .*\n?)+)", fm, re.M)
            return re.sub(r"^  ", "", mm.group(1), flags=re.M).strip() if mm else ""
        mm = re.search(rf"^{key}:\s*(.+)$", fm, re.M)
        return mm.group(1).strip().strip('"') if mm else ""
    concepts = re.findall(r"-\s*([a-z0-9-]+)", (re.search(r"concepts:\s*\n((?:\s*-\s*.+\n?)+)", fm) or type("",(),{"group":lambda s,n:""})()).group(1) if re.search(r"concepts:", fm) else "")
    return {"title": f("title"), "desc": f("description"), "concepts": concepts,
            "demo_title": f("demo_title"), "demo": f("demo", True), "demo_sql": f("demo_sql", True),
            "body": body, "hero": f("hero_image")}

def render_body(body):
    body = re.sub(r"←\s*Back to\s*\[\[mdde-metadata-areas-index\]\].*$", "", body, flags=re.S).strip()
    body = re.sub(r"^#\s+.+?\n", "", body, count=1)
    body = re.sub(r"^>\s.+?\n", "", body, count=1)
    body = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", body)
    paras = [p.strip() for p in body.split("\n\n") if p.strip()]
    return "\n".join(f"<p>{p}</p>" for p in paras)

def b64(s): return base64.b64encode(s.encode()).decode()

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<meta name="robots" content="noindex, nofollow" /><!-- TESTPHASE-NOINDEX: remove at go-live -->
<title>{title} — {sitename}</title>
<meta name="description" content="{desc}" />
<link rel="icon" href="../assets/favicon.svg" type="image/svg+xml" />
<link rel="stylesheet" href="../assets/site.css" />
</head>
<body>
<header class="site">
  <div class="wrap">
    <a class="brand" href="../index.html">{brand}</a>
    <nav class="main">
      <a href="../index.html">Home</a>
      <a href="../index.html#demo">The demo</a>
      <a href="../browser.html">Browser</a>
      <a href="../concepts/index.html">Concepts</a>
      <a class="cta" href="https://structurebeatsmagic.com">The method &rarr;</a>
    </nav>
  </div>
</header>
<div class="hero wrap" style="padding-bottom:20px">
  <div class="eyebrow">Metadata area</div>
  <h1>{title}</h1>
  <p class="sub">{desc}</p>
</div>
<section class="wrap">
{herohtml}
{bodyhtml}
{demohtml}
{relhtml}
  <p style="margin-top:34px"><a href="../index.html#demo">&larr; All areas</a></p>
</section>
<footer><div class="wrap">
  <p><span class="badge">Test phase</span> &nbsp; Part of the <a href="https://structurebeatsmagic.com">Structure Beats Magic</a> family.</p>
</div></footer>
</body>
</html>
"""

def build(site_dir, slugs, sitename, brand):
    load_concept_titles()
    outdir = os.path.join(site_dir, "areas")
    assetdir = os.path.join(outdir, "assets")
    os.makedirs(assetdir, exist_ok=True)
    for slug in slugs:
        p = os.path.join(SRC, slug, slug + ".md")
        if not os.path.isfile(p):
            print("  MISSING:", slug); continue
        a = parse(p)
        # hero
        herohtml = ""
        if a["hero"]:
            src = os.path.join(SRC, slug, "assets", a["hero"])
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(assetdir, a["hero"]))
                herohtml = f'<figure class="c-hero"><img src="assets/{a["hero"]}" alt="{html.escape(a["title"])}" loading="eager" /></figure>'
        # demo query (deep-link into the browser, query preloaded)
        demohtml = ""
        if a["demo_sql"]:
            link = f'../browser.html?q={b64(a["demo_sql"])}'
            demohtml = (f'<div class="callout" style="margin-top:26px"><p><strong>{html.escape(a["demo_title"] or "Try it")}:</strong> '
                        f'{html.escape(a["demo"])}</p>'
                        f'<pre style="overflow-x:auto;background:var(--code);border-radius:8px;padding:12px 14px;font-size:.85rem;margin:.6rem 0 0"><code>{html.escape(a["demo_sql"])}</code></pre>'
                        f'<p style="margin:.7rem 0 0"><a class="btn" href="{link}">Run this in the live browser &rarr;</a></p></div>')
        # related concepts
        relhtml = ""
        cs = [c for c in a["concepts"] if c in CONCEPT_TITLES]
        if cs:
            items = "".join(f'<li><a href="../concepts/{c}.html">{CONCEPT_TITLES[c]}</a></li>' for c in cs)
            relhtml = f'<div class="c-rel"><h3>Related concepts</h3><ul>{items}</ul></div>'
        htmlout = PAGE.format(title=html.escape(a["title"]), sitename=sitename, brand=brand,
                              desc=html.escape(a["desc"]), herohtml=herohtml,
                              bodyhtml=render_body(a["body"]), demohtml=demohtml, relhtml=relhtml)
        with open(os.path.join(outdir, slug + ".html"), "w", encoding="utf-8") as f:
            f.write(htmlout)
    print(f"  built {len(slugs)} area pages in {outdir}")

if __name__ == "__main__":
    build(sys.argv[1], [s.strip() for s in sys.argv[2].split(",") if s.strip()],
          sys.argv[3] if len(sys.argv) > 3 else "Structured Metadata",
          sys.argv[4] if len(sys.argv) > 4 else 'Structured <span class="abbr">Metadata</span>')
