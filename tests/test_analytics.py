"""Numerical contracts and failure cases, independent of downloaded fund data."""

import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from managerlab import analyze
from managerlab.analytics import _capture, _detail, _factor, _fit_style, _style


@pytest.fixture
def study():
    rng = np.random.default_rng(104)
    index = pd.date_range("2016-01-31", "2025-12-31", freq="ME")
    returns = pd.DataFrame(rng.normal(0.007, 0.04, (120, 6)), index=index,
                           columns=["FCNTX", "SPY", "IWF", "IWD", "VIG", "IWM"])
    factors = pd.DataFrame(rng.normal(0, 0.025, (120, 5)), index=index,
                           columns=["Mkt-RF", "SMB", "HML", "RMW", "CMA"])
    factors["RF"] = 0.002
    universe = [{"ticker": "FCNTX", "name": "Test fund", "mandate": "Illustrative equity",
                 "benchmark": "SPY", "issuer_url": "https://example.org/fund"}]
    return returns, factors, universe


def detail(fund, benchmark, rf=None):
    index = pd.date_range("2020-01-31", periods=len(fund), freq="ME")
    return _detail(pd.Series(fund, index=index), pd.Series(benchmark, index=index),
                   pd.Series(np.zeros(len(fund)) if rf is None else rf, index=index))


def test_initial_loss_is_in_maximum_drawdown_and_growth():
    result = detail([-0.2, 0.1, 0.0], [0.01, 0.01, 0.01])
    assert result["max_drawdown"] == pytest.approx(-0.2)
    assert result["growth"][0] == {"date": "2019-12-31", "fund": 100.0,
                                   "benchmark": 100.0, "drawdown": 0.0}
    assert result["growth"][1]["fund"] == pytest.approx(80.0)
    assert result["growth"][-1]["fund"] == pytest.approx(88.0)
    assert len(result["growth"]) == result["observations"] + 1


def test_equal_benchmark_has_zero_tracking_error_and_undefined_ir():
    series = [0.03, -0.02, 0.01, -0.04, 0.06, 0.02]
    result = detail(series, series)
    assert result["active_cagr"] == pytest.approx(0)
    assert result["tracking_error"] == pytest.approx(0)
    assert result["information_ratio"] is None
    assert result["beta"] == pytest.approx(1)
    assert result["up_capture"] == pytest.approx(1)
    assert result["down_capture"] == pytest.approx(1)
    assert result["positive_active_months"] == 0


def test_geometric_cagr_difference_is_not_active_return_cagr():
    result = detail([0.1, -0.1] * 6, [0.02] * 12)
    assert result["cagr"] == pytest.approx(0.99 ** 6 - 1)
    assert result["benchmark_cagr"] == pytest.approx(1.02 ** 12 - 1)
    assert result["active_cagr"] == pytest.approx(0.99 ** 6 - 1.02 ** 12)
    assert result["active_cagr"] != pytest.approx((1.08 * 0.88) ** 6 - 1)


def test_capture_uses_matching_benchmark_subsets_and_excludes_flat_months():
    fund = np.array([0.02, -0.03, 0.5, 0.04, -0.01])
    benchmark = np.array([0.01, -0.02, 0.0, 0.03, -0.04])
    expected_up = ((1.02 * 1.04) ** 6 - 1) / ((1.01 * 1.03) ** 6 - 1)
    expected_down = ((0.97 * 0.99) ** 6 - 1) / ((0.98 * 0.96) ** 6 - 1)
    assert _capture(fund, benchmark, up=True) == pytest.approx(expected_up)
    assert _capture(fund, benchmark, up=False) == pytest.approx(expected_down)
    assert _capture(fund, np.ones(5) * 0.01, up=False) is None
    assert _capture(fund, np.zeros(5), up=True) is None


def test_sharpe_and_beta_use_monthly_risk_free_returns():
    rf = np.array([0.001, 0.003, 0.002, 0.004])
    benchmark_excess = np.array([0.02, -0.01, 0.03, -0.02])
    fund_excess = 1.7 * benchmark_excess + 0.003
    result = detail(fund_excess + rf, benchmark_excess + rf, rf)
    assert result["beta"] == pytest.approx(1.7)
    expected_sharpe = fund_excess.mean() / fund_excess.std(ddof=1) * np.sqrt(12)
    assert result["sharpe"] == pytest.approx(expected_sharpe)


