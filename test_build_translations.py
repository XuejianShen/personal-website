"""Checks for corresponding language pages, shared scientific data, and path safety."""

from html import escape
from html.parser import HTMLParser
import json
import datetime as dt
from pathlib import Path
import re
import unittest
from urllib.parse import urlsplit, unquote
from urllib.robotparser import RobotFileParser
import xml.etree.ElementTree as ET

import build_projects
import build_translations as translations


class Inventory(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags=[]
    def handle_starttag(self,tag,attrs):
        self.tags.append((tag,dict(attrs)))


class TranslationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs=translations.plan_outputs()

    def test_generation_is_current_and_idempotent(self):
        for path,content in self.outputs.items():
            self.assertEqual(path.read_bytes(),content,str(path))
        self.assertEqual(translations.plan_outputs(self.outputs),self.outputs)

    def test_each_page_has_its_corresponding_switch_notice_and_seo_links(self):
        for english,chinese in translations.PAGE_PAIRS.items():
            for relative,chinese_version in ((english,False),(chinese,True)):
                text=self.outputs[translations.ROOT/relative].decode()
                parser=Inventory(); parser.feed(text)
                expected_lang='zh-CN' if chinese_version else 'en'
                self.assertIn(('html',{'lang':expected_lang}),parser.tags)
                alternates={a['hreflang']:a['href'] for tag,a in parser.tags if tag=='link' and a.get('rel')=='alternate'}
                self.assertEqual(alternates,{'en':translations.public_url(english),'zh-CN':translations.public_url(chinese),'x-default':translations.public_url(english)})
                expected_url = translations.public_url(relative)
                self.assertEqual([a['href'] for tag,a in parser.tags if tag=='link' and a.get('rel')=='canonical'], [expected_url])
                self.assertEqual([a['content'] for tag,a in parser.tags if tag=='meta' and a.get('property')=='og:url'], [expected_url])
                switches=[a for tag,a in parser.tags if 'language-option' in a.get('class','').split()]
                self.assertEqual(len(switches),2)
                self.assertEqual([a['lang'] for a in switches],['en','zh-CN'])
                for choice,destination_path in zip(switches,[english,chinese]):
                    destination=(Path(relative).parent/choice['href']).resolve()
                    self.assertEqual(destination,(translations.ROOT/destination_path).resolve())
                    self.assertEqual(choice['translate'],'no')
                active=[a for a in switches if a.get('aria-current')=='true']
                self.assertEqual(len(active),1)
                self.assertEqual(active[0]['lang'],expected_lang)
                self.assertIn('is-active',active[0]['class'].split())
                notices=[a for tag,a in parser.tags if 'translation-notice' in a.get('class','').split()]
                self.assertEqual(len(notices),int(chinese_version))
                if chinese_version:self.assertIn(translations.NOTICE,text)
                self.assertEqual(text.count('<main '),1)
                self.assertEqual(text.count('<h1'),1)

    def test_rebased_assets_and_links_exist(self):
        for relative in translations.PAGE_PAIRS.values():
            parser=Inventory();parser.feed(self.outputs[translations.ROOT/relative].decode())
            for tag,attrs in parser.tags:
                refs=[attrs[key] for key in ('href','src','poster','data-src') if key in attrs]
                if 'srcset' in attrs:refs.extend(v.strip().split()[0] for v in attrs['srcset'].split(','))
                if 'style' in attrs:refs.extend(m[1] for m in re.findall(r'url\(([\'"]?)([^)\'\"]+)\1\)',attrs['style']))
                for ref in refs:
                    url=urlsplit(ref)
                    if url.scheme or url.netloc or not url.path:continue
                    self.assertTrue((translations.ROOT/relative).parent.joinpath(unquote(url.path)).exists(),(relative,ref))

    def test_research_uses_chinese_bundle_and_preserves_ids(self):
        for filename in ('research1.html','research3.html'):
            text=self.outputs[translations.ROOT/'zh'/filename].decode()
            self.assertIn('../assets/js/projects-data.zh-CN.js',text)
            self.assertNotIn('src="../assets/js/projects-data.js"',text)
            self.assertIn('data-category=',text)

    def test_citations_and_roles_match_english(self):
        english=self.outputs[translations.ROOT/'pages/publications.html'].decode()
        chinese=self.outputs[translations.ROOT/'zh/publications.html'].decode()
        def titles(text):return re.findall(r'<a class="pub-title-link"[^>]*>(.*?)</a>',text)
        self.assertEqual(titles(english),titles(chinese))
        for label,count in [('pub-item',36),('pub-journal',31),('pub-arxiv',35)]:
            self.assertEqual(chinese.count('class="'+label+'"'),count)
        self.assertIn('参与指导的论文',chinese)
        self.assertIn('lang="en"',chinese)

    def test_project_text_and_papers_are_in_the_static_pages(self):
        english, chinese = build_projects.load_projects()
        for folder, projects in [('pages', english), ('zh', chinese)]:
            found = []
            for filename in build_projects.RESEARCH_PAGES:
                page = self.outputs[translations.ROOT / folder / filename].decode()
                found.extend(re.findall(r'<section class="project-summary" id="([^"]+)">(.*?)</section>', page, re.S))
            self.assertCountEqual([project_id for project_id, _ in found], [p['id'] for p in projects])
            blocks = dict(found)
            for project in projects:
                block = blocks[project['id']]
                self.assertIn('<h4>' + escape(project['title']) + '</h4>', block)
                self.assertIn(project['description'], block)
                for link in project['paperLinks']:
                    self.assertIn(f'<a href="{escape(link["url"])}">{escape(link["label"])}</a>', block)

    def test_dynamic_counts_follow_prospective_data(self):
        path=translations.ROOT/'publication_metrics.json'
        metrics=json.loads(path.read_text());metrics['citation_count']=12345
        metrics['selected_citation_count']=9876
        outputs=translations.plan_outputs({path:json.dumps(metrics).encode()})
        text=outputs[translations.ROOT/'zh/index.html'].decode()
        self.assertIn('12,345',text)
        self.assertIn('9,876',text)
        date=dt.date.fromisoformat(metrics['updated'])
        self.assertIn(f'{date.year}年{date.month}月{date.day}日',text)

    def test_sitemap_lists_both_language_versions(self):
        root=ET.fromstring(self.outputs[translations.ROOT/'sitemap.xml'])
        ns={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
        locations=[node.text for node in root.findall('s:url/s:loc',ns)]
        self.assertEqual(len(locations),len(set(locations)))
        self.assertTrue(all(url.startswith(translations.BASE) for url in locations))
        robots = RobotFileParser()
        robots.parse((translations.ROOT / 'robots.txt').read_text().splitlines())
        self.assertEqual(robots.site_maps(), [translations.BASE + 'sitemap.xml'])
        for agent in ('Googlebot', 'bingbot', 'OAI-SearchBot'):
            self.assertTrue(all(robots.can_fetch(agent, url) for url in locations))
        for english,chinese in translations.PAGE_PAIRS.items():
            self.assertIn(translations.public_url(english),locations)
            self.assertIn(translations.public_url(chinese),locations)


if __name__=='__main__':
    unittest.main()
