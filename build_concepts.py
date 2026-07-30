#!/usr/bin/env python3
"""Render selected MDDE concept folder-notes into concepts/<slug>.html for a site.

Usage: python build_concepts.py <site_dir> <slug1,slug2,...>
Reads folder-notes from W:/data/rules/mdde-concepts/<slug>/<slug>.md,
renders each to <site_dir>/concepts/<slug>.html + builds concepts/index.html.
Only links between concepts that are IN the selected set are kept as links;
others become plain text (self-contained site).
"""
import os, re, sys

SRC = "W:/data/rules/mdde-concepts"

def parse_note(path):
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S)
    fm, body = (m.group(1), m.group(2)) if m else ("", raw)
    def field(key):
        mm = re.search(rf"^\s*{key}:\s*(.+)$", fm, re.M)
        return mm.group(1).strip().strip('"') if mm else ""
    name = field("name")
    desc = field("description").strip('"')
    cat = field("category")
    related = re.findall(r"-\s*(concept-[a-z0-9-]+)", fm)
    return {"name": name, "desc": desc, "category": cat, "related": related, "body": body}

def slug_from_concept(cslug):  # concept-executable-metadata -> executable-metadata
    return cslug[len("concept-"):] if cslug.startswith("concept-") else cslug

def title_from_slug(slug):
    return slug.replace("-", " ").title()

def render_body(body, selected):
    """Convert [[concept-x|text]] and [[concept-x]] links; strip index backlink; md->html-ish."""
    # drop the "← Back to [[mdde-concepts-index]]" line
    body = re.sub(r"←\s*Back to\s*\[\[mdde-concepts-index\]\].*$", "", body, flags=re.S).strip()
    # drop the leading "# Title" (we render our own header) and the blockquote lede + Category line
    body = re.sub(r"^#\s+.+?\n", "", body, count=1)
    body = re.sub(r"^>\s.+?\n", "", body, count=1)
    body = re.sub(r"^\*\*Category:\*\*.+?\n", "", body, flags=re.M)
    def link(m):
        target = m.group(1); text = m.group(2) or title_from_slug(slug_from_concept(target))
        tslug = slug_from_concept(target)
        if tslug in selected:
            return f'<a href="{tslug}.html">{text}</a>'
        return text
    body = re.sub(r"\[\[(concept-[a-z0-9-]+)(?:\|([^\]]+))?\]\]", link, body)
    # drop an in-body "## Related concepts" section (we render related separately) and any trailing list
    body = re.sub(r"\n##+\s*Related concepts.*$", "", body, flags=re.S | re.I)
    # bold
    body = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", body)
    # remaining markdown headings -> h3
    out = []
    for p in [p.strip() for p in body.split("\n\n") if p.strip()]:
        h = re.match(r"^(#{2,4})\s+(.+)$", p)
        if h:
            out.append(f"<h3>{h.group(2).strip()}</h3>")
        else:
            out.append(f"<p>{p}</p>")
    return "\n".join(out)

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
    <a class="brand" href="/">{brand}</a>
    <nav class="main">
      <a href="/">Home</a>
      <a href="index.html">Concepts</a>
      <a class="cta" href="https://structurebeatsmagic.com">The method &rarr;</a>
    </nav>
  </div>
</header>
<div class="hero wrap" style="padding-bottom:20px">
  <div class="eyebrow">{category}</div>
  <h1>{title}</h1>
  <p class="sub">{desc}</p>
</div>
<section class="wrap">
{bodyhtml}
{relatedhtml}
  <p style="margin-top:34px"><a href="index.html">&larr; All concepts</a></p>
</section>
<footer><div class="wrap">
  <p><span class="badge">Test phase</span> &nbsp; Part of the <a href="https://structurebeatsmagic.com">Structure Beats Magic</a> family.</p>
