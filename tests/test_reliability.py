"""Reject corrupt payloads, unsafe evidence assumptions and executable drift."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from engines import engine
from diagnostics import diagnostics
from probe_ap import validate
from create_chapter_fixture import create_chapters
from check_machine import inspect
import shutil
from zipfile import ZipFile


class ReliabilityTests(unittest.TestCase):
    def test_engine_pin_rejects_changed_binary_and_unknown_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'adapters').mkdir();(root/'emu').write_bytes(b'pinned')
            (root/'adapters/engines.json').write_text(json.dumps({'esp-emu-0.48.0':dict(path='emu',version='0.48.0',sha256=hashlib.sha256(b'pinned').hexdigest())}))
            self.assertEqual(engine('esp-emu',root=root)[1]['version'],'0.48.0')
            with self.assertRaises(ValueError):engine('esp-emu','0.49.0',root=root)
            (root/'emu').write_bytes(b'changed')
            with self.assertRaises(ValueError):engine('esp-emu',root=root)

    def test_fault_attribution_does_not_hide_warnings_or_extra_faults(self):
        uart='Bus fault: read8 unmapped 0x00000000\n'
        trace='[remote] Sending packet: $m0,2#fb\n[remote] Packet received: E14\n'
        d=diagnostics(uart,remote_log=trace)
        self.assertEqual(d['debugger_read_faults'],1)
        self.assertFalse(d['modeled_execution_clean'])
        self.assertEqual(diagnostics(uart+uart,remote_log=trace)['unexplained_bus_faults'],2)
        self.assertEqual(diagnostics('Guru Meditation Error: Core 0 panic\n')['guest_panics'],1)

    def test_ap_evidence_rejects_missing_transfer_corruption_and_teardown(self):
        evidence=ROOT/'evidence/2026-10-08/ap48-restart/result.json'
        result=json.loads(evidence.read_text());self.assertTrue(validate(result))
        for mutate in (
            lambda r:r['transfers'].pop(),
            lambda r:r['transfers'][0]['response'].update(bytes=1),
            lambda r:r.update(records=[e for e in r['records'] if e.get('phase')!='off']),
            lambda r:r.update(done=False),
        ):
            altered=copy.deepcopy(result);mutate(altered)
            with self.assertRaises(ValueError):validate(altered)

    def test_large_epub_is_distinct_and_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=create_chapters(Path(tmp),3001,'omega');before=p.read_bytes()
            with ZipFile(p) as z:
                self.assertEqual(len([n for n in z.namelist() if n.endswith('.xhtml')]),3001)
                self.assertIn(b'GAMMA CHAPTER 3001 TARGET',z.read('OEBPS/c3001.xhtml'))
            self.assertEqual(create_chapters(Path(tmp),3001,'omega').read_bytes(),before)

    def test_current_activity_paint_is_required(self):
        source=ROOT/'evidence/2026-10-08/checkpoint2-qemu-xtch'
        self.assertTrue(inspect(source)['activity_paint_verified'])
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp)
            for file in source.iterdir():
                if file.is_file():shutil.copyfile(file,d/file.name)
            frames=json.loads((d/'display-writes.json').read_text());frames[-1]['activity']='XtcReader'
            (d/'display-writes.json').write_text(json.dumps(frames))
            with self.assertRaises(ValueError):inspect(d)

    def test_crosspoint_ap_rejects_wrong_download_and_unexecuted_reset_claim(self):
        source=ROOT/'evidence/2026-10-08/crosspoint-ap-upload'
        self.assertTrue(inspect(source)['web_ap_completed'])
        for file,edit in [('http-result.json',lambda r:r.update(downloaded_sha256='wrong')),
                          ('checkpoint.json',lambda r:r.update(reset_executed=True))]:
            with self.subTest(file=file),tempfile.TemporaryDirectory() as tmp:
                d=Path(tmp)
                for p in source.iterdir():
                    if p.is_file():shutil.copyfile(p,d/p.name)
                r=json.loads((d/file).read_text());edit(r);(d/file).write_text(json.dumps(r))
                with self.assertRaises(ValueError):inspect(d)
