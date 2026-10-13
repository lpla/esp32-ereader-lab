"""Exercise a firmware-free first setup and actionable readiness failures."""
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from doctor import packaged
from engine_packages import select_files


class DeveloperSetupTests(unittest.TestCase):
    def test_selected_setup_needs_no_closed_firmware_or_other_engines(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'scripts').mkdir()
            (root / 'downloads').mkdir()
            for name in ('prepare.py', 'engine_packages.py', 'engines.py'):
                shutil.copyfile(ROOT / 'scripts' / name, root / 'scripts' / name)
            archive = root / 'downloads/esp-emu-0.49.0-x86_64-unknown-linux-gnu.tar.gz'
            with tarfile.open(archive, 'w:gz') as package:
                member = tarfile.TarInfo('test-engine/esp-emu')
                member.size = 6
                package.addfile(member, io.BytesIO(b'pinned'))
            entry = dict(file=archive.name, bytes=archive.stat().st_size,
                         sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
            files = [entry, dict(file='qemu.tar.xz'), dict(file='closed-stock.bin')]
            (root / 'downloads/manifest.json').write_text(json.dumps(dict(files=files)))
            command = [sys.executable, str(root / 'scripts/prepare.py'),
                       '--engine', 'esp-emu', '--esp-version', '0.49.0']
            subprocess.run(command, check=True, capture_output=True)
            self.assertEqual((root / 'tools/test-engine/esp-emu').read_bytes(), b'pinned')
            self.assertEqual(list((root / 'firmware').iterdir()), [])
            archive.write_bytes(b'corrupt')
            failure = subprocess.run([command[0], '-O', *command[1:]], capture_output=True, text=True)
            self.assertNotEqual(failure.returncode, 0)
            self.assertIn('Package mismatch', failure.stderr)

    def test_selection_is_identical_for_downloader_and_preparer(self):
        files = json.loads((ROOT / 'downloads/manifest.json').read_text())['files']
        for version in ('0.45.0', '0.48.0', '0.49.0'):
            selected = select_files(files, 'all', version)
            self.assertEqual(len(selected), 2)
            self.assertEqual(len(select_files(files, 'esp-emu', version)), 1)
            self.assertFalse(any(f['file'].endswith('.bin') or 'wasm' in f['file'] for f in selected))
        with self.assertRaises(ValueError):
            select_files([], 'qemu')

    def test_doctor_without_docker_returns_remediation_and_json(self):
        with tempfile.TemporaryDirectory() as empty_path:
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/doctor.py'), '--json'],
                                    env={**os.environ, 'PATH': empty_path}, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report['ready'])
        docker = next(c for c in report['checks'] if c['name'] == 'Docker CLI')
        self.assertFalse(docker['ok'])
        self.assertIn('Install Docker', docker['fix'])
        self.assertNotIn('Traceback', result.stderr)

    def test_doctor_rejects_guest_source_drift(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'firmware').mkdir()
            (root / 'firmware/image.bin').write_bytes(b'image')
            (root / 'source.cpp').write_bytes(b'source')
            (root / 'firmware/wifi-ap.json').write_text(json.dumps(dict(
                image='firmware/image.bin', image_sha256=hashlib.sha256(b'image').hexdigest(),
                sources={'source.cpp': hashlib.sha256(b'source').hexdigest()})))
            self.assertTrue(packaged('wifi-ap', root)[0])
            (root / 'source.cpp').write_bytes(b'changed')
            self.assertFalse(packaged('wifi-ap', root)[0])


if __name__ == '__main__':
    unittest.main()
