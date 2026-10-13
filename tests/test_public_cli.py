"""Exercise the public interface and reject misleading component-test passes."""
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from firmware_contract import image_layout, verdict


def merged_image(chip_id=5):
    data = bytearray(b'\xff' * 0x10100)
    for offset in (0, 0x10000):
        data[offset] = 0xe9
        struct.pack_into('<H', data, offset + 12, chip_id)
    struct.pack_into('<HBBII16sI', data, 0x8000, 0x50aa, 0, 0, 0x10000, 0x100000, b'factory', 0)
    return data


class PublicCliTests(unittest.TestCase):
    def cli(self, *args, cwd=None):
        return subprocess.run([sys.executable, str(ROOT / 'lab.py'), *args],
                              cwd=cwd, capture_output=True, text=True)

    def test_profiles_work_outside_checkout_without_tools(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.cli('profiles', '--json', cwd=directory)
        self.assertEqual(result.returncode, 0, result.stderr)
        profiles = json.loads(result.stdout)
        self.assertEqual(profiles['default_esp_version'], '0.49.0')
        self.assertEqual({p['id'] for p in profiles['profiles']}, {'ap', 'reader', 'file-transfer'})
        self.assertIn('not arbitrary builds', next(p['scope'] for p in profiles['profiles'] if p['id'] == 'reader'))

    def test_custom_build_requires_explicit_project_and_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.cli('build', '--project', directory)
        self.assertEqual(result.returncode, 2)
        self.assertIn('--environment', result.stderr)
        self.assertNotIn('Traceback', result.stderr)

    def test_custom_build_preserves_failure_and_complete_log(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'scripts').mkdir()
            (root / 'config').mkdir()
            (root / 'project').mkdir()
            (root / 'project/platformio.ini').write_text('[env:test]\n')
            shutil.copyfile(ROOT / 'lab.py', root / 'lab.py')
            shutil.copyfile(ROOT / 'config/profiles.json', root / 'config/profiles.json')
            for name in ('engines.py', 'run_lab.py', 'render_display.py'):
                shutil.copyfile(ROOT / 'scripts' / name, root / 'scripts' / name)
            tool = root / 'pio'
            tool.write_text(f'#!{sys.executable}\nimport sys\nprint("FULL_BUILD_DIAGNOSTIC")\nprint(sys.argv[1:])\nsys.exit(7)\n')
            tool.chmod(0o755)
            result = subprocess.run([sys.executable, str(root / 'lab.py'), 'build',
                                     '--project', 'project', '--environment', 'test'], cwd=root,
                                    env={**os.environ, 'PATH': str(root) + os.pathsep + os.environ['PATH']},
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 7)
            logs = list((root / 'results/build-logs').glob('*.log'))
            self.assertEqual(len(logs), 1)
            self.assertIn('FULL_BUILD_DIAGNOSTIC', logs[0].read_text())
            self.assertIn(str(root / 'project'), logs[0].read_text())
            self.assertIn('Build failed:', result.stdout)
            self.assertNotIn('Traceback', result.stderr)

    def test_public_run_rejects_invalid_budget_and_path_traversal(self):
        for options in (['--name', '../outside'], ['--name', 'valid-new-name', '--seconds', '0']):
            result = self.cli('run', '--profile', 'reader', *options)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn('Traceback', result.stderr)

    def test_transfer_doctor_rejects_unsupported_engine_without_ready_claim(self):
        result = self.cli('doctor', '--profile', 'file-transfer', '--engine', 'qemu', '--json')
        self.assertEqual(result.returncode, 2)
        self.assertIn('requires esp-emulator', result.stderr)
        self.assertEqual(result.stdout, '')

    def test_ota_and_other_chip_fail_before_launching_docker(self):
        self.assertEqual(image_layout(merged_image(), 'esp32c3')['images'][1]['offset'], 0x10000)
        with self.assertRaisesRegex(ValueError, 'chip ID'):
            image_layout(merged_image(9), 'esp32c3')
        with self.assertRaisesRegex(ValueError, 'merged flash'):
            image_layout(merged_image()[:0x100], 'esp32c3')
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / 'ota.bin'
            image.write_bytes(merged_image()[:0x100])
            result = self.cli('firmware', '--image', str(image), '--name', 'unused-ota', '--expect', 'PASS')
        self.assertEqual(result.returncode, 1)
        self.assertIn('merged flash', result.stderr)
        self.assertNotIn('Traceback', result.stderr)

    def test_exit_and_marker_alone_cannot_hide_faults(self):
        self.assertTrue(verdict('TEST_PASS\n', 'TEST_PASS', 0, False)['passed'])
        for uart, code, timed_out in [('nothing', 0, False), ('TEST_PASS', 1, False),
                                     ('TEST_PASS', 0, True), ('TEST_PASS\nGuru Meditation Error', 0, False),
                                     ('TEST_PASS\nBus fault: unmapped 0x0', 0, False),
                                     ('TEST_PASS\nassert failed: test.cpp', 0, False),
                                     ('TEST_PASS\nabort() was called', 0, False)]:
            self.assertFalse(verdict(uart, 'TEST_PASS', code, timed_out)['passed'], uart)


if __name__ == '__main__':
    unittest.main()
