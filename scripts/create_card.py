"""Create a disposable MBR/FAT32 SD fixture without mounting a host filesystem."""
import argparse
from pathlib import Path
import os
import shutil
import struct
import subprocess
from create_fixtures import create
from create_media_fixture import create_media
from create_chapter_fixture import create_chapters
from run_lab import ROOT, IMAGE


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fixture', choices=['alpha', 'beta', 'gamma'], default='alpha')
    parser.add_argument('--name', default='base', help='new image name inside cards/')
    args = parser.parse_args()
    if not args.name.replace('-', '').replace('_', '').isalnum():
        parser.error('name must contain letters, numbers, hyphens or underscores')
    fixtures = ROOT / 'fixtures/generated'
    create(fixtures)
    if args.fixture == 'beta':
        create_media(fixtures)
    elif args.fixture == 'gamma':
        create_chapters(fixtures)
    names = [f'{args.fixture}.epub'] + (['control.txt'] if args.fixture == 'alpha' else [])
    for name in names:
        os.utime(fixtures / name, (1767225600, 1767225600))
    cards = ROOT / 'cards'
    cards.mkdir(exist_ok=True)
    output = cards / f'{args.name}.img'
    volume_path = cards / f'{args.name}-volume.img'
    if output.exists() or volume_path.exists():
        raise RuntimeError('Card output exists; choose a new --name to preserve earlier tests')
    volume = f'cards/{volume_path.name}'
    command = ['docker', 'run', '--rm', '--network', 'none', '-e', 'TZ=UTC',
               '-v', f'{ROOT}:/work', IMAGE, 'sh', '-ec',
               f'truncate -s 64M {volume}; mkfs.fat --invariant -F 32 -n EREADERLAB {volume}; ' +
               '; '.join(f'mcopy -m -i {volume} fixtures/generated/{name} ::' for name in names)]
    subprocess.run(command, check=True)
    mbr = bytearray(1048576)
    struct.pack_into('<B3sB3sII', mbr, 446, 0, b'\0\2\0', 0x0c,
                     b'\xfe\xff\xff', 2048, 131072)
    mbr[510:512] = b'\x55\xaa'
    with output.open('xb') as out, volume_path.open('rb') as volume_file:
        out.write(mbr)
        shutil.copyfileobj(volume_file, out)
    volume_path.unlink()
    print(f'Created {output.relative_to(ROOT)}: 65 MiB, FAT32 partition at sector 2048')


if __name__ == '__main__':
    main()
