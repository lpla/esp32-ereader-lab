"""Select the same pinned packages for download and extraction."""
from engines import DEFAULT_ESP, ESP_VERSIONS


def add_selection(parser):
    parser.add_argument('--emulators-only', action='store_true',
                        help='All historical emulator packages; no stock firmware')
    parser.add_argument('--engine', choices=('qemu', 'esp-emu', 'all'),
                        help='Only the chosen Linux x86_64 engine(s); no stock firmware or WASM')
    parser.add_argument('--esp-version', choices=ESP_VERSIONS, default=DEFAULT_ESP)
    parser.add_argument('--legacy-fixtures', action='store_true',
                        help='Explicitly include the archived stock-firmware setup')


def select_files(files, engine=None, esp_version=DEFAULT_ESP, emulators_only=False):
    if engine is None:
        return [f for f in files if not emulators_only or
                f['file'].startswith(('esp-emu', 'qemu'))]
    names = set()
    if engine in ('qemu', 'all'):
        names.add('qemu.tar.xz')
    if engine in ('esp-emu', 'all'):
        names.add('esp-emu.tar.gz' if esp_version == '0.45.0' else
                  f'esp-emu-{esp_version}-x86_64-unknown-linux-gnu.tar.gz')
    selected = [f for f in files if f['file'] in names]
    if {f['file'] for f in selected} != names:
        raise ValueError('Selected engine package is missing from downloads/manifest.json')
    return selected
