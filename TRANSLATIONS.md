# Chinese version

The eight current pages have committed Simplified Chinese counterparts in `zh/`.
Every Chinese page prominently identifies the text as AI translated, warns that
errors may remain, and links to the matching English source. Paper titles,
authors, and journal citations retain their original English for identification.
CV and external press articles remain in their original languages.

The desktop navigation and mobile title bar both show English / 中文, with the
current language highlighted. Language names are protected from browser translation.
The selector retains the current project or publication-section anchor. Switching is
explicit; the site does not automatically redirect visitors by browser language.

## Editing and rebuilding

Edit English HTML as the source of truth. Chinese static copy is mapped in
`translations/pages.zh-CN.json`: keys are the original text with HTML entities
decoded and whitespace collapsed; values are the AI-produced Chinese text.
Research-project translations live in `translations/projects.zh-CN.json`, keyed
by the stable project IDs. Links, images, sorting, and scientific identifiers
are inherited from the English project records.

```bash
python3 build_projects.py
python3 build_translations.py
python3 build_translations.py --check
```

Commit the dictionaries, both generated project bundles, and generated `zh/`
HTML with the source edits. English HTML receives only language controls and
reciprocal language metadata; it remains directly editable. Generated Chinese
HTML should not be edited independently.

`python3 build_translations.py --audit` lists unmapped static strings for review.
New English text falls back to English until a translation is added, rather than
reusing an unrelated translation. Update the Chinese project overlay whenever
the English research descriptions change. No translation service, API key,
JavaScript HTML build, or package installation is needed for visitors or builds.

## Publications and metrics

`python3 update_publications.py --metrics` refreshes the English and Chinese
publication pages and metric snapshots together. Role assignments, titles,
authors, Journal/arXiv destinations, dates, and counts come from the same data.
`python3 update_publications.py --offline --check` also checks the generated
Chinese pages without network access or credentials.

The two language versions have self-canonical URLs, reciprocal `hreflang`
links, and entries in `sitemap.xml`. Scientific media is shared, not duplicated.
