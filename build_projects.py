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
import sys

PROJECTS_DIR = os.path.join(os.path.dirname(__file__), 'projects')
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), 'assets', 'js', 'projects-data.js')

def load_json(path, description):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        sys.exit(f'Error: {description} not found at {path}')
    except json.JSONDecodeError as e:
        sys.exit(f'Error: {description} at {path} is not valid JSON: {e}')

def main():
    manifest_path = os.path.join(PROJECTS_DIR, 'manifest.json')
    manifest = load_json(manifest_path, 'manifest.json')

    projects = []
    for filename in manifest:
        filepath = os.path.join(PROJECTS_DIR, filename)
        projects.append(load_json(filepath, f'project file "{filename}" (listed in manifest.json)'))

    js_content = 'var RESEARCH_PROJECTS = ' + json.dumps(projects, indent=2, ensure_ascii=False) + ';\n'

    with open(OUTPUT_FILE, 'w') as f:
        f.write(js_content)

    print(f'Generated {OUTPUT_FILE} with {len(projects)} projects.')

if __name__ == '__main__':
    main()
