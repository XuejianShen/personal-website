"""Regression checks for publication refresh identities and static rendering."""

import copy
import contextlib
import io
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

import update_publications as refresh


def paper(bibcode="2025arXiv250100001S", first=refresh.AUTHOR, citations=0):
    return {"bibcode": bibcode, "title": ["A galaxy at z ≥ 9"],
            "author": [first] if first == refresh.AUTHOR else [first, refresh.AUTHOR],
            "year": "2025", "pubdate": "2025-01-00", "pub": "arXiv e-prints",
            "doctype": "eprint", "identifier": ["arXiv:2501.00001"],
            "citation_count": citations}


def snapshot(records=()):
    result = {"selected_library_id": refresh.SELECTED_LIBRARY, "records": []}
    result["records"] = refresh.reconcile(list(records), result)
    return result


class IdentityTests(unittest.TestCase):
    def test_arxiv_doi_only_fallback_strips_version(self):
        record = paper()
        record["identifier"] = []
        record["doi"] = ["10.48550/arXiv.2501.00001v3"]
        self.assertEqual(refresh.arxiv_id(record), "2501.00001")
        self.assertEqual(refresh.primary_link(record), "https://arxiv.org/abs/2501.00001")

    def test_journal_update_keeps_key_and_explicit_section(self):
        old = snapshot([paper(first="Student, Example")])
        old["records"][0]["section"] = "advising_supervision"
        updated = paper("2026MNRAS.555..123S", first="Student, Example")
        updated.update(doctype="article", doi=["10.1093/mnras/example"],
                       alternate_bibcode=["2025arXiv250100001S"])
        result = refresh.reconcile([updated], old)[0]
        self.assertEqual(result["key"], old["records"][0]["key"])
        self.assertEqual(result["section"], "advising_supervision")
        self.assertIn("bibcode:2025arXiv250100001S", result["aliases"])
        self.assertIn("doi:10.1093/mnras/example", result["aliases"])

    def test_preserves_explicit_advising_even_if_first_author_metadata_changes(self):
        old = snapshot([paper(first="Student, Example")])
        result = refresh.reconcile([paper()], old)[0]
        self.assertEqual(result["section"], "advising_supervision")

    def test_new_curated_papers_use_approved_library_policy(self):
        first = paper()
        other = paper("2026ApJ...999....1S", first="Shen, Tingwei")
        other["identifier"] = ["arXiv:2601.00001"]
        result = refresh.reconcile([first, other], snapshot())
        self.assertEqual([item["section"] for item in result], ["first_author", "advising_supervision"])
        wrong = snapshot()
        wrong["selected_library_id"] = refresh.FULL_LIBRARY
        with self.assertRaises(refresh.RefreshError):
            refresh.reconcile([other], wrong)

    def test_rejects_unknown_authors_and_conflicting_first_author(self):
        unknown = paper()
        unknown["author"] = ["Another, Person"]
        with self.assertRaises(refresh.RefreshError):
            refresh.reconcile([unknown], snapshot())
        old = snapshot([paper()])
        with self.assertRaises(refresh.RefreshError):
            refresh.reconcile([paper(first="Student, Example")], old)

    def test_rejects_alias_collisions(self):
        old = snapshot([paper()])
        old["records"].append(copy.deepcopy(old["records"][0]))
        with self.assertRaises(refresh.RefreshError):
            refresh.reconcile([paper()], old)


