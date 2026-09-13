# OWN_ACCOUNT.md — the unconstrained 8-sleeve portfolio, re-measured

Secondary track for a stock account with options approval. Sleeve code is Thread A's, imported unchanged where a script exists (it7/it8/it9/it11); TSMOM/XSMOM inverse-vol from it8b; S13 re-implemented from ASSESSMENT_iteration17 with a 0.5 weight cap. Each sleeve vol-targeted to 10% (60-day trailing, lagged), equal weight; two buckets 50/50.

**ETF panel status: PENDING** `data/ext/etf_daily_2017-11_2026-09.csv.gz`. S2, S3, S6 (25-ETF universe) and S13 (VXX/VXZ via the VIXY/VIXM bridge) stop at 2017-11-10; S1, S5, S8 run to 2026-03-20 on the fetched SPY and stock panels; S12 to 2020-05-13.

## BASELINE 2006-2017-11 full

| label | cagr | vol | sharpe | maxdd | n_days | start | end |
|---|---|---|---|---|---|---|---|
| S1_MEANREV | 0.079 | 0.102 | 0.800 | -0.179 | 2987 | 2006-01-03 | 2017-11-10 |
| S2_TSMOM | 0.042 | 0.102 | 0.456 | -0.168 | 2987 | 2006-01-03 | 2017-11-10 |
| S3_XSMOM | 0.026 | 0.103 | 0.297 | -0.281 | 2987 | 2006-01-03 | 2017-11-10 |
| S5_VOLMGD | 0.049 | 0.101 | 0.527 | -0.264 | 2987 | 2006-01-03 | 2017-11-10 |
| S6_STREV | -0.011 | 0.105 | -0.058 | -0.306 | 2987 | 2006-01-03 | 2017-11-10 |
| S8_BAB | 0.047 | 0.101 | 0.506 | -0.414 | 2989 | 2006-01-03 | 2017-11-10 |
| S12_GAPUP | 0.022 | 0.102 | 0.268 | -0.311 | 2987 | 2006-01-03 | 2017-11-10 |
| S13_VOLTS | 0.028 | 0.052 | 0.564 | -0.057 | 2212 | 2009-01-30 | 2017-11-10 |
| EQUAL_available(1-8) | 0.038 | 0.051 | 0.769 | -0.065 | 2989 | 2006-01-03 | 2017-11-10 |
| BUCKET_A | 0.052 | 0.058 | 0.900 | -0.094 | 2987 | 2006-01-03 | 2017-11-10 |
| BUCKET_B | 0.034 | 0.063 | 0.558 | -0.116 | 2989 | 2006-01-03 | 2017-11-10 |
| TWO_BUCKET_50_50 | 0.043 | 0.049 | 0.882 | -0.058 | 2989 | 2006-01-03 | 2017-11-10 |

## BASELINE train <2012

| label | cagr | vol | sharpe | maxdd | n_days | start | end |
|---|---|---|---|---|---|---|---|
| S1_MEANREV | 0.067 | 0.094 | 0.736 | -0.179 | 1511 | 2006-01-03 | 2011-12-30 |
| S2_TSMOM | 0.028 | 0.100 | 0.328 | -0.168 | 1511 | 2006-01-03 | 2011-12-30 |
| S3_XSMOM | -0.021 | 0.102 | -0.152 | -0.245 | 1511 | 2006-01-03 | 2011-12-30 |
| S5_VOLMGD | 0.026 | 0.098 | 0.309 | -0.264 | 1511 | 2006-01-03 | 2011-12-30 |
| S6_STREV | 0.013 | 0.105 | 0.173 | -0.154 | 1511 | 2006-01-03 | 2011-12-30 |
| S8_BAB | -0.015 | 0.104 | -0.093 | -0.414 | 1513 | 2006-01-03 | 2011-12-30 |
| S12_GAPUP | 0.082 | 0.114 | 0.747 | -0.177 | 1511 | 2006-01-03 | 2011-12-30 |
| S13_VOLTS | 0.031 | 0.049 | 0.645 | -0.044 | 736 | 2009-01-30 | 2011-12-30 |
| EQUAL_available(1-8) | 0.029 | 0.053 | 0.567 | -0.065 | 1513 | 2006-01-03 | 2011-12-30 |
| BUCKET_A | 0.074 | 0.065 | 1.132 | -0.081 | 1511 | 2006-01-03 | 2011-12-30 |
| BUCKET_B | 0.009 | 0.063 | 0.179 | -0.116 | 1513 | 2006-01-03 | 2011-12-30 |
| TWO_BUCKET_50_50 | 0.042 | 0.052 | 0.809 | -0.058 | 1513 | 2006-01-03 | 2011-12-30 |

