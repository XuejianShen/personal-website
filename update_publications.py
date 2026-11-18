#!/usr/bin/env python3
"""Refresh committed SciX/ADS metadata and render static publication markup."""

import argparse
import copy
import datetime as dt
import html
import importlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent
SELECTED_LIBRARY = "lRUUPWajQLK3lmzrBoDI2w"
FULL_LIBRARY = "2hvI1lT2Txm315CD1U2fUg"
AUTHOR = "Shen, Xuejian"
SECTIONS = ("first_author", "advising_supervision")
START = "<!-- PUBLICATIONS:START -->"
END = "<!-- PUBLICATIONS:END -->"
METRICS_START = "<!-- PUBLICATION_METRICS:START -->"
METRICS_END = "<!-- PUBLICATION_METRICS:END -->"
FIELDS = "bibcode,alternate_bibcode,title,author,year,pubdate,pub,volume,issue,page,eid,doi,identifier,doctype,property,citation_count"


class RefreshError(Exception):
    """An incomplete or ambiguous refresh must not change committed files."""


def arxiv_id(record):
    for value in record.get("identifier", []) + record.get("doi", []):
        match = re.search(r"(?:arxiv:|arxiv\.org/abs/|10\.48550/arxiv\.)([^\s]+)", value, re.I)
        if match:
            return re.sub(r"v\d+$", "", match.group(1))
    return None


def aliases(record):
    result = {"bibcode:" + value for value in
              [record["bibcode"]] + record.get("alternate_bibcode", [])}
    result.update("doi:" + value.lower() for value in record.get("doi", []))
    if arxiv_id(record):
        result.add("arxiv:" + arxiv_id(record).lower())
    return result


def stable_key(record):
    if arxiv_id(record):
        return "arxiv:" + arxiv_id(record).lower()
    dois = sorted(value.lower() for value in record.get("doi", [])
                  if not value.lower().startswith("10.48550/arxiv."))
    return "doi:" + dois[0] if dois else "bibcode:" + record["bibcode"]


def validate_record(record):
    if not record.get("bibcode") or not record.get("title") or not record.get("year"):
        raise RefreshError("A record is missing its bibcode, title, or year.")
    authors = record.get("author")
    if not isinstance(authors, list) or not authors or AUTHOR not in authors:
        raise RefreshError("Missing or unexpected authors for " + record["bibcode"])
    if record.get("doctype") not in ("article", "eprint", "abstract"):
        raise RefreshError("Review the unsupported publication type for " + record["bibcode"])


def reconcile(records, snapshot):
    """Keep explicit assignments when preprints gain journal/ADS identifiers."""
    if snapshot.get("selected_library_id") != SELECTED_LIBRARY:
        raise RefreshError("The classification policy applies only to the configured curated library.")
    previous = snapshot.get("records", [])
    result = []
    used_keys = set()
    for record in records:
        validate_record(record)
        identities = aliases(record)
        matches = [item for item in previous if identities.intersection(item["aliases"])]
        if len(matches) > 1:
            raise RefreshError("Ambiguous identity aliases for " + record["bibcode"])
        if matches:
            old = matches[0]
            section = old["section"]
            key = old["key"]
            identities.update(old["aliases"])
        else:
            # This is the user's explicitly curated first/advising library, not
            # a general author search. Its non-first papers were approved as advising.
            section = "first_author" if record["author"][0] == AUTHOR else "advising_supervision"
            key = stable_key(record)
        if section not in SECTIONS:
            raise RefreshError("Unknown section for " + record["bibcode"])
        if section == "first_author" and record["author"][0] != AUTHOR:
            raise RefreshError("A first-author assignment conflicts with metadata: " + record["bibcode"])
        if key in used_keys:
            raise RefreshError("Duplicate publication identity: " + key)
        used_keys.add(key)
        result.append({"key": key, "section": section,
                       "aliases": sorted(identities), "metadata": record})
    # Stable sort preserves API/snapshot ordering for publications in the same month.
    result.sort(key=lambda item: item["metadata"].get("pubdate", item["metadata"]["year"]), reverse=True)
    return result


def request_json(path, token, params=None):
    url = "https://api.adsabs.harvard.edu/v1/" + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"Authorization": "Bearer " + token,
                                                 "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        raise RefreshError("SciX/ADS API returned HTTP " + str(error.code) + ". No files changed.") from None
    except (urllib.error.URLError, TimeoutError, ValueError):
        raise RefreshError("Unable to read valid SciX/ADS API data. No files changed.") from None


