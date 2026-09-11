#!/usr/bin/env python3
"""
Build the site: Markdown in `content/` -> HTML pages at the repo root.

This replaced Hugo. It is deliberately small and readable -- roughly: parse TOML
front matter, expand two shortcodes, render Markdown, drop the result into one
of two page templates. There is no theme, no template language, and no plugin
system. If you want to change how a page looks, edit the templates below or the
CSS; nothing else is involved.

The generated HTML is committed, so deployment stays a dumb file copy and a bug
in this script can never take the live site down.

Usage:
    python3 build.py          # build
    python3 build.py --check  # build to a temp dir and report diffs, write nothing

Requires markdown-it-py (already present on this machine's WSL python3):
    pip install markdown-it-py
"""

from __future__ import annotations

import argparse
import html
import re
import shutil
import sys
import tempfile
import tomllib
from datetime import date, datetime
from pathlib import Path

try:
    from markdown_it import MarkdownIt
except ImportError:
    sys.exit(
        "markdown-it-py is required.\n"
        "  WSL/Linux : pip install markdown-it-py\n"
        "  Windows   : python -m pip install markdown-it-py"
    )

ROOT = Path(__file__).parent.resolve()
CONTENT = ROOT / "content"

SITE_TITLE = "BaiShiXi's Blog"
BASE_URL = "https://baishixi.blog"

# Nav lives here and only here -- every generated page gets the same block, so
# adding an entry is a one-line change rather than an edit to every HTML file.
# The home page IS the bio page, so there is no separate /about/ entry.
NAV = [
    ("/", "Home"),
    ("/posts/", "Posts"),
    ("/projects/", "Projects"),
]


# --------------------------------------------------------------------------- md

def markdown_renderer() -> MarkdownIt:
    # "gfm-like" gives tables + strikethrough; html=True lets the raw <sub>,
    # <div> and <a> tags already present in the report pass through.
    #
    # linkify is switched off on purpose: it needs the extra linkify-it-py
    # package, and every link in the content is already an explicit Markdown
    # link, so autolinking would add a dependency for no gain.
    md = MarkdownIt("gfm-like", {"html": True, "linkify": False, "typographer": True})
    md.disable("linkify")
    return md


MD = markdown_renderer()


def render_md(text: str) -> str:
    return MD.render(text)


def render_inline(text: str) -> str:
    """For captions, which are markdown fragments that must not become <p>."""
    return MD.renderInline(text)


# -------------------------------------------------------------------- shortcodes

SHORTCODE_RE = re.compile(r"\{\{<\s*(report-figure|rollout-video)\s+(.*?)>\}\}", re.S)
ATTR_RE = re.compile(r'(\w[\w-]*)\s*=\s*"(.*?)"', re.S)


def expand_shortcodes(text: str) -> str:
    """Replace the two Hugo shortcodes with the HTML they used to produce."""

    def one(m: re.Match) -> str:
        name, raw = m.group(1), m.group(2)
        a = {k: v.strip() for k, v in ATTR_RE.findall(raw)}
        caption = a.get("caption", "")
        figcaption = (
            f"\n  <figcaption>{render_inline(caption)}</figcaption>" if caption else ""
        )

        if name == "report-figure":
            cls = (" " + a["class"]) if a.get("class") else ""
            return (
                f'<figure class="report-figure{cls}">\n'
                f'  <img src="{html.escape(a.get("src", ""))}" '
                f'alt="{html.escape(a.get("alt", ""))}" loading="lazy" />'
                f"{figcaption}\n</figure>"
            )

        # rollout-video
        src = a.get("src", "")
        title = html.escape(a.get("title", ""))
        exists = (ROOT / src.lstrip("/")).is_file()
        if exists:
            media = (
                f'  <video controls preload="metadata" aria-label="{title}">\n'
                f'    <source src="{html.escape(src)}" type="video/mp4" />\n'
                f"    Your browser does not support embedded video.\n"
                f"  </video>"
            )
        else:
            # mirrors the old shortcode's placeholder branch
            media = (
                f'  <div class="video-placeholder" role="img" '
                f'aria-label="Video placeholder: {title}">\n'
                f"    <strong>{title}</strong>\n"
                f"    <span>Rollout video coming soon</span>\n"
                f"    <code>{html.escape(src)}</code>\n  </div>"
            )
        return f'<figure class="rollout-media">\n{media}{figcaption}\n</figure>'

    return SHORTCODE_RE.sub(one, text)


