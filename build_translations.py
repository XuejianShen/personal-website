#!/usr/bin/env python3
"""Build committed Simplified Chinese pages from English sources and AI translations."""

import argparse
import datetime as dt
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import posixpath
import re
import sys
from urllib.parse import urlsplit, urlunsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
BASE = 'https://xuejianshen.github.io/personal-website/'
PAGE_PAIRS = {'index.html': 'zh/index.html', **{
    'pages/' + name + '.html': 'zh/' + name + '.html'
    for name in ('about_me', 'research1', 'research3', 'publications', 'press', 'credits')
}}
NOTICE = '本中文版本由 AI 翻译，可能存在错误或表述不准确之处。科研内容与个人信息请以英文版为准。'
LANG_START = '<!-- LANGUAGES:START -->'
LANG_END = '<!-- LANGUAGES:END -->'
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}
TEXT_ATTRIBUTES = {'alt', 'title', 'aria-label', 'data-full-label'}


def normalized(value):
    return ' '.join(html.unescape(value).split())


def public_url(path):
    if path == 'index.html':
        return BASE
    if path == 'zh/index.html':
        return BASE + 'zh/'
    return BASE + path


def language_controls(source, english, chinese_page, chinese):
    badge = '<span class="translation-badge">AI 译文</span>' if chinese else ''
    label = '语言' if chinese else 'Language'
    options = []
    for language, destination, text, active, aria in (
        ('en', english, 'English', not chinese, 'English'),
        ('zh-CN', chinese_page, '中文', chinese, '中文（AI 翻译）'),
    ):
        href = posixpath.relpath(destination, posixpath.dirname(source) or '.')
        classes = 'language-option' + (' is-active' if active else '')
        current = ' aria-current="true"' if active else ''
        options.append('<a class="' + classes + '" data-language-option data-language-switch translate="no" href="' + href + '" hreflang="' + language + '" lang="' + language + '" aria-label="' + aria + '"' + current + '>' + text + '</a>')
    return '<li class="language-item">' + badge + '<span class="language-choices" role="group" aria-label="' + label + '" translate="no">' + ''.join(options) + '</span></li>'


def configure_language(text, source, english, chinese_page, chinese=False):
    # Shared, reciprocal metadata is kept outside the translated text dictionary.
    en_url, zh_url = public_url(english), public_url(chinese_page)
    locale = 'zh_CN' if chinese else 'en_US'
    alternate = 'en_US' if chinese else 'zh_CN'
    metadata = '\n'.join([
        LANG_START,
        '\t\t<link rel="alternate" hreflang="en" href="' + en_url + '" />',
        '\t\t<link rel="alternate" hreflang="zh-CN" href="' + zh_url + '" />',
        '\t\t<link rel="alternate" hreflang="x-default" href="' + en_url + '" />',
        '\t\t<meta property="og:locale" content="' + locale + '" />',
        '\t\t<meta property="og:locale:alternate" content="' + alternate + '" />',
        '\t\t' + LANG_END,
    ])
    if LANG_START in text:
        text = re.sub(re.escape(LANG_START) + r'.*?' + re.escape(LANG_END), lambda _: metadata, text, count=1, flags=re.S)
    else:
        marker = re.search(r'<link rel="canonical"[^>]+>', text)
        if not marker:
            raise ValueError('Missing canonical URL in ' + source)
        text = text[:marker.end()] + '\n\t\t' + metadata + text[marker.end():]
    link = language_controls(source, english, chinese_page, chinese)
    nav = re.search(r'(<nav id="nav"[^>]*>)(.*?)(</nav>)', text, re.S)
    if not nav:
        raise ValueError('Missing main navigation in ' + source)
    body = nav[2]
    if 'class="language-item"' in body:
        body = re.sub(r'<li class="language-item">.*?</li>', lambda _: link, body, count=1, flags=re.S)
    else:
        body = body.replace('</ul>', '\t<li class="language-item">PLACEHOLDER</li>\n\t\t\t\t\t\t\t</ul>', 1).replace('<li class="language-item">PLACEHOLDER</li>', link, 1)
    return text[:nav.start(2)] + body + text[nav.end(2):]