def fetch_library(token, library_id):
    bibcodes = []
    total = None
    for start in range(0, 100000, 100):
        payload = request_json("biblib/libraries/" + library_id, token,
                               {"start": start, "rows": 100})
        response = payload.get("solr", {}).get("response", {})
        count = response.get("numFound", payload.get("metadata", {}).get("num_documents"))
        if not isinstance(count, int) or count < 0 or (total is not None and count != total):
            raise RefreshError("Library size changed or could not be verified; retry the refresh.")
        total = count
        batch = payload.get("documents")
        if not isinstance(batch, list) or (not batch and len(bibcodes) < total):
            raise RefreshError("The API returned an incomplete library page.")
        bibcodes.extend(batch)
        if len(bibcodes) >= total:
            break
    if total is None or len(bibcodes) != total or len(set(bibcodes)) != total:
        raise RefreshError("The API returned duplicate or incomplete library records.")
    records = []
    for start in range(0, len(bibcodes), 50):
        chunk = bibcodes[start:start + 50]
        query = "bibcode:(" + " OR ".join('"' + value + '"' for value in chunk) + ")"
        payload = request_json("search/query", token,
                               {"q": query, "fl": FIELDS, "rows": 100, "sort": "date desc"})
        response = payload.get("response", {})
        batch = response.get("docs", [])
        if response.get("numFound") != len(chunk) or len(batch) != len(chunk):
            raise RefreshError("Some library metadata is missing; no files changed.")
        records.extend(batch)
    if len({record["bibcode"] for record in records}) != total:
        raise RefreshError("Duplicate publication metadata returned by the API.")
    records.sort(key=lambda record: record.get("pubdate", record.get("year", "")), reverse=True)
    return records


def primary_link(record):
    journal_dois = [value for value in record.get("doi", [])
                    if not value.lower().startswith("10.48550/arxiv.")]
    if journal_dois:
        return "https://doi.org/" + journal_dois[0]
    if arxiv_id(record):
        return "https://arxiv.org/abs/" + arxiv_id(record)
    return "https://scixplorer.org/abs/" + urllib.parse.quote(record["bibcode"], safe=".") + "/abstract"


def journal_link(record):
    if record["doctype"] != "article":
        return None
    for value in record.get("doi", []):
        if not value.lower().startswith("10.48550/arxiv."):
            return "https://doi.org/" + value
    return "https://scixplorer.org/abs/" + urllib.parse.quote(record["bibcode"], safe=".") + "/abstract"


def venue(record):
    if record["doctype"] == "eprint":
        return "arXiv:" + arxiv_id(record) if arxiv_id(record) else "arXiv e-prints"
    result = record.get("pub", "")
    if record["doctype"] == "abstract":
        return result + ", Abstract " + str(record.get("eid", record.get("page", [""])[0]))
    if not record.get("volume"):
        return result + ", Advance online publication"
    result += ", Volume " + str(record["volume"])
    if record.get("issue"):
        result += ", Issue " + str(record["issue"])
    page = record.get("eid") or next(iter(record.get("page", [])), None)
    if page:
        result += (", Article " if record.get("eid") else ", p. ") + str(page)
    return result


