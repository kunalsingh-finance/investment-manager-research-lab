# Methodology

This lab supports a public-fund analyst's review of performance, benchmark fit, and changes in return behavior. Its outputs are research evidence and questions for further diligence. They do not establish manager skill, verify a manager's stated process, or make an automatic hiring, retention, or termination decision.

The workflow draws on the distinction between quantitative appraisal and qualitative investment and operational due diligence in CFA Institute's [Investment Manager Selection](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/investment-manager-selection). The lab implements a limited quantitative review. An actual mandate decision also needs evidence about people, investment process, organization, vehicle terms, and operations.

## Review universe and measurement period

The evaluation period is January 2016 through December 2025: 120 monthly returns. A December 2015 month-end adjusted price supplies the starting value. This is a retrospective analysis of a declared set of surviving funds. It is not a point-in-time selection exercise or a representative mutual-fund database.

| Fund ticker | Analyst-assigned comparison proxy | Purpose in this lab |
| --- | --- | --- |
| FCNTX | IWF | Compare with a large-cap growth ETF return series |
| TRBCX | IWF | Compare with the same growth-oriented proxy |
| DODGX | IWD | Compare with a large-cap value ETF return series |
| PRDGX | VIG | Compare with a dividend-appreciation ETF return series |

These assignments are project assumptions. They are **not assertions about the funds' official prospectus benchmarks**. SPY supplies a broad large-cap comparison. IWF, IWD, and IWM form the limited style-analysis basis. These are investable ETF return proxies with their own expenses and tracking differences; they are not frictionless index returns.

The fund names identify real public funds. Monitoring thresholds, benchmark assignments, analyst notes, and committee workflow are illustrative project choices rather than the policies of a real investment organization.

## Inputs, provenance, and return convention

Daily adjusted-close histories come from Yahoo Finance's public chart responses. The research uses the current downloaded vendor vintage for a fixed historical measurement period. Saved raw responses and SHA-256 hashes identify the source bytes used in a build. A hash verifies file identity; it does not prove independent reconciliation to an issuer, historical availability, or a license to redistribute vendor data.

For each calendar month, the final available daily adjusted price defines the month-end observation. The monthly return is:

```text
r[t] = adjusted_price[t] / adjusted_price[t-1] - 1
```

Adjusted prices incorporate the vendor's distribution and split adjustments. They provide a distribution-aware return proxy. The lab does not reconstruct each dividend reinvestment transaction, model investor-specific taxes, or reconcile NAVs to a fund administrator. Fund operating expenses are already reflected in the fund NAV return history; the lab does not deduct the expense ratio a second time. Investor sales charges, advisory fees, and other account-specific costs are outside the calculation.

The Fama-French five-factor and risk-free series come from the official [Kenneth R. French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html), using its monthly five-factor archive. Percentage values in the source are converted to decimal returns. The risk-free series is the archive's `RF` column; it is not estimated from an ETF trailing return.

French's library documents a transition to CRSP's CIZ files starting with its January 2025 release. The library's historical series can change with source revisions and methodological updates. A current factor download is therefore not evidence of the values available to an analyst in an earlier year. The source archive and retrieval metadata preserve this lab's particular input vintage.

Monthly observations are aligned by calendar month. The displayed measurement end is separate from the later retrieval date. The 2016-2025 window is fixed for this demonstration rather than selected by a search for the strongest fund result. It is not an out-of-sample test, and no historical investment decision is claimed.

Source loading verifies the saved hashes, ticker and USD currency fields, valid positive adjusted prices, and monthly coverage. The analytics require the exact 120-month aligned window and finite inputs. Missing observations are not filled with zero or replaced with synthetic returns. An undefined ratio is exported as `null`, not as a zero result.

All fund and ETF month-end observation dates must match the last observed SPY session for that month. This rejects an isolated missing final fund price rather than silently substituting a stale close. SPY is a shared observed reference, not an independently verified exchange calendar; a common missing session across every source could remain undetected.

## Performance and benchmark comparisons

