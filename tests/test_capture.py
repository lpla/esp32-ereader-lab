"""Exercise display composition using independently placed expected pixels."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from render_display import render, portrait


class CaptureTests(unittest.TestCase):
    def test_partial_invert_mirror_and_retention(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'full.bin').write_bytes(b'\xff' * 48000)
            (root / 'part.bin').write_bytes(b'\x80\x40')
            writes = [dict(file='full.bin', x=0, y=0, width=800, height=480,
                           invert=False, mirror_y=False),
                      dict(file='part.bin', x=3, y=4, width=2, height=2,
                           invert=True, mirror_y=True)]
            (root / 'display-writes.json').write_text(json.dumps(writes))
            self.assertEqual(render(root), 2)
            expected = bytearray(b'\xff' * 48000)
            # Mirrored row 0 is 01; invert makes 10. Row 1 becomes 01.
            expected[4 * 100] &= ~0x08  # x=4,y=4
            expected[5 * 100] &= ~0x10  # x=3,y=5
            self.assertEqual((root / 'panel-ram.bin').read_bytes(), expected)
            self.assertTrue((root / 'screen.png').read_bytes().startswith(b'\x89PNG\r\n\x1a\n'))

    def test_orientation_corners(self):
        panel = bytearray(b'\xff' * 48000)
        panel[0] = 0x7f
        expected = bytearray(b'\xff' * 48000)
        expected[59] = 0xfe  # (0,0) maps to (479,0)
        self.assertEqual(portrait(panel), expected)

    def test_archived_screen_identity(self):
        base = Path(__file__).resolve().parents[1] / 'evidence/2026-10-04'
        a = (base / 'qemu-x4-settings/screen.png').read_bytes()
        b = (base / 'validated-settings-native-esp-emu-x4-app-x3-layout-settings/screen.png').read_bytes()
        self.assertEqual(a, b)
        self.assertEqual(hashlib.sha256(a).hexdigest(),
                         '2dc4eb10a7d5f21d0bffa40c775acb6588c4934efa914e0604ec72de1d7fbe40')


if __name__ == '__main__':
    unittest.main()
