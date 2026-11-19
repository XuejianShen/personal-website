# Updating publications

The site serves committed static HTML. Visitors do not make SciX/ADS requests,
and credentials never go into the website or a generated file.

`publications.json` contains the selected-library metadata snapshot and explicit
section assignments. `publication_metrics.json` contains the dated metrics for
the full and selected libraries. `update_publications.py` uses Python's standard
library; no packages or site build step are needed.

## Refresh from SciX / NASA ADS

With `ADS_API_TOKEN` already configured in the environment, run:

```bash
python3 update_publications.py --metrics
```

The script also accepts `ADS_TOKEN`, `NASA_ADS_API_TOKEN`, or `SCIX_API_TOKEN`.
It never accepts a token as a command-line argument, prints it, or saves it.
Do not add credentials to the repository.

This command fetches every page of both curated libraries, refreshes the
selected papers' journal/preprint metadata, calculates citation totals and
h-index, and regenerates the marked publication and homepage sections.
Without `--metrics`, it refreshes the selected library only and retains the
existing dated metric snapshot.

Review the changes, then commit the JSON snapshots and generated HTML together.
The full-library publication count counts all library records, including
conference abstracts if present. Selected-paper totals refer to the curated
selected library; they do not assert first/corresponding authorship.

## Render without credentials or network

```bash
python3 update_publications.py --offline
python3 update_publications.py --offline --check
python3 -m unittest -v test_update_publications.py
```

Offline rendering is deterministic. `--check` checks the generated HTML and
never changes files. Rendering changes only content between
`PUBLICATIONS:START` / `PUBLICATIONS:END` on the publications page and, when a
metric snapshot exists, `PUBLICATION_METRICS:START` / `PUBLICATION_METRICS:END`
on the homepage. It also updates the homepage's
`time#publication-metrics-updated` element. Other page markup, metadata,
navigation, and footers stay outside the generated regions. HTML retains CRLF
line endings.

When `build_translations.py` is present, every render, refresh, and check also
plans both language versions through its `plan_outputs(source_overrides=...)`
interface. It receives the prospective English markup and refreshed JSON
snapshots before any files are replaced. A translation failure stops the entire
refresh; `--check` includes generated Chinese HTML and never writes it.

The publication and metric renderers accept `locale="zh-CN"` for Chinese
headings, navigation, link labels, and metric descriptions. Paper titles, author
names, and journal citations retain their original English text and are marked
`lang="en"`. The same snapshot, section assignments, metrics, and update date
are used for both languages.

## Section assignments and identity changes

Every record stores a stable `key`, accumulated DOI/arXiv/bibcode `aliases`,
its explicit `section`, and the fetched `metadata`. Existing assignments persist
when a preprint receives a journal DOI or a new ADS bibcode. Change a record's
`section` in `publications.json` only when the site owner requests a different
classification, then render offline.

For papers that introduce or use a listed resource, `DATA_RESOURCE_BY_PAPER`
in `update_publications.py` maps a DOI, arXiv, or bibcode alias to the matching
resource ID in `pages/data.html`. Both languages use this mapping for the
**Code & data** link.

The site owner explicitly approved non-first-author papers in the selected
library `lRUUPWajQLK3lmzrBoDI2w` as advising/supervision papers. Accordingly, a
new entry in **that curated library only** defaults to `first_author` when its
first author is exactly `Shen, Xuejian`, otherwise `advising_supervision`.
This policy is not applied to the full bibliography or general author searches.
Review newly added papers as part of reviewing the refresh diff.

An unexpected author list, conflicting first-author assignment, ambiguous
identity, incomplete API response, or API failure stops the refresh before any
files are changed. Each successful file replacement is atomic. If SciX is
unavailable, use the committed snapshot with `--offline`.
