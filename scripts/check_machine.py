"""Compare completed guest checkpoints; never infer physical speed from timers."""
import argparse,collections,json,re
from pathlib import Path


def inspect(directory):
 status=json.loads((directory/'status.json').read_text())
 checkpoint=json.loads((directory/'checkpoint.json').read_text()) if (directory/'checkpoint.json').exists() else {}
 if status['gdb_exit']!=0 or not status['image_unchanged'] or not checkpoint:
  raise ValueError('Guest checkpoint did not complete')
 log=(directory/'guest.log').read_text()
 lines=re.findall(r'\[MEM\] Free: (\d+) bytes, Total: (\d+) bytes, Min Free: (\d+) bytes, MaxAlloc: (\d+) bytes',log)
 if not lines:raise ValueError('Missing guest heap diagnostic')
 heap=dict(zip(('free','total','minimum','largest'),map(int,lines[-1])))
 if not 0<heap['largest']<=heap['free']<=heap['total'] or heap['minimum']>heap['free']:
  raise ValueError('Inconsistent heap diagnostic')
 renders=log.count('Rendered page in')+len(re.findall(r'\[XTR\] Rendered page \d+/\d+',log))
 if checkpoint.get('rendered_pages',renders)<1 or renders<1:
  raise ValueError('No reader render completed')
 if checkpoint.get('scenario')=='turn-exit' and (checkpoint['rendered_pages']<2 or 'Entering activity: Home' not in log):
  raise ValueError('Reader turn/exit did not complete')
 events=json.loads((directory/'sd-events.json').read_text())
 if not events or not all(e['result'] for e in events):raise ValueError('Failed SD boundary operation')
 inputs=json.loads((directory/'input.json').read_text())
 checkpoint.setdefault('scenario',inputs.get('scenario','read'))
 checkpoint.setdefault('rendered_pages',renders)
 return dict(heap=heap,checkpoint=checkpoint,source_inputs={k:inputs.get(k) for k in ('crosspoint','sdk','environment','card_source_sha256','resumed_book')},sd_operations=dict(collections.Counter(e['operation'] for e in events)),
  sd_read_sectors=sum(e.get('count',0) for e in events if e['operation']=='read'),
  sd_write_sectors=sum(e.get('count',0) for e in events if e['operation']=='write'),
  image_sha256=status['image_sha256'],render_completed=True,physical_performance_valid=False)


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
 p.add_argument('--output',type=Path);a=p.parse_args();text=json.dumps(compare(a.first,a.second),indent=2)+'\n'
 if a.output:a.output.write_text(text)
 print(text)


if __name__=='__main__':main()
