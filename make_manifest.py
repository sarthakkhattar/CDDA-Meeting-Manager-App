#!/usr/bin/env python3
import json
import hashlib
import os

def md5_file(filepath):
    md5 = hashlib.md5()
    with open(filepath, 'rb') as f:
        md5.update(f.read())
    return md5.hexdigest()

exclude = {'.env', '.env.local', '__pycache__', '.git', '.gitignore', '.DS_Store'}
files = {}

for root, dirs, filenames in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in exclude]
    for filename in filenames:
        if filename.startswith('.'):
            continue
        filepath = os.path.join(root, filename)
        rel_path = filepath[2:]
        try:
            checksum = md5_file(filepath)
            files[rel_path] = {'checksum': checksum}
        except:
            pass

manifest = {
    'version': 1,
    'locale': 'en_US.UTF-8',
    'metadata': {
        'appmode': 'python-api',
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

print("[OK] Generated manifest.json")
print(f"  Files: {len(files)}")
