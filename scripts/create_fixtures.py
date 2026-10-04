"""Generate deterministic, original EPUB/TXT content for reading comparisons."""
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_STORED, ZIP_DEFLATED
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]

def create(directory):
    directory.mkdir(parents=True, exist_ok=True)
    chapter = '''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><head><title>Chapter One</title></head><body>
<h1>Chapter One</h1><p>ALPHA EPUB BASELINE. This sentence must appear in the reader.</p>
<p>Regular words, <b>bold words</b>, <i>italic words</i>, and <u>underlined words</u>.</p>
<p>A reference <a href="second.xhtml#note">[1]</a> points to a note in the next chapter.</p>
''' + ''.join('<p>Paragraph %02d. Reading across page boundaries tests pagination, wrapping, and remembered position. A small book can still expose useful behavior.</p>' % i for i in range(1, 31)) + '</body></html>'
    files = {
        'mimetype': 'application/epub+zip',
        'META-INF/container.xml': '''<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>''',
        'OEBPS/content.opf': '''<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="book"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>ALPHA Feature Probe</dc:title><dc:creator>ESP32 e-reader lab</dc:creator><dc:language>en</dc:language><dc:identifier id="book">urn:ereader-lab:alpha:1</dc:identifier></metadata><manifest><item id="c1" href="first.xhtml" media-type="application/xhtml+xml"/><item id="c2" href="second.xhtml" media-type="application/xhtml+xml"/><item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/></manifest><spine toc="ncx"><itemref idref="c1"/><itemref idref="c2"/></spine></package>''',
        'OEBPS/toc.ncx': '''<?xml version="1.0"?><ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1"><head><meta name="dtb:uid" content="urn:ereader-lab:alpha:1"/></head><docTitle><text>ALPHA Feature Probe</text></docTitle><navMap><navPoint id="one" playOrder="1"><navLabel><text>Chapter One</text></navLabel><content src="first.xhtml"/></navPoint><navPoint id="two" playOrder="2"><navLabel><text>Chapter Two</text></navLabel><content src="second.xhtml"/></navPoint></navMap></ncx>''',
        'OEBPS/first.xhtml': chapter,
        'OEBPS/second.xhtml': '''<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml"><head><title>Chapter Two</title></head><body><h1>Chapter Two</h1><p>BETA SECOND CHAPTER.</p><p id="note">NOTE ONE: internal link target.</p></body></html>''',
    }
    path = directory / 'alpha.epub'
    with ZipFile(path, 'w') as archive:
        for name, text in files.items():
            info = ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_STORED if name == 'mimetype' else ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, text.encode())
    (directory / 'control.txt').write_text('TXT CONTROL. SD access works if this text appears.\n' * 30)
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(directory.iterdir()) if p.is_file()}

if __name__ == '__main__':
    print(json.dumps(create(ROOT / 'fixtures/generated'), indent=2))
