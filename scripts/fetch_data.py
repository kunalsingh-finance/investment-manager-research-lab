"""Acquire and pin public raw inputs. Existing snapshots are never overwritten."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import sys
import tempfile

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from managerlab.data import SYMBOLS, chart_monthly_prices, parse_french_zip, sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, default=ROOT / 'data' / 'raw')
    args = parser.parse_args()
    target = args.destination.resolve()
    if target.exists():
        raise SystemExit(f'Snapshot already exists: {target}. Use a different --destination for a new vintage.')
    target.parent.mkdir(parents=True, exist_ok=True)
    start = int(datetime(2015, 12, 1, tzinfo=timezone.utc).timestamp())
    end = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp())
    session = requests.Session()
    session.headers['User-Agent'] = 'Mozilla/5.0 MeridianResearchEducational/1.0'
    records = []
    with tempfile.TemporaryDirectory(prefix='.acquire-', dir=target.parent) as temp:
        stage = Path(temp)
        for symbol in SYMBOLS:
            url = f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}'
            response = session.get(url, params={'period1': start, 'period2': end, 'interval': '1d', 'events': 'div,splits,capitalGains'}, timeout=45)
            response.raise_for_status()
            monthly = chart_monthly_prices(response.json(), symbol)
            content = response.content
            packed = gzip.compress(content, mtime=0)
            filename = f'{symbol}.json.gz'
            (stage / filename).write_bytes(packed)
            records.append({'name': symbol, 'file': filename, 'url': response.url,
                            'retrieved_at': datetime.now(timezone.utc).isoformat(),
                            'sha256': sha256(packed), 'content_sha256': sha256(content),
                            'monthly_prices': len(monthly), 'source_type': 'vendor_adjusted_close'})
            print(f'{symbol}: {len(monthly)} verified month-end prices', flush=True)
        url = 'https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_5_Factors_2x3_CSV.zip'
        response = session.get(url, timeout=45)
        response.raise_for_status()
        factors = parse_french_zip(response.content)
        filename = 'ff5_monthly.zip'
        (stage / filename).write_bytes(response.content)
        records.append({'name': 'Fama-French 5 factors', 'file': filename, 'url': url,
                        'retrieved_at': datetime.now(timezone.utc).isoformat(), 'sha256': sha256(response.content),
                        'months': len(factors), 'source_type': 'academic_factor_archive'})
        manifest = {'schema_version': 1, 'label': 'Pinned public-source retrospective research snapshot',
                    'retrieved_at': datetime.now(timezone.utc).isoformat(),
                    'measurement_start': '2016-01-31', 'measurement_end': '2025-12-31',
                    'return_convention': 'Monthly change in last daily vendor adjusted close; distribution-adjusted total-return proxy. Fund expenses already embedded; taxes, loads, dealing costs and investor cash flows excluded.',
                    'limitations': [
                        'Current vendor and academic data vintage, not data known at each historical date.',
                        'Four selected surviving funds; no complete peer universe or survivorship correction.',
                        'ETF adjusted market-price benchmarks are analyst-selected proxies, not official index/NAV returns or verified fund prospectus benchmarks.',
                        'Vendor distribution adjustments are not independently reconciled to fund administrator records.',
                        'Historical returns and regressions cannot establish manager skill or predict returns.',
                        'Team, process, capacity, liquidity and operational diligence remain outstanding.',
                        'Style weights are a constrained returns-based fit to three correlated proxies, not observed holdings.',
                        'This is a research demonstration; no orders, client portfolios or automatic manager approvals.'
                    ], 'records': records}
        (stage / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        target.mkdir()
        for path in stage.iterdir():
            path.replace(target / path.name)
    print(f'Pinned {len(records)} sources at {target}')


if __name__ == '__main__':
    main()
