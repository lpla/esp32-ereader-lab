"""Container side of the serial test runner; no addresses from a board adapter."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from engines import engine
from firmware_contract import image_layout, verdict

ROOT = Path('/work')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*', args.name):
        parser.error('Invalid result name')
    directory = ROOT / 'results' / args.name
    pin = json.loads((directory / 'input.json').read_text())
    if (directory / 'result.json').exists() or (directory / 'uart.log').exists():
        raise ValueError('This run already has output; preserve it and choose a new name')
    image = directory / 'flash.bin'
    data = image.read_bytes()
    if hashlib.sha256(data).hexdigest() != pin['image_sha256']:
        raise ValueError('Run image differs from recorded input')
    image_layout(data, pin['chip'])
    executable, identity = engine('esp-emu', pin['esp_version'])
    command = [str(executable), '--chip', pin['chip'], '--firmware', str(image),
               '--timeout', f"{pin['seconds']}s", '--exit-on', pin['completion_marker'],
               '--net', 'user,restrict=yes', '--log-color', 'never']
    if pin['esp_version'] != '0.45.0':
        command.extend(['--wifi-fw-ap-password', ''])
    (directory / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
    timed_out = False
    with (directory / 'uart.log').open('x') as output:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT)
        try:
            process.wait(timeout=pin['seconds'] + 10)
        except subprocess.TimeoutExpired:
            timed_out = True
        finally:
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
    result = verdict((directory / 'uart.log').read_text(errors='replace'), pin['completion_marker'],
                     process.returncode, timed_out)
    result.update(engine=identity, run_image_after_sha256=hashlib.sha256(image.read_bytes()).hexdigest())
    (directory / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
