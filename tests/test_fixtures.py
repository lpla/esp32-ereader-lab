"""Validate that comparison fixtures exercise the documented EPUB contracts."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_STORED
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from create_fixtures import create
from create_media_fixture import create_media
from create_chapter_fixture import create_chapters


class FixtureTests(unittest.TestCase):
    def test_epub_structure_and_pinned_hashes(self):
        expected = {'alpha.epub': '9cfb793219cb30489e65e5568a469b0f2958be70ce44ed175fdcc220121ba604',
                    'beta.epub': '7f36a1727e0f1821e04581ca7f46e00441b0f109843693efbe100d6ba9737fa5'}
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            create(directory); create_media(directory); create_chapters(directory)
            for name in ('alpha.epub', 'beta.epub', 'gamma.epub'):
                data = (directory / name).read_bytes()
                if name in expected:
                    self.assertEqual(hashlib.sha256(data).hexdigest(), expected[name])
                with ZipFile(directory / name) as archive:
                    self.assertEqual(archive.namelist()[0], 'mimetype')
                    self.assertEqual(archive.getinfo('mimetype').compress_type, ZIP_STORED)
                    self.assertEqual(archive.read('mimetype'), b'application/epub+zip')
                    for member in archive.namelist():
                        if member.endswith(('.xml', '.opf', '.ncx', '.xhtml')):
                            ET.fromstring(archive.read(member))
                    opf = ET.fromstring(archive.read('OEBPS/content.opf'))
                    ns = {'o': 'http://www.idpf.org/2007/opf'}
                    items = {item.attrib['id']: item for item in opf.findall('o:manifest/o:item', ns)}
                    for item in items.values():
                        self.assertIn('OEBPS/' + item.attrib['href'], archive.namelist())
                    spine = opf.findall('o:spine/o:itemref', ns)
                    self.assertEqual(len(spine), 120 if name == 'gamma.epub' else 2)
                    for ref in spine:
                        self.assertIn(ref.attrib['idref'], items)
            gamma = (directory / 'gamma.epub').read_bytes()
            create_chapters(directory)
            self.assertEqual(gamma, (directory / 'gamma.epub').read_bytes())


if __name__ == '__main__':
    unittest.main()
