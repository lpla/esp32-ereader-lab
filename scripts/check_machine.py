"""Compare completed guest checkpoints; never infer physical speed from timers."""
import argparse,collections,json,re
from pathlib import Path
from diagnostics import diagnostics


def inspect(directory):
 status=json.loads((directory/'status.json').read_text())
 checkpoint=json.loads((directory/'checkpoint.json').read_text()) if (directory/'checkpoint.json').exists() else {}
 if status['gdb_exit']!=0 or not status['image_unchanged'] or not checkpoint:
  raise ValueError('Guest checkpoint did not complete')
 log=(directory/'guest.log').read_text()
 inputs=json.loads((directory/'input.json').read_text())
 web=inputs.get('scenario')=='web-ap'
 lines=re.findall(r'\[MEM\] Free: (\d+) bytes, Total: (\d+) bytes, Min Free: (\d+) bytes, MaxAlloc: (\d+) bytes',log)
 if not lines:raise ValueError('Missing guest heap diagnostic')
 heap=dict(zip(('free','total','minimum','largest'),map(int,lines[-1])))
 if not 0<heap['largest']<=heap['free']<=heap['total'] or heap['minimum']>heap['free']:
  raise ValueError('Inconsistent heap diagnostic')
 renders=log.count('Rendered page in')+len(re.findall(r'\[XTR\] Rendered page \d+/\d+',log))
 if not web and (checkpoint.get('rendered_pages',renders)<1 or renders<1):
  raise ValueError('No reader render completed')
 if checkpoint.get('scenario')=='turn-exit' and (checkpoint['rendered_pages']<2 or 'Entering activity: Home' not in log):
  raise ValueError('Reader turn/exit did not complete')
 if checkpoint.get('protocol')==2:
  expected='CrossPointWebServer' if web else 'Home' if checkpoint.get('scenario')=='turn-exit' else ('XtcReader' if inputs_book(directory).endswith(('.xtc','.xtch')) else 'EpubReader')
  display=json.loads((directory/'display-writes.json').read_text())
  if checkpoint.get('activity')!=expected or not checkpoint.get('display_after_activity_entered') or not display or display[-1].get('activity')!=expected:
   raise ValueError('Checkpoint did not paint its current activity')
 if web:
  http=json.loads((directory/'http-result.json').read_text())
  if not http.get('completed') or http.get('status',{}).get('mode')!='AP' or http.get('payload_sha256')!=inputs.get('http_payload_sha256') or http.get('downloaded_sha256')!=http.get('payload_sha256') or http.get('downloaded_bytes')!=http.get('bytes'):
   raise ValueError('Full CrossPoint AP upload/download did not preserve bytes')
  if checkpoint.get('reason')!='guest requested restart after AP exit' or checkpoint.get('reset_executed') is not False or 'Silent restart (target=home)' not in log:
   raise ValueError('CrossPoint AP exit did not reach its real restart request')
 events=json.loads((directory/'sd-events.json').read_text())
 if not events or not all(e['result'] for e in events):raise ValueError('Failed SD boundary operation')
 checkpoint.setdefault('scenario',inputs.get('scenario','read'))
 checkpoint.setdefault('rendered_pages',renders)
 diag=diagnostics((directory/'uart.log').read_text(errors='replace') if (directory/'uart.log').exists() else '',log,
  (directory/'gdb.log').read_text(errors='replace') if (directory/'gdb.log').exists() else '')
 return dict(heap=heap,checkpoint=checkpoint,activity_paint_verified=checkpoint.get('protocol')==2,diagnostics=diag,engine=status.get('engine'),source_inputs={k:inputs.get(k) for k in ('crosspoint','sdk','environment','card_source_sha256','resumed_book')},sd_operations=dict(collections.Counter(e['operation'] for e in events)),
  sd_read_sectors=sum(e.get('count',0) for e in events if e['operation']=='read'),
  sd_write_sectors=sum(e.get('count',0) for e in events if e['operation']=='write'),
  image_sha256=status['image_sha256'],render_completed=not web,web_ap_completed=web,physical_performance_valid=False)


def inputs_book(directory):
 return (json.loads((directory/'input.json').read_text()).get('resumed_book') or '').lower()


def compare(first,second):
 a,b=inspect(first),inspect(second)
 if a['image_sha256']!=b['image_sha256'] or a['checkpoint']['scenario']!=b['checkpoint']['scenario'] or a['source_inputs']!=b['source_inputs']:
  raise ValueError('Different firmware or scenarios are not a matched engine control')
 # Only these controls demonstrated identical heap snapshots. The script reports
 # differences instead of silently treating a looser envelope as equivalent.
 return dict(first=a,second=b,heap_equal=a['heap']==b['heap'],
  logical_sd_counts_equal=(a['sd_read_sectors'],a['sd_write_sectors'])==(b['sd_read_sectors'],b['sd_write_sectors']),
  semantic_screen_requires_image_inspection=True,physical_performance_valid=False)


def main():
 p=argparse.ArgumentParser();p.add_argument('first',type=Path);p.add_argument('second',type=Path)
 p.add_argument('--output',type=Path)
 p.add_argument('--require-activity-paint',action='store_true');a=p.parse_args();result=compare(a.first,a.second)
 if a.require_activity_paint and not all(result[k]['activity_paint_verified'] for k in ('first','second')):
  raise ValueError('Legacy checkpoint cannot establish the requested activity paint')
 text=json.dumps(result,indent=2)+'\n'
 if a.output:a.output.write_text(text)
 print(text)


if __name__=='__main__':main()
