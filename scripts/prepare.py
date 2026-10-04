"""Verify downloads and prepare reproducible, explicitly labelled flash images."""
from pathlib import Path
import hashlib
import json
import struct
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def inspect(data):
    parts = []
    for pos in range(0x8000, min(len(data), 0x9000), 32):
        if data[pos:pos + 2] != b"\xaa\x50":
            break
        _, kind, subtype, offset, size, label, flags = struct.unpack(
            "<HBBII16sI", data[pos:pos + 32])
        parts.append(dict(type=kind, subtype=subtype, offset=offset, size=size,
                          label=label.rstrip(b"\0").decode(), flags=flags))
    images = []
    for offset in [0] + [p["offset"] for p in parts if p["type"] == 0]:
        header = data[offset:offset + 24]
        if len(header) != 24 or header[0] != 0xe9:
            continue
        image = dict(offset=offset, segments=header[1],
                     entry=hex(struct.unpack_from("<I", header, 4)[0]),
                     chip_id=struct.unpack_from("<H", header, 12)[0],
                     flash_size_code=header[3] >> 4,
                     min_chip_rev=header[14],
                     min_chip_rev_full=struct.unpack_from("<H", header, 15)[0])
        desc = data[offset + 32:offset + 288]
        if desc[:4] == b"2T\xcd\xab":
            image["app"] = {k: desc[a:b].rstrip(b"\0").decode(errors="replace")
                            for k, a, b in [("version", 16, 48), ("project", 48, 80),
                                            ("time", 80, 96), ("date", 96, 112),
                                            ("idf", 112, 144)]}
        images.append(image)
    return dict(bytes=len(data), partitions=parts, images=images)


def main():
    for directory in ('firmware', 'tools', 'results'):
        (ROOT / directory).mkdir(exist_ok=True)
    manifest = json.loads((ROOT / 'downloads/manifest.json').read_text())
    for entry in manifest['files']:
        data = (ROOT / 'downloads' / entry['file']).read_bytes()
        assert len(data) == entry['bytes'], entry['file']
        assert hashlib.sha256(data).hexdigest() == entry['sha256'], entry['file']
    archives = [
        ("esp-emu.tar.gz", "esp-emu-SHA256SUMS",
         "esp-emu-0.45.0-x86_64-unknown-linux-gnu.tar.gz"),
        ("qemu.tar.xz", "qemu-SHA256SUMS",
         "qemu-riscv32-softmmu-esp_develop_9.2.2_20260417-x86_64-linux-gnu.tar.xz"),
        ("esp-emu-wasm.tar.gz", "esp-emu-SHA256SUMS",
         "esp-emu-0.45.0-wasm.tar.gz"),
    ]
    for archive, checksums, name in archives:
        expected = next(line.split()[0] for line in
                        (ROOT / "downloads" / checksums).read_text().splitlines()
                        if not line.startswith("#") and name in line)
        assert hashlib.sha256((ROOT / "downloads" / archive).read_bytes()).hexdigest() == expected
        with tarfile.open(ROOT / "downloads" / archive) as tar:
            tar.extractall(ROOT / "tools", filter="data")
    for source, name in [('x4pro-xtos-v7.4.4.bin', 'x4pro-stock-padded'),
                         ('x4pro-xtos_licorice-260923.bin', 'x4pro-licorice-padded')]:
        data = (ROOT / 'downloads' / source).read_bytes()
        assert inspect(data)['images'][0]['chip_id'] == 9
        assert len(data) <= 16 * 1024 * 1024
        padded = data + b'\xff' * (16 * 1024 * 1024 - len(data))
        (ROOT / 'firmware' / (name + '.bin')).write_bytes(padded)
        provenance = dict(source=source, source_sha256=hashlib.sha256(data).hexdigest(),
                          transformation='append FF to 16 MiB; preserve every downloaded byte',
                          sha256=hashlib.sha256(padded).hexdigest(), **inspect(padded))
        (ROOT / 'firmware' / (name + '.json')).write_text(json.dumps(provenance, indent=2) + '\n')
    x3 = (ROOT / "downloads/x3_en_v5.2.13_full.bin").read_bytes()
    x4 = (ROOT / "downloads/x4_en_v5.1.6_ota.bin").read_bytes()
    layout = {"x3-stock": inspect(x3), "x4-ota": inspect(x4)}
    (ROOT / "firmware/x3-stock.bin").write_bytes(x3)
    app0 = bytearray(x3)
    app0[0xe000:0x10000] = b'\xff' * 0x2000
    (ROOT / 'firmware/x3-app0-empty-otadata.bin').write_bytes(app0)
    # This is a constructed execution fixture, not an original X4 flash dump.
    # Keep the public X3 bootloader/table/data and replace every application slot
    # with the unmodified X4 OTA payload so any OTA selection boots the X4 app.
    assembled = bytearray(x3)
    for part in layout["x3-stock"]["partitions"]:
        if part["type"] != 0:
            continue
        assert len(x4) <= part["size"], part
        off, size = part["offset"], part["size"]
        assembled[off:off + size] = b"\xff" * size
        assembled[off:off + len(x4)] = x4
    (ROOT / "firmware/x4-app-x3-layout.bin").write_bytes(assembled)
    layout["x4-app-x3-layout"] = inspect(assembled)
    for name, data, offset in [
        ('x3_en_v5.2.13_full-segments', x3, 0x10000),
        ('x3-app1-segments', x3, 0x780000),
        ('x4_en_v5.1.6_ota-segments', x4, 0),
    ]:
        directory = ROOT / 'firmware' / name
        directory.mkdir(exist_ok=True)
        segments = []
        cursor = offset + 24
        for _ in range(data[offset + 1]):
            address, size = struct.unpack_from('<II', data, cursor)
            cursor += 8
            assert cursor + size <= len(data)
            (directory / f'{address:08x}.bin').write_bytes(data[cursor:cursor + size])
            segments.append(dict(address=hex(address), bytes=size, file_offset=cursor))
            cursor += size
        (directory / 'segments.json').write_text(json.dumps(segments, indent=2) + '\n')
    (ROOT / "firmware/layout.json").write_text(json.dumps(layout, indent=2) + "\n")
    print(json.dumps(layout, indent=2))


if __name__ == "__main__":
    main()