## BASELINE test 2012-2017-11

| label | cagr | vol | sharpe | maxdd | n_days | start | end |
|---|---|---|---|---|---|---|---|
| S1_MEANREV | 0.093 | 0.110 | 0.860 | -0.161 | 1476 | 2012-01-03 | 2017-11-10 |
| S2_TSMOM | 0.056 | 0.104 | 0.582 | -0.149 | 1476 | 2012-01-03 | 2017-11-10 |
| S3_XSMOM | 0.075 | 0.104 | 0.747 | -0.195 | 1476 | 2012-01-03 | 2017-11-10 |
| S5_VOLMGD | 0.074 | 0.103 | 0.739 | -0.126 | 1476 | 2012-01-03 | 2017-11-10 |
| S6_STREV | -0.036 | 0.105 | -0.293 | -0.306 | 1476 | 2012-01-03 | 2017-11-10 |
| S8_BAB | 0.114 | 0.097 | 1.163 | -0.149 | 1476 | 2012-01-03 | 2017-11-10 |
| S12_GAPUP | -0.035 | 0.088 | -0.365 | -0.278 | 1476 | 2012-01-03 | 2017-11-10 |
| S13_VOLTS | 0.027 | 0.053 | 0.527 | -0.057 | 1476 | 2012-01-03 | 2017-11-10 |
| EQUAL_8 | 0.048 | 0.049 | 0.994 | -0.056 | 1476 | 2012-01-03 | 2017-11-10 |
| BUCKET_A | 0.029 | 0.050 | 0.608 | -0.094 | 1476 | 2012-01-03 | 2017-11-10 |
| BUCKET_B | 0.059 | 0.063 | 0.949 | -0.079 | 1476 | 2012-01-03 | 2017-11-10 |
| TWO_BUCKET_50_50 | 0.045 | 0.046 | 0.971 | -0.049 | 1476 | 2012-01-03 | 2017-11-10 |

## EXTENDED (each sleeve to its data end)

| label | cagr | vol | sharpe | maxdd | n_days | start | end |
|---|---|---|---|---|---|---|---|
| S1_MEANREV | 0.075 | 0.104 | 0.747 | -0.179 | 5085 | 2006-01-03 | 2026-03-20 |
| S2_TSMOM | 0.042 | 0.102 | 0.456 | -0.168 | 2987 | 2006-01-03 | 2017-11-10 |
| S3_XSMOM | 0.026 | 0.103 | 0.297 | -0.281 | 2987 | 2006-01-03 | 2017-11-10 |
| S5_VOLMGD | 0.060 | 0.103 | 0.613 | -0.264 | 5085 | 2006-01-03 | 2026-03-20 |
| S6_STREV | -0.011 | 0.105 | -0.058 | -0.306 | 2987 | 2006-01-03 | 2017-11-10 |
| S8_BAB | 0.022 | 0.096 | 0.274 | -0.414 | 5087 | 2006-01-03 | 2026-03-20 |
| S12_GAPUP | 0.020 | 0.105 | 0.238 | -0.340 | 3615 | 2006-01-03 | 2020-05-13 |
| S13_VOLTS | 0.028 | 0.052 | 0.564 | -0.057 | 2212 | 2009-01-30 | 2017-11-10 |
| EQUAL_available(1-8) | 0.040 | 0.053 | 0.763 | -0.065 | 5087 | 2006-01-03 | 2026-03-20 |
| BUCKET_A | 0.051 | 0.078 | 0.679 | -0.155 | 5085 | 2006-01-03 | 2026-03-20 |
| BUCKET_B | 0.033 | 0.061 | 0.572 | -0.116 | 5087 | 2006-01-03 | 2026-03-20 |
| TWO_BUCKET_50_50 | 0.043 | 0.055 | 0.794 | -0.069 | 5087 | 2006-01-03 | 2026-03-20 |

