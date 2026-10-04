"""Auditable monthly investment-manager analytics.

All inputs and outputs use decimal returns. The study is fixed to 120 monthly
observations from January 2016 through December 2025. There is no imputation.
Benchmark-relative metrics use fund and benchmark returns over the same window.
Sharpe and beta use the supplied contemporaneous monthly risk-free rate.

FF5 inference uses OLS with Newey-West covariance (Bartlett weights, three lags,
n/(n-k) finite-sample correction), normal 95% intervals, and an arithmetic
annualization of the monthly intercept. These intervals do not establish skill.
"""

from __future__ import annotations

from collections.abc import Sequence
import math

import numpy as np
import pandas as pd
from scipy.optimize import minimize


BENCHMARKS = ("SPY", "IWF", "IWD", "VIG")
STYLE_LABELS = ("IWF", "IWD", "IWM")
FACTOR_LABELS = ("Mkt-RF", "SMB", "HML", "RMW", "CMA")
EXPECTED_MONTHS = pd.period_range("2016-01", "2025-12", freq="M")
_EPS = 1e-14


def _number(value: float | None) -> float | None:
    """Convert numerical scalars to strict-JSON finite numbers."""
    if value is None:
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def _date(value: pd.Timestamp) -> str:
    return value.strftime("%Y-%m-%d")


def _cagr(values: np.ndarray) -> float | None:
    if len(values) == 0:
        return None
    return _number(np.expm1(np.log1p(values).mean() * 12.0))


def _ratio(numerator: float, denominator: float) -> float | None:
    if not math.isfinite(denominator) or abs(denominator) <= _EPS:
        return None
    return _number(numerator / denominator)


def _r_squared(actual: np.ndarray, fitted: np.ndarray) -> float | None:
    centered_ss = float(np.square(actual - actual.mean()).sum())
    if centered_ss <= _EPS:
        return None
    return _number(1.0 - np.square(actual - fitted).sum() / centered_ss)


def _capture(fund: np.ndarray, benchmark: np.ndarray, up: bool) -> float | None:
    """Geometric annualized capture on strictly up/down benchmark months."""
    mask = benchmark > 0 if up else benchmark < 0
    if not np.any(mask):
        return None
    fund_cagr = _cagr(fund[mask])
    benchmark_cagr = _cagr(benchmark[mask])
    if fund_cagr is None or benchmark_cagr is None:
        return None
    return _ratio(fund_cagr, benchmark_cagr)


def _detail(fund: pd.Series, benchmark: pd.Series, rf: pd.Series) -> dict:
    """Compute one matched fund/benchmark window, including baseline wealth."""
    y = fund.to_numpy(dtype=float)
    b = benchmark.to_numpy(dtype=float)
    cash = rf.to_numpy(dtype=float)
    active = y - b
    excess = y - cash
    benchmark_excess = b - cash
    wealth = 100.0 * np.concatenate(([1.0], np.cumprod(1.0 + y)))
    benchmark_wealth = 100.0 * np.concatenate(([1.0], np.cumprod(1.0 + b)))
    drawdowns = wealth / np.maximum.accumulate(wealth) - 1.0
    dates = [fund.index[0] - pd.offsets.MonthEnd(1), *fund.index]
    annual_vol = float(y.std(ddof=1) * np.sqrt(12))
    annual_excess_vol = float(excess.std(ddof=1) * np.sqrt(12))
    tracking_error = float(active.std(ddof=1) * np.sqrt(12))
    benchmark_var = float(benchmark_excess.var(ddof=1))
    fund_cagr = _cagr(y)
    benchmark_cagr = _cagr(b)
    return {
        "cagr": fund_cagr,
        "benchmark_cagr": benchmark_cagr,
        # A CAGR difference, not the CAGR of monthly active returns.
        "active_cagr": _number(fund_cagr - benchmark_cagr)
        if fund_cagr is not None and benchmark_cagr is not None else None,
        "volatility": _number(annual_vol),
        "sharpe": _ratio(float(excess.mean() * 12), annual_excess_vol),
        "max_drawdown": _number(drawdowns.min()),
        "tracking_error": _number(tracking_error),
        "information_ratio": _ratio(float(active.mean() * 12), tracking_error),
        "beta": _ratio(float(np.cov(excess, benchmark_excess, ddof=1)[0, 1]), benchmark_var),
        "up_capture": _capture(y, b, up=True),
        "down_capture": _capture(y, b, up=False),
        "positive_active_months": _number(np.mean(active > 0)),
        "observations": int(len(y)),
        "growth": [
            {"date": _date(date), "fund": _number(fw), "benchmark": _number(bw), "drawdown": _number(dd)}
            for date, fw, bw, dd in zip(dates, wealth, benchmark_wealth, drawdowns)
        ],
    }


