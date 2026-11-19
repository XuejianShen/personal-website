# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## What this is

Static personal academic website for Xuejian (Jacob) Shen (astrophysicist, Harvard CfA), based on the **Arcana** HTML5 UP template. Plain HTML/CSS/JS — there is **no HTML/CSS/JS build step or package manager**. The only build script is `build_projects.py` (see below).

## Commands

```bash
# Local preview — serve from repo root so relative paths resolve
# (index.html is at root; pages/ reference assets via ../).
python3 -m http.server 8000      # then open http://localhost:8000/

# Regenerate the research-projects data bundle after editing projects/*.json
python3 build_projects.py
```

## Deployment

`.github/workflows/pages.yml` deploys the **entire repo as-is** to GitHub Pages on every push to `master` (live at `https://shenxuejian.com/`). There is no compile/transform step in CI — what you commit is what ships. The checkout uses `lfs: true` because videos are stored in Git LFS (see Media below).

## Research projects data pipeline (the main non-obvious architecture)

Research project cards are data-driven and span four files — understand all four before editing:

1. **`projects/*.json`** — one file per project. Schema:
   `title`, `category`, `order` (sort within category), `description` (HTML allowed), `paperLinks: [{label, url}]`, `image` (filename only; resolved against `../images/`).
2. **`projects/manifest.json`** — ordered array of which JSON filenames to include. A project file is ignored unless listed here.
3. **`build_projects.py`** — reads the manifest + each JSON and writes `assets/js/projects-data.js` (a single `var RESEARCH_PROJECTS = [...]` global). **This generated file is committed**; the site loads it directly.
4. **`assets/js/research-tabs.js`** — at page load, finds every `<div class="project-tabs" data-category="X">`, groups `RESEARCH_PROJECTS` by `category`, sorts by `order`, and renders a tabbed UI. Styled by `assets/css/research-tabs.css` (linked only on research pages).

**Workflow gotcha:** editing a project JSON has no effect until you run `python3 build_projects.py` and commit the regenerated language bundles and research pages. The project titles, descriptions, and paper links are also built into the HTML so readers and crawlers can access them with JavaScript disabled. To add a new project, create the JSON **and** add its filename to `manifest.json`, then rebuild.

Category → page mapping: `sidm` + `axions` render on `pages/research1.html`; `highz_galaxies` + `smbh` render on `pages/research3.html`.

## Page structure & conventions

- `index.html` is at repo root; active pages live in `pages/` (archived pages in `legacy/` — see below) and reference assets with `../`.
- **Nav and footer are hand-duplicated in every HTML file** — there is no templating/includes. A nav or footer change must be applied to each page individually (and to `sitemap.xml` when adding/removing a page).
- **Canonical (linked) pages:** `index.html`, `pages/about_me.html`, `pages/research1.html`, `pages/research3.html`, `pages/group.html`, `pages/publications.html`, `pages/data.html`, `pages/press.html`, `pages/credits.html`. These match `sitemap.xml`.
- **Legacy/orphaned pages live in `legacy/` (repo root), NOT in the nav or `sitemap.xml`:** `legacy/research2.html`, `legacy/research4.html`, `legacy/research_main.html`, `legacy/talks.html`. They were moved out of `pages/` to keep the active site uncluttered; their content was folded into research1/research3 (plus an old talks listing) and they use an older, deeper nav layout. `legacy/` sits at the same depth as `pages/`, so their `../assets`, `../images`, `../documents`, and `../index.html` references still resolve; links to canonical pages were repointed to `../pages/…`. They are still deployed (CI ships the whole repo) but are unlinked. When asked to edit "the research pages," target research1 and research3 unless told otherwise.
- **Inner-page presentation classes** (styles under `/* Inner pages */` in `main.css`): research pages open with a `.page-hero` band (background image via inline style, `.research-switch` pills linking research1/research3, then either `.page-hero-grid` text + figure card, or centered text + a `.page-hero-strip` of images with a `.page-hero-credit`), followed by stacked `<article class="topic">` blocks (`.topic-intro`, optional `.topic-intro--with-figure`, `.projects-heading`, then the `.project-tabs` container). Publications open with a `.pubs-hero` header (the word cloud as a faded `.pubs-hero-cloud` backdrop behind the ADS logo and the `.pubs-note` sentence), then a `.pub-list` of `.pub-item` entries (`.pub-title` / `.pub-authors` / `.pub-venue` + `.pub-year`). Press groups coverage by story: a `.press-stories` list of `.press-story` cards, each with a `.press-story-title` (one of the original headlines) and a `.press-outlets` chip row whose links carry the outlet name as text and the full original "Outlet: headline" as the `title` tooltip. Footer social links are one `ul.icons.social-icons` row. When editing these pages keep the wording intact and change only markup/classes; page files use CRLF line endings.
- `templates/*.html` are the original HTML5 UP layout samples (left/right/two-sidebar). They are reference boilerplate, not part of the live site.