def render_publications(snapshot, locale="en"):
    if locale not in ("en", "zh-CN"):
        raise RefreshError("Unsupported publication locale: " + locale)
    chinese = locale == "zh-CN"
    first_title = "第一作者论文" if chinese else "First-author Papers"
    advising_title = "参与指导的论文" if chinese else "Advising and Supervision"
    language = ' lang="en"' if chinese else ''
    records = snapshot["records"]
    lines = ['<nav class="pub-shortcuts" aria-label="' + ("论文分类" if chinese else "Publication sections") + '">',
             '\t<a href="#first-author-papers">' + first_title + '</a>',
             '\t<a href="#advising-supervision-papers">' + advising_title + '</a>', '</nav>']
    for section, anchor, title in (("first_author", "first-author-papers", first_title),
                                   ("advising_supervision", "advising-supervision-papers", advising_title)):
        lines += ['<section class="pub-section" aria-labelledby="' + anchor + '">',
                  '\t<h2 class="pub-section-title" id="' + anchor + '">' + title + '</h2>']
        if section == "advising_supervision":
            lines.append('\t<p class="pub-section-note">' + ("我在以下论文的研究指导或课题督导中发挥了重要作用。" if chinese else "Papers in which I played a major role in advising or supervision.") + '</p>')
        lines.append('\t<ol class="pub-list">')
        for item in records:
            if item["section"] != section:
                continue
            record = item["metadata"]
            validate_record(record)
            display_authors = record["author"][:4]
            if AUTHOR not in display_authors:
                display_authors.append(AUTHOR)
            authors = "; ".join('<strong>' + html.escape(author) + '</strong>' if author == AUTHOR
                                else html.escape(author) for author in display_authors)
            if len(record["author"]) > len(display_authors):
                authors += " et al."
            lines += ['\t\t<li class="pub-item">',
                      '\t\t\t<span class="pub-title"' + language + '><a class="pub-title-link" href="' + html.escape(primary_link(record), quote=True) + '" target="_blank" rel="noopener">' + html.escape(record["title"][0]) + '</a></span>',
                      '\t\t\t<span class="pub-authors"' + language + '>' + authors + '</span>',
                      '\t\t\t<span class="pub-venue"' + language + '>' + html.escape(venue(record)) + '<span class="pub-year">' + html.escape(record["year"]) + '</span></span>']
            actions = []
            title_label = html.escape(record["title"][0], quote=True)
            if journal_link(record):
                label = "阅读《" + title_label + "》的期刊版" if chinese else "Read " + title_label + " in the journal"
                actions.append('<a class="pub-journal" href="' + html.escape(journal_link(record), quote=True) + '" target="_blank" rel="noopener" aria-label="' + label + '">' + ("期刊版" if chinese else "Journal") + '</a>')
            if arxiv_id(record):
                label = "阅读《" + title_label + "》的 arXiv 版本" if chinese else "Read " + title_label + " on arXiv"
                actions.append('<a class="pub-arxiv" href="https://arxiv.org/abs/' + html.escape(arxiv_id(record), quote=True) + '" target="_blank" rel="noopener" aria-label="' + label + '">arXiv</a>')
            if actions:
                lines.append('\t\t\t<span class="pub-links">' + ' '.join(actions) + '</span>')
            lines.append('\t\t</li>')
        lines += ['\t</ol>', '</section>']
    return "\n".join(lines)


def metrics_for(full_records, selected_records, date):
    counts = []
    for record in full_records + selected_records:
        value = record.get("citation_count")
        if not isinstance(value, int) or value < 0:
            raise RefreshError("Citation counts are missing; no files changed.")
    counts = sorted((record["citation_count"] for record in full_records), reverse=True)
    return {"schema_version": 1, "updated": date, "source": "SciX / NASA ADS",
            "full_library_id": FULL_LIBRARY, "selected_library_id": SELECTED_LIBRARY,
            "publication_count": len(full_records), "citation_count": sum(counts),
            "h_index": sum(value >= rank for rank, value in enumerate(counts, 1)),
            "selected_publication_count": len(selected_records),
            "selected_citation_count": sum(record["citation_count"] for record in selected_records)}


def render_metrics(metrics, locale="en"):
    if locale not in ("en", "zh-CN"):
        raise RefreshError("Unsupported metric locale: " + locale)
    chinese = locale == "zh-CN"
    e = html.escape
    full_url = "https://scixplorer.org/public-libraries/" + FULL_LIBRARY
    return '\n'.join(['<div class="highlights-grid">',
        '\t<a class="highlight-stat" href="' + ("publications.html" if chinese else "pages/publications.html") + '">',
        '\t\t<span class="highlight-number">' + format(metrics["publication_count"], ",") + '</span>',
        '\t\t<span class="highlight-label">' + ("论文" if chinese else "Publications") + '</span>',
        '\t\t<span class="highlight-sub">' + format(metrics["selected_publication_count"], ",") + (' 篇精选论文' if chinese else ' selected papers') + '</span>', '\t</a>',
        '\t<a class="highlight-stat" href="' + e(full_url) + '">',
        '\t\t<span class="highlight-number">' + format(metrics["citation_count"], ",") + '</span>',
        '\t\t<span class="highlight-label">' + ("引用次数" if chinese else "Citations") + '</span>',
        '\t\t<span class="highlight-sub">' + (("精选论文获引 " + format(metrics["selected_citation_count"], ",") + " 次") if chinese else (format(metrics["selected_citation_count"], ",") + ' on selected papers')) + '</span>', '\t</a>',
        '\t<div class="highlight-stat">',
        '\t\t<span class="highlight-number">' + str(metrics["h_index"]) + '</span>',
        '\t\t<span class="highlight-label">' + ("h 指数" if chinese else "h-index") + '</span>',
        '\t\t<span class="highlight-sub">' + ("SciX 指标" if chinese else "SciX metrics") + '</span>', '\t</div>', '</div>'])


