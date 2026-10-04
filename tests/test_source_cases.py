"""Keep source claims attached to cases and reject incorrect machine verdicts."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from check_soc import check
from run_feature import compile_case


class SourceCaseTests(unittest.TestCase):
    def test_catalog_references(self):
        catalog = json.loads((ROOT / 'cases/catalog.json').read_text())
        ids = [f['id'] for f in catalog['features']]
        self.assertEqual(len(ids), len(set(ids)))
        for feature in catalog['features']:
            self.assertTrue(feature['expected_semantic_result'])
            for source in feature['sources']:
                self.assertIn(source, catalog['sources'])
            for evidence in feature['evidence']:
                self.assertTrue((ROOT / evidence).is_file(), evidence)
        for path in (ROOT / 'cases').glob('*.json'):
            if path.name == 'catalog.json':
                continue
            case = json.loads(path.read_text())
            self.assertIn(case['source'], catalog['sources'])
            self.assertTrue(case['expected'])
            compile_case(case)

    def load_runs(self):
        return [json.loads((ROOT / f'evidence/2026-10-04/tcp-df-{label}/status.json').read_text())
                for label in ('base', 'patched')]

    def test_recorded_guest_contract(self):
        base, patched = self.load_runs()
        self.assertTrue(check(base, patched)['contract_pass'])

    def test_reject_packet_regressions(self):
        base, patched = self.load_runs()
        for field, value in [('tcp_df', 0), ('udp_df', 1), ('bad_ip_checksums', 1)]:
            altered = copy.deepcopy(patched)
            next(r for r in altered['records'] if r['kind'] == 'LAB_PACKETS')[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                check(base, altered)

    def test_reject_missing_cycle_or_heap_corruption(self):
        base, patched = self.load_runs()
        altered = copy.deepcopy(patched)
        altered['records'] = [r for r in altered['records'] if not (r['kind'] == 'LAB_TCP' and r['cycle'] == 2)]
        with self.assertRaises(ValueError):
            check(base, altered)
        altered = copy.deepcopy(patched)
        next(r for r in altered['records'] if r['kind'] == 'LAB_HEAP')['integrity'] = False
        with self.assertRaises(ValueError):
            check(base, altered)


if __name__ == '__main__':
    unittest.main()
