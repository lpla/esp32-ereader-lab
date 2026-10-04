"""Run a pin-checked full CrossPoint reader with real guest heap and SD filesystem."""
import argparse,hashlib,json,shutil,subprocess
from pathlib import Path
from run_lab import ROOT,IMAGE
from render_display import render
from prepare_machine import HEAD,SDK


def main():
 p=argparse.ArgumentParser();p.add_argument('--engine',choices=['qemu','esp-emu'],required=True)
 p.add_argument('--name',required=True);p.add_argument('--card',type=Path,required=True)
 p.add_argument('--book',help='Absolute SD path to resume; omitted means Home')
 p.add_argument('--scenario',choices=['read','turn-exit'],default='read')
 p.add_argument('--seconds',type=int,default=90);a=p.parse_args()
 if not a.name.replace('-','').isalnum():p.error('Use letters, digits and hyphens')
 if a.book and (not a.book.startswith('/') or '\n' in a.book):p.error('Book must be an absolute SD path')
 if not 5<=a.seconds<=300:p.error('Run budget must be 5–300 seconds')
 manifest=json.loads((ROOT/'firmware/crosspoint-machine.json').read_text())
 elf=ROOT/'tools/crosspoint-machine/.pio/build/default/firmware.elf'
 flash=ROOT/'firmware/crosspoint-machine.bin'
 if not manifest.get('abi_layout_verified') or manifest['crosspoint']!=HEAD or manifest['sdk']!=SDK or hashlib.sha256(flash.read_bytes()).hexdigest()!=manifest['flash_sha256'] or hashlib.sha256(elf.read_bytes()).hexdigest()!=manifest['elf_sha256']:
  raise ValueError('Unsupported build ABI: derive and verify adapter addresses for this ELF first')
 d=ROOT/'results'/a.name;d.mkdir(exist_ok=False)
 shutil.copyfile(a.card,d/'card.img')
 (d/'input.json').write_text(json.dumps(dict(**manifest,card_source_sha256=hashlib.sha256(a.card.read_bytes()).hexdigest(),
  resumed_book=a.book,scenario=a.scenario,simulated_boot='AfterFlash',diagnostic_override='lastMemPrint after render',
  clock_substitution=False,physical_performance_valid=False,allocator_substituted=False,
  substitutions=['SD sector transport including card begin','ADC/GPIO','panel SPI/BUSY','USB TX']),indent=2)+'\n')
 if a.book:
  (d/'state-seed.json').write_text(json.dumps(dict(openEpubPath=a.book,lastSleepFromReader=True,showBootScreen=True,readerActivityLoadCount=0)))
  rel=d.relative_to(ROOT)
  subprocess.run(['docker','run','--rm','--network','none','-v',f'{ROOT}:/work',IMAGE,'bash','-c',
   f'mmd -i {rel}/card.img@@1048576 ::/.crosspoint; mcopy -o -i {rel}/card.img@@1048576 {rel}/state-seed.json ::/.crosspoint/state.json'],check=True)
 activity='EpubReader' if a.book and a.scenario=='read' else 'Home'
 cmd=['docker','run','--rm','--network','none','--cpus','2','--memory','1g','-e',f'LAB_CHECKPOINT_ACTIVITY={activity}',
      '-e',f'LAB_MACHINE_SCENARIO={a.scenario}','-v',f'{ROOT}:/work',IMAGE,'python3','scripts/probe.py',a.engine,'firmware/crosspoint-machine.bin',a.name,
      '--card',f'results/{a.name}/card.img','--pre-file','scripts/crosspoint-board.gdb','--commands','continue',
      '--gdb-seconds',str(a.seconds),'--emulator-seconds',str(a.seconds+10)]
 with (d/'runner.log').open('w') as f:subprocess.run(cmd,check=True,stdout=f,stderr=subprocess.STDOUT,timeout=a.seconds+15)
 if (d/'display-writes.json').exists():render(d)
 status=json.loads((d/'status.json').read_text());logs=(d/'guest.log').read_text() if (d/'guest.log').exists() else ''
 completed=status['gdb_exit']==0 and (d/'checkpoint.json').exists() and (not a.book or 'Rendered page in' in logs)
 if a.scenario=='turn-exit':
  checkpoint=json.loads((d/'checkpoint.json').read_text()) if (d/'checkpoint.json').exists() else {}
  completed=completed and checkpoint.get('rendered_pages',0)>=2 and 'Entering activity: Home' in logs
 verdict=dict(guest_checkpoint_completed=completed,semantic_page_requires_image_inspection=True,
              physical_performance_valid=False,allocator_substituted=False)
 (d/'verdict.json').write_text(json.dumps(verdict,indent=2)+'\n');print(json.dumps(verdict,indent=2))
 if not completed:raise SystemExit(1)


if __name__=='__main__':main()