def include_translations(writes):
    """Plan both language versions from prospective data before changing files."""
    outputs = dict(writes)
    if (ROOT / "build_translations.py").exists():
        try:
            builder = importlib.import_module("build_translations")
            translated = builder.plan_outputs(source_overrides=outputs)
            if not isinstance(translated, dict) or not all(isinstance(path, Path) and isinstance(data, bytes) for path, data in translated.items()):
                raise RefreshError("The translation builder returned invalid planned outputs.")
            outputs.update(translated)
        except Exception as error:
            raise RefreshError("Unable to generate both language versions; no files changed (" + type(error).__name__ + ").") from None
    return list(outputs.items())


def replace_block(text, start, end, content):
    if text.count(start) != 1 or text.count(end) != 1 or text.index(start) > text.index(end):
        raise RefreshError("Missing or ambiguous generated-content markers.")
    pattern = r"(?m)^([ \t]*)" + re.escape(start) + r"[\s\S]*?" + re.escape(end)
    match = re.search(pattern, text)
    if not match:
        raise RefreshError("Generated-content markers must start on their own lines.")
    indent = match.group(1)
    block = indent + start + "\n" + "\n".join(indent + line if line else "" for line in content.splitlines()) + "\n" + indent + end
    return text[:match.start()] + block + text[match.end():]


def atomic_write(path, data):
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix="." + path.name, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(data)
        os.chmod(temporary, path.stat().st_mode & 0o777 if path.exists() else 0o644)
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def json_bytes(data):
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Render committed snapshots without network access or credentials")
    parser.add_argument("--check", action="store_true", help="Check generated HTML; do not write any files")
    parser.add_argument("--metrics", action="store_true", help="Also refresh full/selected-library citation metrics")
    args = parser.parse_args(argv)
    snapshot_path = ROOT / "publications.json"
    metrics_path = ROOT / "publication_metrics.json"
    page_path = ROOT / "pages/publications.html"
    home_path = ROOT / "index.html"
    try:
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        snapshot = copy.deepcopy(snapshot)
        metrics = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.exists() else None
        if not args.offline:
            token = next((os.environ[name] for name in ("ADS_API_TOKEN", "ADS_TOKEN", "NASA_ADS_API_TOKEN", "SCIX_API_TOKEN") if os.environ.get(name)), None)
            if not token:
                raise RefreshError("Set ADS_API_TOKEN (or ADS_TOKEN / NASA_ADS_API_TOKEN / SCIX_API_TOKEN), or use --offline.")
            records = fetch_library(token, SELECTED_LIBRARY)
            if not records:
                raise RefreshError("The selected library is unexpectedly empty; no files changed.")
            snapshot["records"] = reconcile(records, snapshot)
            snapshot["updated"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
            if args.metrics:
                metrics = metrics_for(fetch_library(token, FULL_LIBRARY), records, snapshot["updated"])
        else:
            # Validate offline data and preserve all explicit section assignments.
            snapshot["records"] = reconcile([item["metadata"] for item in snapshot["records"]], snapshot)
        page = page_path.read_text(encoding="utf-8")
        rendered_page = replace_block(page, START, END, render_publications(snapshot))
        writes = [(page_path, rendered_page.replace("\n", "\r\n").encode("utf-8"))]
        if not args.offline:
            writes.append((snapshot_path, json_bytes(snapshot)))
            if args.metrics:
                writes.append((metrics_path, json_bytes(metrics)))
        if metrics:
            home = home_path.read_text(encoding="utf-8")
            if METRICS_START in home or METRICS_END in home:
                rendered_home = replace_block(home, METRICS_START, METRICS_END, render_metrics(metrics))
                date = dt.date.fromisoformat(metrics["updated"])
                time_text = '<time id="publication-metrics-updated" datetime="' + date.isoformat() + '">' + date.strftime("%B ") + str(date.day) + date.strftime(", %Y") + '</time>'
                rendered_home = re.sub(r'<time\s+id="publication-metrics-updated"[^>]*>.*?</time>', lambda _: time_text, rendered_home)
                writes.append((home_path, rendered_home.replace("\n", "\r\n").encode("utf-8")))
        writes = include_translations(writes)
        if args.check:
            changed = [str(path.relative_to(ROOT)) for path, content in writes if path.suffix == ".html" and path.read_bytes() != content]
            if changed:
                raise RefreshError("Generated content is out of date: " + ", ".join(changed))
            print("Generated publication content is current.")
        else:
            # Everything above succeeds before the first atomic replacement.
            for path, content in writes:
                if not path.exists() or path.read_bytes() != content:
                    atomic_write(path, content)
            print("Rendered " + str(len(snapshot["records"])) + " selected publications" + (" and citation metrics." if metrics else "."))
        return 0
    except (RefreshError, OSError, ValueError, KeyError, TypeError) as error:
        print("Publication refresh failed: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
