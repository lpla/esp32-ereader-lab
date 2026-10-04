"""Create a disposable MBR/FAT32 SD fixture without mounting a host filesystem."""
from pathlib import Path
import os
import shutil
import struct
import subprocess
from create_fixtures import create
from run_lab import ROOT, IMAGE


def main():
    fixtures = ROOT / 'fixtures/generated'
    create(fixtures)
    for path in fixtures.iterdir():
        os.utime(path, (1767225600, 1767225600))
    cards = ROOT / 'cards'
    cards.mkdir(exist_ok=True)
    if (cards / 'base.img').exists():
        raise RuntimeError('cards/base.img exists; move it aside to preserve earlier tests')
    command = ['docker', 'run', '--rm', '--network', 'none', '-e', 'TZ=UTC',
               '-v', f'{ROOT}:/work', IMAGE, 'sh', '-ec',
               'truncate -s 64M cards/volume.img; '
               'mkfs.fat --invariant -F 32 -n EREADERLAB cards/volume.img; '
               'mcopy -m -i cards/volume.img fixtures/generated/alpha.epub ::; '
               'mcopy -m -i cards/volume.img fixtures/generated/control.txt ::']
    subprocess.run(command, check=True)
    mbr = bytearray(1048576)
    struct.pack_into('<B3sB3sII', mbr, 446, 0, b'\0\2\0', 0x0c,
                     b'\xfe\xff\xff', 2048, 131072)
    mbr[510:512] = b'\x55\xaa'
    with (cards / 'base.img').open('wb') as out, (cards / 'volume.img').open('rb') as volume:
        out.write(mbr)
        shutil.copyfileobj(volume, out)
    (cards / 'volume.img').unlink()
    print('Created cards/base.img: 65 MiB, FAT32 partition at sector 2048')


if __name__ == '__main__':
    main()
