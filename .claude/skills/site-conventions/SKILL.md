---
name: site-conventions
description: Standing rules for baishixi.blog — the home page must be the owner's bio (never the report), personal pages must not use the old Hugo/Simple.css theme styling, and the co-authored CS295 report keeps its own design untouched. Load before editing any page, stylesheet, build.py, or content file in this repository.
---

# Site conventions for baishixi.blog

Standing requirements from the site's owner. These override defaults and earlier
conversation; apply them without re-asking.

## 1. The home page is the bio page

`/` shows the owner's bio — who they are, what they work on, where to find them.

- Source: `content/_index.md`. `build.py` renders it to `index.html`.
- **It is never the report.** An earlier Hugo layout made `/` render the full CS295
  report; that was removed on purpose. Do not restore it, and do not add a second copy
  of any post to the home page.
- There is no separate `/about/` page — the home page *is* the about page, so the nav
  has no About entry. Do not add one back alongside a bio home page; that duplicates.
- Long-form posts live only at `/posts/<slug>/`.

## 2. No Hugo theme styling on the owner's pages

The site was migrated off Hugo. The theme's stylesheet still exists as `css/site.css`
(Simple.css + the theme's `style.css`, vendored when the submodule was deleted), but
**it must not be used on the owner's own pages.**

- Home, posts index, projects, now and 404 load **`css/pages.css` only**.
- `css/pages.css` is the site's real design: monospace, hairline rules, three-state
  theming (bare `:root`, then `prefers-color-scheme`, then `[data-theme]`).
- If a page looks like the old theme — Simple.css's centered serif-ish body, its blue
  links, its default list styling — that is a bug.

## 3. The report keeps its own design, untouched

`content/posts/vla-policy-size.md` is a CS295 final report **co-authored with Eric and
Sean**. It is not solely the owner's to restyle.

- It loads `css/site.css` + `css/report.css`, and that combination must stay.
- **`css/report.css` cannot stand alone.** It defines its own tokens but still depends
  on Simple.css's body grid for layout. Removing `site.css` from the report page
  collapses it into a squeezed column with content overflowing off-screen — this was
  tested, not assumed. This is the one place the vendored theme CSS is legitimate.
- Do not restyle, reflow, or "modernize" the report unless asked directly. If a change
  touches it, screenshot `/posts/vla-policy-size/` before and after and confirm the
  design has not drifted.

## 4. Do not publish unpublished or in-progress research

**Default to not putting research on the site until its owner says it is publishable.**
This site is public and indexed; anything added to it is disclosure.

- Do not add a project, repo, dataset, result, method or live demo just because a public
  GitHub repo exists. A public repo is not consent to publicise the work — an unannounced
  or pre-publication project can be findable without being *published*.
- This applies with extra force to **collaborative work**, where the decision is not the
  site owner's alone to make. Forked or shared repos are a signal to ask, not to proceed.
- If asked to "add my project X", add it — but if X looks like active, unreleased research,
  say so and confirm scope before writing anything public-facing.
- The CS295 VLA report **is** publishable: it is a finished, already-live report. Treat it
  as the exception, not the pattern.

If something like this has to be removed, also check it never reached git
(`git log --all -S '<term>'`) and, if it was committed or pushed, say so plainly rather
than quietly deleting — removal from the working tree does not undo publication.

## Applying this

The split lives in `build.py` as `CSS_REPORT` and `CSS_PAGES`; route new page types
through one of those rather than hardcoding stylesheet paths.

After editing anything in `content/`, run `python3 build.py` and **commit the generated
HTML too** — the deploy workflow performs no build, so unbuilt changes never ship.
`python3 build.py --check` reports whether the committed output is stale.