</div></footer>
</body>
</html>
"""

INDEX = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<meta name="robots" content="noindex, nofollow" /><!-- TESTPHASE-NOINDEX: remove at go-live -->
<title>Concepts — {sitename}</title>
<meta name="description" content="The metadata concepts behind {sitename}: {n} named ideas, grouped by family." />
<link rel="icon" href="../assets/favicon.svg" type="image/svg+xml" />
<link rel="stylesheet" href="../assets/site.css" />
</head>
<body>
<header class="site">
  <div class="wrap">
    <a class="brand" href="/">{brand}</a>
    <nav class="main">
      <a href="/">Home</a>
      <a href="index.html">Concepts</a>
      <a class="cta" href="https://structurebeatsmagic.com">The method &rarr;</a>
    </nav>
  </div>
</header>
<div class="hero wrap" style="padding-bottom:20px">
  <div class="eyebrow">Concept library</div>
  <h1>Concepts</h1>
  <p class="sub">The named ideas behind the model &mdash; {n} metadata concepts, grouped by family. Each one is a small, self-contained idea you can point at.</p>
</div>
<section class="wrap">
{groups}
  <p style="margin-top:34px"><a href="/">&larr; Back home</a></p>
</section>
<footer><div class="wrap">
  <p><span class="badge">Test phase</span> &nbsp; Part of the <a href="https://structurebeatsmagic.com">Structure Beats Magic</a> family.</p>
</div></footer>
</body>
</html>
"""

def build(site_dir, slugs, sitename, brand):
    selected = set(slugs)
    concepts = {}
    for slug in slugs:
        path = os.path.join(SRC, slug, slug + ".md")
        if not os.path.exists(path):
            print("  MISSING:", slug); continue
        concepts[slug] = parse_note(path)
    outdir = os.path.join(site_dir, "concepts")
    os.makedirs(outdir, exist_ok=True)
    # per-concept pages
    for slug, c in concepts.items():
        title = title_from_slug(slug)
        rel = [slug_from_concept(r) for r in c["related"] if slug_from_concept(r) in selected]
        relhtml = ""
        if rel:
            items = " · ".join(f'<a href="{r}.html">{title_from_slug(r)}</a>' for r in rel)
            relhtml = f'<div class="callout" style="margin-top:30px"><p><strong>Related concepts:</strong> {items}</p></div>'
        html = PAGE.format(title=title, sitename=sitename, brand=brand,
                           desc=c["desc"].replace('"', "&quot;"), category=c["category"],
                           bodyhtml=render_body(c["body"], selected), relatedhtml=relhtml)
        with open(os.path.join(outdir, slug + ".html"), "w", encoding="utf-8") as f:
            f.write(html)
    # index grouped by family
    fams = {}
    for slug, c in concepts.items():
        fams.setdefault(c["category"] or "Other", []).append(slug)
    order = ["Umbrella thesis", "Signature principle", "Metadata OS", "SQL & generation",
             "Lineage & governance", "Business-Friendly family", "Method", "Delivery & method",
             "Temporal patterns", "Semantics", "AI & innovation", "Architecture"]
    groups_html = ""
    for fam in order + [f for f in fams if f not in order]:
        if fam not in fams: continue
        cards = ""
        for slug in sorted(fams[fam]):
            c = concepts[slug]
            cards += (f'<div class="card"><h3><a href="{slug}.html">{title_from_slug(slug)}</a></h3>'
                      f'<p>{c["desc"]}</p></div>\n')
        groups_html += f'<h2>{fam}</h2>\n<div class="cards">\n{cards}</div>\n'
    with open(os.path.join(outdir, "index.html"), "w", encoding="utf-8") as f:
        f.write(INDEX.format(sitename=sitename, brand=brand, n=len(concepts), groups=groups_html))
    print(f"  built {len(concepts)} concept pages + index in {outdir}")

if __name__ == "__main__":
    site_dir, csv = sys.argv[1], sys.argv[2]
    sitename = sys.argv[3] if len(sys.argv) > 3 else "Structured Metadata"
    brand = sys.argv[4] if len(sys.argv) > 4 else 'Structured <span class="abbr">Metadata</span>'
    build(site_dir, [s.strip() for s in csv.split(",") if s.strip()], sitename, brand)
