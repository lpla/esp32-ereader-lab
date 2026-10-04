"""Keep failed, incomplete and mismatched historical runs out of positive reports."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from check_image_heap import compare, inspect
from check_machine import compare as compare_machine

EVIDENCE = ROOT / 'evidence/2026-10-04'


class HistoryTests(unittest.TestCase):
    def test_original_and_revised_dither_results_match_across_engines(self):
        results = []
        for engine in ('qemu', 'esp'):
            results.append(compare(EVIDENCE / f'history-image-final-base-{engine}',
                                   EVIDENCE / f'history-image-final-head-{engine}'))
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0]['pressure']['atkinson1'], {'base': True, 'head': False})
        self.assertTrue(results[0]['all_cleanup_recovered'])

    def test_reject_missing_case_failed_cleanup_or_incomplete_run(self):
        source = EVIDENCE / 'history-image-final-head-esp'
        for edit in (lambda d: d.update(completed=False),
                     lambda d: d['records'].pop(2),
                     lambda d: d['records'][2].update(recovered=False)):
            with tempfile.TemporaryDirectory() as tmp:
                directory = Path(tmp)
                shutil.copyfile(source / 'input.json', directory / 'input.json')
                data = json.loads((source / 'result.json').read_text())
                edit(data)
                (directory / 'result.json').write_text(json.dumps(data))
                with self.assertRaises(ValueError):
                    inspect(directory)

    def test_reject_different_pixel_output(self):
        source = EVIDENCE / 'history-image-final-head-esp'
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            shutil.copyfile(source / 'input.json', directory / 'input.json')
            data = json.loads((source / 'result.json').read_text())
            data['records'][2]['hash'] ^= 1
            (directory / 'result.json').write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                compare(EVIDENCE / 'history-image-final-base-esp', directory)

    def test_xtch_control_keeps_observed_heap_difference(self):
        result = compare_machine(EVIDENCE / 'history-xtch6001-turn-qemu',
                                 EVIDENCE / 'history-xtch6001-turn-esp')
        self.assertTrue(result['logical_sd_counts_equal'])
        self.assertFalse(result['heap_equal'])
        self.assertEqual(result['first']['heap']['largest'], result['second']['heap']['largest'])
        self.assertEqual(result['second']['checkpoint']['rendered_pages'], 2)


if __name__ == '__main__':
    unittest.main()
