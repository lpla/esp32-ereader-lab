"""Run a bounded unmodified guest heap/Wi-Fi probe with an isolated HTTP server."""
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import subprocess
import threading

ROOT = Path('/work')


class Handler(BaseHTTPRequestHandler):
    requests = 0
    def do_GET(self):
        type(self).requests += 1
        self.send_response(200);self.end_headers();self.wfile.write(b'EREADER LAB TCP OK\n')
    def log_message(self, *args):
        pass


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--engine',choices=['qemu','esp-emu'],required=True)
    p.add_argument('--image',required=True,type=Path)
    p.add_argument('--name',required=True)
    a=p.parse_args()
    if not a.name.replace('-','').isalnum():p.error('name must contain letters, numbers, hyphens')
    d=ROOT/'results'/a.name;d.mkdir(exist_ok=False)
    server=HTTPServer(('127.0.0.1',8088),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    if a.engine=='esp-emu':
        cmd=[str(ROOT/'tools/esp-emu-0.45.0-x86_64-unknown-linux-gnu/esp-emu'), '--chip','esp32c3',
             '--firmware',str(a.image),'--timeout','65s','--net','user','--log-color','never','--exit-on','LAB_DONE']
    else:
        cmd=[str(ROOT/'tools/qemu/bin/qemu-system-riscv32'),'-nographic','-monitor','none','-icount','3',
             '-machine','esp32c3','-drive',f'file={a.image},if=mtd,format=raw','-snapshot']
    before=hashlib.sha256(a.image.read_bytes()).hexdigest()
    (d/'command.json').write_text(json.dumps(cmd,indent=2)+'\n')
    timed_out=False
    with (d/'uart.log').open('w') as out:
        proc=subprocess.Popen(cmd,stdout=out,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL)
        try:code=proc.wait(timeout=70 if a.engine=='esp-emu' else 25)
        except subprocess.TimeoutExpired:
            timed_out=True;proc.terminate()
            try:code=proc.wait(timeout=3)
            except subprocess.TimeoutExpired:proc.kill();code=proc.wait()
    server.shutdown();server.server_close()
    lines=(d/'uart.log').read_text(errors='replace').splitlines()
    records=[]
    for line in lines:
        for label in ('LAB_START','LAB_HEAP','LAB_WIFI','LAB_TCP','LAB_LARGE','LAB_PACKETS','LAB_EDGE'):
            at=line.find(label+' ')
            if at>=0:
                try:records.append(dict(kind=label,**json.loads(line[at+len(label)+1:])))
                except json.JSONDecodeError:pass
    status=dict(engine=a.engine,exit=code,timeout=timed_out,done=any('LAB_DONE' in l for l in lines),
                image_sha256=before,image_unchanged=before==hashlib.sha256(a.image.read_bytes()).hexdigest(),
                http_requests=Handler.requests,records=records,gdb_hardware_substitutions=False,
                physical_radio_validated=False,physical_performance_validated=False)
    (d/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(status,indent=2))


if __name__=='__main__':main()
