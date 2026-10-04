"""Run bounded native CrossPoint comparisons on fresh synthetic SD directories."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
from create_fixtures import ROOT, create
from create_media_fixture import create_media
from create_chapter_fixture import create_chapters

SCENARIOS = {
    'dark': ('900:DOWN;1300:ENTER;1900:DOWN;2300:ENTER;3500:ENTER;4200:DOWN;4500:DOWN;4800:DOWN;5200:ENTER;5700:BACK;7200:QUIT', [(3100,'before'),(6700,'dark')]),
    'orientation': ('900:DOWN;1300:ENTER;1900:DOWN;2300:ENTER;3500:ENTER;4200:DOWN;4500:DOWN;4800:DOWN;5100:DOWN;5400:DOWN;5800:ENTER;6300:DOWN;6700:ENTER;7400:BACK;9200:QUIT', [(3100,'before'),(8700,'orientation')]),
    'reading': ('900:DOWN;1300:ENTER;1900:DOWN;2300:ENTER;3500:DOWN;4500:ENTER;6500:QUIT',
                [(3100,'book'),(4100,'page'),(5800,'menu')]),
    'links': ('900:DOWN;1300:ENTER;1900:DOWN;2300:ENTER;3500:ENTER;4500:DOWN;5000:ENTER;6300:BACK;7500:QUIT',
              [(4200,'menu'),(6000,'target'),(7000,'return')]),
    'toc': ('900:DOWN;1300:ENTER;1900:DOWN;2300:ENTER;3500:ENTER;4200:ENTER;5200:DOWN;5600:ENTER;7300:QUIT',
            [(4900,'toc'),(6800,'chapter-two')]),
    'bookmark': ('900:DOWN;1300:ENTER;1900:DOWN;2300:ENTER;3500:ENTER:1200;5800:QUIT', [(4900,'bookmark')]),
    'reopen': ('900:DOWN;1300:ENTER;1900:DOWN;2300:ENTER;3500:DOWN;4500:BACK;5300:ENTER;7000:QUIT', [(4100,'page'),(6500,'reopen')]),
    'chapters': ('900:DOWN;1300:ENTER;1900:DOWN;2300:ENTER;3500:ENTER;4200:ENTER;5200:DOWN:850;6900:QUIT', [(4900,'toc'),(6400,'held-navigation')]),
    'media': ('900:DOWN;1300:ENTER;1900:DOWN;2300:ENTER;3500:DOWN;4500:QUIT',
              [(3000,'style'),(4000,'page')]),
    'media-css': ('900:DOWN;1300:ENTER;1900:DOWN;2300:ENTER;4000:QUIT',[(3200,'style')]),
}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--binary',required=True,type=Path)
    parser.add_argument('--firmware-repo',type=Path)
    parser.add_argument('--scenario',choices=SCENARIOS,default='reading')
    parser.add_argument('--prefix',required=True)
    args=parser.parse_args()
    if not args.prefix.replace('-','').replace('_','').isalnum():
        parser.error('prefix must contain letters, numbers, hyphens or underscores')
    binary=args.binary.resolve(strict=True)
    directory=ROOT/'results'/args.prefix
    directory.mkdir(parents=True,exist_ok=False)
    sd=directory/'sd';sd.mkdir()
    fixtures=ROOT/'fixtures/generated'
    create(fixtures)
    media=args.scenario.startswith('media')
    if media:create_media(fixtures)
    if args.scenario == 'chapters': create_chapters(fixtures)
    book=fixtures/('gamma.epub' if args.scenario == 'chapters' else ('beta.epub' if media else 'alpha.epub'))
    shutil.copyfile(book,sd/book.name)
    if args.scenario in ('media-css', 'bookmark'):
        (sd/'.crosspoint').mkdir()
        settings = {'paragraphAlignment': 4, 'embeddedStyle': 1} if args.scenario == 'media-css' else {'longPressMenuFunction': 2}
        (sd/'.crosspoint/settings.json').write_text(json.dumps(settings)+'\n')
    actions,shots=SCENARIOS[args.scenario]
    env={**os.environ,'SDL_VIDEODRIVER':'dummy','SDL_RENDER_DRIVER':'software',
         'CROSSPOINT_SIM_SD':str(sd),'CROSSPOINT_SIM_INPUT_SCRIPT':actions,
         'CROSSPOINT_SIM_SCREENSHOTS':';'.join(f'{time}:{directory}/{name}.bmp' for time,name in shots)}
    metadata=dict(scenario=args.scenario,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
                  fixture=book.name,fixture_sha256=hashlib.sha256(book.read_bytes()).hexdigest(),
                  input=actions,screenshots=shots,heap_and_timing_are_host_only=True)
    if args.firmware_repo:
        metadata['firmware_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=args.firmware_repo,text=True).strip()
    (directory/'command.json').write_text(json.dumps(metadata,indent=2)+'\n')
    with (directory/'uart.log').open('w') as log:
        completed=subprocess.run([str(binary)],env=env,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=15)
    for _,name in shots:
        bmp=directory/f'{name}.bmp'
        if not bmp.exists():raise RuntimeError(f'Missing screenshot: {bmp}')
        if platform.system()=='Darwin':
            subprocess.run(['sips','-s','format','png',str(bmp),'--out',str(directory/f'{name}.png')],check=True,stdout=subprocess.DEVNULL)
    metadata['exit']=completed.returncode
    metadata['feature_success_requires_image_inspection']=True
    (directory/'status.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(json.dumps(metadata,indent=2))
    if completed.returncode:raise SystemExit(completed.returncode)


if __name__=='__main__':main()
