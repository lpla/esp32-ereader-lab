"""Check prerequisites without downloading, building or modifying a guest image."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys

from engines import DEFAULT_ESP, ESP_VERSIONS, engine
from prepare_machine import HEAD, SDK
from run_lab import IMAGE, ROOT


def command(args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=20)
        return result.returncode == 0, (result.stdout or result.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as error:
        return False, str(error)


def packaged(profile, root=ROOT):
    """Reject stale packages as well as missing files before a guest run."""
    try:
        manifest = json.loads((root / 'firmware' / f'{profile}.json').read_text())
        if profile == 'wifi-ap':
            pairs = [(manifest['image'], manifest['image_sha256'])]
            pairs.extend(manifest['sources'].items())
        else:
            if (manifest['crosspoint'], manifest['sdk']) != (HEAD, SDK) or not manifest['abi_layout_verified']:
                raise ValueError('Unsupported firmware revision or unverified adapter ABI')
            pairs = [('firmware/crosspoint-machine.bin', manifest['flash_sha256']),
                     ('tools/crosspoint-machine/.pio/build/default/firmware.elf', manifest['elf_sha256'])]
        for relative, expected in pairs:
            path = root / relative
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError(f'Package changed: {relative}')
        return True, 'Source/image hashes match the package'
    except (OSError, ValueError, KeyError) as error:
        return False, str(error)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=('setup', 'ap', 'reader'), default='setup')
    parser.add_argument('--engine', choices=('qemu', 'esp-emu'), default='esp-emu')
    parser.add_argument('--esp-version', choices=ESP_VERSIONS, default=DEFAULT_ESP)
    parser.add_argument('--card', type=Path, default=ROOT / 'cards/base.img')
    parser.add_argument('--json', action='store_true', help='Machine-readable checks and next actions')
    args = parser.parse_args()
    if args.profile == 'ap' and (args.engine != 'esp-emu' or args.esp_version == '0.45.0'):
        parser.error('AP host reachability requires esp-emulator 0.48.0 or 0.49.0')
    checks = []

    def add(name, ok, detail, fix):
        checks.append(dict(name=name, ok=ok, detail=detail, fix='' if ok else fix))

    add('Python', sys.version_info >= (3, 12), platform.python_version(), 'Use Python 3.12 or newer')
    docker = shutil.which('docker')
    add('Docker CLI', docker is not None, docker or 'docker not found on PATH', 'Install Docker and start its engine')
    ok, detail = command(['docker', 'info', '--format', '{{.OSType}}/{{.Architecture}}'])
    add('Docker server', ok and detail.startswith('linux/'), detail, 'Start Docker with Linux containers')
    ok, detail = command(['docker', 'image', 'inspect', IMAGE, '--format', '{{.Os}}/{{.Architecture}}'])
    image_ok = ok and detail == 'linux/amd64'
    add('Lab image', image_ok, detail, f'docker build --platform linux/amd64 -t {IMAGE} .')
    if image_ok:
        ok, detail = command(['docker', 'run', '--rm', '--network', 'none', IMAGE,
                              'python3', '-c', 'import platform; print(platform.machine())'])
        add('Linux x86_64 execution', ok and detail == 'x86_64', detail,
            'Enable Docker x86_64 translation or use a Linux x86_64 host')
    try:
        _, identity = engine(args.engine, args.esp_version)
        add('Engine package', True, f"{identity['name']} {identity['version']}: hash verified", '')
    except (OSError, ValueError) as error:
        options = f'--engine {args.engine} --esp-version {args.esp_version}'
        add('Engine package', False, str(error),
            f'python3 scripts/download.py {options}; python3 scripts/prepare.py {options}')
    if args.profile in ('ap', 'reader'):
        profile = 'wifi-ap' if args.profile == 'ap' else 'crosspoint-machine'
        ok, detail = packaged(profile)
        fix = ('pio run -d probes/wifi-ap && python3 scripts/prepare_ap.py' if args.profile == 'ap'
               else 'python3 scripts/prepare_machine.py')
        add('Guest package', ok, detail, fix)
    if args.profile == 'reader':
        add('SD fixture', args.card.is_file(), str(args.card),
            'python3 scripts/create_card.py --name base (or choose an existing --card)')
    report = dict(profile=args.profile, ready=all(c['ok'] for c in checks), checks=checks,
                  host=dict(system=platform.system(), machine=platform.machine()),
                  physical_device_validated=False)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for check in checks:
            print(f"{'OK' if check['ok'] else 'MISSING'} {check['name']}: {check['detail']}")
            if check['fix']:
                print(f"  Next: {check['fix']}")
        print('Ready for this profile.' if report['ready'] else 'Complete the missing steps, then rerun doctor.')
    return 0 if report['ready'] else 1


if __name__ == '__main__':
    sys.exit(main())