class ChinesePage(HTMLParser):
    def __init__(self, source, destination, translations):
        super().__init__(convert_charrefs=True)
        self.source = source
        self.destination = destination
        self.translations = translations
        self.output = []
        self.stack = []
        self.generated = False
        self.missing = set()

    def translate(self, value):
        key = normalized(value)
        if not key:
            return value
        if key not in self.translations:
            if re.search(r'[A-Za-z]', key):
                self.missing.add(key)
            return value
        match = re.match(r'^(\s*)(.*?)(\s*)$', value, re.S)
        return match[1] + self.translations[key] + match[3]

    def local_url(self, value):
        url = urlsplit(value)
        if url.scheme or url.netloc or not url.path:
            return value
        path = posixpath.normpath(posixpath.join(posixpath.dirname(self.source), url.path))
        path = PAGE_PAIRS.get(path, path)
        relative = posixpath.relpath(path, posixpath.dirname(self.destination))
        return urlunsplit(('', '', relative, url.query, url.fragment))

    def start(self, tag, attrs, self_closing=False):
        attrs = dict(attrs)
        if tag == 'html':
            attrs['lang'] = 'zh-CN'
        alternate = tag == 'link' and attrs.get('rel') == 'alternate'
        for name, value in list(attrs.items()):
            if value is None:
                continue
            if name in ('href', 'src', 'poster', 'data-src') and not alternate:
                attrs[name] = self.local_url(value)
            elif name == 'srcset':
                attrs[name] = ', '.join(' '.join([self.local_url(part.strip().split()[0]), *part.strip().split()[1:]]) for part in value.split(','))
            elif name == 'style':
                attrs[name] = re.sub(r'url\(([\'"]?)([^)\'\"]+)\1\)', lambda m: 'url(' + m[1] + self.local_url(m[2]) + m[1] + ')', value)
            elif not self.generated and name in TEXT_ATTRIBUTES:
                attrs[name] = self.translate(value)
            elif not self.generated and tag == 'meta' and name == 'content' and (attrs.get('name') == 'description' or attrs.get('property') in ('og:title', 'og:description', 'og:site_name', 'og:image:alt') or attrs.get('name') in ('twitter:title', 'twitter:description', 'twitter:image:alt')):
                attrs[name] = self.translate(value)
        if tag == 'link' and attrs.get('rel') == 'canonical':
            attrs['href'] = public_url(self.destination)
        if tag == 'meta' and attrs.get('property') == 'og:url':
            attrs['content'] = public_url(self.destination)
        if tag == 'script' and attrs.get('src', '').endswith('/projects-data.js'):
            attrs['src'] = attrs['src'].replace('/projects-data.js', '/projects-data.zh-CN.js')
        rendered = '<' + tag + ''.join(' ' + name + ('' if value is None else '="' + html.escape(value, quote=True) + '"') for name, value in attrs.items()) + (' />' if self_closing else '>')
        self.output.append(rendered)
        if tag not in VOID and not self_closing:
            self.stack.append(tag)

    def handle_starttag(self, tag, attrs):
        self.start(tag, attrs)

    def handle_startendtag(self, tag, attrs):
        self.start(tag, attrs, True)

    def handle_endtag(self, tag):
        self.output.append('</' + tag + '>')
        if tag in self.stack:
            self.stack = self.stack[:len(self.stack) - 1 - self.stack[::-1].index(tag)]

    def handle_data(self, data):
        if any(tag in ('script', 'style') for tag in self.stack):
            self.output.append(data)
        elif self.generated:
            self.output.append(html.escape(data, quote=False))
        else:
            self.output.append(html.escape(self.translate(data), quote=False))

    def handle_comment(self, data):
        self.output.append('<!--' + data + '-->')
        if data.strip() in ('PUBLICATIONS:START', 'PUBLICATION_METRICS:START'):
            self.generated = True
        elif data.strip() in ('PUBLICATIONS:END', 'PUBLICATION_METRICS:END'):
            self.generated = False

    def handle_decl(self, decl):
        self.output.append('<!' + decl + '>')


