# Meridian · Investment Manager Research Lab

An investment analyst's workspace for evaluating fund performance, testing benchmark choice, and turning quantitative findings into questions for manager due diligence.

The project compares **four real actively managed US equity mutual funds across 120 monthly observations, January 2016–December 2025**. Its central question is whether a manager's apparent performance survives a closer look at benchmark fit, downside behavior, style exposure, and statistical uncertainty.

**Open [the research dashboard](output/report.html)** or double-click **Open Research Lab.cmd** on Windows. The saved dashboard works offline in a modern browser; viewing it needs no Python, account, API key, server, or external JavaScript library.

## What to demonstrate

| Research task | Implemented evidence |
| --- | --- |
| Compare funds within mandate context | FCNTX, TRBCX, DODGX and PRDGX with explicit analyst-assigned ETF comparison proxies |
| Challenge benchmark choice | 48 fund/window/proxy combinations across 3-, 5- and 10-year windows; growth, value, dividend and broad-market comparisons |
| Explain return and downside behavior | Wealth curves, CAGR differences, tracking error, information ratio, beta, capture ratios, Sharpe ratio and month-end drawdowns |
| Investigate changes in style | Quarterly rolling 36-month constrained return fits; separate adjacent nonoverlapping 36-month drift comparison |
| Separate intercept estimates from confidence | Fama–French five-factor regressions with Newey–West uncertainty intervals |
| Prepare a committee discussion | Explained monitoring triggers, an automatically assembled research brief, locally saved analyst notes, JSON/CSV exports and print view |
| Reproduce and audit the evidence | Raw source snapshots and hashes, strict input validation, numerical tests, full offline recomputation, CSV and SQLite outputs |

The selected funds are an illustrative research set, not a representative peer universe. The application does not rank funds as “best,” place trades, or infer completed qualitative diligence from a performance chart.

## Rebuild and validate

Use Python 3.11 or later from this directory. The included snapshot makes all analysis and validation offline after dependencies are installed.

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
python scripts/build_report.py
python scripts/verify_report.py
```

With Node.js 20 or later installed, `node scripts/check_interface.mjs` checks all 48 comparison states across four views, selector handlers, note isolation, storage-failure behavior, CSV/JSON exports and print wiring using a DOM adapter. This is a JavaScript behavior check, not a rendered browser or visual-layout test.

Current local validation: **36 Python tests passed**, complete offline rebuild and verification passed, and all 48 interface comparison states passed. A visual browser check could not be performed because this session's browser policy blocks local-file navigation.

The build creates the HTML dashboard, complete research JSON, monthly return/factor/price CSVs, a 48-row metric table, a SQLite database, and an artifact manifest. The verifier checks source and artifact hashes, reconstructs all analysis, reconciles CSV/SQL returns, and checks ten-year CAGR independently against endpoint adjusted prices. A failed refresh replaces the dashboard with a failure notice.

## Data and interpretation

The raw input snapshot contains public Yahoo Finance daily adjusted-close responses for four funds and five ETFs, plus the official [Kenneth R. French five-factor archive](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html). These are real downloaded series. Source links, acquisition times, conventions and SHA-256 fingerprints are in [the source manifest](data/raw/manifest.json) and the dashboard's Sources view.

Fund returns are vendor distribution-adjusted NAV return proxies; ETF series use adjusted market prices. Fund expenses are already embedded and are not deducted again. Distribution adjustments have not been independently reconciled to fund administrator records. Measurement ends December 2025 even though sources were retrieved later. The data are a revised vendor/research vintage, not historical point-in-time observations.

IWF for FCNTX/TRBCX, IWD for DODGX, and VIG for PRDGX are **analyst choices for this demonstration**, not assertions about official fund benchmarks. SPY is an alternative broad-market comparison. Monitoring flags use the assigned proxy over the latest 36 months; exploratory chart changes do not change the monitoring policy.

Style-fit weights are estimates of return behavior, not actual holdings. Regression alpha is conditional on one model and a limited historical sample. Team, process, capacity, vehicle terms and operations require separate diligence. The quantitative/qualitative distinction follows the framework discussed by [CFA Institute](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/investment-manager-selection).

To acquire a different source vintage, preserve the checked-in snapshot and download to another directory:

```powershell
python scripts/fetch_data.py --destination data/new_vintage
```

This optional command needs internet access. Acquisition never overwrites an existing directory. Replacing the analysis snapshot is an explicit manual maintenance step that requires rebuilding and revalidating the outputs. Source availability and data-use terms remain those of the providers; the project supplies no data redistribution license.

## Review the implementation

| File | Purpose |
| --- | --- |
| [Interview walkthrough](docs/INTERVIEW_WALKTHROUGH.md) | Five-minute demo, technical questions, and factual project bullets |
| [Methodology](docs/METHODOLOGY.md) | Equations, estimator conventions, benchmark assumptions and limitations |
| [Analytics](managerlab/analytics.py) | Performance, robust factor inference, constrained style fits and monitoring |
| [Source validation](managerlab/data.py) | Hash checks, daily-to-monthly conversion, factor parsing and coverage checks |
| [SQL examples](sql/research_queries.sql) | Benchmark sensitivity, monitoring and coverage queries |
| [Dashboard template](web/template.html) | Dependency-free interactive presentation |

The project demonstrates investment research, Python, SQL, statistics, financial communication, and reproducible data work. It is an independent portfolio project; it does not imply employment by, affiliation with, or endorsement from the fund companies.