def test_zero_volatility_statistics_are_null():
    result = detail([0.01] * 12, [0.02] * 12)
    assert result["sharpe"] is None
    assert result["beta"] is None
    assert result["information_ratio"] is None
    assert result["down_capture"] is None
    assert result["max_drawdown"] == 0


def test_style_recovers_known_long_only_mixture():
    rng = np.random.default_rng(45)
    proxies = rng.normal(0.008, 0.04, (72, 3))
    expected = np.array([0.6, 0.3, 0.1])
    weights, r_squared = _fit_style(proxies @ expected, proxies)
    np.testing.assert_allclose(weights, expected, atol=1e-7)
    assert r_squared == pytest.approx(1)


def test_style_boundary_solution_is_feasible():
    rng = np.random.default_rng(46)
    proxies = rng.normal(0.008, 0.04, (72, 3))
    weights, _ = _fit_style(proxies[:, 0], proxies)
    np.testing.assert_allclose(weights, [1, 0, 0], atol=1e-7)
    assert np.all(weights >= 0)
    assert weights.sum() == pytest.approx(1)


@pytest.mark.parametrize("success,weights", [(False, [0.3, 0.3, 0.4]),
                                               (True, [1.1, -0.1, 0]),
                                               (True, [0.1, 0.1, 0.1])])
def test_style_rejects_failed_or_infeasible_solver(monkeypatch, success, weights):
    monkeypatch.setattr("managerlab.analytics.minimize", lambda *a, **kw:
                        SimpleNamespace(success=success, x=np.array(weights), message="test"))
    with pytest.raises(ValueError, match="Style optimization failed"):
        _fit_style(np.ones(36), np.ones((36, 3)))


def test_style_windows_do_not_overlap_and_history_has_no_look_ahead(study):
    returns, _, _ = study
    returns.loc[:, "FCNTX"] = returns["IWF"]
    returns.loc[returns.index[-36:], "FCNTX"] = returns["IWD"].iloc[-36:]
    original = _style(returns["FCNTX"], returns)
    np.testing.assert_allclose(original["previous"], [1, 0, 0], atol=1e-7)
    np.testing.assert_allclose(original["current"], [0, 1, 0], atol=1e-7)
    assert original["turnover"] == pytest.approx(1, abs=1e-7)
    assert original["history"][0]["date"] == "2018-12-31"
    assert original["history"][-1]["date"] == "2025-12-31"
    assert len(original["history"]) == 29
    changed = returns.copy()
    changed.iloc[72:] = changed.iloc[72:] * -0.5 + 0.2
    later = _style(changed["FCNTX"], changed)
    # Every estimate dated before the changed future is unchanged to solver
    # precision; pandas block consolidation can change BLAS rounding.
    original_early = [row for row in original["history"] if row["date"] <= "2021-12-31"]
    later_early = [row for row in later["history"] if row["date"] <= "2021-12-31"]
    assert [row["date"] for row in original_early] == [row["date"] for row in later_early]
    np.testing.assert_allclose([row["weights"] for row in original_early],
                               [row["weights"] for row in later_early], atol=1e-8)
    np.testing.assert_allclose([row["r_squared"] for row in original_early],
                               [row["r_squared"] for row in later_early], atol=1e-10)


