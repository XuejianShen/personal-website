# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Static personal academic website for Xuejian (Jacob) Shen (astrophysicist, MIT), based on the **Arcana** HTML5 UP template. Plain HTML/CSS/JS — there is **no HTML/CSS/JS build step or package manager**. The only build script is `build_projects.py` (see below).

## Commands

```bash
# Local preview — serve from repo root so relative paths resolve
# (index.html is at root; pages/ reference assets via ../).
python3 -m http.server 8000      # then open http://localhost:8000/

# Regenerate the research-projects data bundle after editing projects/*.json
python3 build_projects.py
```

## Deployment

`.github/workflows/pages.yml` deploys the **entire repo as-is** to GitHub Pages on every push to `master` (live at `https://xuejianshen.github.io/personal-website/`). There is no compile/transform step in CI — what you commit is what ships. The checkout uses `lfs: true` because videos are stored in Git LFS (see Media below).

## Research projects data pipeline (the main non-obvious architecture)

Research project cards are data-driven and span four files — understand all four before editing:

1. **`projects/*.json`** — one file per project. Schema:
   `title`, `category`, `order` (sort within category), `description` (HTML allowed), `paperLinks: [{label, url}]`, `image` (filename only; resolved against `../images/`).
2. **`projects/manifest.json`** — ordered array of which JSON filenames to include. A project file is ignored unless listed here.
3. **`build_projects.py`** — reads the manifest + each JSON and writes `assets/js/projects-data.js` (a single `var RESEARCH_PROJECTS = [...]` global). **This generated file is committed**; the site loads it directly.
4. **`assets/js/research-tabs.js`** — at page load, finds every `<div class="project-tabs" data-category="X">`, groups `RESEARCH_PROJECTS` by `category`, sorts by `order`, and renders a tabbed UI. Styled by `assets/css/research-tabs.css` (linked only on research pages).

**Workflow gotcha:** editing a project JSON has no effect until you run `python3 build_projects.py` and commit the regenerated `projects-data.js`. To add a new project, create the JSON **and** add its filename to `manifest.json`, then rebuild.

Category → page mapping: `sidm` + `axions` render on `pages/research1.html`; `highz_galaxies` + `smbh` render on `pages/research3.html`.

## Page structure & conventions

- `index.html` is at repo root; active pages live in `pages/` (archived pages in `legacy/` — see below) and reference assets with `../`.
- **Nav and footer are hand-duplicated in every HTML file** — there is no templating/includes. A nav or footer change must be applied to each page individually (and to `sitemap.xml` when adding/removing a page).
- **Canonical (linked) pages:** `index.html`, `pages/about_me.html`, `pages/research1.html`, `pages/research3.html`, `pages/publications.html`, `pages/press.html`. These match `sitemap.xml`.
- **Legacy/orphaned pages live in `legacy/` (repo root), NOT in the nav or `sitemap.xml`:** `legacy/research2.html`, `legacy/research4.html`, `legacy/research_main.html`, `legacy/talks.html`. They were moved out of `pages/` to keep the active site uncluttered; their content was folded into research1/research3 (plus an old talks listing) and they use an older, deeper nav layout. `legacy/` sits at the same depth as `pages/`, so their `../assets`, `../images`, `../documents`, and `../index.html` references still resolve; links to canonical pages were repointed to `../pages/…`. They are still deployed (CI ships the whole repo) but are unlinked. When asked to edit "the research pages," target research1 and research3 unless told otherwise.
- `templates/*.html` are the original HTML5 UP layout samples (left/right/two-sidebar). They are reference boilerplate, not part of the live site.

## CSS

- `assets/css/main.css` is the served stylesheet. Although `assets/sass/` contains the template's SASS sources, **custom site styles (e.g. the home `.gallery-grid` and lazy-video rules) were added directly to `main.css` and do not exist in the SASS**. Recompiling SASS over `main.css` would destroy those additions — edit `main.css` directly.
- `assets/css/research-tabs.css` holds the project-tab styles and is linked only on the research pages.

## Media & Git LFS

- `*.mp4` files are tracked via **Git LFS** (`.gitattributes`). Ensure LFS is installed before committing videos.
- Home-page gallery videos are **lazy-loaded** by the IntersectionObserver block at the bottom of `assets/js/main.js`. To add one, follow the existing pattern: class `gallery-video-lazy` and `<source data-src="...">` (note `data-src`, not `src`, so it loads only when scrolled into view). Some videos ship a separate low-res `*_preview.mp4` used as the in-page source while the full file is the click-through target.
