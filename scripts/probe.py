"""Run one emulator and automate a bounded GDB inspection inside Docker."""
from pathlib import Path
import argparse
import json
import signal
import os
import hashlib
import subprocess
import time
import threading
from engines import engine, ESP_VERSIONS, DEFAULT_ESP
from diagnostics import diagnostics

ROOT = Path('/work')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('engine', choices=['esp-emu', 'qemu'])
    parser.add_argument('image')
    parser.add_argument('name')
    parser.add_argument('--esp-version', choices=ESP_VERSIONS, default=DEFAULT_ESP)
    parser.add_argument('--debug-remote', action='store_true', help='Record GDB packets for bus-warning attribution')
    parser.add_argument('--snapshot-startup', action='store_true')
    parser.add_argument('--crosspoint-http',type=Path,help='Upload/download these EPUB bytes through the actual guest AP')
    parser.add_argument('--break-at')
    parser.add_argument('--elf', type=Path, help='Load an ELF before connecting; use --strip-debug output with Ubuntu GDB 15')
    parser.add_argument('--card', type=Path)
    parser.add_argument('--commands', default='')
    parser.add_argument('--pre-commands', default='')
    parser.add_argument('--pre-file', type=Path)
    parser.add_argument('--post-file', type=Path)
    parser.add_argument('--seconds', type=float, default=3)
    parser.add_argument('--gdb-seconds', type=float, default=15)
    parser.add_argument('--emulator-seconds', type=float, default=20)
    args = parser.parse_args()
    executable, engine_identity = engine(args.engine, args.esp_version)
    image_hash = hashlib.sha256(Path(args.image).read_bytes()).hexdigest()
    if args.engine == 'esp-emu':
        command = [str(executable), '--chip', 'esp32c3', '--firmware', args.image,
                   '--gdb', '1234', '--timeout', f'{args.emulator_seconds:g}s',
                   '--net', 'user,restrict=yes', '--log-color', 'never']
        if args.break_at or args.pre_commands or args.pre_file:
            command += ['--gdb-halt']
        if args.crosspoint_http:
            if args.esp_version!='0.48.0':parser.error('Full AP workflow requires esp-emulator 0.48.0')
            command[command.index('user,restrict=yes')]='user,restrict=yes,hostfwd=tcp:127.0.0.1:18080-:80'
            command+=['--wifi-fw-ap-password','']
    else:
        command = [str(executable), '-nographic', '-monitor', 'none', '-icount', '3',
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
        if args.crosspoint_http:
            from crosspoint_http import exercise
            threading.Thread(target=exercise,args=(result_dir,args.crosspoint_http.read_bytes(),args.gdb_seconds-10),daemon=True).start()
        try:
            # Connecting and disconnecting a readiness socket resumes ESP-EMU.
            # Let GDB own the first connection so reset-state injection is valid.
            time.sleep(0.3 if args.break_at or args.pre_commands or args.pre_file else args.seconds)
            commands = ['set pagination off', 'set confirm off', 'set architecture riscv:rv32']
            if args.debug_remote:
                commands += ['set debug remote 1']
            if args.elf:
                commands += [f'file {args.elf}', 'set trust-readonly-sections on']
            commands += ['target remote :1234']
            commands += [c for c in args.pre_commands.split(';') if c]
            if args.pre_file:
                commands += args.pre_file.read_text().splitlines()
            if args.break_at:
                commands += [f'hbreak *{args.break_at}', 'continue']
            if args.snapshot_startup or not args.pre_file:
                commands += ['info registers', 'x/12i $pc', 'x/8wx 0x600c0040',
                             'x/4wx 0x6000403c']
            commands += [c for c in args.commands.split(';') if c]
            if args.post_file:
                commands += args.post_file.read_text().splitlines()
            # Kill while GDB still owns the stopped guest. Detach resumes it
            # after removing transport breakpoints and can manufacture panics.
            commands += ['python', 'import os,signal,time',
                         "os.kill(int(os.environ['LAB_EMULATOR_PID']), signal.SIGTERM)",
                         'time.sleep(0.1)', 'end', 'quit']
            script = result_dir / 'probe.gdb'
            script.write_text('\n'.join(commands) + '\n')
            with (result_dir / 'gdb.log').open('w') as out:
                try:
                    gdb = subprocess.Popen(['gdb-multiarch', '-q', '-nx', '-batch',
                                            '-x', str(script)], stdout=out,
                                           stderr=subprocess.STDOUT,
                                           env={**os.environ, 'LAB_RESULT_DIR': str(result_dir),
                                                'LAB_EMULATOR_PID': str(process.pid),
                                                **({'LAB_CARD_IMAGE': str(args.card)} if args.card else {})})
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
            # On a debugger error, terminate before its connection goes away.
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(2)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait()
            after_hash = hashlib.sha256(Path(args.image).read_bytes()).hexdigest()
            (result_dir / 'status.json').write_text(json.dumps({
                'gdb_exit': code, 'image_sha256': image_hash,
                'engine': engine_identity,
                'termination': 'terminate emulator before debugger disconnect' if code==0 else 'bounded debugger failure; forced host cleanup',
                'diagnostics': diagnostics((result_dir/'uart.log').read_text(errors='replace'),
                    (result_dir/'guest.log').read_text(errors='replace') if (result_dir/'guest.log').exists() else '',
                    (result_dir/'gdb.log').read_text(errors='replace') if args.debug_remote else ''),
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
