"""Verify published evidence integrity and the reading-position identity claim."""
import hashlib
import json
from pathlib import Path
import unittest

BASE = Path(__file__).resolve().parents[1] / 'evidence/2026-10-04'


class EvidenceTests(unittest.TestCase):
    def test_archive_hashes(self):
        for manifest in BASE.glob('*/archive.json'):
            data = json.loads(manifest.read_text())
            for name, expected in data['files_sha256'].items():
                with self.subTest(archive=manifest.parent.name, file=name):
                    self.assertEqual(hashlib.sha256((manifest.parent / name).read_bytes()).hexdigest(), expected)

    def test_reopen_identity(self):
        data = json.loads((BASE / 'comparison.json').read_text())
        for engine, pair in data['reading_position_identity'].items():
            with self.subTest(engine=engine):
                before = (BASE / pair['before']).read_bytes()
                after = (BASE / pair['after']).read_bytes()
                self.assertEqual(before, after)
                self.assertEqual(hashlib.sha256(after).hexdigest(), pair['sha256'])


if __name__ == '__main__':
    unittest.main()