## POST-BASELINE 2017-11-13 →

| label | cagr | vol | sharpe | maxdd | n_days | start | end |
|---|---|---|---|---|---|---|---|
| S1_MEANREV | 0.068 | 0.106 | 0.676 | -0.155 | 2098 | 2017-11-13 | 2026-03-20 |
| S2_TSMOM |  |  |  |  | 0 |  |  |
| S3_XSMOM |  |  |  |  | 0 |  |  |
| S5_VOLMGD | 0.075 | 0.106 | 0.730 | -0.135 | 2098 | 2017-11-13 | 2026-03-20 |
| S6_STREV |  |  |  |  | 0 |  |  |
| S8_BAB | -0.013 | 0.088 | -0.102 | -0.230 | 2098 | 2017-11-13 | 2026-03-20 |
| S12_GAPUP | 0.007 | 0.117 | 0.115 | -0.178 | 628 | 2017-11-13 | 2020-05-13 |
| S13_VOLTS |  |  |  |  | 0 |  |  |
| EQUAL_available(3-4) | 0.041 | 0.055 | 0.757 | -0.059 | 2098 | 2017-11-13 | 2026-03-20 |
| BUCKET_A | 0.051 | 0.100 | 0.544 | -0.155 | 2098 | 2017-11-13 | 2026-03-20 |
| BUCKET_B | 0.033 | 0.058 | 0.594 | -0.100 | 2098 | 2017-11-13 | 2026-03-20 |
| TWO_BUCKET_50_50 | 0.043 | 0.063 | 0.708 | -0.069 | 2098 | 2017-11-13 | 2026-03-20 |

## By year (sum of daily returns at 10% sleeve vol)

| year | EQUAL_available | BUCKET_A | BUCKET_B | TWO_BUCKET_50_50 | sleeves_mean | sleeves_min |
|---|---|---|---|---|---|---|
| 2006 | 0.058 | 0.027 | 0.070 | 0.049 | 7.000 | 7 |
| 2007 | 0.012 | 0.147 | -0.042 | 0.052 | 6.953 | 1 |
| 2008 | 0.018 | 0.127 | -0.025 | 0.051 | 7.000 | 7 |
| 2009 | 0.034 | 0.071 | 0.014 | 0.042 | 7.925 | 7 |
| 2010 | 0.039 | -0.030 | 0.080 | 0.025 | 8.000 | 8 |
| 2011 | 0.019 | 0.099 | -0.029 | 0.035 | 7.996 | 7 |
| 2012 | 0.061 | -0.015 | 0.107 | 0.046 | 8.000 | 8 |
| 2013 | 0.130 | 0.043 | 0.182 | 0.112 | 8.000 | 8 |
| 2014 | -0.004 | -0.008 | -0.001 | -0.005 | 8.000 | 8 |
| 2015 | 0.029 | 0.030 | 0.028 | 0.029 | 8.000 | 8 |
| 2016 | 0.004 | 0.057 | -0.029 | 0.014 | 8.000 | 8 |
| 2017 | 0.083 | 0.064 | 0.105 | 0.084 | 7.474 | 4 |
| 2018 | -0.007 | -0.014 | 0.001 | -0.007 | 4.000 | 4 |
| 2019 | 0.119 | 0.124 | 0.114 | 0.119 | 4.000 | 4 |
| 2020 | 0.072 | 0.110 | 0.027 | 0.069 | 3.364 | 3 |
| 2021 | 0.052 | 0.072 | 0.043 | 0.057 | 3.000 | 3 |
| 2022 | -0.003 | -0.001 | -0.005 | -0.003 | 3.000 | 3 |
| 2023 | 0.023 | 0.022 | 0.023 | 0.022 | 3.000 | 3 |
| 2024 | 0.057 | 0.036 | 0.067 | 0.052 | 3.000 | 3 |
| 2025 | 0.035 | 0.118 | -0.007 | 0.055 | 3.000 | 3 |
| 2026 | -0.016 | -0.006 | -0.021 | -0.014 | 3.000 | 3 |

## By regime (annualised mean; uptrend = SPY above a rising 200-day average, high-vol = prior VIX above its expanding upper tercile)

