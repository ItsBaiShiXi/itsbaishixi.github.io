# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

The site at `https://baishixi.blog/` — primarily a CS295 final report,
*"How Much Policy Does a VLA Need?"*, co-authored by Shengzhe Zhang with **Eric and Sean**,
plus a few personal pages.

**This is other people's work as well as the owner's.** Treat the report's content and visual
design as things to preserve unless explicitly asked to change them.

It used to be a Hugo site on the `hugo-simple` theme. Hugo was removed deliberately — do not
reintroduce a static site generator, a bundler, or npm.

## Architecture

Markdown in `content/` → static HTML at the repo root, via one script.

```
content/posts/*.md   -> posts/<slug>/index.html   (+ index.html if report = true)
content/*.md         -> <slug>/index.html
```

**[build.py](build.py) is the whole generator** (~330 lines, stdlib + `markdown-it-py`). It
parses TOML front matter, expands two shortcodes, renders Markdown, and fills one of two page
templates. There is no theme and no template language — to change how pages look, edit the
template functions in that file or the CSS.

**Generated HTML is committed.** That is deliberate: deployment stays a plain file copy, so a
bug in `build.py` can never take the live site down.
[.github/workflows/pages.yml](.github/workflows/pages.yml) runs no build — it rsyncs the repo
(minus `content/`, `build.py`, and docs) to Pages.

## Commands

```bash
# Rebuild after editing anything in content/  (WSL python3 already has markdown-it-py)
python3 build.py

# See what would change without writing
python3 build.py --check

# Preview. WSL: python3. Windows PowerShell: python (python3 is a Store stub there).
python3 -m http.server 8000
```

Run from the repo root — all asset paths are absolute (`/css/site.css`, `/videos/*.mp4`).

## Things that will bite you

- **The home page is the bio**, rendered from `content/_index.md`. It is deliberately *not* the
  report — an earlier Hugo layout made `/` render the full report, and that was removed. There is
  no separate `/about/`; the home page is the about page, so the nav has no About entry.
- **Two stylesheets, two audiences.** The owner's pages (home, posts index, projects, now, 404)
  load `css/pages.css` **only** — that is the site's real design and none of the old theme
  styling reaches them. The report loads `css/site.css` + `css/report.css`.
- **`css/report.css` cannot stand alone.** It defines its own tokens but still relies on
  Simple.css's body grid; dropping `site.css` from the report collapses it into a squeezed column
  with content running off-screen (tested). That is the only page where the vendored theme CSS
  belongs. The split is `CSS_REPORT` / `CSS_PAGES` in [build.py](build.py).
- **The report is co-authored with Eric and Sean** — preserve its design unless asked directly.
  See [.claude/skills/site-conventions/SKILL.md](.claude/skills/site-conventions/SKILL.md).
- **Two shortcodes survive from Hugo** and are expanded by `build.py`: `{{< report-figure >}}`
  and `{{< rollout-video >}}`. The video one checks whether the file exists and falls back to a
  placeholder card, mirroring the original template.
- **The report embeds raw HTML in the Markdown** — 21 `<sub>` tags plus some `<a>`/`<div>`/`<ol>`.
  The renderer runs with `html=True` for this reason; do not turn that off.
- **`linkify` is disabled** because it needs an extra package and every link is already explicit.
- **13 of the 16 files in `videos/` are unreferenced.** Only three 410M clips are embedded. The
  other 13 are ~50 MB of dead weight; leave them unless the owner says to prune.
- After editing `content/`, **rebuild and commit the generated HTML too**, or the live site keeps
  serving the previous version. `build.py --check` tells you if you forgot.

## Verifying a change

There are no tests. The meaningful check is to serve the site and compare against what is live:

1. `python3 build.py && python3 -m http.server 8000`
2. Confirm `/` (the bio), `/posts/vla-policy-size/` (the report), `/posts/`, `/projects/`, `/now/` all render.
3. Confirm the 3 embedded `/videos/*.mp4` return 200 and the TOC anchors resolve to real ids.
4. For anything touching the report, screenshot `/` before and after — the design is co-authored
   work and should not drift.

## Commit conventions

Do not add AI-attribution trailers or footers to commits or PRs in this repository — no
`Co-Authored-By: Claude`, no "Generated with Claude Code". See
[.claude/skills/no-ai-attribution/SKILL.md](.claude/skills/no-ai-attribution/SKILL.md).
