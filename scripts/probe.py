"""Run one emulator and automate a bounded GDB inspection inside Docker."""
from pathlib import Path
import argparse
import json
import signal
import os
import hashlib
import subprocess
import time

ROOT = Path('/work')
ESP = ROOT / 'tools/esp-emu-0.45.0-x86_64-unknown-linux-gnu/esp-emu'
QEMU = ROOT / 'tools/qemu/bin/qemu-system-riscv32'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('engine', choices=['esp-emu', 'qemu'])
    parser.add_argument('image')
    parser.add_argument('name')
    parser.add_argument('--break-at')
    parser.add_argument('--commands', default='')
    parser.add_argument('--pre-commands', default='')
    parser.add_argument('--pre-file', type=Path)
    parser.add_argument('--post-file', type=Path)
    parser.add_argument('--seconds', type=float, default=3)
    parser.add_argument('--gdb-seconds', type=float, default=15)
    parser.add_argument('--emulator-seconds', type=float, default=20)
    args = parser.parse_args()
    image_hash = hashlib.sha256(Path(args.image).read_bytes()).hexdigest()
    if args.engine == 'esp-emu':
        command = [str(ESP), '--chip', 'esp32c3', '--firmware', args.image,
                   '--gdb', '1234', '--timeout', f'{args.emulator_seconds:g}s',
                   '--net', 'user,restrict=yes', '--log-color', 'never']
        if args.break_at or args.pre_commands or args.pre_file:
            command += ['--gdb-halt']
    else:
        command = [str(QEMU), '-nographic', '-monitor', 'none', '-icount', '3',
                   '-machine', 'esp32c3', '-drive',
                   f'file={args.image},if=mtd,format=raw', '-snapshot',
                   '-gdb', 'tcp:127.0.0.1:1234']
        if args.break_at or args.pre_commands or args.pre_file:
            command += ['-S']
    result_dir = ROOT / 'results' / args.name
    result_dir.mkdir(exist_ok=True)
    (result_dir / 'command.json').write_text(json.dumps(command, indent=2))
    with (result_dir / 'uart.log').open('w') as log:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                                   stdout=log, stderr=subprocess.STDOUT)
        try:
            # Connecting and disconnecting a readiness socket resumes ESP-EMU.
            # Let GDB own the first connection so reset-state injection is valid.
            time.sleep(0.3 if args.break_at or args.pre_commands or args.pre_file else args.seconds)
            commands = ['set pagination off', 'set confirm off',
                        'set architecture riscv:rv32', 'target remote :1234']
            commands += [c for c in args.pre_commands.split(';') if c]
            if args.pre_file:
                commands += args.pre_file.read_text().splitlines()
            if args.break_at:
                commands += [f'hbreak *{args.break_at}', 'continue']
            commands += ['info registers', 'x/12i $pc', 'x/8wx 0x600c0040',
                         'x/4wx 0x6000403c']
            commands += [c for c in args.commands.split(';') if c]
            if args.post_file:
                commands += args.post_file.read_text().splitlines()
            commands += ['detach', 'quit']
            script = result_dir / 'probe.gdb'
            script.write_text('\n'.join(commands) + '\n')
            with (result_dir / 'gdb.log').open('w') as out:
                try:
                    gdb = subprocess.Popen(['gdb-multiarch', '-q', '-nx', '-batch',
                                            '-x', str(script)], stdout=out,
                                           stderr=subprocess.STDOUT,
                                           env={**os.environ, 'LAB_RESULT_DIR': str(result_dir)})
                    code = gdb.wait(args.gdb_seconds)
                except subprocess.TimeoutExpired:
                    # GDB interrupts the running guest, then executes the
                    # remaining snapshot commands. This is a bounded probe,
                    # never evidence that the target completed its scenario.
                    gdb.send_signal(signal.SIGINT)
                    try:
                        gdb.wait(3)
                        code = 'interrupted_for_snapshot'
                    except subprocess.TimeoutExpired:
                        gdb.kill()
                        gdb.wait()
                        code = 'timeout'
            time.sleep(0.5)
            after_hash = hashlib.sha256(Path(args.image).read_bytes()).hexdigest()
            (result_dir / 'status.json').write_text(json.dumps({
                'gdb_exit': code, 'image_sha256': image_hash,
                'image_unchanged': after_hash == image_hash,
                'timeout_is_not_feature_success': True}, indent=2) + '\n')
            print(args.name, 'GDB result:', code, flush=True)
        finally:
            process.terminate()
            try:
                process.wait(2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == '__main__':
    main()
