"""Run a pin-checked full CrossPoint reader with real guest heap and SD filesystem."""
import argparse,hashlib,json,shutil,subprocess
from pathlib import Path
from run_lab import ROOT,IMAGE
from render_display import render
from prepare_machine import HEAD,SDK
from engines import ESP_VERSIONS,DEFAULT_ESP
from diagnostics import diagnostics
from check_machine import inspect


def main():
 p=argparse.ArgumentParser();p.add_argument('--engine',choices=['qemu','esp-emu'],required=True)
 p.add_argument('--name',required=True);p.add_argument('--card',type=Path,required=True)
 p.add_argument('--esp-version',choices=ESP_VERSIONS,default=DEFAULT_ESP)
 p.add_argument('--debug-remote',action='store_true')
 p.add_argument('--symbols',action='store_true',help='Load the verified stripped symbol ELF for remote register access')
 p.add_argument('--book',help='Absolute SD path to resume; omitted means Home')
 p.add_argument('--scenario',choices=['read','turn-exit','web-ap'],default='read')
 p.add_argument('--seconds',type=int,default=90);a=p.parse_args()
 if not a.name.replace('-','').isalnum():p.error('Use letters, digits and hyphens')
 if a.book and (not a.book.startswith('/') or '\n' in a.book):p.error('Book must be an absolute SD path')
 if not 5<=a.seconds<=300:p.error('Run budget must be 5–300 seconds')
 if a.scenario=='web-ap' and (a.engine!='esp-emu' or a.esp_version!='0.48.0' or a.book):p.error('AP workflow requires esp-emulator 0.48.0 and a fresh Home card')
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
  debugger_symbol_elf=a.symbols,
  adapter_sha256=hashlib.sha256((ROOT/'scripts/crosspoint-board.gdb').read_bytes()).hexdigest(),
  substitutions=['SD sector transport including card begin','ADC/GPIO','panel SPI/BUSY','USB TX']),indent=2)+'\n')
 if a.book:
  (d/'state-seed.json').write_text(json.dumps(dict(openEpubPath=a.book,lastSleepFromReader=True,showBootScreen=True,readerActivityLoadCount=0)))
  rel=d.relative_to(ROOT)
  subprocess.run(['docker','run','--rm','--network','none','-v',f'{ROOT}:/work',IMAGE,'bash','-c',
   f'mmd -i {rel}/card.img@@1048576 ::/.crosspoint; mcopy -o -i {rel}/card.img@@1048576 {rel}/state-seed.json ::/.crosspoint/state.json'],check=True)
 book_activity='XtcReader' if a.book and a.book.lower().endswith(('.xtc','.xtch')) else 'EpubReader'
 render_marker='Rendered page ' if book_activity=='XtcReader' else 'Rendered page in'
 activity='CrossPointWebServer' if a.scenario=='web-ap' else book_activity if a.book and a.scenario=='read' else 'Home'
 cmd=['docker','run','--rm','--network','none','--cpus','2','--memory','1g','-e',f'LAB_CHECKPOINT_ACTIVITY={activity}',
      '-e',f'LAB_MACHINE_SCENARIO={a.scenario}','-v',f'{ROOT}:/work',IMAGE,'python3','scripts/probe.py',a.engine,'firmware/crosspoint-machine.bin',a.name,
      '--card',f'results/{a.name}/card.img','--pre-file','scripts/crosspoint-board.gdb','--commands','continue',
      '--esp-version',a.esp_version,
      '--gdb-seconds',str(a.seconds),'--emulator-seconds',str(a.seconds+10)]
 if a.debug_remote:cmd+=['--debug-remote']
 if a.scenario=='web-ap':
  payload=ROOT/'fixtures/generated/alpha.epub'
  pin=json.loads((d/'input.json').read_text());pin['http_payload_sha256']=hashlib.sha256(payload.read_bytes()).hexdigest()
  (d/'input.json').write_text(json.dumps(pin,indent=2)+'\n')
  nm=subprocess.check_output(['docker','run','--rm','--network','none','-v',f'{ROOT}:/work',IMAGE,'riscv64-linux-gnu-nm','-C',str(elf.relative_to(ROOT))],text=True)
  pin['symbols']['esp_restart']=next(int(line.split()[0],16) for line in nm.splitlines() if line.endswith(' esp_restart'))
  (d/'input.json').write_text(json.dumps(pin,indent=2)+'\n')
  cmd+=['--crosspoint-http','fixtures/generated/alpha.epub']
 if a.symbols:
  stripped=d/'symbols.elf'
  subprocess.run(['docker','run','--rm','--network','none','-v',f'{ROOT}:/work',IMAGE,
   'riscv64-linux-gnu-objcopy','--strip-debug',str(elf.relative_to(ROOT)),str(stripped.relative_to(ROOT))],check=True)
  cmd+=['--elf',str(stripped.relative_to(ROOT))]
 with (d/'runner.log').open('w') as f:subprocess.run(cmd,check=True,stdout=f,stderr=subprocess.STDOUT,timeout=a.seconds+15)
 if (d/'display-writes.json').exists():render(d)
 status=json.loads((d/'status.json').read_text());logs=(d/'guest.log').read_text() if (d/'guest.log').exists() else ''
 completed=status['gdb_exit']==0 and (d/'checkpoint.json').exists() and (not a.book or render_marker in logs)
 if a.scenario=='turn-exit':
  checkpoint=json.loads((d/'checkpoint.json').read_text()) if (d/'checkpoint.json').exists() else {}
  completed=completed and checkpoint.get('rendered_pages',0)>=2 and 'Entering activity: Home' in logs
 if a.scenario=='web-ap':
  http=json.loads((d/'http-result.json').read_text()) if (d/'http-result.json').exists() else {}
  checkpoint=json.loads((d/'checkpoint.json').read_text()) if (d/'checkpoint.json').exists() else {}
  completed=completed and http.get('completed',False) and checkpoint.get('reason')=='guest requested restart after AP exit'
 checkpoint=json.loads((d/'checkpoint.json').read_text()) if (d/'checkpoint.json').exists() else {}
 completed=completed and checkpoint.get('protocol')==2 and checkpoint.get('display_after_activity_entered') is True and checkpoint.get('activity')==activity
 if completed and (a.book or a.scenario=='web-ap'):
  inspect(d) # Reject failed SD operations, stale paints or mismatched HTTP bytes.
 verdict=dict(guest_checkpoint_completed=completed,semantic_page_requires_image_inspection=True,
              diagnostics=status['diagnostics'],
              physical_performance_valid=False,allocator_substituted=False)
 (d/'verdict.json').write_text(json.dumps(verdict,indent=2)+'\n');print(json.dumps(verdict,indent=2))
 if not completed:raise SystemExit(1)


if __name__=='__main__':main()
