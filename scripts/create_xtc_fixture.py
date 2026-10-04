"""Generate valid large XTC page tables with two distinct shared payloads.

This stresses 6001 index entries, not storage volume or 6001 unique pages.
"""
from pathlib import Path
import hashlib
import json
import struct

ROOT = Path(__file__).resolve().parents[1]


def create(directory):
    directory.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for depth in (1, 2):
        count = 6001
        offset = 56 + 16 * count
        pages = []
        for pattern in (0xaa, 0xcc):
            payload = bytes([pattern]) * (48000 * depth)
            pages.append(struct.pack('<IHHBBIQ', 0x00485458 if depth == 2 else 0x00475458,
                                     480, 800, 0, 0, len(payload), 0) + payload)
        header = struct.pack('<IBBHBBBBIQQQQII', 0x48435458 if depth == 2 else 0x00435458,
                             1, 0, count, 0, 0, 0, 0, 1, 0, 56, offset, 0, 0, 0)
        table = b''.join(struct.pack('<QIHH', offset if i == 0 else offset + len(pages[0]),
                                    len(pages[0]), 480, 800) for i in range(count))
        data = header + table + b''.join(pages)
        name = f'table6001.{"xtch" if depth == 2 else "xtc"}'
        (directory / name).write_bytes(data)
        manifest[name] = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                              table_entries=count, distinct_payloads=2, dimensions=[480, 800], bit_depth=depth)
    (directory / 'xtc-table-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    print(json.dumps(create(ROOT / 'fixtures/generated'), indent=2))
