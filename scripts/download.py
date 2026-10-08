"""Fetch only the pinned public fixtures; verify every file before use."""
from pathlib import Path
import hashlib
import json
import urllib.request
import argparse

parser=argparse.ArgumentParser()
parser.add_argument('--emulators-only',action='store_true',help='Do not fetch closed firmware fixtures')
args=parser.parse_args()

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / 'downloads/manifest.json').read_text())
for entry in manifest['files']:
    if args.emulators_only and not entry['file'].startswith(('esp-emu','qemu')):continue
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