Let `r[t]` denote a fund's monthly return, `b[t]` the selected proxy's return, `rf[t]` the monthly risk-free return, and `n` the number of aligned observations. All calculations use decimal returns internally. Standard deviations use the sample convention, with `n - 1` in the denominator.

| Measure | Calculation | Interpretation |
| --- | --- | --- |
| Cumulative return | `product(1 + r[t]) - 1` | Growth over the actual observed interval |
| CAGR | `product(1 + r[t])^(12/n) - 1` | Geometric annualized return |
| CAGR difference | `CAGR(fund) - CAGR(proxy)` | Difference in percentage points per year |
| Annualized volatility | `sd(r) * sqrt(12)` | Annualized dispersion of monthly fund returns |
| Sharpe ratio | `mean(r - rf) / sd(r - rf) * sqrt(12)` | Arithmetic excess-return reward per unit of excess-return variability |
| Tracking error | `sd(r - b) * sqrt(12)` | Variability of monthly arithmetic active returns |
| Information ratio | `mean(r - b) / sd(r - b) * sqrt(12)` | Arithmetic active-return reward per unit of tracking error |
| Benchmark beta | `cov(r - rf, b - rf) / var(b - rf)` | Sensitivity to the selected proxy's excess return |
| Positive active months | `count(r > b) / n` | Fraction of aligned months in which the fund outperformed the proxy |

CAGR difference is not the annualized relative wealth return, and it is not factor-model alpha. The information ratio uses the arithmetic monthly active return; it does not divide CAGR difference by tracking error. Annualization assumes twelve monthly periods per year. Square-root-of-time scaling is a reporting convention and does not establish independent returns.

The application calculates these comparisons over trailing 36, 60, and 120 months for each available comparison proxy. Changing the selected comparison or displayed window changes the comparison evidence. Monitoring rules retain the analyst-assigned proxy and most recent 36-month window so that exploratory chart changes do not silently redefine a policy trigger.

Wealth begins at `W[0] = 1`, then `W[t] = W[t-1] * (1 + r[t])`. Drawdown is `W[t] / max(W[0], ..., W[t]) - 1`; maximum drawdown is its minimum. Including starting wealth ensures that a loss in the first observed month counts. Month-end sampling can miss a deeper decline within a month.

### Capture ratios

Upside months are those with `b[t] > 0`; downside months have `b[t] < 0`. Zero-return benchmark months belong to neither subset. For a selected subset `S` containing `k` months:

```text
fund_subset_return = product(1 + r[t], t in S)^(12/k) - 1
proxy_subset_return = product(1 + b[t], t in S)^(12/k) - 1
capture_percent = 100 * fund_subset_return / proxy_subset_return
```

Both numerator and denominator use the same benchmark-selected months. These are annualized geometric returns across selected observations, not the realized return of a continuously held portfolio during a calendar year. The count of selected months matters to interpretation. An empty subset or zero denominator cannot support a meaningful ratio.

In down months, both subset returns are often negative. A value above 100% then means the fund lost more than the proxy under this convention. A negative capture ratio can occur when the fund gains while the proxy loses. Capture formulas differ across data vendors, so this lab's convention must accompany comparisons.

## Factor diagnostics and statistical uncertainty

For the full 120-month sample, each fund is fit by ordinary least squares:

```text
r_fund[t] - RF[t] = alpha
                    + beta_MKT * (Mkt-RF)[t]
                    + beta_SMB * SMB[t]
                    + beta_HML * HML[t]
                    + beta_RMW * RMW[t]
                    + beta_CMA * CMA[t]
                    + residual[t]
```

The fit includes an intercept. Newey-West heteroskedasticity and autocorrelation consistent standard errors use three monthly lags and Bartlett weights. The covariance estimate includes a finite-sample multiplier of `n / (n - k)`, where `k = 6` includes the intercept and five factors. The reported 95% interval uses the normal approximation, `alpha +/- 1.96 * SE(alpha)`. Annualized arithmetic alpha and both interval endpoints are the corresponding monthly quantities multiplied by twelve. They are not compounded returns, fund-versus-proxy CAGR differences, or forecasts.

