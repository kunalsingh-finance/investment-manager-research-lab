-- Examine how benchmark choice changes the same manager's evaluation.
SELECT ticker, benchmark, ROUND(active_cagr * 100, 2) AS active_cagr_percentage_points,
       ROUND(tracking_error * 100, 2) AS tracking_error_pct,
       ROUND(information_ratio, 2) AS information_ratio
FROM metrics WHERE window_months = 36
ORDER BY ticker, benchmark;

-- Research flags against the declared analyst proxy, not all comparison proxies.
SELECT m.ticker, f.name, f.benchmark, m.active_cagr, m.down_capture
FROM metrics m JOIN funds f ON f.ticker = m.ticker AND f.benchmark = m.benchmark
WHERE m.window_months = 36 AND (m.active_cagr < -0.02 OR m.down_capture > 1.10);

-- Coverage check: nine series for every month; no missing return imputation.
SELECT date, COUNT(*) AS series_count FROM monthly_returns
GROUP BY date HAVING COUNT(*) <> 9;