class ApiTests(unittest.TestCase):
    def test_failed_refresh_leaves_both_committed_files_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pages").mkdir()
            original = refresh.json_bytes(snapshot([paper()]))
            (root / "publications.json").write_bytes(original)
            page = b"original site page"
            (root / "pages/publications.html").write_bytes(page)
            unexpected = paper()
            unexpected["author"] = ["Unrelated, Author"]
            for failure in (refresh.RefreshError("API unavailable"), None):
                options = {"side_effect": failure} if failure else {"return_value": [unexpected]}
                with patch.object(refresh, "ROOT", root), patch.dict(refresh.os.environ, {"ADS_API_TOKEN": "test-token"}), patch.object(refresh, "fetch_library", **options), contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(refresh.main([]), 1)
                self.assertEqual((root / "publications.json").read_bytes(), original)
                self.assertEqual((root / "pages/publications.html").read_bytes(), page)

    def test_fetches_all_library_pages_and_metadata_batches(self):
        codes = ["2025Fake" + str(index) for index in range(123)]
        documents = {code: dict(paper(code), identifier=["arXiv:2501." + str(index).zfill(5)])
                     for index, code in enumerate(codes)}
        seen_starts = []

        def fake_request(path, token, params):
            self.assertEqual(token, "test-token")
            if path.startswith("biblib/"):
                start = params["start"]
                seen_starts.append(start)
                return {"documents": codes[start:start + params["rows"]],
                        "solr": {"response": {"numFound": len(codes)}}}
            query_codes = [code for code in codes if '"' + code + '"' in params["q"]]
            return {"response": {"numFound": len(query_codes),
                                 "docs": [documents[code] for code in query_codes]}}

        with patch.object(refresh, "request_json", side_effect=fake_request):
            result = refresh.fetch_library("test-token", refresh.FULL_LIBRARY)
        self.assertEqual(seen_starts, [0, 100])
        self.assertEqual({item["bibcode"] for item in result}, set(codes))

    def test_rejects_partial_api_results(self):
        partial = {"documents": [], "solr": {"response": {"numFound": 5}}}
        with patch.object(refresh, "request_json", return_value=partial):
            with self.assertRaises(refresh.RefreshError):
                refresh.fetch_library("test-token", refresh.SELECTED_LIBRARY)

    def test_rejects_missing_search_results(self):
        library = {"documents": ["one"], "solr": {"response": {"numFound": 1}}}
        with patch.object(refresh, "request_json", side_effect=[library, {"response": {"numFound": 0, "docs": []}}]):
            with self.assertRaises(refresh.RefreshError):
                refresh.fetch_library("test-token", refresh.SELECTED_LIBRARY)


