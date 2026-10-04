"""Compose captured X4 writeImage rectangles and emit PNGs without dependencies.

Images represent the driver's requested panel RAM, not optical e-paper output.
"""
import argparse
import json
from pathlib import Path
import struct
import zlib


def png(path, width, height, data):
    stride = (width + 7) // 8
    assert len(data) == stride * height
    def chunk(kind, body):
        return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body))
    scanlines = b''.join(b'\0' + data[y * stride:(y + 1) * stride] for y in range(height))
    path.write_bytes(b'\x89PNG\r\n\x1a\n' +
                     chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 1, 0, 0, 0, 0)) +
                     chunk(b'IDAT', zlib.compress(scanlines)) + chunk(b'IEND', b''))


def portrait(data):
    out = bytearray(b'\xff' * 48000)
    for y in range(480):
        for x in range(800):
            if not data[y * 100 + x // 8] & (0x80 >> (x % 8)):
                dx, dy = 479 - y, x
                out[dy * 60 + dx // 8] &= ~(0x80 >> (dx % 8))
    return out


def render(directory):
    writes = json.loads((directory / 'display-writes.json').read_text())
    canvas = bytearray(b'\xff' * 48000)
    for index, entry in enumerate(writes):
        x, y, w, h = (entry[k] for k in ('x', 'y', 'width', 'height'))
        assert 0 <= x < 800 and 0 <= y < 480 and x + w <= 800 and y + h <= 480, entry
        data = (directory / entry['file']).read_bytes()
        stride = (w + 7) // 8
        assert len(data) == stride * h
        for row in range(h):
            source_y = h - 1 - row if entry['mirror_y'] else row
            for col in range(w):
                white = bool(data[source_y * stride + col // 8] & (0x80 >> (col % 8)))
                if entry['invert']:
                    white = not white
                offset = (y + row) * 100 + (x + col) // 8
                mask = 0x80 >> ((x + col) % 8)
                if white:
                    canvas[offset] |= mask
                else:
                    canvas[offset] &= ~mask
        png(directory / f'screen-{index:03d}.png', 480, 800, portrait(canvas))
    if writes:
        (directory / 'panel-ram.bin').write_bytes(canvas)
        png(directory / 'screen.png', 480, 800, portrait(canvas))
    return len(writes)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    print('captured writes:', render(parser.parse_args().directory))
