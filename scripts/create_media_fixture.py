"""Original EPUB with external CSS and a known lossless embedded image."""
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_STORED, ZIP_DEFLATED
import tempfile
from create_fixtures import ROOT, create
from render_display import png


def create_media(directory):
    create(directory)
    with ZipFile(directory / 'alpha.epub') as source:
        files = {n: source.read(n) for n in source.namelist()}
    files['OEBPS/content.opf'] = files['OEBPS/content.opf'].replace(b'ALPHA Feature Probe', b'BETA Style and Image Probe').replace(b'urn:ereader-lab:alpha:1', b'urn:ereader-lab:beta:1').replace(b'</manifest>', b'<item id="css" href="styles.css" media-type="text/css"/><item id="img" href="probe.png" media-type="image/png"/></manifest>')
    files['OEBPS/toc.ncx'] = files['OEBPS/toc.ncx'].replace(b'ALPHA Feature Probe',b'BETA Style and Image Probe').replace(b'urn:ereader-lab:alpha:1',b'urn:ereader-lab:beta:1')
    files['OEBPS/first.xhtml'] = b'''<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml"><head><title>Style Probe</title><link rel="stylesheet" type="text/css" href="styles.css"/></head><body><h1>STYLE PROBE</h1><p class="center">CENTER LINE</p><p class="right">RIGHT LINE</p><p class="indent">INDENT LINE</p><p>Regular, <b>BOLD</b>, <i>ITALIC</i>, <u>UNDERLINE</u>.</p><p><img src="probe.png" alt="IMAGE PROBE" width="128" height="80"/></p><p>IMAGE END MARKER.</p><p>Line one<br/>Line two.</p><ul><li>First bullet</li><li>Second bullet</li></ul></body></html>'''
    files['OEBPS/styles.css'] = b'.center {text-align:center;} .right {text-align:right;} .indent {text-indent:2em;} h1 {text-align:center;}'
    pixels = bytearray(b'\xff' * (16 * 80))
    for y in range(80):
        for x in range(128):
            if x in (0,127) or y in (0,79) or (16<=x<112 and 16<=y<64 and ((x//16+y//16)%2==0)):
                pixels[y*16+x//8] &= ~(0x80>>(x%8))
    with tempfile.TemporaryDirectory() as tmp:
        image=Path(tmp)/'probe.png';png(image,128,80,pixels);files['OEBPS/probe.png']=image.read_bytes()
    path=directory/'beta.epub'
    with ZipFile(path,'w') as archive:
        for name,data in files.items():
            info=ZipInfo(name,(2026,1,1,0,0,0));info.compress_type=ZIP_STORED if name=='mimetype' else ZIP_DEFLATED;info.external_attr=0o644<<16
            archive.writestr(info,data)
    return path

if __name__=='__main__':
    print(create_media(ROOT/'fixtures/generated'))
