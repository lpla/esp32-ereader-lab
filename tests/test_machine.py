"""Reject incomplete machine/packet evidence and verify recorded engine controls."""
import copy
import json
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from check_machine import compare,inspect
from check_soc import check
from fast_inputs import jump


class MachineTests(unittest.TestCase):
    def test_recorded_engine_controls(self):
        evidence=ROOT/'evidence/2026-10-04'
        result=compare(evidence/'machine-symbol-profile-qemu',evidence/'machine-symbol-profile-esp')
        self.assertTrue(result['heap_equal'])
        self.assertTrue(result['logical_sd_counts_equal'])
        self.assertEqual(result['first']['checkpoint']['rendered_pages'],2)
        self.assertFalse(result['physical_performance_valid'])

    def test_reject_timeout_failed_sd_or_incomplete_render(self):
        source=ROOT/'evidence/2026-10-04/machine-symbol-profile-qemu'
        for name,edit in [
            ('status.json',lambda d:d.update(gdb_exit='interrupted_for_snapshot')),
            ('sd-events.json',lambda d:d[0].update(result=0)),
            ('checkpoint.json',lambda d:d.update(rendered_pages=1)),
        ]:
            with self.subTest(name=name),tempfile.TemporaryDirectory() as tmp:
                directory=Path(tmp)
                for file in ('status.json','input.json','checkpoint.json','guest.log','sd-events.json'):
                    shutil.copyfile(source/file,directory/file)
                data=json.loads((directory/name).read_text());edit(data)
                (directory/name).write_text(json.dumps(data))
                with self.assertRaises(ValueError):inspect(directory)

    def test_packet_edges_are_required_and_fail_closed(self):
        evidence=ROOT/'evidence/2026-10-04'
        base=json.loads((evidence/'tcp-edge-base/status.json').read_text())
        patched=json.loads((evidence/'tcp-edge-patched/status.json').read_text())
        self.assertEqual(check(base,patched,True)['summaries']['patched']['edge_cases_passed'],11)
        altered=copy.deepcopy(patched)
        next(r for r in altered['records'] if r['kind']=='LAB_EDGE')['pass']=False
        with self.assertRaises(ValueError):check(base,altered,True)
        altered=copy.deepcopy(patched)
        altered['records']=[r for r in altered['records'] if r['kind']!='LAB_EDGE']
        with self.assertRaises(ValueError):check(base,altered,True)

    def test_absolute_runtime_jump_signed_lower_immediate(self):
        for target in (0x50001600,0x50001fff,0x40385000):
            upper,lower,branch=struct.unpack('<III',jump(target))
            self.assertEqual(upper&0xfff,(5<<7)|0x37)
            self.assertEqual(lower&0xfffff,(5<<15)|(5<<7)|0x13)
            self.assertEqual(branch,(5<<15)|0x67)
            immediate=lower>>20
            if immediate&0x800:immediate-=4096
            self.assertEqual(((upper&0xfffff000)+immediate)&0xffffffff,target)


if __name__=='__main__':unittest.main()
