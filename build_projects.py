#!/usr/bin/env python3
"""
Generates assets/js/projects-data.js from individual JSON files in projects/.

Usage:
    python build_projects.py

After adding or editing a project JSON file in projects/, run this script
and commit the updated projects-data.js.
"""

import json
import os

PROJECTS_DIR = os.path.join(os.path.dirname(__file__), 'projects')
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), 'assets', 'js', 'projects-data.js')

def main():
    manifest_path = os.path.join(PROJECTS_DIR, 'manifest.json')
    with open(manifest_path) as f:
        manifest = json.load(f)

    projects = []
    for filename in manifest:
        filepath = os.path.join(PROJECTS_DIR, filename)
        with open(filepath) as f:
            projects.append(json.load(f))

    js_content = 'var RESEARCH_PROJECTS = ' + json.dumps(projects, indent=2, ensure_ascii=False) + ';\n'

    with open(OUTPUT_FILE, 'w') as f:
        f.write(js_content)

    print(f'Generated {OUTPUT_FILE} with {len(projects)} projects.')

if __name__ == '__main__':
    main()
