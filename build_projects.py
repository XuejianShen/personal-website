#!/usr/bin/env python3
"""
Generate the English and Simplified Chinese research-project bundles and HTML.

Usage:
    python3 build_projects.py

Edit projects/*.json for English content and translations/projects.zh-CN.json
for Chinese content, then commit the generated bundles and research pages.
"""

import copy
from html import escape
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import sys

ROOT_DIR = os.path.dirname(__file__)
PROJECTS_DIR = os.path.join(ROOT_DIR, 'projects')
OUTPUT_FILE = os.path.join(ROOT_DIR, 'assets', 'js', 'projects-data.js')
ZH_OUTPUT_FILE = os.path.join(ROOT_DIR, 'assets', 'js', 'projects-data.zh-CN.js')
ZH_TRANSLATION_FILE = os.path.join(ROOT_DIR, 'translations', 'projects.zh-CN.json')
RESEARCH_PAGES = ('research1.html', 'research3.html')
PROJECT_SUMMARIES = re.compile(r'\s*<!-- PROJECTS:START -->.*?<!-- PROJECTS:END -->\s*', re.S)
PROJECT_CONTAINER = re.compile(r'^([ \t]*)<div class="project-tabs" data-category="([^"]+)"></div>', re.M)


def load_json(path, description):
    try:
        with open(path, encoding='utf-8') as source:
            return json.load(source)
    except FileNotFoundError:
        raise ValueError(f'{description} not found at {path}') from None
    except json.JSONDecodeError as error:
        raise ValueError(f'{description} at {path} is not valid JSON: {error}') from None


class MarkupSignature(HTMLParser):
    """Keep the source's markup and link attributes intact in translations."""

    def __init__(self, html):
        super().__init__()
        self.signature = []
        self.feed(html)
        self.close()

    def handle_starttag(self, tag, attrs):
        self.signature.append((tag, sorted(attrs)))

    def handle_endtag(self, tag):
        self.signature.append(('/' + tag, []))

    def handle_startendtag(self, tag, attrs):
        self.signature.append((tag + '/', sorted(attrs)))


def translate_projects(projects, translations):
    """Validate a complete overlay and return translated copies of the records."""
    project_ids = {project['id'] for project in projects}
    if not isinstance(translations, dict):
        raise ValueError('Chinese translations must be an object keyed by project id.')
    missing = project_ids - translations.keys()
    extra = translations.keys() - project_ids
    if missing or extra:
        raise ValueError('Chinese project translation IDs do not match the manifest: '
                         f'missing={sorted(missing)}, unknown={sorted(extra)}.')
    result = []
    for project in projects:
        project_id = project['id']
        overlay = translations[project_id]
        if not isinstance(overlay, dict) or set(overlay) != {'title', 'description', 'paperLinks'}:
            raise ValueError(f'{project_id}: Chinese overlay needs exactly title, description, and paperLinks.')
        for field in ['title', 'description']:
            if not isinstance(overlay[field], str) or not overlay[field].strip():
                raise ValueError(f'{project_id}: Chinese {field} must be a non-empty string.')
        if MarkupSignature(overlay['description']).signature != MarkupSignature(project['description']).signature:
            raise ValueError(f'{project_id}: Chinese description must preserve the English HTML tags and link attributes.')
        labels = overlay['paperLinks']
        links = project.get('paperLinks', [])
        if not isinstance(labels, list) or len(labels) != len(links):
            raise ValueError(f'{project_id}: Chinese paperLinks needs one label for each English paper link.')
        if any(not isinstance(label, str) or not label.strip() for label in labels):
            raise ValueError(f'{project_id}: Chinese paper-link labels must be non-empty strings.')
        translated = copy.deepcopy(project)
        translated['title'] = overlay['title']
        translated['description'] = overlay['description']
        for link, label in zip(translated.get('paperLinks', []), labels):
            link['label'] = label
        result.append(translated)
    return result


def load_projects():
    manifest_path = os.path.join(PROJECTS_DIR, 'manifest.json')
    manifest = load_json(manifest_path, 'manifest.json')
    projects = []
    project_ids = set()
    for filename in manifest:
        filepath = os.path.join(PROJECTS_DIR, filename)
        project = load_json(filepath, f'project file "{filename}" (listed in manifest.json)')
        project_id = project.get('id', '')
        if not isinstance(project_id, str) or not re.fullmatch(r'[a-z][a-z0-9]*(?:-[a-z0-9]+)*', project_id):
            raise ValueError(f'{filename} needs a stable lowercase "id" using letters, numbers, and hyphens.')
        if project_id in project_ids:
            raise ValueError(f'duplicate project id "{project_id}" in {filename}.')
        project_ids.add(project_id)
        projects.append(project)
    translations = load_json(ZH_TRANSLATION_FILE, 'Chinese project translations')
    return projects, translate_projects(projects, translations)


def render_project_summaries(page, projects):
    """Make the project text and paper links available before the tabs run."""
    def render_slot(match):
        indent, category = match.groups()
        ordered = sorted((p for p in projects if p['category'] == category),
                         key=lambda p: p.get('order', 0))
        lines = [f'<div class="project-tabs" data-category="{escape(category)}">',
                 '\t<!-- PROJECTS:START -->']
        for project in ordered:
            lines.extend([
                f'\t<section class="project-summary" id="{escape(project["id"])}">',
                f'\t\t<h4>{escape(project["title"])}</h4>',
                f'\t\t<div class="project-description">{project["description"]}</div>',
            ])
            links = [f'<a href="{escape(link["url"])}">{escape(link["label"])}</a>'
                     for link in project.get('paperLinks', [])]
            if links:
                lines.append('\t\t<p class="project-papers">' + ' '.join(links) + '</p>')
            lines.append('\t</section>')
        lines.extend(['\t<!-- PROJECTS:END -->', '</div>'])
        return '\n'.join(indent + line for line in lines)

    return PROJECT_CONTAINER.sub(render_slot, PROJECT_SUMMARIES.sub('', page))


def main():
    from update_publications import atomic_write

    try:
        projects, chinese_projects = load_projects()
    except ValueError as error:
        sys.exit(f'Error: {error}')

    outputs = {}
    for output_file, folder, records in [(OUTPUT_FILE, 'pages', projects), (ZH_OUTPUT_FILE, 'zh', chinese_projects)]:
        js_content = 'var RESEARCH_PROJECTS = ' + json.dumps(records, indent=2, ensure_ascii=False) + ';\n'
        outputs[Path(output_file)] = js_content.encode()
        for filename in RESEARCH_PAGES:
            page = Path(ROOT_DIR, folder, filename)
            rendered = render_project_summaries(page.read_text(encoding='utf-8'), records)
            outputs[page] = rendered.replace('\n', '\r\n').encode()
    for path, data in outputs.items():
        if not path.exists() or path.read_bytes() != data:
            atomic_write(path, data)
    print(f'Built research bundles and static project summaries for {len(projects)} projects in both languages.')


if __name__ == '__main__':
    main()
