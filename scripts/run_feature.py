"""Execute a source-backed X4 feature case, preserving its claim and input schedule."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from run_lab import ROOT, IMAGE, X4_SHA
from render_display import render

BUTTONS = {'Back': 3512, 'Confirm': 2694, 'Left': 1493, 'Right': 5}


def compile_case(case):
    actions = case['actions']
    previous = 0
    for action in actions:
        if action['button'] not in BUTTONS or not previous <= action['start'] < action['end'] < case['stop']:
            raise ValueError('Invalid or overlapping front-button schedule')
        previous = action['end']
    template = (ROOT / 'scripts/x4-book-controls.gdb').read_text()
    first = template.index('if $front_reads > 50')
    last = template.index('end\nset {unsigned int}', first)
    schedule = ''.join(f"if $front_reads > {a['start']} && $front_reads <= {a['end']}\nset $raw_adc = {BUTTONS[a['button']]}\nend\n" for a in actions)
    template = template[:first] + schedule + template[last:]
    return template.replace('if $front_reads < 330', f"if $front_reads < {case['stop']}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument('case', type=Path)
    p.add_argument('--card', type=Path, required=True)
    p.add_argument('--prefix', required=True)
    a = p.parse_args()
    if not a.prefix.replace('-', '').isalnum():p.error('prefix must contain letters, digits, hyphens')
    case = json.loads(a.case.read_text())
    catalog = json.loads((ROOT / 'cases/catalog.json').read_text())
    if case['source'] not in catalog['sources'] or not case.get('expected'):
        raise ValueError('Every case needs a catalogued source and semantic expectation')
    ota = (ROOT / 'downloads/x4_en_v5.1.6_ota.bin').read_bytes()
    if hashlib.sha256(ota).hexdigest() != X4_SHA:raise ValueError('Unsupported stock application')
    flash = ROOT / 'firmware/x4-app-x3-layout.bin'
    for offset in (0x10000, 0x780000):
        if flash.read_bytes()[offset:offset+len(ota)] != ota:raise ValueError('Application slots differ')
    d = ROOT / 'results' / a.prefix;d.mkdir(exist_ok=False)
    import shutil
    shutil.copyfile(a.card, d/'card.img')
    (d/'case.json').write_text(json.dumps(case,indent=2)+'\n')
    (d/'inputs.gdb').write_text(compile_case(case))
    (d/'input.json').write_text(json.dumps(dict(card_source_sha256=hashlib.sha256(a.card.read_bytes()).hexdigest(),
        firmware_sha256=hashlib.sha256(flash.read_bytes()).hexdigest(),performance_valid=False),indent=2)+'\n')
    hooks = 'source /work/scripts/x4-sd.gdb;source /work/scripts/x4-display-capture.gdb;'
    if case['clock_substitution']:hooks += 'source /work/scripts/x4-longpress-clock.gdb;'
    cmd = ['docker','run','--rm','--network','none','--cpus','2','--memory','1g','-v',f'{ROOT}:/work',IMAGE,
           'python3','scripts/probe.py','qemu','firmware/x4-app-x3-layout.bin',a.prefix,
           '--card',f'/work/results/{a.prefix}/card.img','--pre-file',f'results/{a.prefix}/inputs.gdb',
           '--pre-commands',hooks,'--break-at','0x420087d0','--commands','print $front_reads',
           '--gdb-seconds','105','--emulator-seconds','125']
    with (d/'runner.log').open('w') as out:completed=subprocess.run(cmd,cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,timeout=120)
    writes=render(d) if (d/'display-writes.json').exists() else 0
    status=json.loads((d/'status.json').read_text()) if (d/'status.json').exists() else {}
    print(json.dumps(dict(case=case['id'],command_exit=completed.returncode,status=status,
                         display_writes=writes,expected=case['expected'],screen=str(d/'screen.png'),
                         feature_success_requires_image_inspection=True),indent=2))
    if completed.returncode or status.get('gdb_exit')!=0:sys.exit(1)


if __name__=='__main__':main()