# --------------------------------------------------------------------- headings

def slugify(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text).lower()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_]+", "-", text).strip("-")


def add_heading_ids(body: str) -> tuple[str, list[tuple[int, str, str]]]:
    """Give h2/h3 stable ids and collect them for the table of contents."""
    toc: list[tuple[int, str, str]] = []
    seen: dict[str, int] = {}

    def one(m: re.Match) -> str:
        level, attrs, inner = int(m.group(1)), m.group(2), m.group(3)
        slug = slugify(inner) or "section"
        if slug in seen:
            seen[slug] += 1
            slug = f"{slug}-{seen[slug]}"
        else:
            seen[slug] = 0
        toc.append((level, slug, inner))
        return f'<h{level} id="{slug}"{attrs}>{inner}</h{level}>'

    body = re.sub(r"<h([23])([^>]*)>(.*?)</h\1>", one, body, flags=re.S)
    return body, toc


def render_toc(toc: list[tuple[int, str, str]]) -> str:
    """Nested <ul> matching Hugo's .TableOfContents structure."""
    if not toc:
        return ""
    out = ['<nav id="TableOfContents">', "<ul>"]
    prev = toc[0][0]
    for i, (level, slug, label) in enumerate(toc):
        text = re.sub(r"<[^>]+>", "", label)
        if i == 0:
            pass
        elif level > prev:
            out.append("<ul>")          # open a child list; parent <li> stays open
        elif level == prev:
            out.append("</li>")         # close the sibling
        else:
            out.append("</li>")         # close the sibling, then unwind
            out.extend(["</ul></li>"] * (prev - level))
        out.append(f'<li><a href="#{slug}">{text}</a>')
        prev = level
    out.append("</li>")
    out.extend(["</ul></li>"] * (prev - toc[0][0]))
    out.append("</ul>")
    out.append("</nav>")
    return "\n".join(out)


# -------------------------------------------------------------------- templates

# The report keeps the vendored theme CSS: report.css defines its own tokens but
# still relies on Simple.css's body grid for layout -- dropping it collapses the
# report into an unreadable narrow column (verified). Every other page uses
# pages.css only, so none of the old theme styling reaches them.
CSS_REPORT = ["/css/site.css", "/css/report.css"]
CSS_PAGES = ["/css/pages.css"]


def head(title: str, description: str, url: str, css_files: list[str]) -> str:
    css = "\n".join(f'    <link href="{c}" rel="stylesheet" />' for c in css_files)
    desc = html.escape(description)
    t = html.escape(title)
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{t}&nbsp;|&nbsp;{html.escape(SITE_TITLE)}</title>
    <meta name="description" content="{desc}" />
    <link rel="canonical" href="{BASE_URL}{url}" />
    <meta property="og:url" content="{BASE_URL}{url}" />
    <meta property="og:site_name" content="{html.escape(SITE_TITLE)}" />
    <meta property="og:title" content="{t}" />
    <meta property="og:description" content="{desc}" />
    <meta name="twitter:card" content="summary" />
    <meta name="twitter:title" content="{t}" />
    <meta name="twitter:description" content="{desc}" />
    <meta name="referrer" content="no-referrer-when-downgrade" />
{css}
  </head>
  <body>"""


def nav_html(current: str) -> str:
    links = []
    for href, label in NAV:
        cls = ' class="current"' if href == current else ""
        links.append(f'<a href="{href}"{cls}>{label}</a>')
    return "\n        ".join(links)


def chrome_open(heading: str, current: str, subtitle: str = "") -> str:
    sub = f"\n      <p>{html.escape(subtitle)}</p>" if subtitle else ""
    return f"""
    <header>
      <nav>
        {nav_html(current)}
      </nav>
      <h1>{html.escape(heading)}</h1>{sub}
    </header>
    <main>"""


# The year is computed at build time, so the footer stops being wrong every
# January. Note the side effect: on 1 Jan, `build.py --check` will report every
# page out of date until you rebuild and commit.
CHROME_CLOSE = f"""    </main>
    <footer>
      <span>&copy; {datetime.now().year} Shengzhe Zhang</span>
    </footer>
  </body>
