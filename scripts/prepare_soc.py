"""Fetch the exact PR source and prepare independently built C3 probe images."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--images', action='store_true', help='package both already-built factory images')
    p.add_argument('--edges', action='store_true', help='Package the expanded packet edge-case environments')
    a = p.parse_args()
    project = ROOT / 'probes/esp32c3'
    manifest = json.loads((project / 'pr-manifest.json').read_text())
    target = project / 'src/pr'
    target.mkdir(exist_ok=True)
    for entry in manifest['files']:
        destination = target / entry['file']
        if not destination.exists():
            with urllib.request.urlopen(entry['url'], timeout=30) as response:
                destination.write_bytes(response.read())
        data = destination.read_bytes()
        if len(data) != entry['bytes'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
            raise ValueError(f"PR source mismatch: {entry['file']}")
    shutil.copyfile(project / 'Logging.h', target / 'Logging.h')
    if a.images:
        metadata = dict(pr=manifest, images={})
        environments = [('c3_edges', 'base'), ('c3_df_edges', 'patched')] if a.edges else [('c3', 'base'), ('c3_df', 'patched')]
        tag = 'edges' if a.edges else 'df'
        for env, label in environments:
            data = (project / f'.pio/build/{env}/firmware.factory.bin').read_bytes()
            if len(data) > 4 * 1024 * 1024 or data[0] != 0xe9:
                raise ValueError('Expected a merged C3 image smaller than 4 MiB')
            padded = data + b'\xff' * (4 * 1024 * 1024 - len(data))
            destination = ROOT / f'firmware/soc-c3-{tag}-{label}.bin'
            destination.parent.mkdir(exist_ok=True)
            destination.write_bytes(padded)
            metadata['images'][label] = dict(file=destination.name,
                sha256=hashlib.sha256(padded).hexdigest(), factory_bytes=len(data))
        (ROOT / f'firmware/soc-{tag}-provenance.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print('Verified pinned PR source' + (' and packaged C3 images' if a.images else ''))


if __name__ == '__main__':
    main()
