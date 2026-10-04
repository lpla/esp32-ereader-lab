"""Inspect the pinned Licorice S3 RTC wait without a host Xtensa GDB install.

The optional wake experiment skips one verified polling block. It is diagnostic,
not a real wake/reset implementation and never a feature or performance pass.
"""
import argparse
import hashlib
import json
from pathlib import Path
import socket
import struct
import subprocess
import time

ROOT = Path('/work')


class Remote:
    def __init__(self, stream):
        self.stream = stream

    def byte(self):
        value = self.stream.recv(1)
        if not value:
            raise EOFError('Emulator disconnected')
        return value

    def request(self, command):
        data = command.encode()
        self.stream.sendall(b'$' + data + b'#' + f'{sum(data) % 256:02x}'.encode())
        while self.byte() != b'$':
            pass
        payload = bytearray()
        while (value := self.byte()) != b'#':
            payload.extend(value)
        checksum = self.byte() + self.byte()
        if int(checksum, 16) != sum(payload) % 256:
            raise ValueError('Invalid RSP checksum')
        self.stream.sendall(b'+')
        return payload.decode()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', required=True)
    parser.add_argument('--wake-experiment', action='store_true')
    args = parser.parse_args()
    if not args.name.replace('-', '').isalnum():
        parser.error('Use letters, digits and hyphens')
    image = ROOT / 'firmware/x4pro-licorice-padded.bin'
    pin = json.loads((ROOT / 'firmware/x4pro-licorice-padded.json').read_text())
    original = image.read_bytes()
    if hashlib.sha256(original).hexdigest() != pin['sha256']:
        raise ValueError('Unknown S3 image')
    directory = ROOT / 'results' / args.name
    directory.mkdir(exist_ok=False)
    command = [str(ROOT / 'tools/esp-emu-0.45.0-x86_64-unknown-linux-gnu/esp-emu'),
               '--chip', 'esp32s3', '--firmware', str(image), '--psram-size', '8M',
               '--gdb', '1234', '--gdb-halt', '--timeout', '25s', '--log-color', 'never']
    (directory / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
    transactions = []
    status = dict(image_sha256=pin['sha256'], feature_validated=False,
                  wake_experiment=args.wake_experiment, rtc_wait_reached=False)
    with (directory / 'uart.log').open('w') as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        stream = None
        try:
            time.sleep(0.5)
            stream = socket.create_connection(('127.0.0.1', 1234), timeout=5)
            stream.settimeout(20)
            remote = Remote(stream)

            def request(value):
                reply = remote.request(value)
                transactions.append(dict(command=value, reply=reply))
                return reply

            request('qSupported')
            status['target_xml'] = request('qXfer:features:read:target.xml:0,ffff')
            if request('Z1,4037d1c0,1') != 'OK':
                raise ValueError('Breakpoint installation failed')
            request('c')
            registers = request('g')
            # S3 g-packet starts with PC; do not interpret its AR window layout
            # using the erroneous RV32 target XML advertised by this release.
            if struct.unpack('<I', bytes.fromhex(registers[:8]))[0] != 0x4037d1c0:
                raise ValueError('Unexpected S3 stop')
            if request('m4037d1c0,3') != '922a00':
                raise ValueError('Unknown Xtensa polling instruction')
            status['rtc_wait_reached'] = True
            status['rtc_raw'] = request('m60008044,4')
            if args.wake_experiment:
                # Advance past the poll and status read, retaining all app bytes.
                if request('P0=cfd13740') != 'OK':
                    raise ValueError('PC write failed')
                request('z1,4037d1c0,1')
                request('c')
        except (TimeoutError, EOFError) as error:
            status['bounded_stop'] = type(error).__name__
        finally:
            if stream:
                stream.close()
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
    status['image_unchanged'] = original == image.read_bytes()
    (directory / 'rsp.json').write_text(json.dumps(transactions, indent=2) + '\n')
    (directory / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
    print(json.dumps(status, indent=2))
    if not status['rtc_wait_reached'] or not status['image_unchanged']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
