"""Select a pinned engine without silently changing historical runs."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ESP_VERSIONS = ('0.45.0', '0.48.0')
DEFAULT_ESP = '0.48.0'


def engine(engine_name, esp_version=DEFAULT_ESP, root=ROOT):
    key = 'qemu' if engine_name == 'qemu' else f'esp-emu-{esp_version}'
    pins = json.loads((root / 'adapters/engines.json').read_text())
    if engine_name not in ('qemu', 'esp-emu') or key not in pins:
        raise ValueError('Unsupported emulator version')
    pin = pins[key]
    path = root / pin['path']
    if hashlib.sha256(path.read_bytes()).hexdigest() != pin['sha256']:
        raise ValueError('Emulator executable differs from its verified package')
    return path, dict(name=engine_name, version=pin['version'], executable_sha256=pin['sha256'])
