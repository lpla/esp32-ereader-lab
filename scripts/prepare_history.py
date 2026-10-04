"""Fetch pinned historical image helpers and package separately built C3 probes."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--images', action='store_true')
    args = parser.parse_args()
    project = ROOT / 'probes/image-heap'
    manifest = json.loads((project / 'source-manifest.json').read_text())
    for entry in manifest['files']:
        destination = project / 'vendor' / entry['label'] / entry['file']
        if not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(entry['url'], timeout=30) as response:
                destination.write_bytes(response.read())
        if digest(destination) != entry['sha256']:
            raise ValueError(f"Historical source mismatch: {destination}")
    if args.images:
        metadata = dict(source=manifest, probe_sha256=digest(project / 'src/main.cpp'), images={})
        for label in ('base', 'head'):
            build = project / '.pio/build' / label
            sources = [project / 'src/main.cpp', project / 'platformio.ini'] + [
                project / 'vendor' / entry['label'] / entry['file']
                for entry in manifest['files'] if entry['label'] == label]
            if (build / 'firmware.elf').stat().st_mtime < max(path.stat().st_mtime for path in sources):
                raise ValueError('Run the PlatformIO build after source/config changes before packaging')
            factory = (build / 'firmware.factory.bin').read_bytes()
            if not factory or factory[0] != 0xe9 or len(factory) > 4 * 1024 * 1024:
                raise ValueError('Expected a merged C3 probe smaller than 4 MiB')
            # QEMU's 16 MiB flash model accepts the current IDF initialization.
            image = ROOT / 'firmware' / f'image-heap-{label}.bin'
            image.write_bytes(factory + b'\xff' * (16 * 1024 * 1024 - len(factory)))
            metadata['images'][label] = dict(file=image.name, sha256=digest(image),
                elf_sha256=digest(build / 'firmware.elf'), factory_bytes=len(factory))
        (ROOT / 'firmware/image-heap-provenance.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print('Historical source verified' + ('; images packaged' if args.images else ''))


if __name__ == '__main__':
    main()
