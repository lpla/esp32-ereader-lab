"""Host HTTP uploads and reconnects to the actual emulated firmware AP.

Run inside a --network none container: forwarded sockets use its loopback only.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
import urllib.request
from engines import engine,ESP_VERSIONS,DEFAULT_ESP
from diagnostics import diagnostics

ROOT=Path('/work')


def fnv(data):
    value=2166136261
    for byte in data:value=((value^byte)*16777619)&0xffffffff
    return value


def validate(result):
    if not result.get('done') or not result.get('image_unchanged') or not result.get('diagnostics',{}).get('modeled_execution_clean'):
        raise ValueError('AP probe incomplete or faulted')
    transfers=result.get('transfers',[])
    if len(transfers)!=6 or {r['cycle'] for r in transfers}!={0,1,2}:
        raise ValueError('Missing upload/reconnect cycles')
    for r in transfers:
        if r['response']!={'bytes':r['bytes'],'fnv32':r['fnv32']}:
            raise ValueError('Guest upload payload differs from host')
    records=result.get('records',[])
    uploads=[r for r in records if r['kind']=='AP_UPLOAD']
    if [(r['cycle'],r['bytes'],r['fnv32']) for r in uploads]!=[(r['cycle'],r['bytes'],r['fnv32']) for r in transfers]:
        raise ValueError('Guest completed-upload records differ from host responses')
    phases={(r.get('cycle'),r.get('phase')) for r in records if r['kind']=='AP_HEAP'}
    if not all((cycle,phase) in phases for cycle in range(3) for phase in ('active','uploaded','off')):
        raise ValueError('Missing real AP teardown heap sample')
    if any(not r['integrity'] for r in records if r['kind']=='AP_HEAP'):
        raise ValueError('Guest heap integrity failed')
    if not all(any(r['kind']=='AP_READY' and r['cycle']==c and r['started'] for r in records) for c in range(3)):
        raise ValueError('AP did not restart')
    return True


def main():
    p=argparse.ArgumentParser();p.add_argument('--name',required=True)
    p.add_argument('--esp-version',choices=ESP_VERSIONS,default=DEFAULT_ESP)
    a=p.parse_args()
    if not a.name.replace('-','').isalnum():p.error('Use letters, digits and hyphens')
    d=ROOT/'results'/a.name;d.mkdir(exist_ok=False)
    pin=json.loads((ROOT/'firmware/wifi-ap.json').read_text());image=ROOT/pin['image']
    for path,sha in [(image,pin['image_sha256'])]+[(ROOT/path,sha) for path,sha in pin['sources'].items()]:
        if hashlib.sha256(path.read_bytes()).hexdigest()!=sha:raise ValueError('AP source/image changed since packaging')
    executable,identity=engine('esp-emu',a.esp_version)
    command=[str(executable),'--chip','esp32c3','--firmware',str(image),'--timeout','85s',
        '--net','user,restrict=yes,hostfwd=tcp:127.0.0.1:18080-:80','--log-color','never','--exit-on','LAB_DONE']
    if a.esp_version!='0.45.0':command+=['--wifi-fw-ap-password','']
    (d/'command.json').write_text(json.dumps(command,indent=2)+'\n')
    (d/'input.json').write_text(json.dumps(dict(**pin,engine=identity,wifi_driver_substituted=False,
        guest_network_isolated=True,physical_radio_validated=False,physical_performance_validated=False),indent=2)+'\n')
    deadline=time.monotonic()+80
    transfers=[];failure=None
    def request(path,body=None,headers=None):
        req=urllib.request.Request('http://127.0.0.1:18080'+path,data=body,headers=headers or {})
        with urllib.request.urlopen(req,timeout=8) as response:return response.read()
    def wait_cycle(cycle):
        while time.monotonic()<deadline:
            try:
                value=json.loads(request('/health'))
                if value['cycle']==cycle:return
            except (OSError,ValueError):pass
            time.sleep(0.1)
        raise TimeoutError('AP host reachability/restart did not complete')
    with (d/'uart.log').open('w') as out:
        process=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=out,stderr=subprocess.STDOUT)
        try:
            for cycle in range(3):
                wait_cycle(cycle)
                for size in (4097,262177):
                    payload=bytes((i*13+cycle*19)&255 for i in range(size))
                    body=b'--lab\r\nContent-Disposition: form-data; name="file"; filename="probe.epub"\r\nContent-Type: application/octet-stream\r\n\r\n'+payload+b'\r\n--lab--\r\n'
                    response=json.loads(request('/upload',body,{'Content-Type':'multipart/form-data; boundary=lab'}))
                    transfers.append(dict(cycle=cycle,bytes=size,fnv32=fnv(payload),response=response))
                request('/restart' if cycle<2 else '/done',b'')
            process.wait(timeout=8)
        except (OSError,ValueError,TimeoutError,subprocess.TimeoutExpired) as error:failure=str(error)
        finally:
            if process.poll() is None:process.terminate()
            try:process.wait(timeout=3)
            except subprocess.TimeoutExpired:process.kill();process.wait()
    uart=(d/'uart.log').read_text(errors='replace');records=[]
    for line in uart.splitlines():
        m=re.search(r'(AP_HEAP|AP_READY|AP_UPLOAD) (\{.*\})',line)
        if m:records.append(dict(kind=m[1],**json.loads(m[2])))
    result=dict(engine=identity,done='LAB_DONE' in uart,failure=failure,transfers=transfers,records=records,
        image_unchanged=hashlib.sha256(image.read_bytes()).hexdigest()==pin['image_sha256'],diagnostics=diagnostics(uart),
        crosspoint_candidate_validated=False,ap_max_station_limit_validated=False)
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2));validate(result)


if __name__=='__main__':main()
