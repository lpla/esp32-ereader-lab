"""Build bounded guest-resident RV32 input stubs for the pinned stock X4.

Runtime substitutions cover ADC/GPIO and (optionally) Arduino millis only.
RTC scratch is never used for heap/performance scenarios. No on-disk patching.
"""
import json
from pathlib import Path
import struct
import subprocess
from run_lab import ROOT, IMAGE

CODE, CONTROL, TABLE, LIMIT = 0x50001600, 0x50001bc0, 0x50001c00, 0x50001fd8


def jump(address):
    upper = (address + 0x800) >> 12
    lower = address - (upper << 12)
    return struct.pack('<III', (upper << 12) | (5 << 7) | 0x37,
                       ((lower & 4095) << 20) | (5 << 15) | (5 << 7) | 0x13,
                       (5 << 15) | 0x67)


def build(case, directory, buttons):
    actions = case['actions']
    if len(actions) * 16 > LIMIT - TABLE:
        raise ValueError('Schedule exceeds reserved RTC scratch')
    settings = dict(CONTROL=CONTROL, TABLE=TABLE, BOOT_CALLER=0x42008c3e,
                    TIMER=0x403835f2, DIV64=0x400008ac)
    (directory/'settings.inc').write_text(''.join(f'.equ {k}, {v}\n' for k,v in settings.items()))
    rel = directory.relative_to(ROOT)
    command = ['docker','run','--rm','--network','none','-v',f'{ROOT}:/work',IMAGE,
               'bash','-c',f'cd /work/{rel} && riscv64-linux-gnu-as -march=rv32im -mabi=ilp32 -o inputs.o /work/adapters/rv32_io.S && riscv64-linux-gnu-ld -m elf32lriscv -Ttext={hex(CODE)} -o inputs.elf inputs.o && riscv64-linux-gnu-objcopy -O binary inputs.elf inputs.bin && riscv64-linux-gnu-nm inputs.elf']
    result = subprocess.run(command,check=True,capture_output=True,text=True)
    symbols = {line.split()[2]:int(line.split()[0],16) for line in result.stdout.splitlines() if len(line.split())==3}
    data = (directory/'inputs.bin').read_bytes()
    if CODE + len(data) > CONTROL:
        raise ValueError('Stub exceeds RTC code scratch')
    table = b''.join(struct.pack('<IIII',buttons[a['button']][0],a['start'],a['end'],buttons[a['button']][1]) for a in actions)
    patches = [(0x420973e0, jump(symbols['gpio_stub'])),(0x420a1bd4,jump(symbols['adc_stub']))]
    if case['clock_substitution']:
        patches.append((0x4209523a,jump(symbols['millis_stub'])))
    script = ['python','import gdb,json,os',
              'class BootGPIO(gdb.Breakpoint):',
              ' def stop(self):',
              "  pin=int(gdb.parse_and_eval('$a0')); ra=int(gdb.parse_and_eval('$ra'))",
              "  gdb.execute('set $a0 = %d' % (0 if pin==6 or ra==0x42008c3e else 1))",
              "  gdb.execute('set $pc = $ra'); return False",
              "boot=BootGPIO('*0x420973e0',type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)",
              "ready=gdb.Breakpoint('*0x420a1bd4',type=gdb.BP_HARDWARE_BREAKPOINT,internal=True,temporary=True)",
              'end','continue','python','boot.delete()','from pathlib import Path',
              "d=Path(os.environ['LAB_RESULT_DIR'])",'guest=gdb.selected_inferior()',
              f"scratch=bytes(guest.read_memory({CODE}, {LIMIT-CODE}))",
              "if any(scratch): raise RuntimeError('RTC scratch is occupied; refuse input injection')",
              f'guest.write_memory({CODE},bytes.fromhex({data.hex()!r}))',
              f'guest.write_memory({CONTROL},bytes.fromhex({struct.pack("<III",0,len(actions),case["stop"]).hex()!r}))',
              f'guest.write_memory({TABLE},bytes.fromhex({table.hex()!r}))','patches=[]']
    for address, payload in patches:
        script += [f'original=bytes(guest.read_memory({address},12))',
                   "if not any(original): raise RuntimeError('Application text not mapped')",
                   f'guest.write_memory({address},bytes.fromhex({payload.hex()!r}))',
                   f'patches.append(dict(address=hex({address}),original=original.hex(),replacement={payload.hex()!r}))']
    script += ["(d/'runtime-input-substitutions.json').write_text(json.dumps(dict(patches=patches,rtc_start=hex("+str(CODE)+"),rtc_end=hex("+str(LIMIT)+"),performance_valid=False),indent=2))",'end']
    trap = CODE + data.index(struct.pack('<I', 0x00100073))
    script += [f'hbreak *{hex(trap)}']
    return '\n'.join(script)+'\n'
