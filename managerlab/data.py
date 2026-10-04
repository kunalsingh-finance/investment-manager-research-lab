"""Verified source ingestion. No network calls, imputation, or synthetic fallback."""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

SYMBOLS = ('FCNTX', 'TRBCX', 'DODGX', 'PRDGX', 'SPY', 'IWF', 'IWD', 'VIG', 'IWM')
FACTOR_COLUMNS = ['Mkt-RF', 'SMB', 'HML', 'RMW', 'CMA', 'RF']


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _chart_dates(payload: dict) -> pd.DatetimeIndex:
    timestamps = payload['chart']['result'][0]['timestamp']
    return pd.to_datetime(timestamps, unit='s', utc=True).tz_localize(None).normalize()


def chart_monthly_prices(payload: dict, symbol: str, *,
                         expected_session_dates: pd.Series | None = None) -> pd.Series:
    if payload['chart'].get('error'):
        raise ValueError(f'{symbol}: source returned an error')
    result = payload['chart']['result'][0]
    if result['meta']['symbol'] != symbol or result['meta']['currency'] != 'USD':
        raise ValueError(f'{symbol}: symbol/currency mismatch')
    dates = _chart_dates(payload)
    prices = result['indicators']['adjclose'][0]['adjclose']
    series = pd.Series(prices, index=dates, dtype=float, name=symbol)
    if not series.index.is_unique or not series.index.is_monotonic_increasing:
        raise ValueError(f'{symbol}: duplicate or unsorted dates')
    if not np.isfinite(series).all() or (series <= 0).any():
        raise ValueError(f'{symbol}: invalid adjusted prices')
    series = series.loc['2015-12-01':'2025-12-31']
    monthly = series.resample('ME').last()
    expected = pd.date_range('2015-12-31', '2025-12-31', freq='ME')
    if not monthly.index.equals(expected) or monthly.isna().any():
        raise ValueError(f'{symbol}: incomplete monthly price coverage')
    for end, group in series.groupby(pd.Grouper(freq='ME')):
        if len(group) < 15 or (end - group.index[-1]).days > 4:
            raise ValueError(f'{symbol}: incomplete daily observations at {end.date()}')
    if expected_session_dates is not None:
        observation_dates = series.index.to_series().resample('ME').last()
        if not observation_dates.equals(expected_session_dates):
            raise ValueError(f'{symbol}: month-end observation dates do not match SPY reference')
    return monthly


def parse_french_zip(content: bytes) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        names = [x for x in archive.namelist() if x.lower().endswith('.csv')]
        if len(names) != 1:
            raise ValueError('Expected one French factor CSV')
        source = archive.read(names[0]).decode('utf-8-sig')
    rows = [line for line in source.splitlines() if re.match(r'^\s*\d{6}\s*,', line)]
    table = pd.read_csv(io.StringIO('\n'.join(rows)), header=None, names=['date'] + FACTOR_COLUMNS)
    table.index = pd.to_datetime(table.pop('date').astype(str), format='%Y%m') + pd.offsets.MonthEnd(0)
    if not table.index.is_unique or not table.index.is_monotonic_increasing:
        raise ValueError('Duplicate or unsorted factor months')
    table = table.loc['2016-01-31':'2025-12-31'] / 100.0
    expected = pd.date_range('2016-01-31', '2025-12-31', freq='ME')
    if not table.index.equals(expected) or not np.isfinite(table.to_numpy()).all():
        raise ValueError('Incomplete factor coverage')
    if (table.abs() >= .9).any().any():
        raise ValueError('Invalid factor units or missing-value sentinel')
    return table


def load_snapshot(root: Path):
    raw = root / 'data' / 'raw'
    manifest = json.loads((raw / 'manifest.json').read_text(encoding='utf-8'))
    payloads = {}
    factors = None
    records = manifest['records']
    if {r['name'] for r in records} != set(SYMBOLS) | {'Fama-French 5 factors'} or len(records) != 10:
        raise ValueError('Unexpected source inventory')
    for record in records:
        filename = record['file']
        if Path(filename).name != filename:
            raise ValueError('Source filename must be a basename')
        content = (raw / filename).read_bytes()
        if sha256(content) != record['sha256']:
            raise ValueError(f"Source hash mismatch: {record['name']}")
        if record['name'] == 'Fama-French 5 factors':
            factors = parse_french_zip(content)
        else:
            decoded = gzip.decompress(content)
            if sha256(decoded) != record['content_sha256']:
                raise ValueError('Decompressed source hash mismatch')
            payloads[record['name']] = json.loads(decoded)
    # SPY supplies a shared observed trading-session calendar. This catches an
    # isolated missing final fund/ETF price, rather than silently using a stale
    # close. It does not independently prove completeness of the SPY calendar.
    prices = {'SPY': chart_monthly_prices(payloads['SPY'], 'SPY')}
    spy_dates = _chart_dates(payloads['SPY']).to_series().loc['2015-12-01':'2025-12-31']
    expected_session_dates = spy_dates.resample('ME').last()
    for symbol, payload in payloads.items():
        if symbol != 'SPY':
            prices[symbol] = chart_monthly_prices(payload, symbol,
                                                  expected_session_dates=expected_session_dates)
    monthly_prices = pd.DataFrame(prices).loc[:, list(SYMBOLS)]
    returns = monthly_prices.pct_change(fill_method=None).iloc[1:]
    if factors is None or not factors.index.equals(returns.index):
        raise ValueError('Factors do not align with returns')
    return returns, factors, manifest, monthly_prices