def _fit_style(fund: np.ndarray, proxies: np.ndarray) -> tuple[np.ndarray, float | None]:
    """Long-only, fully-invested least-squares return-based style fit.

    The fit has no intercept or cash sleeve. Scaling both sides to percentage
    points improves solver conditioning without changing the minimizer.
    """
    y = np.asarray(fund, dtype=float) * 100.0
    x = np.asarray(proxies, dtype=float) * 100.0
    n = len(y)

    def objective(weights: np.ndarray) -> float:
        return float(np.square(x @ weights - y).mean())

    def jacobian(weights: np.ndarray) -> np.ndarray:
        return 2.0 * x.T @ (x @ weights - y) / n

    fitted = minimize(
        objective,
        np.full(x.shape[1], 1.0 / x.shape[1]),
        jac=jacobian,
        method="SLSQP",
        bounds=[(0.0, 1.0)] * x.shape[1],
        constraints={"type": "eq", "fun": lambda w: w.sum() - 1.0,
                     "jac": lambda w: np.ones_like(w)},
        options={"ftol": 1e-12, "maxiter": 1000},
    )
    weights = np.asarray(fitted.x, dtype=float)
    feasible = (
        np.isfinite(weights).all()
        and abs(weights.sum() - 1.0) <= 1e-8
        and weights.min() >= -1e-8
        and weights.max() <= 1.0 + 1e-8
    )
    if not fitted.success or not feasible:
        raise ValueError(f"Style optimization failed or returned infeasible weights: {fitted.message}")
    # Remove machine-precision bound violations only after checking feasibility.
    weights = np.clip(weights, 0.0, 1.0)
    weights /= weights.sum()
    return weights, _r_squared(y, x @ weights)


def _style(fund: pd.Series, returns: pd.DataFrame) -> dict:
    proxies = returns.loc[:, STYLE_LABELS].to_numpy(dtype=float)
    y = fund.to_numpy(dtype=float)
    previous, _ = _fit_style(y[-72:-36], proxies[-72:-36])
    current, r_squared = _fit_style(y[-36:], proxies[-36:])
    history = []
    for end in range(36, len(y) + 1, 3):
        weights, rolling_r_squared = _fit_style(y[end - 36:end], proxies[end - 36:end])
        history.append({"date": _date(fund.index[end - 1]),
                        "weights": [float(v) for v in weights],
                        "r_squared": rolling_r_squared})
    return {"labels": list(STYLE_LABELS),
            "previous": [float(v) for v in previous],
            "current": [float(v) for v in current],
            "turnover": float(np.abs(current - previous).sum() / 2.0),
            "history": history, "r_squared": r_squared}


def _factor(fund: pd.Series, factors: pd.DataFrame) -> dict:
    y = fund.to_numpy(dtype=float) - factors["RF"].to_numpy(dtype=float)
    x = np.column_stack((np.ones(len(y)), factors.loc[:, FACTOR_LABELS].to_numpy(dtype=float)))
    n, k = x.shape
    coefficients, _, rank, _ = np.linalg.lstsq(x, y, rcond=None)
    if rank < k:
        raise ValueError("FF5 factor design is rank deficient; alpha inference is not identifiable")
    residual = y - x @ coefficients
    scores = x * residual[:, None]
    meat = scores.T @ scores
    for lag in range(1, 4):
        cross = scores[lag:].T @ scores[:-lag]
        meat += (1.0 - lag / 4.0) * (cross + cross.T)
    bread = np.linalg.inv(x.T @ x)
    covariance = (bread @ meat @ bread) * n / (n - k)
    alpha_se = math.sqrt(max(0.0, float(covariance[0, 0])))
    alpha_monthly = float(coefficients[0])
    return {
        "alpha_ann": _number(12.0 * alpha_monthly),
        "alpha_ci_low": _number(12.0 * (alpha_monthly - 1.96 * alpha_se)),
        "alpha_ci_high": _number(12.0 * (alpha_monthly + 1.96 * alpha_se)),
        "alpha_t": _ratio(alpha_monthly, alpha_se),
        "r_squared": _r_squared(y, x @ coefficients),
        "observations": int(n),
        "betas": {name: _number(value) for name, value in zip(FACTOR_LABELS, coefficients[1:])},
    }


