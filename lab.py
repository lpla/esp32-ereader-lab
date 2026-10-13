#!/usr/bin/env python3
"""Developer entry point for setup, builds and bounded emulator tests."""
import argparse
import datetime
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
from engines import DEFAULT_ESP, ESP_VERSIONS
from run_lab import IMAGE


def execute(command):
    subprocess.run(command, cwd=ROOT, check=True)


def script(name, *arguments):
    execute([sys.executable, str(ROOT / 'scripts' / name), *map(str, arguments)])


def logged(command, kind):
    logs = ROOT / 'results' / f'{kind}-logs'
    logs.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    log = logs / f'{stamp}.log'
    with log.open('x') as output:
        result = subprocess.run(command, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT)
    print(f"{kind.capitalize()} {'passed' if result.returncode == 0 else 'failed'}: {log}")
    if result.returncode:
        print('\n'.join(log.read_text(errors='replace').splitlines()[-20:]), file=sys.stderr)
        raise subprocess.CalledProcessError(result.returncode, command)


def engine_options(parser):
    parser.add_argument('--engine', choices=('qemu', 'esp-emu'))
    parser.add_argument('--esp-version', choices=ESP_VERSIONS, default=DEFAULT_ESP)


def main():
    profiles = json.loads((ROOT / 'config/profiles.json').read_text())['profiles']
    by_id = {p['id']: p for p in profiles}
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    setup = commands.add_parser('setup', help='Download selected engines and build the Linux container')
    setup.add_argument('--engine', choices=('qemu', 'esp-emu', 'all'), default='all')
    setup.add_argument('--esp-version', choices=ESP_VERSIONS, default=DEFAULT_ESP)
    listing = commands.add_parser('profiles', help='Show supported workflows and their limits')
    listing.add_argument('--json', action='store_true')
    doctor = commands.add_parser('doctor', help='Read-only prerequisite and package checks')
    doctor.add_argument('--profile', choices=tuple(by_id), help='Omit for setup checks')
    doctor.add_argument('--card', type=Path)
    doctor.add_argument('--json', action='store_true')
    engine_options(doctor)
    build = commands.add_parser('build', help='Build a known control or your own PlatformIO project')
    choice = build.add_mutually_exclusive_group(required=True)
    choice.add_argument('--profile', choices=tuple(by_id))
    choice.add_argument('--project', type=Path, help='Your project; no checkout, source edits or repinning')
    build.add_argument('--environment', help='Required with --project')
    card = commands.add_parser('card', help='Create a new disposable SD fixture')
    card.add_argument('--name', required=True)
    card.add_argument('--fixture', choices=('alpha', 'beta', 'gamma'), default='alpha')
    run = commands.add_parser('run', help='Execute a supported workflow; preserve results under a new name')
    run.add_argument('--profile', choices=tuple(by_id), required=True)
    run.add_argument('--name', required=True)
    run.add_argument('--card', type=Path)
    run.add_argument('--book', default='/alpha.epub', help='Reader only: absolute SD book path')
    run.add_argument('--scenario', choices=('read', 'turn-exit'), default='turn-exit', help='Reader only')
    run.add_argument('--seconds', type=int, help='Reader/transfer only: 5–300 seconds')
    run.add_argument('--debug-remote', action='store_true', help='Reader/transfer only: capture GDB packets')
    engine_options(run)
    firmware = commands.add_parser('firmware', help='Run your own merged test firmware with a serial assertion')
    firmware.add_argument('--image', type=Path, required=True)
    firmware.add_argument('--name', required=True)
    firmware.add_argument('--expect', required=True, help='Serial completion marker emitted by your test')
    firmware.add_argument('--chip', choices=('esp32c3', 'esp32s3'), default='esp32c3')
    firmware.add_argument('--source', type=Path, help='Optional Git checkout to record revision and diff hash')
    firmware.add_argument('--seconds', type=int, default=60)
    firmware.add_argument('--esp-version', choices=ESP_VERSIONS, default=DEFAULT_ESP)
    check = commands.add_parser('check', help='Compare completed engine controls with identical firmware and inputs')
    check.add_argument('first', type=Path)
    check.add_argument('second', type=Path)
    commands.add_parser('test', help='Run the host regression suite')
    args = parser.parse_args()
    for key in ('project', 'card', 'image', 'source', 'first', 'second'):
        value = getattr(args, key, None)
        if value is not None:
            setattr(args, key, value.resolve())
    try:
        if args.command == 'setup':
            options = ('--engine', args.engine, '--esp-version', args.esp_version)
            script('download.py', *options)
            script('prepare.py', *options)
            execute(['docker', 'build', '--platform', 'linux/amd64', '-t', IMAGE, '.'])
        elif args.command == 'profiles':
            if args.json:
                print(json.dumps(dict(schema=1, default_esp_version=DEFAULT_ESP, profiles=profiles), indent=2))
            else:
                for profile in profiles:
                    print(f"{profile['id']}: {profile['description']}\n  {profile['scope']}")
        elif args.command == 'doctor':
            profile = by_id.get(args.profile)
            selected_engine = args.engine or (profile['preferred_engine'] if profile else 'esp-emu')
            if profile and profile['id'] == 'file-transfer' and (selected_engine != 'esp-emu' or args.esp_version == '0.45.0'):
                parser.error('File transfer requires esp-emulator 0.48.0 or 0.49.0')
            options = ['--profile', profile['doctor_profile'] if profile else 'setup',
                       '--engine', selected_engine, '--esp-version', args.esp_version]
            if args.json:
                options.append('--json')
            if args.card:
                options.extend(['--card', args.card])
            script('doctor.py', *options)
        elif args.command == 'build':
            if args.project:
                if not args.environment or not (args.project / 'platformio.ini').is_file():
                    parser.error('--project requires platformio.ini and an explicit --environment')
                logged(['pio', 'run', '-d', str(args.project), '-e', args.environment], 'build')
                return 0
            if args.environment:
                parser.error('--environment is only used with --project')
            if by_id[args.profile]['build'] == 'wifi-ap':
                logged(['pio', 'run', '-d', str(ROOT / 'probes/wifi-ap')], 'build')
                logged([sys.executable, str(ROOT / 'scripts/prepare_ap.py')], 'build')
            else:
                logged([sys.executable, str(ROOT / 'scripts/prepare_machine.py')], 'build')
        elif args.command == 'card':
            script('create_card.py', '--name', args.name, '--fixture', args.fixture)
        elif args.command == 'run':
            if not re.fullmatch(r'[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*', args.name):
                parser.error('Use letters, digits and single hyphens for the result name')
            if (ROOT / 'results' / args.name).exists():
                parser.error('Result name already exists; choose a new name to preserve evidence')
            if args.seconds is not None and not 5 <= args.seconds <= 300:
                parser.error('--seconds must be between 5 and 300 for reader/transfer workflows')
            profile = by_id[args.profile]
            selected_engine = args.engine or profile['preferred_engine']
            if profile['requires_card'] and not args.card:
                parser.error('This profile requires --card; create one with lab.py card')
            if args.profile == 'file-transfer' and args.esp_version == '0.45.0':
                parser.error('File transfer requires esp-emulator 0.48.0 or 0.49.0')
            if args.profile == 'file-transfer' and selected_engine != 'esp-emu':
                parser.error('File transfer requires esp-emulator')
            if args.profile == 'ap' and (selected_engine != 'esp-emu' or args.card or args.seconds is not None or args.debug_remote):
                parser.error('AP uses esp-emulator, no SD/debug adapter, and its fixed bounded budget')
            readiness = subprocess.run([sys.executable, str(ROOT / 'scripts/doctor.py'),
                                        '--profile', profile['doctor_profile'], '--engine', selected_engine,
                                        '--esp-version', args.esp_version,
                                        *(['--card', str(args.card)] if args.card else [])],
                                       cwd=ROOT, capture_output=True, text=True)
            if readiness.returncode:
                print(readiness.stdout, end='')
                print(readiness.stderr, end='', file=sys.stderr)
                return readiness.returncode
            if args.profile == 'ap':
                logged(['docker', 'run', '--rm', '--network', 'none', '-v', f'{ROOT}:/work', IMAGE,
                        'python3', 'scripts/probe_ap.py', '--name', args.name, '--esp-version', args.esp_version], 'run')
            else:
                options = ['--engine', selected_engine, '--esp-version', args.esp_version,
                           '--name', args.name, '--card', args.card,
                           '--seconds', args.seconds if args.seconds is not None else (300 if selected_engine == 'esp-emu' else 180)]
                if args.profile == 'file-transfer':
                    options.extend(['--scenario', 'web-ap'])
                else:
                    options.extend(['--book', args.book, '--scenario', args.scenario])
                if args.debug_remote:
                    options.append('--debug-remote')
                logged([sys.executable, str(ROOT / 'scripts/run_machine.py'), *map(str, options)], 'run')
            print(f"Results: {ROOT / 'results' / args.name}")
        elif args.command == 'firmware':
            options = ['--image', args.image, '--name', args.name, '--expect', args.expect,
                       '--chip', args.chip, '--seconds', args.seconds, '--esp-version', args.esp_version]
            if args.source:
                options.extend(['--source', args.source])
            script('run_firmware.py', *options)
        elif args.command == 'check':
            script('check_machine.py', args.first, args.second, '--require-activity-paint')
        elif args.command == 'test':
            execute([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'])
    except subprocess.CalledProcessError as error:
        return error.returncode
    except (OSError, ValueError) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
