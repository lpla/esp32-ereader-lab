"""Publish only selected screenshots, diagnostic logs and metadata from a lab run."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('run', help='directory name inside results/')
    parser.add_argument('label', help='new directory name inside evidence/2026-10-04/')
    args = parser.parse_args()
    for name in (args.run, args.label):
        if not name.replace('-', '').replace('_', '').isalnum():
            parser.error('directory names must contain letters, numbers, hyphens or underscores')
    source = ROOT / 'results' / args.run
    target = ROOT / 'evidence/2026-10-04' / args.label
    if not source.is_dir():
        parser.error('run directory does not exist')
    target.mkdir(exist_ok=False)
    hashes = {}
    for path in sorted(source.iterdir()):
        if not path.is_file() or path.suffix not in ('.png', '.json', '.log', '.gdb'):
            continue
        dest = target / path.name
        if path.suffix == '.png':
            shutil.copyfile(path, dest)
        else:
            text = path.read_text().replace(str(ROOT), '<LAB_ROOT>')
            dest.write_text(text)
        hashes[path.name] = hashlib.sha256(dest.read_bytes()).hexdigest()
    (target / 'archive.json').write_text(json.dumps(dict(
        source_run=args.run, files_sha256=hashes,
        local_lab_paths_replaced=True,
        omitted=['firmware', 'emulator executables', 'SD image/files', 'raw guest RAM', 'raw display write bytes']), indent=2) + '\n')
    print(target.relative_to(ROOT))


if __name__ == '__main__':
    main()
