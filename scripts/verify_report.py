"""Verify source/artifact integrity and recompute all saved analytics offline."""
from __future__ import annotations

import json
from contextlib import closing
from pathlib import Path
import sqlite3
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from managerlab.analytics import analyze
from managerlab.data import load_snapshot, sha256


def compare(actual, expected, path='root'):
    """Keep exact structure while allowing harmless BLAS/solver roundoff."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise ValueError(f'Object mismatch: {path}')
        for key in expected:
            compare(actual[key], expected[key], f'{path}.{key}')
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise ValueError(f'List mismatch: {path}')
        for i, (a, e) in enumerate(zip(actual, expected)):
            compare(a, e, f'{path}[{i}]')
    elif isinstance(expected, (int, float)) and not isinstance(expected, bool):
        if not isinstance(actual, (int, float)) or not np.isclose(actual, expected, rtol=1e-9, atol=1e-10):
            raise ValueError(f'Numerical mismatch: {path}')
    elif actual != expected:
        raise ValueError(f'Value mismatch: {path}')


def main():
    output = ROOT / 'output'
    status = json.loads((output / 'status.json').read_text())
    if status['status'] != 'complete':
        raise ValueError('Latest build is not complete')
    build = json.loads((output / 'build_manifest.json').read_text())
    for filename, expected in build['artifacts'].items():
        if sha256((output / filename).read_bytes()) != expected:
            raise ValueError(f'Artifact hash mismatch: {filename}')
    for filename, expected in build['model_fingerprints'].items():
        if sha256((ROOT / filename).read_bytes()) != expected:
            raise ValueError(f'Model/input changed; rebuild required: {filename}')
    returns, factors, manifest, prices = load_snapshot(ROOT)
    universe = json.loads((ROOT / 'config/universe.json').read_text(encoding='utf-8'))
    recomputed = analyze(returns, factors, universe)
    saved = json.loads((output / 'research.json').read_text(encoding='utf-8'))
    for key in recomputed:
        compare(saved[key], recomputed[key], key)
    if saved['source'] != manifest:
        raise ValueError('Source manifest mismatch')
    exported = pd.read_csv(output / 'monthly_returns.csv', index_col='date', parse_dates=True)
    np.testing.assert_allclose(exported, returns, atol=1e-14, rtol=1e-12)
    # Independent multiplicative-return identity against the underlying prices.
    for fund in saved['funds']:
        ticker = fund['ticker']
        d = fund['windows']['120'][fund['benchmark']]
        independent = (prices[ticker].iloc[-1] / prices[ticker].iloc[0]) ** .1 - 1
        np.testing.assert_allclose(d['cagr'], independent, atol=1e-12)
    with closing(sqlite3.connect(output / 'research.sqlite')) as conn:
        count = conn.execute('SELECT COUNT(*) FROM monthly_returns').fetchone()[0]
        if count != returns.size:
            raise ValueError('SQLite return count mismatch')
        db_returns = pd.read_sql_query('SELECT date,ticker,return FROM monthly_returns', conn)
        db_returns['date'] = pd.to_datetime(db_returns['date'])
        db_returns = db_returns.pivot(index='date', columns='ticker', values='return')[returns.columns]
        np.testing.assert_allclose(db_returns, returns, atol=1e-15)
        if conn.execute('SELECT COUNT(*) FROM metrics').fetchone()[0] != 48:
            raise ValueError('SQLite comparison count mismatch')
    print(f"PASS: 10 source hashes, {len(build['artifacts'])} artifacts, full analytic recomputation, CSV/SQL reconciliation, independent price-to-CAGR checks.")


if __name__ == '__main__':
    main()
