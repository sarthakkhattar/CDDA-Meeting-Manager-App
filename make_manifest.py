#!/usr/bin/env python3
"""Generate manifest.json for Posit Connect deployment."""

import json
import hashlib
import os

def md5_file(filepath):
    md5 = hashlib.md5()
    with open(filepath, 'rb') as f:
        md5.update(f.read())
    return md5.hexdigest()

EXCLUDE_DIRS = {'.env', '.env.local', '__pycache__', '.git', '.gitignore',
                '.DS_Store', 'venv', '.venv', 'static'}
EXCLUDE_FILES = {'.env', '.env.local', '.DS_Store', '.gitignore'}

files = {}
for root, dirs, filenames in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
    for filename in filenames:
        if filename.startswith('.') or filename in EXCLUDE_FILES:
            continue
        filepath = os.path.join(root, filename)
        rel_path = filepath[2:]  # strip leading ./
        try:
            checksum = md5_file(filepath)
            files[rel_path] = {'checksum': checksum}
        except Exception:
            pass

manifest = {
    'version': 1,
    'locale': 'en_US.UTF-8',
    'metadata': {
        'appmode': 'python-dash',
        'entrypoint': 'app:server'
    },
    'python': {
        'version': '3.12.0',
        'package_manager': {
            'name': 'pip',
            'package_file': 'requirements.txt'
        }
    },
    'files': files
}

with open('manifest.json', 'w') as f:
    json.dump(manifest, f, indent=2)

print("[OK] Generated manifest.json (appmode: python-dash)")
print(f"  Files: {len(files)}")
for p in sorted(files):
    print(f"    {p}")