## CSS

- `assets/css/main.css` is the served stylesheet. Although `assets/sass/` contains the template's SASS sources, **custom site styles (e.g. the home `.gallery-grid` and lazy-video rules) were added directly to `main.css` and do not exist in the SASS**. Recompiling SASS over `main.css` would destroy those additions — edit `main.css` directly.
- `assets/css/research-tabs.css` holds the project-tab styles and is linked only on the research pages.
- `assets/css/data-sharing.css` styles `pages/data.html`. Its Chinese counterpart is generated with `build_translations.py`. Repository and THESAN data links are public; THESAN-ZOOM, Lumina, the AREPO-2 SIDM model, and NORI access is through private communication.
- `assets/css/group.css` is linked only on the Group page. The student list and supervision periods start from the Teaching & Advising section of the CV, with current roles and affiliations incorporating the user's corrections. Vinh Tran has a single entry covering both undergraduate and graduate supervision. Current-student research summaries are included when confirmed; visible student links point only to verified personal websites. Alumni use a compact list, and Charline Shen is listed as a master's student. Edit `pages/group.html` and the Chinese translation dictionary, then run `python3 build_translations.py`.

## Media & Git LFS

- `*.mp4` files are tracked via **Git LFS** (`.gitattributes`). Ensure LFS is installed before committing videos.
- **Quotas that bite:** a published GitHub Pages site must stay under **1 GB**, and every CI deploy (`actions/checkout` with `lfs: true`) re-downloads *all* LFS objects, which counts against the **10 GB/month** LFS bandwidth allowance. Keep only web-sized previews in the repo; host multi-hundred-MB originals elsewhere (or accept that each push burns the LFS total).
- **Preview videos:** every big video gets a `*_preview.mp4` (1080p, 30 fps, libx264 CRF 27, `-movflags +faststart`, no audio) that is the in-page/lightbox source; the original is only the "full resolution" link. Recreate with:
  `ffmpeg -i in.mp4 -vf "scale=1920:-2,fps=30" -c:v libx264 -preset slow -crf 27 -pix_fmt yuv420p -movflags +faststart -an out_preview.mp4`
- **Poster frames** for videos live in `images/posters/` (`ffmpeg -ss <t> -i preview.mp4 -frames:v 1 -vf scale=960:-2 -q:v 4 poster.jpg`).
- Large source files (multi-MB PDFs, 8K PNGs) are **not** meant to be committed; commit the derived web-sized JPEG/PNG instead (e.g. `images/lumina_200cMpc_hero.jpg` is a 2400 px JPEG of an 8192 px PNG; `images/AltDM-demo-gas*.{jpg,png}` are rendered from a Keynote PDF via `pdftoppm -r 300`, cropped to the square panel area).

## Home-page gallery (index.html)

The gallery is a compact 4/3/2-column grid of square tiles with an in-page lightbox. Three places cooperate:

1. **Markup** (`index.html`, `<!-- Gallery -->`): one `<figure class="gallery-item" data-type="video|image">` per tile containing `<a class="gallery-tile" href="<full-res file>" data-full-label="...">` around the media (`<video class="gallery-video-lazy" poster=...><source data-src=...>` or `<img>`), a `.gallery-tile-title` overlay, and a hidden `<figcaption class="gallery-meta">` holding the lightbox title/credit HTML. Without JS the tile is a plain link to the full-res file.
2. **Styles** in `assets/css/main.css` under `/* Gallery (home page) ... */` and `/* Gallery lightbox */`.
3. **Behavior** at the bottom of `assets/js/main.js`: (a) the IntersectionObserver block lazy-loads/pauses tile videos (`data-src`, not `src`, so nothing downloads until scrolled into view); (b) the lightbox block builds the viewer DOM on load, and handles click/Esc/arrow keys/swipe, focus trapping, and pausing tile videos while open.

The **Research Highlights** band below the gallery (`.highlights-section`, dark `.wrapper.style3`) is a three-stat grid styled under `/* Research highlights */` in `main.css`; numbers live directly in `index.html`. Section paddings use `.wrapper.gallery-section` / `.wrapper.highlights-section` selectors on purpose: the template's mobile `.wrapper` rules come later in the file and would otherwise override them.

To add a tile: copy an existing `<figure>`, point `href` at the full-res file (with a size in `data-full-label`), `data-src` at the preview, and `poster` at a frame in `images/posters/`.
