"""Run the pinned binary-emulation experiments and return JSON artifact paths."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import shutil
import sys

from render_display import render

ROOT = Path(__file__).resolve().parents[1]
IMAGE = 'crosspoint-esp-emulation-lab:2026-10-04'
X4_SHA = 'be3dd62437914ffe7ac23d2713cf63f97f7eccc06fd1cf4b0924e7cce9878822'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--engine', choices=['qemu', 'esp-emu', 'both'], default='qemu')
    parser.add_argument('--scenario', choices=['baseline', 'right', 'settings', 'language', 'read', 'folder', 'book', 'book-next', 'book-menu', 'book-page'], default='right')
    parser.add_argument('--prefix', default='rerun')
    parser.add_argument('--card', type=Path, help='source SD image; copied for each run')
    args = parser.parse_args()
    if args.scenario in ('folder', 'book', 'book-next', 'book-menu', 'book-page') and not args.card:
        parser.error('SD scenarios require --card cards/base.img')
    if args.card and args.engine != 'qemu':
        parser.error('SD adapter is currently validated only with QEMU')
    (ROOT / 'results').mkdir(exist_ok=True)
    if not args.prefix.replace('-', '').replace('_', '').isalnum():
        parser.error('prefix must contain only letters, numbers, hyphens or underscores')
    engines = ['qemu', 'esp-emu'] if args.engine == 'both' else [args.engine]
    results = []
    for engine in engines:
        fixtures = ['x3-stock', 'x3-app0-empty-otadata', 'x4-app-x3-layout'] if args.scenario == 'baseline' else ['x4-app-x3-layout']
        for fixture in fixtures:
            name = f'{args.prefix}-{engine}-{fixture}-{args.scenario}'
            directory = ROOT / 'results' / name
            if directory.exists():
                raise RuntimeError(f'Result already exists; choose another --prefix: {name}')
            command = ['docker', 'run', '--rm', '--network', 'none', '--cpus', '2',
                       '--memory', '1g', '-v', f'{ROOT}:/work', IMAGE, 'python3',
                       'scripts/probe.py', engine, f'firmware/{fixture}.bin', name]
            if args.card:
                directory.mkdir()
                shutil.copyfile(args.card, directory / 'card.img')
                command += ['--card', f'/work/results/{name}/card.img']
            if args.scenario != 'baseline':
                ota = (ROOT / 'downloads/x4_en_v5.1.6_ota.bin').read_bytes()
                assert hashlib.sha256(ota).hexdigest() == X4_SHA
                flash = (ROOT / 'firmware/x4-app-x3-layout.bin').read_bytes()
                for offset in (0x10000, 0x780000):
                    assert flash[offset:offset + len(ota)] == ota
                script = 'x4-input.gdb' if args.scenario == 'right' else f'x4-{args.scenario}.gdb'
                command += ['--pre-file', f'scripts/{script}', '--pre-commands',
                            ('source /work/scripts/x4-sd.gdb;' if args.card else '') +
                            'source /work/scripts/x4-display-capture.gdb',
                            '--break-at', '0x420087d0', '--commands',
                            'print $front_reads;print $gpio_calls;print $adc_calls',
                            '--gdb-seconds', '70' if engine == 'esp-emu' else ('55' if args.card else '16'),
                            '--emulator-seconds', '90']
            completed = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True, timeout=85)
            status_path = directory / 'status.json'
            status = json.loads(status_path.read_text()) if status_path.exists() else {}
            writes = render(directory) if (directory / 'display-writes.json').exists() else 0
            results.append(dict(engine=engine, fixture=fixture, scenario=args.scenario,
                                command_exit=completed.returncode, status=status,
                                driver_image_writes=writes, directory=str(directory),
                                screen=str(directory / 'screen.png') if writes else None,
                                diagnostic_hardware_substitution=args.scenario != 'baseline',
                                sd_transport_substitution=bool(args.card),
                                feature_success_requires_image_inspection=True))
    report = ROOT / 'results' / f'{args.prefix}-summary.json'
    report.write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps(results, indent=2))
    if any(r['command_exit'] != 0 or not r['status'].get('image_unchanged', False)
           or r['status'].get('gdb_exit') != 0 for r in results):
        sys.exit(1)


if __name__ == '__main__':
    main()