This is a conditional description of historical returns under one model. The interval reflects the chosen estimator and model; it does not cover every form of model uncertainty. The sample is limited, the universe is selected, and several funds and diagnostics are inspected. Intervals are not corrected for multiple comparisons. An interval containing zero is weak evidence for a nonzero model intercept. An interval excluding zero still does not prove persistent skill or justify a mandate decision.

The five-factor model omits potential return drivers, including momentum and fund-specific exposures. Factor portfolios are research constructs, while the fund series incorporates its own implementation and operating expenses. A regression does not identify causal investment decisions.

## Returns-based style analysis

The style model fits a convex combination of IWF, IWD, and IWM monthly returns. For each 36-month window, it minimizes squared tracking differences subject to:

```text
predicted_return[t] = w_growth * IWF[t] + w_value * IWD[t] + w_small * IWM[t]
w_growth, w_value, w_small >= 0
w_growth + w_value + w_small = 1
```

The model has no intercept or cash allocation. Fits are sampled at quarterly endpoints. The chart's adjacent 36-month windows overlap heavily; neighboring plotted observations are not independent evidence of a change.

The drift diagnostic compares the most recent 36-month window with the immediately preceding, nonoverlapping 36-month window:

```text
style_drift = 0.5 * sum(abs(weight_recent - weight_previous))
```

For probability-like weight vectors this lies between zero and one. With the December 2025 measurement end, the comparison is January 2023-December 2025 against January 2020-December 2022.

The exported style field named `turnover` stores this distance between fitted weight vectors. It is not the fund's trading turnover or a transaction-cost estimate. Fit quality uses centered `R-squared = 1 - SSE/SST`. Because the constrained style model has no intercept, its centered R-squared can be negative; the application does not force it into a zero-to-one range.

The fitted weights are **return-replication coefficients, not portfolio holdings**. A 40% style weight does not establish a 40% allocation to that ETF or style in the actual fund. The three proxies are correlated and incomplete; multiple mixtures may explain returns similarly, while omitted exposures can change the fit. Drift may reflect market covariance changes or model instability as well as a change in fund behavior. Confirm a suspected process change with dated holdings, manager commentary, and personnel evidence.

## Monitoring rules and analyst judgment

Three transparent conditions flag questions for further work:

| Diagnostic | Illustrative trigger | Research question |
| --- | --- | --- |
| Most recent 36-month CAGR difference | Below -2 percentage points per year | What explains the shortfall, and is the selected proxy appropriate? |
| Most recent 36-month downside capture | Above 110% | Does downside participation fit the intended mandate? |
| Style drift across nonoverlapping 36-month windows | Above 0.25 | Is the return behavior consistent with the documented investment process? |

These thresholds are chosen to demonstrate a review workflow. They are not calibrated predictors, official limits, or empirically optimized decision rules. A trigger requests investigation. The absence of a trigger does not approve a fund. The application does not combine flags into a quality score or rank funds from best to worst.

The committee view brings the evidence together with analyst notes. Notes and downloaded JSON/CSV are review artifacts, not proof that a committee met or approved an action. Any human decision should identify the evidence considered and the diligence still outstanding.

## Scope and limitations

- The selected surviving funds exclude closed and merged funds and do not support peer percentiles or industry-wide performance conclusions.
- The fixed retrospective window and revised input vintages do not demonstrate a strategy that could have been executed with information available at each historical date.
- Fund histories can span personnel, mandate, and portfolio changes that are not reconstructed here.
- ETF comparisons are analyst-assigned proxies. Benchmark sensitivity is part of the research question, not a substitute for reading each fund's mandate and prospectus.
- Monthly data and a ten-year sample limit tail-risk, regime, and statistical conclusions.
- Style coefficients are approximate return descriptions. There is no holdings-based Active Share, security selection attribution, transaction reconstruction, or verified portfolio turnover calculation.
- Organizational, personnel, legal, compliance, liquidity, and operational due diligence are outside this lab. No issuer endorsement or investment recommendation is implied.

The useful output is a reproducible account of what the data show, where that conclusion depends on assumptions, and what an analyst should investigate next.