def chinese_page(text, source, destination, translations, snapshot, metrics):
    import update_publications as publications
    parser = ChinesePage(source, destination, translations)
    parser.feed(text)
    translated = ''.join(parser.output)
    translated = configure_language(translated, destination, source, destination, chinese=True)
    english_href = posixpath.relpath(source, posixpath.dirname(destination))
    notice = '<aside class="translation-notice" aria-label="AI 翻译说明"><div class="container"><strong>AI 翻译版本</strong><span>' + NOTICE + '</span><a class="translation-original" data-language-switch href="' + english_href + '" lang="en" hreflang="en">查看英文原文</a></div></aside>\n\n\t\t\t'
    translated = translated.replace('<main id="main-content"', notice + '<main id="main-content"', 1)
    if source == 'pages/publications.html':
        translated = publications.replace_block(translated, publications.START, publications.END, publications.render_publications(snapshot, locale='zh-CN'))
    if source == 'index.html':
        if metrics:
            translated = publications.replace_block(translated, publications.METRICS_START, publications.METRICS_END, publications.render_metrics(metrics, locale='zh-CN'))
            date = dt.date.fromisoformat(metrics['updated'])
            translated = re.sub(r'(<time id="publication-metrics-updated"[^>]*>).*?(</time>)', lambda m: m[1] + f'{date.year}年{date.month}月{date.day}日' + m[2], translated)
        def person_json(match):
            person = json.loads(match[1])
            person.update(name='沈学简', alternateName=['Xuejian Shen', 'Jacob Shen', '沈學簡'], url=public_url(destination), jobTitle='ITC 研究员')
            return '<script type="application/ld+json">\n' + json.dumps(person, ensure_ascii=False, indent=2) + '\n\t\t</script>'
        translated = re.sub(r'<script type="application/ld\+json">(.*?)</script>', person_json, translated, count=1, flags=re.S)
    translated = '<!-- Generated by build_translations.py; edit translations/pages.zh-CN.json and English sources. -->\n' + translated
    return translated, parser.missing


def plan_outputs(source_overrides=None):
    overrides = {Path(path).resolve(): content for path, content in (source_overrides or {}).items()}
    def read(relative):
        path = ROOT / relative
        data = overrides[path] if path in overrides else path.read_bytes()
        return data.decode('utf-8').replace('\r\n', '\n')
    translations = json.loads(read('translations/pages.zh-CN.json'))
    snapshot = json.loads(read('publications.json'))
    metrics = json.loads(read('publication_metrics.json')) if (ROOT / 'publication_metrics.json').exists() or ROOT / 'publication_metrics.json' in overrides else None
    outputs = {}
    for english, chinese in PAGE_PAIRS.items():
        text = configure_language(read(english), english, english, chinese)
        outputs[ROOT / english] = text.replace('\n', '\r\n').encode('utf-8')
        translated, _ = chinese_page(text, english, chinese, translations, snapshot, metrics)
        translated = '\n'.join(line.rstrip(' \t') for line in translated.split('\n'))
        outputs[ROOT / chinese] = translated.replace('\n', '\r\n').encode('utf-8')
    ns = 'http://www.sitemaps.org/schemas/sitemap/0.9'
    ET.register_namespace('', ns)
    ET.register_namespace('xsi', 'http://www.w3.org/2001/XMLSchema-instance')
    sitemap = ET.fromstring(read('sitemap.xml'))
    entries = {node.find('{' + ns + '}loc').text: node for node in sitemap}
    for english, chinese in PAGE_PAIRS.items():
        url = public_url(chinese)
        if url not in entries:
            node = ET.SubElement(sitemap, '{' + ns + '}url')
            ET.SubElement(node, '{' + ns + '}loc').text = url
            date = entries.get(public_url(english))
            lastmod = date.find('{' + ns + '}lastmod').text if date is not None else '2026-11-18'
            ET.SubElement(node, '{' + ns + '}lastmod').text = lastmod
            ET.SubElement(node, '{' + ns + '}priority').text = '0.60'
    ET.indent(sitemap, space='  ')
    outputs[ROOT / 'sitemap.xml'] = ET.tostring(sitemap, encoding='UTF-8', xml_declaration=True) + b'\n'
    return outputs


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify committed pages without writing files')
    parser.add_argument('--audit', action='store_true', help='List untranslated static text for editorial review')
    args = parser.parse_args(argv)
    try:
        outputs = plan_outputs()
        if args.audit:
            translations = json.loads((ROOT / 'translations/pages.zh-CN.json').read_text())
            snapshot = json.loads((ROOT / 'publications.json').read_text())
            metrics = json.loads((ROOT / 'publication_metrics.json').read_text())
            for english, chinese in PAGE_PAIRS.items():
                text = outputs[ROOT / english].decode().replace('\r\n', '\n')
                _, missing = chinese_page(text, english, chinese, translations, snapshot, metrics)
                print(english + ':')
                for key in sorted(missing):
                    print('  ' + key)
        changed = [path for path, content in outputs.items() if not path.exists() or path.read_bytes() != content]
        if args.check:
            if changed:
                raise ValueError('Generated language pages are out of date: ' + ', '.join(str(p.relative_to(ROOT)) for p in changed))
            print('English/Chinese language pages are current.')
        else:
            import update_publications
            for path in changed:
                update_publications.atomic_write(path, outputs[path])
            print(f'Built {len(PAGE_PAIRS)} Chinese pages with matching language links; {len(changed)} files updated.')
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print('Translation build failed: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
