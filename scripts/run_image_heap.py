"""Run actual historical dither classes on the guest heap in either C3 engine."""
import argparse
import hashlib
import json
import re
import subprocess
from run_lab import ROOT, IMAGE
from engines import engine,ESP_VERSIONS,DEFAULT_ESP


def records(log):
    result = []
    for line in log.splitlines():
        match = re.search(r'(IMAGE_HEAP|IMAGE_CASE) (\{.*\})', line)
        if match:
            result.append(dict(kind=match[1], **json.loads(match[2])))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--engine', choices=['qemu', 'esp-emu'], required=True)
    parser.add_argument('--label', choices=['base', 'head'], required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--esp-version', choices=ESP_VERSIONS, default=DEFAULT_ESP)
    args = parser.parse_args()
    executable,identity=engine(args.engine,args.esp_version)
    if not args.name.replace('-', '').isalnum():
        parser.error('Use letters, digits and hyphens')
    metadata = json.loads((ROOT / 'firmware/image-heap-provenance.json').read_text())
    project = ROOT / 'probes/image-heap'
    if hashlib.sha256((project / 'src/main.cpp').read_bytes()).hexdigest() != metadata['probe_sha256']:
        raise ValueError('Probe source changed since packaging')
    for entry in metadata['source']['files']:
        source = project / 'vendor' / entry['label'] / entry['file']
        if hashlib.sha256(source.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('Historical source changed since packaging')
    pin = metadata['images'][args.label]
    image = ROOT / 'firmware' / pin['file']
    elf = ROOT / 'probes/image-heap/.pio/build' / args.label / 'firmware.elf'
    for path, sha in ((image, pin['sha256']), (elf, pin['elf_sha256'])):
        if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise ValueError('Probe build differs from packaged provenance')
    directory = ROOT / 'results' / args.name
    directory.mkdir(exist_ok=False)
    (directory / 'input.json').write_text(json.dumps(dict(**metadata, label=args.label,
        engine=args.engine, engine_identity=identity, allocator_substituted=False, tone_adjustment='identity',
        component_scope='BitmapHelpers.h ditherers; not full PNG/BMP/XTC integration'), indent=2) + '\n')
    docker = ['docker', 'run', '--rm', '--network', 'none', '--cpus', '2', '--memory', '1g',
              '-v', f'{ROOT}:/work', IMAGE]
    if args.engine == 'esp-emu':
        command = docker + [str(executable.relative_to(ROOT)),
            '--chip', 'esp32c3', '--firmware', str(image.relative_to(ROOT)),
            '--timeout', '25s', '--exit-on', 'LAB_DONE', '--log-color', 'never']
        with (directory / 'uart.log').open('w') as out:
            completed = subprocess.run(command, stdout=out, stderr=subprocess.STDOUT, timeout=30)
        log = (directory / 'uart.log').read_text(errors='replace')
        code = completed.returncode
    else:
        nm = subprocess.check_output(docker + ['riscv64-linux-gnu-nm', '-C', str(elf.relative_to(ROOT))], text=True)
        serial = next(int(line.split()[0], 16) for line in nm.splitlines()
                      if line.endswith(' HardwareSerial::write(unsigned char const*, unsigned int)'))
        hook = (ROOT / 'scripts/c3-uart-observe.gdb').read_text().replace('0x420074e0', hex(serial))
        hook = hook.replace("if b'LAB_HEAP' in data and b'released' in data:return True", "if b'LAB_DONE' in data:return True")
        (directory / 'serial.gdb').write_text(hook)
        command = docker + ['python3', 'scripts/probe.py', 'qemu', str(image.relative_to(ROOT)), args.name,
            '--pre-file', str((directory / 'serial.gdb').relative_to(ROOT)), '--commands', 'continue',
            '--gdb-seconds', '25', '--emulator-seconds', '30']
        with (directory / 'runner.log').open('w') as out:
            subprocess.run(command, stdout=out, stderr=subprocess.STDOUT, check=True, timeout=35)
        code = json.loads((directory / 'status.json').read_text())['gdb_exit']
        log = (directory / 'guest.log').read_text(errors='replace') if (directory / 'guest.log').exists() else ''
    parsed = records(log)
    completed = code == 0 and 'LAB_DONE' in log and len([r for r in parsed if r['kind'] == 'IMAGE_CASE']) == 6
    result = dict(completed=completed, records=parsed, allocator_substituted=False,
                  physical_timing_valid=False, image_unchanged=hashlib.sha256(image.read_bytes()).hexdigest() == pin['sha256'])
    (directory / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    if not completed or not result['image_unchanged']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
