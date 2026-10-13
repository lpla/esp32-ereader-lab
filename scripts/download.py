"""Fetch only the pinned public fixtures; verify every file before use."""
from pathlib import Path
import hashlib
import json
import urllib.request
import argparse
from engine_packages import add_selection, select_files

parser=argparse.ArgumentParser()
add_selection(parser)
args=parser.parse_args()

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / 'downloads/manifest.json').read_text())
if args.legacy_fixtures and (args.engine or args.emulators_only):
    parser.error('--legacy-fixtures cannot be combined with engine selection')
selection = args.engine or (None if args.emulators_only or args.legacy_fixtures else 'all')
for entry in select_files(manifest['files'], selection, args.esp_version, args.emulators_only):
    destination = root / 'downloads' / entry['file']
    if not destination.exists():
        with urllib.request.urlopen(entry['url'], timeout=60) as response:
            data = response.read()
        if len(data) != entry['bytes'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
            raise RuntimeError(f"Download mismatch: {entry['file']}")
        destination.write_bytes(data)
    data = destination.read_bytes()
    if len(data) != entry['bytes'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
        raise RuntimeError(f"Local mismatch: {entry['file']}")
    print('verified', entry['file'])
