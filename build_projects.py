#!/usr/bin/env python3
"""
Generate the English and Simplified Chinese research-project bundles.

Usage:
    python3 build_projects.py

Edit projects/*.json for English content and translations/projects.zh-CN.json
for Chinese content, then commit both generated JavaScript bundles. Chinese
translations overlay only display strings; project IDs and links stay identical.
"""

import copy
from html.parser import HTMLParser
import json
import os
import re
import sys

ROOT_DIR = os.path.dirname(__file__)
PROJECTS_DIR = os.path.join(ROOT_DIR, 'projects')
OUTPUT_FILE = os.path.join(ROOT_DIR, 'assets', 'js', 'projects-data.js')
ZH_OUTPUT_FILE = os.path.join(ROOT_DIR, 'assets', 'js', 'projects-data.zh-CN.js')
ZH_TRANSLATION_FILE = os.path.join(ROOT_DIR, 'translations', 'projects.zh-CN.json')


def load_json(path, description):
    try:
        with open(path, encoding='utf-8') as source:
            return json.load(source)
    except FileNotFoundError:
        sys.exit(f'Error: {description} not found at {path}')
    except json.JSONDecodeError as error:
        sys.exit(f'Error: {description} at {path} is not valid JSON: {error}')


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


def main():
    manifest_path = os.path.join(PROJECTS_DIR, 'manifest.json')
    manifest = load_json(manifest_path, 'manifest.json')
    projects = []
    project_ids = set()
    for filename in manifest:
        filepath = os.path.join(PROJECTS_DIR, filename)
        project = load_json(filepath, f'project file "{filename}" (listed in manifest.json)')
        project_id = project.get('id', '')
        if not isinstance(project_id, str) or not re.fullmatch(r'[a-z][a-z0-9]*(?:-[a-z0-9]+)*', project_id):
            sys.exit(f'Error: {filename} needs a stable lowercase "id" using letters, numbers, and hyphens.')
        if project_id in project_ids:
            sys.exit(f'Error: duplicate project id "{project_id}" in {filename}.')
        project_ids.add(project_id)
        projects.append(project)
    translations = load_json(ZH_TRANSLATION_FILE, 'Chinese project translations')
    try:
        chinese_projects = translate_projects(projects, translations)
    except ValueError as error:
        sys.exit(f'Error: {error}')

    # Validate both languages before touching either committed output file.
    for output_file, records in [(OUTPUT_FILE, projects), (ZH_OUTPUT_FILE, chinese_projects)]:
        js_content = 'var RESEARCH_PROJECTS = ' + json.dumps(records, indent=2, ensure_ascii=False) + ';\n'
        with open(output_file, 'w', encoding='utf-8', newline='\n') as output:
            output.write(js_content)
        print(f'Generated {output_file} with {len(records)} projects.')


if __name__ == '__main__':
    main()
