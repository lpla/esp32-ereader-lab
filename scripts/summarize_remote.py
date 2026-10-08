"""Preserve warning attribution without publishing megabytes of GDB packets."""
import argparse
import hashlib
import json
from pathlib import Path
from diagnostics import diagnostics


def summarize(directory):
    trace=(directory/'gdb.log').read_text(errors='replace')
    uart=(directory/'uart.log').read_text(errors='replace')
    guest=(directory/'guest.log').read_text(errors='replace') if (directory/'guest.log').exists() else ''
    diag=diagnostics(uart,guest,trace)
    excerpts=[]
    for address in diag['debugger_read_addresses']:
        marker=f'Sending packet: $m{int(address,16):x},'
        start=trace.find(marker)
        excerpts.append(trace[max(0,start-50):start+180])
    result=dict(diagnostics=diag,remote_log_sha256=hashlib.sha256((directory/'gdb.log').read_bytes()).hexdigest(),
        remote_log_bytes=(directory/'gdb.log').stat().st_size,packet_excerpts=excerpts,
        interpretation='Invalid GDB reads match warning addresses/counts; not physical memory safety evidence')
    (directory/'remote-summary.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args()
    print(json.dumps(summarize(a.directory),indent=2))
