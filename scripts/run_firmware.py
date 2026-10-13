"""Run a supplied merged image on a private copy with a bounded serial assertion."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
from engines import DEFAULT_ESP, ESP_VERSIONS
from firmware_contract import image_layout
from run_lab import IMAGE

ROOT = Path(__file__).resolve().parents[1]


def source_identity(path):
    def git(*args):
        return subprocess.check_output(['git', '-C', str(path), *args])
    return dict(path=str(path), head=git('rev-parse', 'HEAD').decode().strip(),
                status=git('status', '--porcelain').decode(),
                diff_sha256=hashlib.sha256(git('diff', 'HEAD', '--binary')).hexdigest(),
                submodules=git('submodule', 'status', '--recursive').decode(),
                untracked_contents_hashed=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--expect', required=True)
    parser.add_argument('--chip', choices=('esp32c3', 'esp32s3'), default='esp32c3')
    parser.add_argument('--source', type=Path)
    parser.add_argument('--seconds', type=int, default=60)
    parser.add_argument('--esp-version', choices=ESP_VERSIONS, default=DEFAULT_ESP)
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*', args.name):
        parser.error('Use letters, digits and single hyphens for the result name')
    if not args.expect.strip() or not 1 <= args.seconds <= 3600:
        parser.error('Use a nonempty completion marker and --seconds between 1 and 3600')
    try:
        original = args.image.resolve()
        data = original.read_bytes()
        layout = image_layout(data, args.chip)
        source = source_identity(args.source.resolve()) if args.source else None
        # Check prerequisites before reserving a run name or copying an image.
        readiness = subprocess.run([sys.executable, str(ROOT / 'scripts/doctor.py'), '--engine', 'esp-emu',
                                    '--esp-version', args.esp_version], cwd=ROOT, capture_output=True, text=True)
        if readiness.returncode:
            print(readiness.stdout, end='')
            print(readiness.stderr, end='', file=sys.stderr)
            return readiness.returncode
        directory = ROOT / 'results' / args.name
        directory.parent.mkdir(exist_ok=True)
        directory.mkdir(exist_ok=False)
        digest = hashlib.sha256(data).hexdigest()
        (directory / 'flash.bin').write_bytes(data)
        metadata = dict(image_sha256=digest, original_path=str(original), layout=layout, source=source,
                        chip=args.chip, completion_marker=args.expect, seconds=args.seconds,
                        esp_version=args.esp_version, scope='serial component test; no board transport adapter',
                        guest_network_isolated=True, flash_state_saved=False,
                        runner_sources_sha256={name: hashlib.sha256((ROOT / 'scripts' / name).read_bytes()).hexdigest()
                                               for name in ('run_firmware.py', 'probe_firmware.py', 'firmware_contract.py',
                                                            'engines.py', 'diagnostics.py', 'prepare.py')})
        (directory / 'input.json').write_text(json.dumps(metadata, indent=2) + '\n')
        command = ['docker', 'run', '--rm', '--network', 'none', '-v', f'{ROOT}:/work', IMAGE,
                   'python3', 'scripts/probe_firmware.py', '--name', args.name]
        result = subprocess.run(command, cwd=ROOT)
        unchanged = hashlib.sha256(original.read_bytes()).hexdigest() == digest
        (directory / 'source-check.json').write_text(json.dumps(dict(original_image_unchanged=unchanged), indent=2) + '\n')
        verdict_file = directory / 'result.json'
        if verdict_file.exists():
            verdict = json.loads(verdict_file.read_text())
            verdict['original_image_unchanged'] = unchanged
            verdict['passed'] = verdict['passed'] and unchanged
            verdict_file.write_text(json.dumps(verdict, indent=2) + '\n')
        if not unchanged:
            print('Original image changed during the run; result rejected', file=sys.stderr)
        print(f"Results: {directory}")
        return result.returncode if unchanged else 1
    except (OSError, ValueError, struct.error, subprocess.CalledProcessError) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