def _validate_frame(frame: pd.DataFrame, label: str) -> None:
    if not isinstance(frame, pd.DataFrame):
        raise ValueError(f"{label} must be a pandas DataFrame")
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise ValueError(f"{label} must have a DatetimeIndex")
    if frame.index.tz is not None:
        raise ValueError(f"{label} index must be timezone-naive month ends")
    if frame.index.hasnans or not frame.index.is_unique or not frame.index.is_monotonic_increasing:
        raise ValueError(f"{label} index must be unique, sorted, and free of missing dates")
    if not frame.columns.is_unique:
        raise ValueError(f"{label} columns must be unique")
    if len(frame) < 72:
        raise ValueError(f"{label} needs at least 72 monthly observations for nonoverlapping style windows")
    if not frame.index.is_month_end.all() or not (frame.index == frame.index.normalize()).all():
        raise ValueError(f"{label} index must contain month-end dates at midnight")
    months = frame.index.to_period("M")
    if len(months) != len(EXPECTED_MONTHS) or not months.equals(EXPECTED_MONTHS):
        raise ValueError(f"{label} must cover exactly 120 contiguous months from January 2016 through December 2025")
    try:
        values = frame.to_numpy(dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} values must be numeric") from exc
    if not np.isfinite(values).all():
        raise ValueError(f"{label} has missing or non-finite values; imputation is not permitted")


def _validate(returns: pd.DataFrame, factors: pd.DataFrame, universe: Sequence[dict]) -> None:
    _validate_frame(returns, "returns")
    _validate_frame(factors, "factors")
    if not returns.index.equals(factors.index):
        raise ValueError("returns and factors must have identical month-end indices")
    if (returns.to_numpy(dtype=float) <= -1).any():
        raise ValueError("returns must be greater than -1")
    missing_factors = set((*FACTOR_LABELS, "RF")) - set(factors.columns)
    if missing_factors:
        raise ValueError(f"Missing factor columns: {', '.join(sorted(missing_factors))}")
    if (factors["RF"].to_numpy(dtype=float) <= -1).any():
        raise ValueError("RF returns must be greater than -1")
    if not isinstance(universe, (list, tuple)) or not universe:
        raise ValueError("universe must be a non-empty list of fund definitions")
    required_keys = {"ticker", "name", "mandate", "benchmark", "issuer_url"}
    tickers = []
    for item in universe:
        if not isinstance(item, dict) or not required_keys.issubset(item):
            raise ValueError("Each universe entry needs ticker, name, mandate, benchmark, and issuer_url")
        if not all(isinstance(item[key], str) and item[key].strip() for key in required_keys):
            raise ValueError("Universe definition fields must be non-empty strings")
        if item["benchmark"] not in BENCHMARKS:
            raise ValueError(f"Unsupported declared benchmark: {item['benchmark']}")
        tickers.append(item["ticker"])
    if len(tickers) != len(set(tickers)):
        raise ValueError("Universe tickers must be unique")
    missing_symbols = set((*tickers, *BENCHMARKS, *STYLE_LABELS)) - set(returns.columns)
    if missing_symbols:
        raise ValueError(f"Missing return symbols: {', '.join(sorted(missing_symbols))}")


def analyze(returns: pd.DataFrame, factors: pd.DataFrame, universe: list[dict]) -> dict:
    """Return strict-JSON-compatible manager diagnostics for the fixed study.

    Mandates and declared benchmarks are illustrative analyst selections.
    Flags are prompts for review, never automated investment recommendations.
    """
    _validate(returns, factors, universe)
    funds = []
    for definition in universe:
        ticker = definition["ticker"]
        windows = {
            str(months): {
                benchmark: _detail(returns[ticker].iloc[-months:], returns[benchmark].iloc[-months:],
                                   factors["RF"].iloc[-months:])
                for benchmark in BENCHMARKS
            }
            for months in (36, 60, 120)
        }
        style = _style(returns[ticker], returns)
        factor = _factor(returns[ticker], factors)
        declared = windows["36"][definition["benchmark"]]
        flags = []
        if declared["active_cagr"] is not None and declared["active_cagr"] < -0.02:
            flags.append({"code": "relative_underperformance", "severity": "warning",
                          "message": "Trailing 36-month CAGR trails the declared benchmark by more than 2 percentage points; review drivers."})
        if declared["down_capture"] is not None and declared["down_capture"] > 1.10:
            flags.append({"code": "downside_capture", "severity": "warning",
                          "message": "Trailing 36-month downside capture exceeds 110% versus the declared benchmark; review downside exposure."})
        if style["turnover"] > 0.25:
            flags.append({"code": "style_drift", "severity": "warning",
                          "message": "Estimated style weights shifted by more than 25% between nonoverlapping 36-month windows; investigate mandate consistency."})
        if not flags:
            flags.append({"code": "stable_monitoring", "severity": "info",
                          "message": "No configured monitoring threshold was breached; continue qualitative and quantitative review."})
        flags.append({"code": "illustrative_benchmark", "severity": "info",
                      "message": "Mandate and declared benchmark are illustrative analyst selections, not claims about the fund's official benchmark. Monitoring flags do not establish manager skill."})
        funds.append({**{key: definition[key] for key in ("ticker", "name", "mandate", "benchmark", "issuer_url")},
                      "windows": windows, "style": style, "factor": factor, "flags": flags})
    return {"as_of": _date(returns.index[-1]), "start_date": _date(returns.index[0]),
            "months": int(len(returns)), "funds": funds}
