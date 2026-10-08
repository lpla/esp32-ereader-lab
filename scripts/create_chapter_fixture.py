"""Create a deterministic 120-chapter EPUB to probe chapter navigation stride."""
from zipfile import ZipFile, ZipInfo, ZIP_STORED, ZIP_DEFLATED
from create_fixtures import ROOT, create
import argparse
import hashlib
import json


def create_chapters(directory,count=120,name='gamma'):
    if not 2<=count<=10000 or not name.isalnum():raise ValueError('Invalid chapter count or name')
    create(directory)
    with ZipFile(directory / 'alpha.epub') as source:
        files = {name: source.read(name) for name in ('mimetype', 'META-INF/container.xml')}
    manifest = ''.join(f'<item id="c{i}" href="c{i:03}.xhtml" media-type="application/xhtml+xml"/>' for i in range(1, count+1))
    spine = ''.join(f'<itemref idref="c{i}"/>' for i in range(1, count+1))
    files['OEBPS/content.opf'] = f'''<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="book"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>GAMMA Chapter Stride Probe</dc:title><dc:creator>ESP32 e-reader lab</dc:creator><dc:language>en</dc:language><dc:identifier id="book">urn:ereader-lab:gamma:1</dc:identifier></metadata><manifest>{manifest}<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/></manifest><spine toc="ncx">{spine}</spine></package>'''.encode()
    nav = ''.join(f'<navPoint id="n{i}" playOrder="{i}"><navLabel><text>Chapter {i:03}</text></navLabel><content src="c{i:03}.xhtml"/></navPoint>' for i in range(1, count+1))
    files['OEBPS/toc.ncx'] = f'''<?xml version="1.0"?><ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1"><head><meta name="dtb:uid" content="urn:ereader-lab:gamma:1"/></head><docTitle><text>GAMMA Chapter Stride Probe</text></docTitle><navMap>{nav}</navMap></ncx>'''.encode()
    for i in range(1, count+1):
        files[f'OEBPS/c{i:03}.xhtml'] = f'''<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml"><head><title>Chapter {i:03}</title></head><body><h1>Chapter {i:03}</h1><p>GAMMA CHAPTER {i:03} TARGET.</p></body></html>'''.encode()
    path = directory / f'{name}.epub'
    with ZipFile(path, 'w') as archive:
        for entry, data in files.items():
            info = ZipInfo(entry, (2026, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_STORED if entry == 'mimetype' else ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, data)
    (directory/f'{name}-manifest.json').write_text(json.dumps(dict(file=path.name,spine_entries=count,toc_entries=count,
        distinct_chapter_files=count,bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest()),indent=2)+'\n')
    return path


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--count',type=int,default=120);parser.add_argument('--name',default='gamma')
    args=parser.parse_args()
    print(create_chapters(ROOT / 'fixtures/generated',args.count,args.name))
