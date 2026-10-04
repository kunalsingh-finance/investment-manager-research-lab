"""Build the complete offline research workspace from pinned sources."""
from __future__ import annotations

import csv
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from managerlab.analytics import analyze
from managerlab.data import load_snapshot, sha256

METRICS = ['cagr', 'benchmark_cagr', 'active_cagr', 'volatility', 'sharpe',
           'max_drawdown', 'tracking_error', 'information_ratio', 'beta',
           'up_capture', 'down_capture', 'positive_active_months', 'observations']


def model_fingerprints():
    files = [ROOT / 'config/universe.json', ROOT / 'data/raw/manifest.json', ROOT / 'web/template.html',
             ROOT / 'scripts/build_report.py', *sorted((ROOT / 'managerlab').glob('*.py'))]
    return {p.relative_to(ROOT).as_posix(): sha256(p.read_bytes()) for p in files}


def main():
    output = ROOT / 'output'
    output.mkdir(exist_ok=True)
    # A running/failed refresh cannot masquerade as the last successful report.
    status = output / 'status.json'
    status.write_text(json.dumps({'status': 'building'}), encoding='utf-8')
    try:
        returns, factors, manifest, prices = load_snapshot(ROOT)
        universe = json.loads((ROOT / 'config/universe.json').read_text(encoding='utf-8'))
        result = analyze(returns, factors, universe)
        result['source'] = manifest
        result['project_version'] = '1.0.0'
        result['monitoring_policy'] = {'window_months': 36, 'active_cagr_below': -.02,
                                       'down_capture_above': 1.10, 'style_drift_above': .25,
                                       'posture': 'Illustrative research triggers; qualitative diligence required.'}
        serialized = json.dumps(result, ensure_ascii=False, allow_nan=False, sort_keys=True)
        safe_json = serialized.replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e')
        template = (ROOT / 'web/template.html').read_text(encoding='utf-8')
        if template.count('__REPORT_JSON__') != 1:
            raise ValueError('Expected exactly one report JSON placeholder')
        rows = []
        for fund in result['funds']:
            for window, benchmarks in fund['windows'].items():
                for benchmark, details in benchmarks.items():
                    rows.append({'ticker': fund['ticker'], 'window_months': int(window), 'benchmark': benchmark,
                                 **{key: details[key] for key in METRICS}})
        with tempfile.TemporaryDirectory(prefix='.build-', dir=output) as directory:
            stage = Path(directory)
            (stage / 'report.html').write_text(template.replace('__REPORT_JSON__', safe_json), encoding='utf-8')
            (stage / 'research.json').write_text(serialized, encoding='utf-8')
            returns.to_csv(stage / 'monthly_returns.csv', index_label='date', float_format='%.15g')
            factors.to_csv(stage / 'monthly_factors.csv', index_label='date', float_format='%.15g')
            prices.to_csv(stage / 'adjusted_month_end_prices.csv', index_label='date', float_format='%.15g')
            with (stage / 'metrics.csv').open('w', newline='', encoding='utf-8') as handle:
                writer = csv.DictWriter(handle, fieldnames=['ticker', 'window_months', 'benchmark'] + METRICS)
                writer.writeheader()
                writer.writerows(rows)
            import pandas as pd
            with closing(sqlite3.connect(stage / 'research.sqlite')) as conn:
                returns.rename_axis('date').reset_index().melt(id_vars='date', var_name='ticker', value_name='return').to_sql('monthly_returns', conn, index=False)
                factors.rename_axis('date').reset_index().to_sql('monthly_factors', conn, index=False)
                pd.DataFrame(universe).to_sql('funds', conn, index=False)
                pd.DataFrame(rows).to_sql('metrics', conn, index=False)
                pd.DataFrame(manifest['records']).to_sql('sources', conn, index=False)
                conn.execute('CREATE UNIQUE INDEX return_key ON monthly_returns(date, ticker)')
                conn.execute('CREATE UNIQUE INDEX metric_key ON metrics(ticker, window_months, benchmark)')
                conn.commit()
            artifacts = {path.name: sha256(path.read_bytes()) for path in stage.iterdir()}
            build = {'status': 'complete', 'as_of': result['as_of'], 'monthly_observations': int(returns.size),
                     'funds': len(universe), 'sources': len(manifest['records']), 'artifacts': artifacts,
                     'model_fingerprints': model_fingerprints()}
            (stage / 'build_manifest.json').write_text(json.dumps(build, indent=2), encoding='utf-8')
            for path in stage.iterdir():
                path.replace(output / path.name)
        status.write_text(json.dumps({'status': 'complete', 'as_of': result['as_of']}), encoding='utf-8')
        print(f"Built {len(universe)} funds, {returns.shape[0]} months, {len(rows)} benchmark/window comparisons.")
        print(output / 'report.html')
    except Exception as error:
        status.write_text(json.dumps({'status': 'failed', 'error': str(error)}), encoding='utf-8')
        (output / 'report.html').write_text('<!doctype html><html lang="en"><title>Research build failed</title><body><h1>Research build failed</h1><p>The latest inputs did not pass validation. Rebuild successfully before using the saved results. See status.json for diagnostics.</p></body></html>', encoding='utf-8')
        raise


if __name__ == '__main__':
    main()
