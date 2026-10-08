"""Package a fresh AP probe with its build and source identities."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def package():
    project = ROOT/'probes/wifi-ap'
    inputs = [project/'src/main.cpp', project/'platformio.ini']
    elf = project/'.pio/build/c3/firmware.elf'
    if elf.stat().st_mtime < max(p.stat().st_mtime for p in inputs):
        raise ValueError('Build the AP probe after its last source edit')
    image = project/'.pio/build/c3/firmware.factory.bin'
    data = image.read_bytes()
    if len(data)>16*1024*1024 or data[0]!=0xe9:
        raise ValueError('Invalid merged C3 factory image')
    flash = ROOT/'firmware/wifi-ap.bin'
    flash.write_bytes(data+b'\xff'*(16*1024*1024-len(data)))
    manifest = dict(image='firmware/wifi-ap.bin',image_sha256=hashlib.sha256(flash.read_bytes()).hexdigest(),
        factory_sha256=hashlib.sha256(data).hexdigest(),elf_sha256=hashlib.sha256(elf.read_bytes()).hexdigest(),
        sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
        scope='Arduino WebServer / actual guest Wi-Fi AP; no CrossPoint application candidate')
    (ROOT/'firmware/wifi-ap.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


if __name__=='__main__':print(json.dumps(package(),indent=2))