def test_ff5_known_coefficients_and_hac_interval_on_orthogonal_design(study):
    _, factors, _ = study
    n = len(factors)
    t = np.arange(n)
    x = np.column_stack([0.03 * np.sin(2 * np.pi * harmonic * t / n)
                         for harmonic in range(1, 6)])
    factor_names = ["Mkt-RF", "SMB", "HML", "RMW", "CMA"]
    factors.loc[:, factor_names] = x
    coefficients = np.array([1.1, -0.2, 0.3, 0.15, -0.1])
    residual = 0.01 * np.cos(2 * np.pi * 2 * t / n)
    alpha = 0.001
    fund = pd.Series(factors["RF"].to_numpy() + alpha + x @ coefficients + residual,
                     index=factors.index)
    result = _factor(fund, factors)
    # Regressors and residual are centered and orthogonal, making the intercept
    # HAC variance a scalar lag-covariance sum, independent of the matrix code.
    meat = float(residual @ residual)
    for lag in (1, 2, 3):
        meat += 2 * (1 - lag / 4) * sum(residual[j] * residual[j - lag] for j in range(lag, n))
    se = np.sqrt(meat / (n * (n - 6)))
    assert result["alpha_ann"] == pytest.approx(alpha * 12, abs=1e-12)
    np.testing.assert_allclose(list(result["betas"].values()), coefficients, atol=1e-12)
    assert result["alpha_ci_low"] == pytest.approx(12 * (alpha - 1.96 * se))
    assert result["alpha_ci_high"] == pytest.approx(12 * (alpha + 1.96 * se))
    assert result["alpha_t"] == pytest.approx(alpha / se)
    assert result["observations"] == 120


def test_rank_deficient_ff5_fails_explicitly(study):
    returns, factors, _ = study
    factors["SMB"] = factors["HML"]
    with pytest.raises(ValueError, match="rank deficient"):
        _factor(returns["FCNTX"], factors)


def test_analyze_contract_is_strict_json_and_benchmarks_stay_selectable(study):
    result = analyze(*study)
    json.dumps(result, allow_nan=False)
    assert result["months"] == 120
    assert result["start_date"] == "2016-01-31"
    assert result["as_of"] == "2025-12-31"
    fund = result["funds"][0]
    assert set(fund["windows"]) == {"36", "60", "120"}
    for length, windows in fund["windows"].items():
        assert set(windows) == {"SPY", "IWF", "IWD", "VIG"}
        assert all(value["observations"] == int(length) for value in windows.values())
    assert any(flag["code"] == "illustrative_benchmark" for flag in fund["flags"])


def test_monitoring_flags_use_declared_benchmark(study):
    returns, factors, universe = study
    returns["FCNTX"] = returns["IWF"]
    returns["SPY"] = returns["IWF"] + 0.01
    universe[0]["benchmark"] = "IWF"
    result = analyze(returns, factors, universe)["funds"][0]
    assert "relative_underperformance" not in {flag["code"] for flag in result["flags"]}
    universe[0]["benchmark"] = "SPY"
    result = analyze(returns, factors, universe)["funds"][0]
    assert "relative_underperformance" in {flag["code"] for flag in result["flags"]}


@pytest.mark.parametrize("invalid", [np.nan, np.inf, -np.inf, -1, -1.1])
def test_invalid_returns_are_rejected_without_filling(study, invalid):
    returns, factors, universe = study
    returns.iloc[7, 0] = invalid
    with pytest.raises(ValueError):
        analyze(returns, factors, universe)


def test_missing_symbol_is_rejected(study):
    returns, factors, universe = study
    with pytest.raises(ValueError, match="Missing return symbols: IWM"):
        analyze(returns.drop(columns="IWM"), factors, universe)


def test_missing_factor_is_rejected(study):
    returns, factors, universe = study
    with pytest.raises(ValueError, match="Missing factor columns: HML"):
        analyze(returns, factors.drop(columns="HML"), universe)


@pytest.mark.parametrize("mutation", ["duplicate", "unsorted", "missing", "short", "wrong_year", "midmonth"])
def test_bad_monthly_coverage_is_rejected(study, mutation):
    returns, factors, universe = study
    if mutation == "duplicate":
        index = list(returns.index)
        index[10] = index[9]
        returns.index = index
    elif mutation == "unsorted":
        returns = returns.iloc[::-1]
    elif mutation == "missing":
        returns = returns.drop(returns.index[10])
    elif mutation == "short":
        returns = returns.iloc[-60:]
    elif mutation == "wrong_year":
        returns.index = returns.index + pd.offsets.MonthEnd(12)
    elif mutation == "midmonth":
        returns.index = returns.index - pd.Timedelta(days=1)
    with pytest.raises(ValueError):
        analyze(returns, factors, universe)