class RenderTests(unittest.TestCase):
    def test_chinese_publications_preserve_citations_and_sections(self):
        record = paper(first="Student, Example")
        record.update(doctype="article", doi=["10.1093/mnras/example"],
                      title=['Stars & galaxies < 10'], pub="Example Journal", volume="5", eid="123")
        data = snapshot([record])
        english = refresh.render_publications(data)
        self.assertEqual(english, refresh.render_publications(data, locale="en"))
        chinese = refresh.render_publications(data, locale="zh-CN")
        self.assertIn('第一作者论文', chinese)
        self.assertIn('参与指导的论文', chinese)
        self.assertIn('我在以下论文的研究指导或课题督导中发挥了重要作用。', chinese)
        self.assertIn('<span class="pub-title" lang="en">', chinese)
        self.assertIn('<span class="pub-authors" lang="en">', chinese)
        self.assertIn('<span class="pub-venue" lang="en">Example Journal, Volume 5, Article 123', chinese)
        self.assertIn('>Stars &amp; galaxies &lt; 10</a>', chinese)
        self.assertIn('aria-label="阅读《Stars &amp; galaxies &lt; 10》的期刊版">期刊版</a>', chinese)
        self.assertIn('on arXiv', english)
        self.assertIn('的 arXiv 版本">arXiv</a>', chinese)
        self.assertEqual(chinese.count('class="pub-item"'), english.count('class="pub-item"'))
        self.assertEqual(data["records"][0]["section"], "advising_supervision")

    def test_chinese_metrics_use_local_links_and_same_numbers(self):
        data = refresh.metrics_for([paper(citations=1234)], [paper(citations=1234)], "2026-11-18")
        chinese = refresh.render_metrics(data, locale="zh-CN")
        self.assertIn('href="publications.html"', chinese)
        self.assertNotIn('href="pages/publications.html"', chinese)
        self.assertIn('>论文</span>', chinese)
        self.assertIn('>引用次数</span>', chinese)
        self.assertIn('>h 指数</span>', chinese)
        self.assertIn('1 篇精选论文', chinese)
        self.assertIn('精选论文获引 1,234 次', chinese)
        self.assertNotIn('第一作者', chinese)
        self.assertEqual(refresh.render_metrics(data), refresh.render_metrics(data, locale="en"))

    def test_publication_link_actions_and_escape(self):
        record = paper()
        record.update(doctype="article", doi=["10.1093/mnras/example", "10.48550/arXiv.2501.00001"],
                      title=['Stars & galaxies < 10'], pub="Example Journal", volume="5", eid="123")
        output = refresh.render_publications(snapshot([record]))
        self.assertIn('class="pub-title-link" href="https://doi.org/10.1093/mnras/example"', output)
        self.assertIn('class="pub-journal" href="https://doi.org/10.1093/mnras/example"', output)
        self.assertIn('class="pub-arxiv" href="https://arxiv.org/abs/2501.00001"', output)
        self.assertLess(output.index('class="pub-journal"'), output.index('class="pub-arxiv"'))
        self.assertIn('Stars &amp; galaxies &lt; 10', output)
        self.assertIn('<span class="pub-venue">Example Journal, Volume 5, Article 123', output)
        self.assertIn('href="#advising-supervision-papers"', output)

    def test_eprints_and_abstracts_do_not_get_journal_actions(self):
        eprint = paper()
        output = refresh.render_publications(snapshot([eprint]))
        self.assertNotIn('class="pub-journal"', output)
        self.assertIn('class="pub-arxiv"', output)
        abstract = paper("2025AAS...24542104R", first="Roy, Sandip")
        abstract.update(doctype="abstract", identifier=["2025AAS...24542104R"])
        output = refresh.render_publications(snapshot([abstract]))
        self.assertNotIn('class="pub-journal"', output)
        self.assertNotIn('class="pub-arxiv"', output)

    def test_data_links_follow_paper_aliases_in_both_languages(self):
        # A paper can gain an arXiv alias after SciX first identifies it by DOI.
        qlf = paper("2020MNRAS.495.3252S")
        qlf.update(identifier=[], doi=["10.1093/mnras/staa1381"])
        data = snapshot([qlf, paper()])
        qlf = dict(qlf, identifier=["arXiv:2001.02696v2"])
        data["records"] = refresh.reconcile([qlf, paper()], data)
        for locale, caption in (("en", "Code &amp; data"), ("zh-CN", "代码与数据")):
            with self.subTest(locale=locale):
                markup = refresh.render_publications(data, locale)
                self.assertEqual(markup.count('class="pub-data"'), 1)
                self.assertIn('class="pub-data" href="data.html#bolometric-qlf"', markup)
                self.assertIn('>' + caption + '</a>', markup)

    def test_article_without_journal_doi_uses_scix_journal_fallback(self):
        record = paper()
        record.update(doctype="article", doi=["10.48550/arXiv.2501.00001"],
                      title=['A "quoted" title & galaxies'])
        output = refresh.render_publications(snapshot([record]))
        self.assertIn('class="pub-journal" href="https://scixplorer.org/abs/2025arXiv250100001S/abstract"', output)
        self.assertIn('aria-label="Read A &quot;quoted&quot; title &amp; galaxies in the journal"', output)

    def test_abstract_uses_scix_fallback(self):
        record = paper("2025AAS...24542104R", first="Roy, Sandip")
        record.update(doctype="abstract", pub="American Astronomical Society Meeting Abstracts #245",
                      eid="421.04", identifier=["2025AAS...24542104R"])
        self.assertEqual(refresh.primary_link(record), "https://scixplorer.org/abs/2025AAS...24542104R/abstract")
        self.assertEqual(refresh.venue(record), "American Astronomical Society Meeting Abstracts #245, Abstract 421.04")

    def test_markers_preserve_page_shell_and_are_idempotent(self):
        shell = '<title>Custom title</title>\n<main>\n\t' + refresh.START + '\nold\n\t' + refresh.END + '\n</main>'
        result = refresh.replace_block(shell, refresh.START, refresh.END, "<p>new</p>")
        self.assertTrue(result.startswith('<title>Custom title</title>\n<main>\n'))
        self.assertTrue(result.endswith('\n</main>'))
        self.assertEqual(refresh.replace_block(result, refresh.START, refresh.END, "<p>new</p>"), result)
        with self.assertRaises(refresh.RefreshError):
            refresh.replace_block(shell.replace(refresh.END, ""), refresh.START, refresh.END, "new")

    def test_metrics_do_not_infer_first_corresponding_roles(self):
        full = [paper(citations=n) for n in [9, 5, 3, 2, 0]]
        metrics = refresh.metrics_for(full, full[:2], "2026-11-18")
        self.assertEqual(metrics["h_index"], 3)
        self.assertEqual(metrics["citation_count"], 19)
        self.assertEqual(metrics["selected_citation_count"], 14)
        self.assertEqual(metrics["selected_publication_count"], 2)
        self.assertNotIn("first_corresponding_count", metrics)
        del full[0]["citation_count"]
        with self.assertRaises(refresh.RefreshError):
            refresh.metrics_for(full, full[1:], "2026-11-18")


