"""Source integrity and data-coverage checks, including intentionally damaged inputs."""
import copy
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from managerlab.data import chart_monthly_prices, load_snapshot

ROOT = Path(__file__).resolve().parents[1]


class SourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(gzip.decompress((ROOT / 'data/raw/FCNTX.json.gz').read_bytes()))

    def test_complete_real_snapshot(self):
        returns, factors, manifest, prices = load_snapshot(ROOT)
        self.assertEqual(returns.shape, (120, 9))
        self.assertEqual(factors.shape, (120, 6))
        self.assertEqual(prices.shape, (121, 9))
        self.assertEqual(len(manifest['records']), 10)
        np.testing.assert_allclose((1 + returns).prod(), prices.iloc[-1] / prices.iloc[0], atol=1e-12)

    def test_wrong_symbol_fails(self):
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            chart_monthly_prices(self.payload, 'TRBCX')

    def test_null_adjusted_price_fails(self):
        payload = copy.deepcopy(self.payload)
        payload['chart']['result'][0]['indicators']['adjclose'][0]['adjclose'][10] = None
        with self.assertRaisesRegex(ValueError, 'invalid adjusted prices'):
            chart_monthly_prices(payload, 'FCNTX')

    def test_duplicate_date_fails(self):
        payload = copy.deepcopy(self.payload)
        result = payload['chart']['result'][0]
        result['timestamp'][1] = result['timestamp'][0]
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            chart_monthly_prices(payload, 'FCNTX')

    def test_missing_last_month_fails(self):
        payload = copy.deepcopy(self.payload)
        result = payload['chart']['result'][0]
        result['timestamp'] = result['timestamp'][:-30]
        result['indicators']['adjclose'][0]['adjclose'] = result['indicators']['adjclose'][0]['adjclose'][:-30]
        with self.assertRaisesRegex(ValueError, 'coverage'):
            chart_monthly_prices(payload, 'FCNTX')

    def test_corrupted_source_fails_before_analytics(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'data/raw'
            target.mkdir(parents=True)
            manifest = (ROOT / 'data/raw/manifest.json').read_bytes()
            (target / 'manifest.json').write_bytes(manifest)
            (target / 'FCNTX.json.gz').write_bytes(b'damaged bytes')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                load_snapshot(Path(directory))

    def test_missing_final_session_fails_cross_symbol_alignment(self):
        # A source can have 20+ valid December observations and still omit the
        # actual final session. Keep hashes internally consistent to exercise
        # the observation-date check rather than the corruption check.
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'data/raw'
            target.mkdir(parents=True)
            manifest = json.loads((ROOT / 'data/raw/manifest.json').read_text(encoding='utf-8'))
            for record in manifest['records']:
                content = (ROOT / 'data/raw' / record['file']).read_bytes()
                if record['name'] == 'FCNTX':
                    payload = json.loads(gzip.decompress(content))
                    result = payload['chart']['result'][0]
                    result['timestamp'].pop()
                    result['indicators']['adjclose'][0]['adjclose'].pop()
                    decoded = json.dumps(payload).encode('utf-8')
                    content = gzip.compress(decoded)
                    record['sha256'] = hashlib.sha256(content).hexdigest()
                    record['content_sha256'] = hashlib.sha256(decoded).hexdigest()
                (target / record['file']).write_bytes(content)
            (target / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'FCNTX: month-end observation dates do not match SPY'):
                load_snapshot(Path(directory))


if __name__ == '__main__':
    unittest.main()