</html>
"""


def report_body(page: dict, body: str, toc_html: str) -> str:
    # `course` is optional: without it the kicker must not render a leading space.
    course = page.get("course", "").strip()
    kicker = html.escape(f"{course} Final Report" if course else "Final Report")

    # "A", "A and B", "A, B and C" -- a plain " and ".join breaks past two authors.
    names = page.get("authors", [])
    if len(names) > 2:
        authors = ", ".join(names[:-1]) + " and " + names[-1]
    else:
        authors = " and ".join(names)
    date = page["date"]
    return f"""
      <div class="report-meta">
        <p class="report-kicker">{kicker}</p>
        <p class="report-byline">
          <span>{html.escape(authors)}</span>
          <span aria-hidden="true">/</span>
          <time datetime="{date:%Y-%m-%d}">{date:%B %Y}</time>
        </p>
      </div>

      <div class="report-layout">
        <aside class="report-toc" aria-label="Table of contents">
          <p class="toc-label">On this page</p>
          {toc_html}
        </aside>

        <article class="report-article">
{body}
        </article>
      </div>
"""


# ------------------------------------------------------------------------ pages

def parse(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    m = re.match(r"\+\+\+\n(.*?)\n\+\+\+\n?(.*)", raw, re.S)
    if not m:
        raise SystemExit(f"{path}: missing +++ TOML front matter")
    meta = tomllib.loads(m.group(1))
    meta["_body"] = m.group(2)
    meta["_slug"] = path.stem
    # Normalise dates to a naive datetime. TOML yields a `date` for `2025-12-12`
    # but a tz-aware `datetime` for `2026-06-07T13:16:01-07:00`, and those three
    # types cannot be sorted against each other. Only Y-M-D is ever rendered, so
    # dropping the time zone loses nothing.
    d = meta.get("date")
    if isinstance(d, str):
        d = datetime.fromisoformat(d)
    if isinstance(d, datetime):
        d = d.replace(tzinfo=None)
    elif isinstance(d, date):
        d = datetime(d.year, d.month, d.day)
    meta["date"] = d
    return meta


def build(out: Path) -> list[Path]:
    written: list[Path] = []

    def write(rel: str, text: str) -> None:
        p = out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        written.append(p)

    # --- posts -------------------------------------------------------------
    posts = [parse(p) for p in sorted((CONTENT / "posts").glob("*.md"))]
    posts = [p for p in posts if not p.get("draft")]
    posts.sort(key=lambda p: p["date"], reverse=True)

    for post in posts:
        body = render_md(expand_shortcodes(post["_body"]))
        body, toc = add_heading_ids(body)
        toc_html = render_toc(toc)
        url = f"/posts/{post['_slug']}/"

        if post.get("report"):
            # Reports keep their own design untouched. They live at their own URL
            # only -- the home page is the bio, never the report.
            page = (
                head(post["title"], post.get("description", ""), url, CSS_REPORT)
                + chrome_open(post["title"], "/posts/", post.get("description", ""))
                + report_body(post, body, toc_html)
                + CHROME_CLOSE
            )
        else:
            page = (
                head(post["title"], post.get("description", ""), url, CSS_PAGES)
                + chrome_open(post["title"], "/posts/", post.get("description", ""))
                + f'      <article class="prose">\n{body}\n      </article>\n'
                + CHROME_CLOSE
            )
        write(f"posts/{post['_slug']}/index.html", page)

    # --- home page = the bio (content/_index.md) ----------------------------
    bio = parse(CONTENT / "_index.md")
    bio_body, _ = add_heading_ids(render_md(expand_shortcodes(bio["_body"])))
    write(
        "index.html",
        head(bio["title"], bio.get("description", ""), "/", CSS_PAGES)
        + chrome_open(bio["title"], "/", bio.get("subtitle", ""))
        + f'      <article class="prose">\n{bio_body}\n      </article>\n'
        + CHROME_CLOSE,
    )

    # --- post index --------------------------------------------------------
    rows = "\n".join(
        f'          <li><span><i><time datetime="{p["date"]:%Y-%m-%d}">'
        f'{p["date"]:%Y-%m-%d}</time></i></span>'
        f'<a href="/posts/{p["_slug"]}/">{html.escape(p["title"])}</a></li>'
        for p in posts
    ) or "          <li>No posts yet.</li>"
    write(
        "posts/index.html",
        head("Posts", "Writing on robotics and machine learning.", "/posts/", CSS_PAGES)
        + chrome_open("Posts", "/posts/")
        + f'      <ul class="blog-posts">\n{rows}\n      </ul>\n'
        + CHROME_CLOSE,
    )

    # --- standalone pages --------------------------------------------------
    for path in sorted(CONTENT.glob("*.md")):
        if path.stem == "_index":
            continue
        pg = parse(path)
        body = render_md(expand_shortcodes(pg["_body"]))
        body, _ = add_heading_ids(body)
        url = f"/{pg['_slug']}/"
        write(
            f"{pg['_slug']}/index.html",
            head(pg["title"], pg.get("description", ""), url, CSS_PAGES)
            + chrome_open(pg["title"], url, pg.get("subtitle", ""))
            + f'      <article class="prose">\n{body}\n      </article>\n'
            + CHROME_CLOSE,
        )

    # --- 404 ---------------------------------------------------------------
    write(
        "404.html",
        head("404", "Page not found", "/404.html", CSS_PAGES)
        + chrome_open("404 — not found", "")
        + '      <p>That page does not exist. Try the <a href="/">home page</a> '
        'or <a href="/posts/">all posts</a>.</p>\n'
        + CHROME_CLOSE,
    )

    # --- sitemap -----------------------------------------------------------
    urls = ["/", "/posts/"] + [f"/posts/{p['_slug']}/" for p in posts]
    urls += [f"/{p.stem}/" for p in sorted(CONTENT.glob("*.md")) if p.stem != "_index"]
    entries = "\n".join(f"  <url><loc>{BASE_URL}{u}</loc></url>" for u in urls)
    write(
        "sitemap.xml",
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{entries}\n</urlset>\n",
    )

    return written


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="build to a temp dir and report what would change")
    args = ap.parse_args()

    if args.check:
        tmp = Path(tempfile.mkdtemp())
        try:
            written = build(tmp)
            changed = []
            for p in written:
                rel = p.relative_to(tmp)
                live = ROOT / rel
                if not live.exists() or live.read_text(encoding="utf-8") != p.read_text(
                    encoding="utf-8"
                ):
                    changed.append(str(rel))
            print(f"{len(written)} pages built")
            print("out of date:" if changed else "everything up to date")
            for c in changed:
                print("  " + c)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        return

    written = build(ROOT)
    print(f"built {len(written)} files:")
    for p in written:
        print("  " + str(p.relative_to(ROOT)).replace("\\", "/"))


if __name__ == "__main__":
    main()