class TranslationSyncTests(unittest.TestCase):
    def test_builder_receives_prospective_snapshots_and_deduplicates_pages(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "build_translations.py").touch()
            page = root / "pages/publications.html"
            snapshot_path = root / "publications.json"
            zh_page = root / "zh/publications.html"
            prospective = {page: b"new English", snapshot_path: b'{"records": []}'}
            called = []

            def plan_outputs(source_overrides):
                called.append(source_overrides.copy())
                return {page: b"new English with language controls", zh_page: b"new Chinese"}

            builder = types.SimpleNamespace(plan_outputs=plan_outputs)
            with patch.object(refresh, "ROOT", root), patch.dict(refresh.sys.modules, {"build_translations": builder}):
                outputs = dict(refresh.include_translations(list(prospective.items())))
            self.assertEqual(called, [prospective])
            self.assertEqual(outputs[page], b"new English with language controls")
            self.assertEqual(outputs[zh_page], b"new Chinese")
            self.assertEqual(outputs[snapshot_path], prospective[snapshot_path])

    def test_translation_failure_prevents_any_refresh_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pages").mkdir()
            (root / "build_translations.py").touch()
            data = refresh.json_bytes(snapshot([paper()]))
            page = (refresh.START + "\nold\n" + refresh.END).encode()
            (root / "publications.json").write_bytes(data)
            (root / "pages/publications.html").write_bytes(page)
            builder = types.SimpleNamespace(plan_outputs=lambda **kwargs: (_ for _ in ()).throw(ValueError("untranslated content")))
            with patch.object(refresh, "ROOT", root), patch.dict(refresh.sys.modules, {"build_translations": builder}), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(refresh.main(["--offline"]), 1)
            self.assertEqual((root / "publications.json").read_bytes(), data)
            self.assertEqual((root / "pages/publications.html").read_bytes(), page)

    def test_check_includes_chinese_html_and_never_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pages").mkdir()
            (root / "zh").mkdir()
            (root / "build_translations.py").touch()
            data = snapshot([paper()])
            (root / "publications.json").write_bytes(refresh.json_bytes(data))
            page = refresh.replace_block(refresh.START + "\n" + refresh.END, refresh.START, refresh.END, refresh.render_publications(data)).replace("\n", "\r\n").encode()
            (root / "pages/publications.html").write_bytes(page)
            zh = root / "zh/publications.html"
            zh.write_bytes(b"old Chinese")
            builder = types.SimpleNamespace(plan_outputs=lambda **kwargs: {zh: b"updated Chinese"})
            with patch.object(refresh, "ROOT", root), patch.dict(refresh.sys.modules, {"build_translations": builder}), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(refresh.main(["--offline", "--check"]), 1)
            self.assertEqual(zh.read_bytes(), b"old Chinese")
            self.assertEqual((root / "pages/publications.html").read_bytes(), page)


if __name__ == "__main__":
    unittest.main()
