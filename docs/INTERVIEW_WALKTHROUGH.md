# Interview walkthrough

## Opening explanation

"I built a public-fund research workspace around a practical investment-management question: when a fund's recent behavior changes, what evidence should an analyst take to a review meeting? It connects benchmark-relative performance, factor diagnostics, style analysis, and explicit monitoring rules to an analyst's review notes. Every result uses a saved data vintage with documented assumptions."

Describe it as an independent research project. The funds and public return histories are real; the mandate assignments, thresholds, and committee workflow are illustrative. The project does not represent employment with an asset manager or responsibility for client assets.

## Five-minute demonstration

| Time | Show | Explain |
| --- | --- | --- |
| 0:00-0:45 | Overview and review period | Four selected public funds, January 2016-December 2025, with analyst-assigned ETF proxies. Explain the review question before pointing to individual numbers. |
| 0:45-1:35 | One fund's performance and benchmark comparison | Read its displayed CAGR difference, tracking error, drawdown, and downside capture. Explain why each addresses a different question. Change the comparison proxy where the interface permits it, and describe what changes in the conclusion. |
| 1:35-2:25 | Factor diagnostic and alpha interval | Distinguish the historical regression intercept from the fund's raw return and benchmark-relative CAGR difference. Explain why the interval matters and why neither sign nor statistical significance proves manager skill. |
| 2:25-3:20 | Style history and drift | Explain the convex fit to growth, value, and small-cap ETF returns. Compare the latest two nonoverlapping 36-month windows. State clearly that the fitted weights are not actual holdings. |
| 3:20-4:15 | Monitoring and committee view | Choose a displayed trigger or explain the absence of triggers. Write a short evidence-based note with a concrete follow-up question. A monitoring flag asks for investigation; it is not an automatic termination decision. |
| 4:15-5:00 | Sources and downloadable evidence | Show the source vintage and saved inputs. Export the review evidence. Explain the difference between historical measurement dates and the later download date, then name the biggest limitation. |

Use values from the current generated report. Do not memorize a numerical result from an older build, select a fund solely because its chart looks favorable, or imply that a demonstration note records a real committee decision.

## A useful review-note structure

Write three connected sentences:

1. **Observation:** Identify the fund, period, selected proxy, displayed measure, and any trigger.
2. **Interpretation:** Explain what that observation suggests and one alternative explanation.
3. **Follow-up:** Name the evidence needed before making a mandate decision.

Example with placeholders to replace from the displayed report:

> Over the latest 36 months, [fund] returned [displayed CAGR difference] percentage points per year relative to [proxy], while downside capture was [displayed value]. This warrants review of downside behavior, although the result may partly reflect the proxy's fit to the fund's mandate. I would compare dated holdings and manager commentary with the stated investment process before proposing an action.

Do not fill missing qualitative evidence with assumptions about a real manager's competence, integrity, personnel, or strategy.

## Questions to prepare for

**Why this project?**

"I wanted to demonstrate the step between calculating performance and making an investment review useful. The application organizes evidence, shows where it depends on a benchmark or model, and leaves a concrete research question for the analyst."

**Why those four funds?**

"They are a deliberately selected set for demonstrating the workflow. The project does not claim representative coverage or peer rankings. A production research process would need a defined eligible universe, closed and merged funds, share-class controls, and documented mandate criteria."

**Are those the funds' official benchmarks?**

"No. They are analyst-assigned ETF comparison proxies in this project. Their purpose is to make the assumptions visible and examine sensitivity. An actual mandate review would verify the prospectus benchmark and the client's policy benchmark separately."

**Did you deduct fund fees?**

"I did not subtract the expense ratio again because operating expenses are already reflected in the NAV-based return history. The project uses vendor-adjusted returns and does not model investor-specific sales loads, advisory fees, or taxes."

**Why can CAGR difference and information ratio tell different stories?**

"CAGR describes compounded wealth growth. The information ratio uses the mean monthly arithmetic active return divided by its sample standard deviation, then annualizes. They measure different aspects of the path, so I preserve the distinction rather than treating them as interchangeable alpha estimates."

**What does the alpha interval mean?**

"It summarizes uncertainty in the historical five-factor intercept under this model and a Newey-West estimator with three lags. The normal-approximation interval does not include every source of model uncertainty, and I do not treat it as a forecast or proof of skill. The displayed annual alpha is twelve times the monthly intercept."

**Do style weights show the manager's holdings?**

"No. They are the constrained mixture of three ETF return series that best approximates the fund's return history over a window. The proxies overlap and omit exposures. I would use dated holdings to test whether a suspected style change is real."

**Why compare nonoverlapping windows for drift?**

"Adjacent quarterly points on a 36-month rolling chart share most of their observations. Comparing two successive nonoverlapping 36-month windows makes the drift comparison easier to interpret, although it still cannot tell me whether a change came from portfolio decisions or the model's fit."

**Is this a backtest?**

"It is a retrospective research review with current downloaded data vintages. I do not claim the selected universe, revised return data, or assumptions were available historically. There is no simulated trading strategy or validated manager-selection rule."

**What would you add next?**

"I would add dated holdings and verified mandate documents first. That would let me test whether return-based observations agree with portfolio evidence. I would also broaden the eligible universe and record manager and share-class changes before attempting peer comparisons."

## Resume and portfolio wording

Use these only after reproducing the completed project and confirming the described features in its current build:

- Built a Python investment-manager research workspace comparing four public funds across a ten-year monthly history, with benchmark-relative performance, five-factor diagnostics, and documented source vintages.
- Implemented constrained returns-based style analysis and transparent monitoring rules; linked downside participation and style changes to analyst review notes and exportable evidence.
- Documented revised vendor data, selected-universe bias, benchmark assumptions, and statistical uncertainty to distinguish historical research findings from investment recommendations.

These describe project scope and methods. Do not add AUM, client impact, return improvements, production use, employer affiliations, or a test-pass count unless there is direct evidence for the claim. A shorter resume can use the first two bullets and link to the repository and saved demonstration.

## Before presenting

Open the saved report, reproduce the documented build and checks, and confirm that the source dates and numerical results agree across the interface and exports. Pick one fund whose evidence you understand well enough to discuss both the initial interpretation and an alternative explanation. Be ready to point to the exact calculation in [METHODOLOGY.md](METHODOLOGY.md).