| regime | EQUAL_available | BUCKET_A | BUCKET_B | TWO_BUCKET_50_50 | sleeves_mean |
|---|---|---|---|---|---|
| downtrend | -0.005 | 0.000 | -0.007 | -0.003 | 6.613 |
| high_vol | 0.036 | 0.089 | 0.008 | 0.049 | 5.484 |
| uptrend | 0.051 | 0.044 | 0.057 | 0.051 | 5.996 |

## VXX / VXZ bridge (A13): daily-return correlations on the overlaps

Old VXX ↔ VIXY and old VXZ ↔ VIXM are measurable now; new-VXX ↔ VIXY and new-VXZ ↔ VIXM need the ext panel. The bridge is refused below 0.98.

| pair | daily_return_corr |
|---|---|
| vxx_vs_vixy | 0.9987 |
| vxz_vs_vixm | 0.9875 |

## VIX − realised vol (variance risk premium), measured not traded

Prior-close VIX minus the next 21 trading days' realised vol of SPY, in vol points. Not tradeable as measured: no option prices, spreads or margin; a defined-risk 30–45 DTE implementation is a recorded non-goal. Coverage ends with the SPY daily panel's final partial year in `out/vrp_vix_minus_rv.csv`: last row 2026 has n = 33.

| year | mean | pct_positive | worst | n |
|---|---|---|---|---|
| 2000 | 0.352 | 55.379 | -11.315 | 251 |
| 2001 | 5.297 | 77.419 | -12.316 | 248 |
| 2002 | 1.888 | 66.667 | -17.898 | 252 |
| 2003 | 6.743 | 100.000 | 2.697 | 252 |
| 2004 | 4.356 | 96.032 | -1.807 | 252 |
| 2005 | 2.646 | 85.317 | -4.236 | 252 |
| 2006 | 3.252 | 89.641 | -3.698 | 251 |
| 2007 | 1.841 | 67.729 | -10.278 | 251 |
| 2008 | -2.488 | 60.079 | -57.807 | 253 |
| 2009 | 7.979 | 96.429 | -4.377 | 252 |
| 2010 | 6.251 | 84.524 | -13.828 | 252 |
| 2011 | 2.962 | 84.524 | -32.146 | 252 |
| 2012 | 4.679 | 98.400 | -0.578 | 250 |
| 2013 | 3.404 | 83.333 | -3.521 | 252 |
| 2014 | 3.183 | 76.191 | -6.583 | 252 |
| 2015 | 1.705 | 75.397 | -18.862 | 252 |
| 2016 | 4.454 | 84.524 | -6.186 | 252 |
| 2017 | 4.375 | 99.203 | -0.183 | 251 |
| 2018 | 0.502 | 59.362 | -15.666 | 251 |
| 2019 | 4.246 | 82.540 | -11.081 | 252 |
| 2020 | 2.569 | 73.913 | -72.112 | 253 |
| 2021 | 6.832 | 94.841 | -2.662 | 252 |
| 2022 | 1.660 | 61.753 | -14.114 | 251 |
| 2023 | 4.311 | 99.600 | -0.121 | 250 |
| 2024 | 3.174 | 81.349 | -9.181 | 252 |
| 2025 | 3.227 | 84.400 | -35.228 | 250 |
| 2026 | 4.442 | 100.000 | 1.078 | 33 |
| ALL 2000-2026 | 3.442 | 81.570 | -72.112 | 6571 |

## Known differences from Thread A's published baseline

Thread A: 8 sleeves Sharpe 1.12 full / 1.35 test, maxDD −6.10%; two buckets 1.20 / 1.40, −5.26%. The BAB sleeve's universe is now cleaned by `pipeline.own_account.clean_universe`, reconstructed from it5.py/it5b.py (history/price/dollar-volume filters, then drop symbols with >5 days of |return|>50%) since `panel_clean.pkl` itself is not in the bundle: 928 raw tickers -> 626, matching Thread A's reported count. This does not close the gap to the published portfolio Sharpes: the BASELINE test-window Sharpe is materially unchanged (EQUAL_8 0.994, TWO_BUCKET 0.971, both within 0.001 of the raw-universe run), so an uncleaned BAB universe is not the explanation for D5's shortfall. S12 is the pipeline's gap-up signal rather than Thread A's scan cell; test-window Sharpes of S2, S3 and S13 match Thread A's published values.
