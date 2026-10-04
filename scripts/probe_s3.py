"""Record bounded X4 Pro bring-up, without treating boot or timeout as a feature pass."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from prepare import inspect

ROOT = Path('/work')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--image', required=True, type=Path)
    p.add_argument('--name', required=True)
    a = p.parse_args()
    if not a.name.replace('-', '').isalnum():
        p.error('name must contain letters, digits, hyphens')
    data = a.image.read_bytes()
    if inspect(data)['images'][0]['chip_id'] != 9:
        p.error('Expected ESP32-S3 image')
    d = ROOT / 'results' / a.name
    d.mkdir(exist_ok=False)
    cmd = [str(ROOT / 'tools/esp-emu-0.45.0-x86_64-unknown-linux-gnu/esp-emu'),
        '--chip', 'esp32s3', '--firmware', str(a.image), '--psram-size', '8M',
        '--net', 'user,restrict=yes', '--timeout', '20s', '--log-color', 'never']
    (d / 'command.json').write_text(json.dumps(cmd, indent=2) + '\n')
    with (d / 'uart.log').open('w') as out:
        completed = subprocess.run(cmd, stdout=out, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL, timeout=25)
    log = (d / 'uart.log').read_text(errors='replace')
    status = dict(exit=completed.returncode, engine='esp-emu v0.45.0',
        image_sha256=hashlib.sha256(data).hexdigest(),
        image_unchanged=data == a.image.read_bytes(), layout=inspect(data),
        watchdog_panics=log.count('Interrupt wdt timeout'),
        emulator_timeout='Timeout reached' in log,
        feature_verdict='blocked before usable reader; boot is not feature validation',
        gdb_substitutions=False, psram_model_bytes=8 * 1024 * 1024)
    (d / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
    print(json.dumps(status, indent=2))


if __name__ == '__main__':
    main()
