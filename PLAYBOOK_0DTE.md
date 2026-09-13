# PLAYBOOK_0DTE.md — the constrained book, every number measured

**Account constraint.** 0DTE options only, long-only, naked calls or puts; no selling, spreads, futures, shares or overnight holds; daily loss limit 3–5% (base case 4%) on marked intraday P&L.

**Pricing model, stated first.** No real 0DTE quotes were obtainable. Every option number below is Black-Scholes with r = 0 and IV = k × prior-close VIX (both prior threads used k = 1.0 and called it generous). At 2% in the money with less than an hour to expiry that model is intrinsic value ± the spread (time value ≤ 0.000 index points at 60 minutes for VIX ≤ 40 and ≤ 0.159 at VIX 83, `out/options_timevalue.csv`), so k only matters for the 13:00 leg and the spread is the real sensitivity axis. SPX/XSP are PM cash-settled: buy at the ask (half the quoted spread), settle at intrinsic. SPY is physically settled and must be sold by 15:55 with both spread halves paid; SPY rows are for that exit.

## 1. The pre-registered specification

**Reconciled last-hour momentum signal (D1 winner):** `15:00|both|vixmove_exp` — decision at 15:00 ET on the bar close; gate: prior-close VIX above its expanding upper tercile AND |prior close → entry| above its expanding upper tercile; direction: call on an up move, put on a down move; entry at the next bar's open; hold to the 16:00 settlement.
For reference, the frozen `vixmove_fixed` boundaries (a different, non-winning configuration: Oanda 2005-2012 upper terciles, `out/reconcile_decision.md`): 15:00 VIX > 22.87 & |move| > 0.815%; 15:30 VIX > 22.87 & |move| > 0.845%. The pre-registered winner uses expanding terciles computed from strictly prior sessions and has no frozen thresholds.

**Thread A's gap-up call (pre-registered by Thread A):** open / prior close − 1 > 0.3% → 2% ITM call at the first bar after 13:00 ET, hold to settlement.

Strike: 2% in the money, rounded away from spot to the grid (5 points SPX, $1 SPY/XSP). Never at-the-money or out-of-the-money (−53% per trade at a 17% hit rate in both threads).

## 2. How the specification was chosen (selection window 2013-01 → 2020-05-13, Oanda SPX, net of 1.0 pt)

| rank | candidate | params | n | win | net_pts | net_pct | sharpe_calday | p_boot_month | p_boot_day | excess_over_control_pct | timing_control_pct | dsr_N12 | dsr_N42 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 15:00\|both\|vixmove_fixed | 2 | 92 | 64.130 | 5.272 | 0.194 | 0.557 |  | 0.063 | 0.206 | 0.416 | 0.756 | 0.662 |
| 2 | 15:30\|both\|vixmove_fixed | 2 | 92 | 59.783 | 3.880 | 0.149 | 0.515 |  | 0.083 | 0.168 | 0.425 | 0.714 | 0.617 |
| 3 | 15:00\|both\|vixmove_exp | 0 | 145 | 62.759 | 3.115 | 0.112 | 0.489 | 0.179 | 0.095 | 0.124 | 0.303 | 0.613 | 0.476 |
| 4 | 15:30\|both\|vixmove_exp | 0 | 146 | 59.589 | 2.382 | 0.091 | 0.467 | 0.115 | 0.102 | 0.111 | 0.302 | 0.587 | 0.451 |
| 5 | 15:30\|put\|mag | 0 | 182 | 57.143 | 0.771 | 0.033 | 0.260 | 0.255 | 0.238 | 0.072 | 0.241 | 0.334 | 0.217 |
| 6 | 15:30\|put\|vixmove_exp | 0 | 62 | 51.613 | 1.542 | 0.054 | 0.170 |  | 0.314 | 0.086 | 0.287 | 0.414 | 0.332 |
| 7 | 15:00\|put\|vixmove_fixed | 2 | 42 | 54.762 | 2.412 | 0.080 | 0.159 |  | 0.335 | 0.116 | 0.342 | 0.447 | 0.376 |
| 8 | 15:00\|put\|vixmove_exp | 0 | 58 | 55.172 | 1.740 | 0.055 | 0.145 |  | 0.351 | 0.085 | 0.286 | 0.393 | 0.313 |
| 9 | 15:00\|put\|mag | 0 | 189 | 52.381 | 0.324 | 0.017 | 0.125 | 0.362 | 0.374 | 0.062 | 0.226 | 0.202 | 0.112 |
| 10 | 15:30\|put\|vixmove_fixed | 2 | 43 | 51.163 | 1.116 | 0.033 | 0.079 |  | 0.409 | 0.074 | 0.312 | 0.364 | 0.298 |
| 11 | 15:30\|both\|mag | 0 | 371 | 54.717 | 0.067 | 0.002 | 0.023 | 0.478 | 0.470 | 0.036 | 0.211 | 0.055 | 0.016 |
| 12 | 15:00\|both\|mag | 0 | 371 | 50.943 | -0.033 | 0.001 | 0.008 | 0.493 | 0.492 | 0.039 | 0.188 | 0.050 | 0.014 |

Literal Thread B thresholds (17.06 / 0.665, in-sample on 2013–2018, reported not ranked):

| candidate | n | win | net_pts | net_pct | sharpe_calday | p_boot_month | p_boot_day |
|---|---|---|---|---|---|---|---|
| 15:00\|put\|vixmove_lit | 101 | 55.446 | 2.111 | 0.080 | 0.341 | 0.141 | 0.175 |
| 15:00\|both\|vixmove_lit | 251 | 58.566 | 2.168 | 0.084 | 0.603 | 0.117 | 0.046 |
| 15:30\|put\|vixmove_lit | 104 | 58.654 | 1.770 | 0.071 | 0.360 | 0.059 | 0.163 |
| 15:30\|both\|vixmove_lit | 252 | 59.127 | 1.425 | 0.057 | 0.484 | 0.114 | 0.088 |

Thread A's gap-up call, same selection window (pre-registered by Thread A, not part of this ranking — see §1):

| candidate | n | win | net_pts | net_pct | sharpe_calday | p_boot_month | p_boot_day |
|---|---|---|---|---|---|---|---|
| 13:00\|call\|gap>0.3% | 423 | 52.719 | -0.138 | -0.004 | -0.047 | 1.000 | 1.000 |

Every VIX-gated two-sided configuration outranks every magnitude-gated or put-only one; the four VIX-gated two-sided variants tie within 0.10 Sharpe and the tie-break (fewest FITTED parameters — an expanding rule has none) picks the 15:00 entry with the expanding-tercile rule. 0 of 36 trials pass BH-FDR at 10% across the family (`out/trials.csv`). Probability of backtest overfitting of this 12-configuration selection (CSCV, 16 blocks, 12,870 splits): 0.73; the in-sample best configuration's median out-of-sample rank logit is -0.81; the per-column shuffled null gives 0.85 (this null preserves each configuration's own mean and variance, so it is a floor for near-duplicate configurations, not 0.5 — reported, not a survival condition).

## 3. Option-level results — IN-SAMPLE (% of premium per trade)

| signal | spread | settle | k | n | trades_per_year | win | mean | median | worst_trade | worst_day | mae_worst | full_loss_trades | premium_mean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 15:00\|both\|vixmove_exp | 1.000 | cash | 1.000 | 145 | 19.762 | 62.069 | 7.339 | 5.489 | -100.000 | -100.000 | -100.000 | 5 | 52.610 |
| 15:00\|both\|vixmove_exp | 1.000 | exit | 1.000 | 145 | 19.762 | 54.483 | 3.675 | 1.349 | -99.260 | -99.260 | -100.000 | 0 | 55.230 |
| 15:00\|both\|vixmove_exp | 2.000 | cash | 1.000 | 145 | 19.762 | 59.310 | 6.303 | 4.245 | -100.000 | -100.000 | -100.000 | 5 | 53.110 |
| 15:00\|both\|vixmove_exp | 2.000 | exit | 1.000 | 145 | 19.762 | 47.586 | 1.809 | -0.647 | -100.000 | -100.000 | -100.000 | 2 | 55.730 |
| 15:00\|both\|vixmove_exp | 3.000 | cash | 1.000 | 145 | 19.762 | 57.241 | 5.287 | 3.148 | -100.000 | -100.000 | -100.000 | 5 | 53.610 |
| 15:00\|both\|vixmove_exp | 3.000 | exit | 1.000 | 145 | 19.762 | 45.517 | -0.010 | -2.576 | -100.000 | -100.000 | -100.000 | 2 | 56.230 |
| 13:00\|call\|gap>0.3% | 1.000 | cash | 1.000 | 423 | 57.650 | 50.827 | 1.175 | 0.569 | -100.000 | -100.000 | -100.000 | 4 | 49.873 |
| 13:00\|call\|gap>0.3% | 1.000 | cash | 1.300 | 423 | 57.650 | 50.827 | 1.099 | 0.569 | -100.000 | -100.000 | -100.000 | 4 | 49.903 |
| 13:00\|call\|gap>0.3% | 1.000 | cash | 1.600 | 423 | 57.650 | 50.827 | 0.971 | 0.569 | -100.000 | -100.000 | -100.000 | 4 | 49.956 |
| 13:00\|call\|gap>0.3% | 1.000 | exit | 1.000 | 423 | 57.650 | 46.809 | 0.071 | -0.443 | -100.000 | -100.000 | -100.000 | 3 | 52.283 |
| 13:00\|call\|gap>0.3% | 1.000 | exit | 1.300 | 423 | 57.650 | 46.809 | 0.012 | -0.443 | -100.000 | -100.000 | -100.000 | 3 | 52.309 |
| 13:00\|call\|gap>0.3% | 1.000 | exit | 1.600 | 423 | 57.650 | 46.809 | -0.090 | -0.443 | -100.000 | -100.000 | -100.000 | 3 | 52.358 |
| 13:00\|call\|gap>0.3% | 2.000 | cash | 1.000 | 423 | 57.650 | 48.463 | 0.131 | -0.376 | -100.000 | -100.000 | -100.000 | 4 | 50.373 |
| 13:00\|call\|gap>0.3% | 2.000 | cash | 1.300 | 423 | 57.650 | 48.463 | 0.056 | -0.376 | -100.000 | -100.000 | -100.000 | 4 | 50.403 |
| 13:00\|call\|gap>0.3% | 2.000 | cash | 1.600 | 423 | 57.650 | 48.227 | -0.069 | -0.376 | -100.000 | -100.000 | -100.000 | 4 | 50.456 |
| 13:00\|call\|gap>0.3% | 2.000 | exit | 1.000 | 423 | 57.650 | 41.135 | -1.889 | -2.632 | -100.000 | -100.000 | -100.000 | 4 | 52.783 |
| 13:00\|call\|gap>0.3% | 2.000 | exit | 1.300 | 423 | 57.650 | 41.135 | -1.948 | -2.632 | -100.000 | -100.000 | -100.000 | 3 | 52.809 |
| 13:00\|call\|gap>0.3% | 2.000 | exit | 1.600 | 423 | 57.650 | 41.135 | -2.048 | -2.632 | -100.000 | -100.000 | -100.000 | 3 | 52.858 |
| 13:00\|call\|gap>0.3% | 3.000 | cash | 1.000 | 423 | 57.650 | 45.390 | -0.891 | -1.441 | -100.000 | -100.000 | -100.000 | 4 | 50.873 |
| 13:00\|call\|gap>0.3% | 3.000 | cash | 1.300 | 423 | 57.650 | 45.390 | -0.965 | -1.441 | -100.000 | -100.000 | -100.000 | 4 | 50.903 |
| 13:00\|call\|gap>0.3% | 3.000 | cash | 1.600 | 423 | 57.650 | 45.390 | -1.088 | -1.441 | -100.000 | -100.000 | -100.000 | 4 | 50.956 |
| 13:00\|call\|gap>0.3% | 3.000 | exit | 1.000 | 423 | 57.650 | 36.407 | -3.809 | -4.722 | -100.000 | -100.000 | -100.000 | 4 | 53.283 |
| 13:00\|call\|gap>0.3% | 3.000 | exit | 1.300 | 423 | 57.650 | 36.407 | -3.867 | -4.722 | -100.000 | -100.000 | -100.000 | 4 | 53.309 |
| 13:00\|call\|gap>0.3% | 3.000 | exit | 1.600 | 423 | 57.650 | 36.407 | -3.966 | -4.725 | -100.000 | -100.000 | -100.000 | 4 | 53.358 |

mae_worst is the worst intraday excursion of the underlying against the position during the hold, in % of premium, capped at −100% (what a prop desk marks; ACCEPTANCE budgets).

## 4. Sizing — IN-SAMPLE, % of account

Position size = daily limit ÷ worst-trade loss with a 100% floor (a hold-to-close option has no stop). The combined book sizes on the worst day when both signals fire.

| signal | limit | size_pct | worst_trade_loss_pct | exp_annual_pct | worst_year_pct | best_year_pct | days_with_two_positions | worst_day_both_positions_pct |
|---|---|---|---|---|---|---|---|---|
| 15:00\|both\|vixmove_exp | 3.000 | 3.000 | 100.000 | 4.351 | -1.487 | 29.789 |  |  |
| 15:00\|both\|vixmove_exp | 4.000 | 4.000 | 100.000 | 5.801 | -1.983 | 39.719 |  |  |
| 15:00\|both\|vixmove_exp | 5.000 | 5.000 | 100.000 | 7.252 | -2.479 | 49.648 |  |  |
| 13:00\|call\|gap>0.3% | 3.000 | 3.000 | 100.000 | 1.900 | -5.403 | 10.339 |  |  |
| 13:00\|call\|gap>0.3% | 4.000 | 4.000 | 100.000 | 2.533 | -7.204 | 13.786 |  |  |
| 13:00\|call\|gap>0.3% | 5.000 | 5.000 | 100.000 | 3.167 | -9.005 | 17.232 |  |  |
| COMBINED BOOK | 3.000 | 1.500 | 200.000 | 3.125 |  |  | 77 | -200.000 |
| COMBINED BOOK | 4.000 | 2.000 | 200.000 | 4.167 |  |  | 77 | -200.000 |
| COMBINED BOOK | 5.000 | 2.500 | 200.000 | 5.209 |  |  | 77 | -200.000 |

## 5. Execution — IN-SAMPLE (underlying index points per signal; unfilled limits count as zero)

| candidate | entry | fill_rate | n_signals | mean_net_per_signal | mean_net_if_filled | improvement | improvement_cost_part | improvement_price_part | p_improvement |
|---|---|---|---|---|---|---|---|---|---|
| 13:00\|call\|gap>0.3% | market | 1.000 | 423 | -0.138 | -0.138 | 0.000 | 0.000 | 0.000 |  |
| 13:00\|call\|gap>0.3% | limit -0.25 ATR | 0.856 | 423 | 0.518 | 0.606 | 0.656 | 0.342 | 0.314 | 0.002 |
| 13:00\|call\|gap>0.3% | limit -0.50 ATR | 0.742 | 423 | 0.704 | 0.948 | 0.842 | 0.297 | 0.545 | 0.004 |
| 13:00\|call\|gap>0.3% | limit -1.00 ATR | 0.556 | 423 | 0.281 | 0.505 | 0.418 | 0.222 | 0.196 | 0.245 |
| 15:00\|both\|vixmove_exp | market | 1.000 | 145 | 3.115 | 3.115 | 0.000 | 0.000 | 0.000 |  |
| 15:00\|both\|vixmove_exp | limit -0.25 ATR | 0.903 | 145 | 3.339 | 3.696 | 0.224 | 0.361 | -0.137 | 0.379 |
| 15:00\|both\|vixmove_exp | limit -0.50 ATR | 0.779 | 145 | 3.076 | 3.947 | -0.040 | 0.312 | -0.351 | 1.000 |
| 15:00\|both\|vixmove_exp | limit -1.00 ATR | 0.538 | 145 | 3.345 | 6.219 | 0.230 | 0.215 | 0.015 | 0.435 |

The improvement over market entry splits into the part that is a cost assumption (fill rate × the 0.40 pt saved by paying commission instead of crossing the entry half of the spread) and the part that is price improvement net of adverse selection (unfilled signals count as zero).

## 6. Contract size and minimum account

A 2% ITM SPX option costs ≈ 2% × S × 100 ≈ $13,000 at S = 6,500 (S = 6,500 is an assumed current index level, not measured here — no post-2020 price file is present; every dollar figure scales linearly with S); XSP is one tenth. At the base size (4% of account per trade) one SPX contract needs ≈ $325k of account, one XSP contract ≈ $32.5k, one SPY contract ≈ $32.5k with the 15:55 exit. Max positions per day: 2 (the two signals can coincide).

## 7. Holdout — what decides whether this is tradeable

Contract window 2020-06-01 → 2026-09-11; minute data present 2020-07-27 → 2026-09-11 (1526 sessions). Sessions before the first date have no minute data (the Oanda series ends 2020-05-13 and the supplied feed starts later, DATA.md); they are absent from every holdout table, not filled.

Survival-rule verdict per pre-registered signal (`out/holdout_summary.csv`; `label_final` includes the family-wide FDR):

| signal | n | win | net_pts | net_pct | worst_trade_pts | p_month | p_day | p_half1_month | p_half2_month | excess_over_control_pct | psr | sharpe_calday | fdr_pass_10pct_family | label_final | data_first_date | data_last_date | sessions_in_window |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 15:00\|both\|vixmove_exp | 274 | 53.650 | -0.143 | -0.011 | -89.200 | 1.000 | 1.000 | 1.000 |  | 0.002 | 0.364 | -0.138 | False | FAILED | 2020-07-27 | 2026-09-11 | 1526 |
| 13:00\|call\|gap>0.3% | 452 | 50.885 | -1.904 | -0.038 | -105.300 | 1.000 | 1.000 | 1.000 | 1.000 | -0.019 | 0.067 | -0.578 | False | FAILED | 2020-07-27 | 2026-09-11 | 1526 |

An empty cell is NA: that bootstrap had fewer than 20 blocks (months or days) to resample, so no p-value is reported (survival rule 2); an empty cell is never 1.0 or 0.

All 16 configurations on the holdout — published, not promoted (`out/reconcile_candidates.csv`, `label` column):

| candidate | label | params | n | win | net_pts | net_pct | sharpe_calday | p_boot_month | p_boot_day | excess_over_control_pct | timing_control_pct |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 15:00\|both\|vixmove_exp | PRE-REGISTERED | 0 | 274 | 53.650 | -0.143 | -0.011 | -0.138 | 1.000 | 1.000 | 0.002 | 0.120 |
| 15:00\|put\|mag | POST-SELECTION | 0 | 222 | 55.405 | 1.939 | 0.039 | 0.476 | 0.099 | 0.113 | 0.046 | 0.198 |
| 15:00\|both\|mag | POST-SELECTION | 0 | 475 | 52.421 | 0.321 | 0.006 | 0.125 | 0.374 | 0.371 | 0.018 | 0.168 |
| 15:30\|put\|mag | POST-SELECTION | 0 | 225 | 51.556 | 0.052 | 0.000 | 0.008 | 0.490 | 0.493 | 0.015 | 0.203 |
| 15:00\|put\|vixmove_exp | POST-SELECTION | 0 | 115 | 55.652 | -0.550 | -0.025 | -0.172 | 1.000 | 1.000 | -0.021 | 0.115 |
| 15:00\|both\|vixmove_lit | POST-SELECTION | 2 | 446 | 52.915 | -0.383 | -0.011 | -0.205 | 1.000 | 1.000 | 0.002 | 0.114 |
| 15:00\|put\|vixmove_lit | POST-SELECTION | 2 | 184 | 52.717 | -0.591 | -0.020 | -0.209 | 1.000 | 1.000 | -0.014 | 0.122 |
| 15:00\|put\|vixmove_fixed | POST-SELECTION | 2 | 76 | 55.263 | -1.456 | -0.050 | -0.254 | 1.000 | 1.000 | -0.045 | 0.121 |
| 15:00\|both\|vixmove_fixed | POST-SELECTION | 2 | 187 | 50.802 | -0.895 | -0.029 | -0.282 | 1.000 | 1.000 | -0.011 | 0.128 |
| 15:30\|put\|vixmove_exp | POST-SELECTION | 0 | 121 | 50.413 | -1.574 | -0.046 | -0.456 | 1.000 | 1.000 | -0.029 | 0.119 |
| 15:30\|put\|vixmove_fixed | POST-SELECTION | 2 | 81 | 48.148 | -2.621 | -0.073 | -0.545 | 1.000 | 1.000 | -0.057 | 0.099 |
| 15:30\|put\|vixmove_lit | POST-SELECTION | 2 | 195 | 49.744 | -1.297 | -0.039 | -0.565 | 1.000 | 1.000 | -0.023 | 0.114 |
| 15:30\|both\|mag | POST-SELECTION | 0 | 485 | 48.660 | -0.833 | -0.020 | -0.576 | 1.000 | 1.000 | 0.005 | 0.157 |
| 15:30\|both\|vixmove_lit | POST-SELECTION | 2 | 469 | 48.401 | -1.304 | -0.033 | -0.871 | 1.000 | 1.000 | -0.010 | 0.108 |
| 15:30\|both\|vixmove_exp | POST-SELECTION | 0 | 291 | 46.048 | -1.923 | -0.050 | -0.930 | 1.000 | 1.000 | -0.025 | 0.107 |
| 15:30\|both\|vixmove_fixed | POST-SELECTION | 2 | 189 | 42.857 | -3.062 | -0.078 | -1.049 | 1.000 | 1.000 | -0.055 | 0.083 |

These 15 POST-SELECTION rows are published for transparency only; they do not enter the survival verdict above or pipeline/trials.py's trial family (never promoted).

By calendar year (`out/holdout_by_year.csv`):

| signal | year | n | win | net_pts | net_pct | worst_trade_pts | p_day | opt_mean_s1 | opt_mean_s2 | opt_mean_s3 | worst_day_pts | mae_worst_pct | data_first_date | data_last_date |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 15:00\|both\|vixmove_exp | 2020 | 41 | 43.902 | -5.630 | -0.164 | -52.000 | 1.000 | -7.034 | -7.682 | -8.320 | -52.000 | -72.338 | 2020-07-27 | 2020-12-31 |
| 15:00\|both\|vixmove_exp | 2021 | 43 | 27.907 | -7.328 | -0.176 | -45.500 | 1.000 | -7.984 | -8.524 | -9.057 | -45.500 | -51.599 | 2021-01-04 | 2021-12-31 |
| 15:00\|both\|vixmove_exp | 2022 | 119 | 62.185 | 3.176 | 0.073 | -89.200 | 0.082 | 4.086 | 3.468 | 2.858 | -89.200 | -100.000 | 2022-01-03 | 2022-12-30 |
| 15:00\|both\|vixmove_exp | 2023 | 10 | 70.000 | 7.215 | 0.182 | -7.300 |  | 9.328 | 8.672 | 8.024 | -7.300 | -25.031 | 2023-01-03 | 2023-12-29 |
| 15:00\|both\|vixmove_exp | 2024 | 11 | 72.727 | -0.941 | -0.023 | -53.200 |  | -0.685 | -1.113 | -1.538 | -53.200 | -48.847 | 2024-01-02 | 2024-12-31 |
| 15:00\|both\|vixmove_exp | 2025 | 32 | 53.125 | 2.592 | 0.045 | -46.700 | 0.319 | 2.756 | 2.321 | 1.889 | -46.700 | -59.474 | 2025-01-02 | 2025-12-31 |
| 15:00\|both\|vixmove_exp | 2026 | 18 | 61.111 | -0.889 | -0.014 | -54.950 |  | -0.303 | -0.662 | -1.019 | -54.950 | -43.171 | 2026-01-02 | 2026-09-11 |
| 13:00\|call\|gap>0.3% | 2020 | 43 | 48.837 | -4.687 | -0.131 | -74.900 | 1.000 | -5.607 | -6.254 | -6.892 | -74.900 | -100.000 | 2020-07-27 | 2020-12-31 |
| 13:00\|call\|gap>0.3% | 2021 | 74 | 41.892 | -3.399 | -0.076 | -105.300 | 1.000 | -2.981 | -3.537 | -4.087 | -105.300 | -100.000 | 2021-01-04 | 2021-12-31 |
| 13:00\|call\|gap>0.3% | 2022 | 78 | 58.974 | 1.799 | 0.056 | -99.700 | 0.258 | 3.508 | 2.892 | 2.283 | -99.700 | -100.000 | 2022-01-03 | 2022-12-30 |
| 13:00\|call\|gap>0.3% | 2023 | 67 | 47.761 | -1.652 | -0.031 | -60.500 | 1.000 | -1.029 | -1.590 | -2.144 | -60.500 | -75.891 | 2023-01-03 | 2023-12-29 |
| 13:00\|call\|gap>0.3% | 2024 | 73 | 56.164 | -0.899 | -0.015 | -102.950 | 1.000 | -0.277 | -0.727 | -1.173 | -102.950 | -97.147 | 2024-01-02 | 2024-12-31 |
| 13:00\|call\|gap>0.3% | 2025 | 66 | 53.030 | -7.381 | -0.129 | -102.400 | 1.000 | -5.911 | -6.280 | -6.647 | -102.400 | -100.000 | 2025-01-02 | 2025-12-31 |
| 13:00\|call\|gap>0.3% | 2026 | 51 | 47.059 | 2.269 | 0.029 | -36.800 | 0.277 | 1.727 | 1.382 | 1.040 | -36.800 | -47.972 | 2026-01-02 | 2026-09-11 |

An empty cell is NA: that bootstrap had fewer than 20 blocks (months or days) to resample, so no p-value is reported (survival rule 2); an empty cell is never 1.0 or 0.

opt_mean_s1/s2/s3 = option return in % of premium at quoted spread 1/2/3 (cash settlement); worst_day_pts = the worst calendar day's net index points; mae_worst_pct = the worst intraday adverse excursion in % of premium at spread 1.

Option-level results on the HOLDOUT (% of premium; `out/holdout_d4_summary.csv`) — THE HEADLINE:

| signal | spread | settle | k | n | trades_per_year | win | mean | median | worst_trade | worst_day | mae_worst | full_loss_trades | premium_mean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 15:00\|both\|vixmove_exp | 1.000 | cash | 1.000 | 274 | 44.778 | 52.555 | 0.084 | 1.536 | -100.000 | -100.000 | -100.000 | 1 | 91.086 |
| 15:00\|both\|vixmove_exp | 1.000 | exit | 1.000 | 274 | 44.778 | 51.825 | -0.096 | 0.284 | -88.492 | -88.492 | -100.000 | 0 | 93.713 |
| 15:00\|both\|vixmove_exp | 2.000 | cash | 1.000 | 274 | 44.778 | 52.190 | -0.481 | 0.981 | -100.000 | -100.000 | -100.000 | 1 | 91.586 |
| 15:00\|both\|vixmove_exp | 2.000 | exit | 1.000 | 274 | 44.778 | 47.810 | -1.194 | -0.777 | -89.123 | -89.123 | -100.000 | 0 | 94.213 |
| 15:00\|both\|vixmove_exp | 3.000 | cash | 1.000 | 274 | 44.778 | 51.095 | -1.040 | 0.481 | -100.000 | -100.000 | -100.000 | 1 | 92.086 |
| 15:00\|both\|vixmove_exp | 3.000 | exit | 1.000 | 274 | 44.778 | 45.255 | -2.280 | -1.861 | -89.748 | -89.748 | -100.000 | 0 | 94.713 |
| 13:00\|call\|gap>0.3% | 1.000 | cash | 1.000 | 452 | 73.867 | 50.000 | -1.277 | -0.085 | -100.000 | -100.000 | -100.000 | 3 | 101.902 |
| 13:00\|call\|gap>0.3% | 1.000 | cash | 1.300 | 452 | 73.867 | 50.000 | -1.282 | -0.087 | -100.000 | -100.000 | -100.000 | 3 | 101.908 |
| 13:00\|call\|gap>0.3% | 1.000 | cash | 1.600 | 452 | 73.867 | 50.000 | -1.308 | -0.100 | -100.000 | -100.000 | -100.000 | 3 | 101.936 |
| 13:00\|call\|gap>0.3% | 1.000 | exit | 1.000 | 452 | 73.867 | 50.885 | -1.874 | 0.360 | -100.000 | -100.000 | -100.000 | 1 | 104.358 |
| 13:00\|call\|gap>0.3% | 1.000 | exit | 1.300 | 452 | 73.867 | 50.885 | -1.876 | 0.356 | -99.982 | -99.982 | -100.000 | 1 | 104.363 |
| 13:00\|call\|gap>0.3% | 1.000 | exit | 1.600 | 452 | 73.867 | 50.885 | -1.895 | 0.334 | -99.661 | -99.661 | -100.000 | 0 | 104.386 |
| 13:00\|call\|gap>0.3% | 2.000 | cash | 1.000 | 452 | 73.867 | 48.894 | -1.784 | -0.551 | -100.000 | -100.000 | -100.000 | 3 | 102.402 |
| 13:00\|call\|gap>0.3% | 2.000 | cash | 1.300 | 452 | 73.867 | 48.894 | -1.789 | -0.551 | -100.000 | -100.000 | -100.000 | 3 | 102.408 |
| 13:00\|call\|gap>0.3% | 2.000 | cash | 1.600 | 452 | 73.867 | 48.894 | -1.815 | -0.551 | -100.000 | -100.000 | -100.000 | 3 | 102.436 |
| 13:00\|call\|gap>0.3% | 2.000 | exit | 1.000 | 452 | 73.867 | 48.451 | -2.866 | -0.578 | -100.000 | -100.000 | -100.000 | 1 | 104.858 |
| 13:00\|call\|gap>0.3% | 2.000 | exit | 1.300 | 452 | 73.867 | 48.451 | -2.867 | -0.581 | -100.000 | -100.000 | -100.000 | 1 | 104.863 |
| 13:00\|call\|gap>0.3% | 2.000 | exit | 1.600 | 452 | 73.867 | 48.451 | -2.886 | -0.616 | -100.000 | -100.000 | -100.000 | 1 | 104.886 |
| 13:00\|call\|gap>0.3% | 3.000 | cash | 1.000 | 452 | 73.867 | 47.788 | -2.286 | -0.992 | -100.000 | -100.000 | -100.000 | 3 | 102.902 |
| 13:00\|call\|gap>0.3% | 3.000 | cash | 1.300 | 452 | 73.867 | 47.788 | -2.291 | -0.992 | -100.000 | -100.000 | -100.000 | 3 | 102.908 |
| 13:00\|call\|gap>0.3% | 3.000 | cash | 1.600 | 452 | 73.867 | 47.788 | -2.317 | -0.992 | -100.000 | -100.000 | -100.000 | 3 | 102.936 |
| 13:00\|call\|gap>0.3% | 3.000 | exit | 1.000 | 452 | 73.867 | 46.239 | -3.846 | -1.560 | -100.000 | -100.000 | -100.000 | 2 | 105.358 |
| 13:00\|call\|gap>0.3% | 3.000 | exit | 1.300 | 452 | 73.867 | 46.239 | -3.848 | -1.570 | -100.000 | -100.000 | -100.000 | 1 | 105.363 |
| 13:00\|call\|gap>0.3% | 3.000 | exit | 1.600 | 452 | 73.867 | 46.239 | -3.867 | -1.628 | -100.000 | -100.000 | -100.000 | 1 | 105.386 |

Sizing on the HOLDOUT (% of account; `out/holdout_d4_sizing.csv`):

| limit | size_pct | worst_trade_loss_pct | exp_annual_pct | worst_year_pct | best_year_pct | size_by_worst_day_pct | signal | window | spread | settle | k | days_with_two_positions | worst_day_both_positions_pct |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3.000 | 3.000 | 100.000 | 0.113 | -10.299 | 14.587 | 3.000 | 15:00\|both\|vixmove_exp | HOLDOUT 2020-06-01..2026-09-11 | 1.000 | cash | 1.000 |  |  |
| 4.000 | 4.000 | 100.000 | 0.151 | -13.732 | 19.449 | 4.000 | 15:00\|both\|vixmove_exp | HOLDOUT 2020-06-01..2026-09-11 | 1.000 | cash | 1.000 |  |  |
| 5.000 | 5.000 | 100.000 | 0.188 | -17.165 | 24.311 | 5.000 | 15:00\|both\|vixmove_exp | HOLDOUT 2020-06-01..2026-09-11 | 1.000 | cash | 1.000 |  |  |
| 3.000 | 3.000 | 100.000 | -2.840 | -11.703 | 8.209 | 3.000 | 13:00\|call\|gap>0.3% | HOLDOUT 2020-06-01..2026-09-11 | 1.000 | cash | 1.300 |  |  |
| 4.000 | 4.000 | 100.000 | -3.786 | -15.605 | 10.945 | 4.000 | 13:00\|call\|gap>0.3% | HOLDOUT 2020-06-01..2026-09-11 | 1.000 | cash | 1.300 |  |  |
| 5.000 | 5.000 | 100.000 | -4.733 | -19.506 | 13.681 | 5.000 | 13:00\|call\|gap>0.3% | HOLDOUT 2020-06-01..2026-09-11 | 1.000 | cash | 1.300 |  |  |
| 3.000 | 1.805 | 166.216 | -1.641 |  |  |  | COMBINED BOOK | HOLDOUT 2020-06-01..2026-09-11 |  |  |  | 128 | -166.216 |
| 4.000 | 2.407 | 166.216 | -2.187 |  |  |  | COMBINED BOOK | HOLDOUT 2020-06-01..2026-09-11 |  |  |  | 128 | -166.216 |
| 5.000 | 3.008 | 166.216 | -2.734 |  |  |  | COMBINED BOOK | HOLDOUT 2020-06-01..2026-09-11 |  |  |  | 128 | -166.216 |

Execution on the HOLDOUT (`out/holdout_d4_execution.csv`):

| window | candidate | entry | fill_rate | n_signals | mean_net_per_signal | mean_net_if_filled | improvement | improvement_cost_part | improvement_price_part | p_improvement | p_boot_day |
|---|---|---|---|---|---|---|---|---|---|---|---|
| HOLDOUT 2020-06-01..2026-09-11 | 13:00\|call\|gap>0.3% | market | 1.000 | 452 | -1.904 | -1.904 | 0.000 | 0.000 | 0.000 |  | 1.000 |
| HOLDOUT 2020-06-01..2026-09-11 | 13:00\|call\|gap>0.3% | limit -0.25 ATR | 0.841 | 452 | -1.658 | -1.973 | 0.245 | 0.336 | -0.091 | 0.278 | 1.000 |
| HOLDOUT 2020-06-01..2026-09-11 | 13:00\|call\|gap>0.3% | limit -0.50 ATR | 0.732 | 452 | -1.794 | -2.450 | 0.110 | 0.293 | -0.183 | 0.422 | 1.000 |
| HOLDOUT 2020-06-01..2026-09-11 | 13:00\|call\|gap>0.3% | limit -1.00 ATR | 0.562 | 452 | -1.592 | -2.833 | 0.312 | 0.225 | 0.087 | 0.331 | 1.000 |
| HOLDOUT 2020-06-01..2026-09-11 | 15:00\|both\|vixmove_exp | market | 1.000 | 274 | -0.143 | -0.143 | 0.000 | 0.000 | 0.000 |  | 1.000 |
| HOLDOUT 2020-06-01..2026-09-11 | 15:00\|both\|vixmove_exp | limit -0.25 ATR | 0.832 | 274 | -0.699 | -0.840 | -0.556 | 0.333 | -0.888 | 1.000 | 1.000 |
| HOLDOUT 2020-06-01..2026-09-11 | 15:00\|both\|vixmove_exp | limit -0.50 ATR | 0.701 | 274 | -1.095 | -1.563 | -0.952 | 0.280 | -1.232 | 1.000 | 1.000 |
| HOLDOUT 2020-06-01..2026-09-11 | 15:00\|both\|vixmove_exp | limit -1.00 ATR | 0.518 | 274 | -1.594 | -3.075 | -1.450 | 0.207 | -1.657 | 1.000 | 1.000 |

IN-SAMPLE + HOLDOUT (2013-01..2026-09-11) — full-sample figures, NOT the headline:

Option-level results (% of premium; `out/fullsample_summary.csv`):

| signal | spread | settle | k | n | trades_per_year | win | mean | median | worst_trade | worst_day | mae_worst | full_loss_trades | premium_mean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 15:00\|both\|vixmove_exp | 1.000 | cash | 1.000 | 419 | 30.657 | 55.847 | 2.595 | 2.522 | -100.000 | -100.000 | -100.000 | 6 | 77.771 |
| 15:00\|both\|vixmove_exp | 1.000 | exit | 1.000 | 419 | 30.657 | 52.745 | 1.209 | 0.655 | -99.260 | -99.260 | -100.000 | 0 | 80.396 |
| 15:00\|both\|vixmove_exp | 2.000 | cash | 1.000 | 419 | 30.657 | 54.654 | 1.866 | 1.963 | -100.000 | -100.000 | -100.000 | 6 | 78.271 |
| 15:00\|both\|vixmove_exp | 2.000 | exit | 1.000 | 419 | 30.657 | 47.733 | -0.155 | -0.773 | -100.000 | -100.000 | -100.000 | 2 | 80.896 |
| 15:00\|both\|vixmove_exp | 3.000 | cash | 1.000 | 419 | 30.657 | 53.222 | 1.149 | 1.394 | -100.000 | -100.000 | -100.000 | 6 | 78.771 |
| 15:00\|both\|vixmove_exp | 3.000 | exit | 1.000 | 419 | 30.657 | 45.346 | -1.495 | -1.990 | -100.000 | -100.000 | -100.000 | 2 | 81.396 |
| 13:00\|call\|gap>0.3% | 1.000 | cash | 1.000 | 875 | 64.021 | 50.400 | -0.091 | 0.265 | -100.000 | -100.000 | -100.000 | 7 | 76.750 |
| 13:00\|call\|gap>0.3% | 1.000 | cash | 1.300 | 875 | 64.021 | 50.400 | -0.131 | 0.265 | -100.000 | -100.000 | -100.000 | 7 | 76.767 |
| 13:00\|call\|gap>0.3% | 1.000 | cash | 1.600 | 875 | 64.021 | 50.400 | -0.206 | 0.265 | -100.000 | -100.000 | -100.000 | 7 | 76.807 |
| 13:00\|call\|gap>0.3% | 1.000 | exit | 1.000 | 875 | 64.021 | 48.914 | -0.934 | -0.155 | -100.000 | -100.000 | -100.000 | 4 | 79.183 |
| 13:00\|call\|gap>0.3% | 1.000 | exit | 1.300 | 875 | 64.021 | 48.914 | -0.963 | -0.155 | -100.000 | -100.000 | -100.000 | 4 | 79.199 |
| 13:00\|call\|gap>0.3% | 1.000 | exit | 1.600 | 875 | 64.021 | 48.914 | -1.022 | -0.155 | -100.000 | -100.000 | -100.000 | 3 | 79.234 |
| 13:00\|call\|gap>0.3% | 2.000 | cash | 1.000 | 875 | 64.021 | 48.686 | -0.858 | -0.429 | -100.000 | -100.000 | -100.000 | 7 | 77.250 |
| 13:00\|call\|gap>0.3% | 2.000 | cash | 1.300 | 875 | 64.021 | 48.686 | -0.897 | -0.429 | -100.000 | -100.000 | -100.000 | 7 | 77.267 |
| 13:00\|call\|gap>0.3% | 2.000 | cash | 1.600 | 875 | 64.021 | 48.571 | -0.971 | -0.429 | -100.000 | -100.000 | -100.000 | 7 | 77.307 |
| 13:00\|call\|gap>0.3% | 2.000 | exit | 1.000 | 875 | 64.021 | 44.914 | -2.394 | -1.824 | -100.000 | -100.000 | -100.000 | 5 | 79.683 |
| 13:00\|call\|gap>0.3% | 2.000 | exit | 1.300 | 875 | 64.021 | 44.914 | -2.423 | -1.824 | -100.000 | -100.000 | -100.000 | 4 | 79.699 |
| 13:00\|call\|gap>0.3% | 2.000 | exit | 1.600 | 875 | 64.021 | 44.914 | -2.481 | -1.824 | -100.000 | -100.000 | -100.000 | 4 | 79.734 |
| 13:00\|call\|gap>0.3% | 3.000 | cash | 1.000 | 875 | 64.021 | 46.629 | -1.612 | -1.130 | -100.000 | -100.000 | -100.000 | 7 | 77.750 |
| 13:00\|call\|gap>0.3% | 3.000 | cash | 1.300 | 875 | 64.021 | 46.629 | -1.650 | -1.130 | -100.000 | -100.000 | -100.000 | 7 | 77.767 |
| 13:00\|call\|gap>0.3% | 3.000 | cash | 1.600 | 875 | 64.021 | 46.629 | -1.723 | -1.132 | -100.000 | -100.000 | -100.000 | 7 | 77.807 |
| 13:00\|call\|gap>0.3% | 3.000 | exit | 1.000 | 875 | 64.021 | 41.486 | -3.828 | -3.440 | -100.000 | -100.000 | -100.000 | 6 | 80.183 |
| 13:00\|call\|gap>0.3% | 3.000 | exit | 1.300 | 875 | 64.021 | 41.486 | -3.857 | -3.440 | -100.000 | -100.000 | -100.000 | 5 | 80.199 |
| 13:00\|call\|gap>0.3% | 3.000 | exit | 1.600 | 875 | 64.021 | 41.486 | -3.915 | -3.440 | -100.000 | -100.000 | -100.000 | 5 | 80.234 |

Sizing (% of account; `out/fullsample_sizing.csv`):

| signal | limit | size_pct | worst_trade_loss_pct | exp_annual_pct | worst_year_pct | best_year_pct | days_with_two_positions | worst_day_both_positions_pct |
|---|---|---|---|---|---|---|---|---|
| 15:00\|both\|vixmove_exp | 3.000 | 3.000 | 100.000 | 2.386 | -10.299 | 21.137 |  |  |
| 15:00\|both\|vixmove_exp | 4.000 | 4.000 | 100.000 | 3.182 | -13.732 | 28.183 |  |  |
| 15:00\|both\|vixmove_exp | 5.000 | 5.000 | 100.000 | 3.977 | -17.165 | 35.228 |  |  |
| 13:00\|call\|gap>0.3% | 3.000 | 3.000 | 100.000 | -0.251 | -11.703 | 10.339 |  |  |
| 13:00\|call\|gap>0.3% | 4.000 | 4.000 | 100.000 | -0.335 | -15.605 | 13.786 |  |  |
| 13:00\|call\|gap>0.3% | 5.000 | 5.000 | 100.000 | -0.419 | -19.506 | 17.232 |  |  |
| COMBINED BOOK | 3.000 | 1.500 | 200.000 | 1.067 |  |  | 205 | -200.000 |
| COMBINED BOOK | 4.000 | 2.000 | 200.000 | 1.423 |  |  | 205 | -200.000 |
| COMBINED BOOK | 5.000 | 2.500 | 200.000 | 1.779 |  |  | 205 | -200.000 |

Execution (`out/fullsample_execution.csv`):

| candidate | entry | fill_rate | n_signals | mean_net_per_signal | mean_net_if_filled | improvement | improvement_cost_part | improvement_price_part | p_improvement |
|---|---|---|---|---|---|---|---|---|---|
| 13:00\|call\|gap>0.3% | market | 1.000 | 875 | -1.050 | -1.050 | 0.000 | 0.000 | 0.000 |  |
| 13:00\|call\|gap>0.3% | limit -0.25 ATR | 0.848 | 875 | -0.606 | -0.715 | 0.444 | 0.339 | 0.105 | 0.035 |
| 13:00\|call\|gap>0.3% | limit -0.50 ATR | 0.737 | 875 | -0.586 | -0.795 | 0.464 | 0.295 | 0.169 | 0.074 |
| 13:00\|call\|gap>0.3% | limit -1.00 ATR | 0.559 | 875 | -0.687 | -1.229 | 0.363 | 0.224 | 0.140 | 0.222 |
| 15:00\|both\|vixmove_exp | market | 1.000 | 419 | 0.984 | 0.984 | 0.000 | 0.000 | 0.000 |  |
| 15:00\|both\|vixmove_exp | limit -0.25 ATR | 0.857 | 419 | 0.698 | 0.815 | -0.286 | 0.343 | -0.628 | 1.000 |
| 15:00\|both\|vixmove_exp | limit -0.50 ATR | 0.728 | 419 | 0.348 | 0.478 | -0.636 | 0.291 | -0.927 | 1.000 |
| 15:00\|both\|vixmove_exp | limit -1.00 ATR | 0.525 | 419 | 0.116 | 0.220 | -0.869 | 0.210 | -1.079 | 1.000 |

## 8. Before any live capital (both threads' rule)

Measure ten real 2%-ITM 0DTE fills at the mid; above 1.5 index points round-trip nothing here works. Paper-trade ≥ 60 qualifying days. Real 0DTE IV runs above 30-day VIX; the 13:00 leg is the only one where that matters.

## 9. Owner-proposed fair-value-gap setup (A36) — pre-registered 2026-09-13, 8 trials

8 trials (side {short, long} × R {1, 2} × BOS {on, off}) from `pipeline.units.fvg` (`out/fvg_candidates.csv`), reported on three windows. Only the SELECTION-window rows are counted in the trial family (`pipeline/trials.py`, `out/trials.csv`); CONTEXT is background and HOLDOUT is these same 8 trials' out-of-sample rows, reported here, not double-counted.

### CONTEXT (2005-01-01 → 2012-12-31)

| trial | n_setups | fill_rate | n | win | net_pts_cost1 | net_pts_cost2 | net_pct_cost1 | worst_trade_pts_cost1 | worst_day_pts_cost1 | sharpe_calday | p_boot_day | p_boot_month | control_mean_pts_cost1 | frac_seeds_beaten | dsr_N33 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| short\|R1\|bos_on | 864 | 0.5660 | 489 | 74.0286 | -0.3945 | -1.3945 | -0.0316 | -4.7875 | -4.7300 | -2.2080 | 1.0000 | 1.0000 | -0.9781 | 1.0000 | 0.0000 |
| short\|R2\|bos_on | 863 | 0.5655 | 488 | 45.9016 | -0.5072 | -1.5072 | -0.0438 | -5.4570 | -7.5095 | -1.7348 | 1.0000 | 1.0000 | -0.8633 | 1.0000 | 0.0000 |
| short\|R1\|bos_off | 1412 | 0.6069 | 857 | 73.9790 | -0.3957 | -1.3957 | -0.0315 | -5.2935 | -8.3605 | -2.8168 | 1.0000 | 1.0000 | -1.0550 | 1.0000 | 0.0000 |
| short\|R2\|bos_off | 1405 | 0.6071 | 853 | 45.6038 | -0.6000 | -1.6000 | -0.0505 | -5.7580 | -8.3605 | -2.7902 | 1.0000 | 1.0000 | -1.0421 | 1.0000 | 0.0000 |
| long\|R1\|bos_on | 776 | 0.5142 | 399 | 71.1779 | -0.3880 | -1.3880 | -0.0296 | -6.7540 | -6.8095 | -1.4248 | 1.0000 | 1.0000 | -1.0255 | 1.0000 | 0.0000 |
| long\|R2\|bos_on | 776 | 0.5142 | 399 | 43.8596 | -0.4895 | -1.4895 | -0.0352 | -6.7540 | -8.0820 | -1.0107 | 1.0000 | 1.0000 | -0.9356 | 1.0000 | 0.0000 |
| long\|R1\|bos_off | 1360 | 0.5816 | 791 | 74.2099 | -0.3118 | -1.3118 | -0.0233 | -5.2600 | -6.8095 | -1.5481 | 1.0000 | 1.0000 | -1.0552 | 1.0000 | 0.0000 |
| long\|R2\|bos_off | 1358 | 0.5810 | 789 | 44.4867 | -0.5377 | -1.5377 | -0.0436 | -12.6225 | -8.0820 | -1.8675 | 1.0000 | 1.0000 | -1.0183 | 1.0000 | 0.0000 |

0 of 8 trials net > 0 at 1 pt; 0 of 8 have p_day < 0.05; no trial survives (net > 0 AND p_day < 0.05 AND excess over control > 0 AND n ≥ 200; DSR at N=33 is reported in the table above, not a survival condition).

### SELECTION (2013-01-01 → 2020-05-13) — counted in the trial family

| trial | n_setups | fill_rate | n | win | net_pts_cost1 | net_pts_cost2 | net_pct_cost1 | worst_trade_pts_cost1 | worst_day_pts_cost1 | sharpe_calday | p_boot_day | p_boot_month | control_mean_pts_cost1 | frac_seeds_beaten | dsr_N33 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| short\|R1\|bos_on | 741 | 0.6221 | 461 | 65.0759 | -0.5035 | -1.5035 | -0.0239 | -6.9260 | -6.9260 | -2.2975 | 1.0000 | 1.0000 | -0.9649 | 1.0000 | 0.0000 |
| short\|R2\|bos_on | 740 | 0.6216 | 460 | 38.0435 | -0.7096 | -1.7096 | -0.0331 | -9.8125 | -9.8125 | -2.0431 | 1.0000 | 1.0000 | -0.7278 | 0.5450 | 0.0000 |
| short\|R1\|bos_off | 1324 | 0.6488 | 859 | 65.7742 | -0.4000 | -1.4000 | -0.0201 | -14.3400 | -14.3400 | -2.3289 | 1.0000 | 1.0000 | -1.0364 | 1.0000 | 0.0000 |
| short\|R2\|bos_off | 1321 | 0.6480 | 856 | 39.6028 | -0.7045 | -1.7045 | -0.0335 | -16.2270 | -16.2270 | -2.7058 | 1.0000 | 1.0000 | -0.9256 | 0.9850 | 0.0000 |
| long\|R1\|bos_on | 608 | 0.5066 | 308 | 62.9870 | -0.3210 | -1.3210 | -0.0168 | -8.1675 | -8.1675 | -0.9845 | 1.0000 | 1.0000 | -1.0390 | 1.0000 | 0.0000 |
| long\|R2\|bos_on | 607 | 0.5058 | 307 | 37.4593 | -0.7274 | -1.7274 | -0.0345 | -18.1860 | -18.1860 | -1.2324 | 1.0000 | 1.0000 | -0.8600 | 0.7350 | 0.0001 |
| long\|R1\|bos_off | 1183 | 0.5613 | 664 | 65.3614 | -0.2309 | -1.2309 | -0.0138 | -11.1020 | -11.1020 | -1.0802 | 1.0000 | 1.0000 | -1.1165 | 1.0000 | 0.0000 |
| long\|R2\|bos_off | 1177 | 0.5616 | 661 | 39.6369 | -0.6737 | -1.6737 | -0.0314 | -26.4970 | -18.1860 | -1.8059 | 1.0000 | 1.0000 | -1.0854 | 1.0000 | 0.0000 |

0 of 8 trials net > 0 at 1 pt; 0 of 8 have p_day < 0.05; no trial survives (net > 0 AND p_day < 0.05 AND excess over control > 0 AND n ≥ 200; DSR at N=33 is reported in the table above, not a survival condition).

### HOLDOUT (2020-07-27 → 2026-09-11)

| trial | n_setups | fill_rate | n | win | net_pts_cost1 | net_pts_cost2 | net_pct_cost1 | worst_trade_pts_cost1 | worst_day_pts_cost1 | sharpe_calday | p_boot_day | p_boot_month | control_mean_pts_cost1 | frac_seeds_beaten | dsr_N33 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| short\|R1\|bos_on | 889 | 0.5546 | 493 | 60.8519 | -0.0039 | -1.0039 | -0.0003 | -14.7242 | -15.5900 | -0.0326 | 1.0000 | 1.0000 | -0.8682 | 1.0000 | 0.0004 |
| short\|R2\|bos_on | 887 | 0.5558 | 493 | 35.4970 | -0.5756 | -1.5756 | -0.0138 | -19.3095 | -19.3095 | -0.8569 | 1.0000 | 1.0000 | -0.3913 | 0.2000 | 0.0000 |
| short\|R1\|bos_off | 1629 | 0.5887 | 959 | 60.3754 | 0.0263 | -0.9737 | 0.0002 | -15.1265 | -22.5450 | 0.0181 | 0.4803 | 0.4870 | -1.1725 | 1.0000 | 0.0000 |
| short\|R2\|bos_off | 1620 | 0.5914 | 958 | 35.3862 | -0.6621 | -1.6621 | -0.0151 | -19.3095 | -19.3095 | -1.2442 | 1.0000 | 1.0000 | -0.9742 | 0.9050 | 0.0000 |
| long\|R1\|bos_on | 616 | 0.4578 | 282 | 56.7376 | -0.5658 | -1.5658 | -0.0140 | -17.6313 | -17.6313 | -0.9564 | 1.0000 | 1.0000 | -0.9846 | 0.9000 | 0.0000 |
| long\|R2\|bos_on | 615 | 0.4585 | 282 | 35.4610 | -1.1434 | -2.1434 | -0.0265 | -17.6313 | -24.2755 | -1.3750 | 1.0000 | 1.0000 | -0.7097 | 0.0800 | 0.0000 |
| long\|R1\|bos_off | 1337 | 0.5236 | 700 | 58.1429 | -0.2276 | -1.2276 | -0.0054 | -17.6313 | -18.4780 | -0.5439 | 1.0000 | 1.0000 | -1.2673 | 1.0000 | 0.0000 |
| long\|R2\|bos_off | 1330 | 0.5233 | 696 | 36.2069 | -0.7222 | -1.7222 | -0.0145 | -17.6313 | -27.0968 | -1.0496 | 1.0000 | 1.0000 | -1.2309 | 1.0000 | 0.0000 |

1 of 8 trials net > 0 at 1 pt; 0 of 8 have p_day < 0.05; no trial survives (net > 0 AND p_day < 0.05 AND excess over control > 0 AND n ≥ 200; DSR at N=33 is reported in the table above, not a survival condition).

FIXED (pre-registration): ATR mult 1.5, structure lookback 12 bars, stop buffer 0.1 ATR, min box height 0.05 ATR, entry = box midpoint. atr_ref for a setup ending at bar t = rolling(20) mean true range of the 20 bars strictly before the displacement bar t-1 (no lookahead into t-1/t); ATR rolls across sessions only for the first ~19 bars of a session, else same-session (pre-registration's own allowance); true range at a session's first bar uses that bar's own open, not the prior session's close (no overnight gap in ATR).

## 10. Overnight-loss forced-liquidation rebound (A39) — pre-registered 2026-09-13, 3 trials

3 trials (T1 long call entry 10:00, T2 same days long call entry 09:31, T3 mirror signal long put entry 10:00) from `pipeline.units.gapliq` (`out/gapliq_candidates.csv`), reported on three windows. Only the SELECTION-window rows are counted in the trial family (`pipeline/trials.py`, `out/trials.csv`); CONTEXT is background and HOLDOUT is these same 3 trials' out-of-sample rows, reported here, not double-counted.

### CONTEXT (2005-01-01 → 2012-12-31)

| trial | side | entry_time | n_signal_days | n_skipped | n | win | net_pts_cost1 | net_pts_cost2 | net_pct_cost1 | worst_trade_pts_cost1 | worst_day_pts_cost1 | sharpe_calday | p_boot_day | p_boot_month | control_mean_pts_cost1 | frac_seeds_beaten | timing_control_pts_cost1 | frac_timing_beaten | opt_mean_pct_s1 | dsr_N37 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T1 | call | 10:00 | 284 | 0 | 284 | 44.7183 | -3.1873 | -4.1873 | -0.2771 | -62.3000 | -62.3000 | -1.0962 | 1.0000 | 1.0000 | -0.6471 | 0.0000 | -2.7408 | 0.0900 | -7.0881 | 0.0000 |
| T2 | call | 09:31 | 284 | 0 | 284 | 47.8873 | -2.4500 | -3.4500 | -0.2029 | -69.6000 | -69.6000 | -0.7298 | 1.0000 | 1.0000 | -0.8500 | 0.0050 | -2.7408 | 0.8150 | -3.5841 | 0.0000 |
| T3 | put | 10:00 | 273 | 0 | 273 | 39.1941 | -3.6725 | -4.6725 | -0.3469 | -73.0000 | -73.0000 | -1.2901 | 1.0000 | 1.0000 | -0.4838 | 0.0000 | -3.7292 | 0.5700 | -9.2340 | 0.0000 |

T1: net <= 0 at 1 pt, p_day >= 0.05, excess over the day-selection control <= 0, n >= 200 -> does not survive the four programmatic checks (DSR at N=37 is reported in the table above, not a survival condition). Fingerprint: T2 >= T1 (fails); T3 <= 0 at 1 pt (holds). Promotion: T1 does not survive, not promoted.

### SELECTION (2013-01-01 → 2020-05-13) — counted in the trial family

| trial | side | entry_time | n_signal_days | n_skipped | n | win | net_pts_cost1 | net_pts_cost2 | net_pct_cost1 | worst_trade_pts_cost1 | worst_day_pts_cost1 | sharpe_calday | p_boot_day | p_boot_month | control_mean_pts_cost1 | frac_seeds_beaten | timing_control_pts_cost1 | frac_timing_beaten | opt_mean_pct_s1 | dsr_N37 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T1 | call | 10:00 | 123 | 2 | 121 | 47.1074 | -2.4124 | -3.4124 | -0.0974 | -99.4000 | -99.4000 | -0.3564 | 1.0000 | 1.0000 | -0.7693 | 0.1050 | -1.9027 | 0.2950 | -2.6008 | 0.0001 |
| T2 | call | 09:31 | 123 | 2 | 121 | 51.2397 | -0.9017 | -1.9017 | -0.0240 | -94.8000 | -94.8000 | -0.0845 | 1.0000 | 1.0000 | -0.9280 | 0.5350 | -1.9027 | 0.8350 | 0.4543 | 0.0010 |
| T3 | put | 10:00 | 132 | 0 | 132 | 31.0606 | -8.5947 | -9.5947 | -0.3526 | -165.0000 | -165.0000 | -1.0583 | 1.0000 | 1.0000 | -0.4166 | 0.0000 | -7.1055 | 0.0500 | -10.4819 | 0.0000 |

T1: net <= 0 at 1 pt, p_day >= 0.05, excess over the day-selection control <= 0, n < 200 -> does not survive the four programmatic checks (DSR at N=37 is reported in the table above, not a survival condition). Fingerprint: T2 >= T1 (fails); T3 <= 0 at 1 pt (holds). Promotion: T1 does not survive, not promoted.

### HOLDOUT (2020-07-27 → 2026-09-11)

| trial | side | entry_time | n_signal_days | n_skipped | n | win | net_pts_cost1 | net_pts_cost2 | net_pct_cost1 | worst_trade_pts_cost1 | worst_day_pts_cost1 | sharpe_calday | p_boot_day | p_boot_month | control_mean_pts_cost1 | frac_seeds_beaten | timing_control_pts_cost1 | frac_timing_beaten | opt_mean_pct_s1 | dsr_N37 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T1 | call | 10:00 | 158 | 0 | 158 | 54.4304 | 2.2016 | 1.2016 | 0.0513 | -166.7500 | -166.7500 | 0.2603 | 0.2592 | 0.2278 | -1.0715 | 0.8550 | 0.0153 | 0.9350 | 3.5742 | 0.4354 |
| T2 | call | 09:31 | 158 | 0 | 158 | 55.0633 | 0.1168 | -0.8832 | -0.0082 | -189.7000 | -189.7000 | -0.0369 | 1.0000 | 1.0000 | -0.4384 | 0.5500 | 0.0153 | 0.5150 | 1.0202 | 0.1841 |
| T3 | put | 10:00 | 154 | 0 | 154 | 39.6104 | 1.8922 | 0.8922 | 0.0131 | -84.5000 | -84.5000 | 0.0662 | 0.4338 | 0.4353 | -1.2510 | 0.9050 | 1.4791 | 0.6450 | 0.9594 | 0.2608 |

T1: net > 0 at 1 pt, p_day >= 0.05, excess over the day-selection control > 0, n < 200 -> does not survive the four programmatic checks (DSR at N=37 is reported in the table above, not a survival condition). Fingerprint: T2 < T1 (holds); T3 > 0 at 1 pt (fails). Promotion: T1 does not survive, not promoted.

FIXED (pre-registration, A39): signal = overnight return (prior session's last RTH close -> this session's first RTH open) <= the expanding 10th percentile (T1/T2) / >= the expanding 90th percentile (T3, mirror) of overnight returns over all strictly prior sessions, min 250 prior sessions, no fitted parameter. T1 long call entry 10:00 bar close; T2 same days as T1, long call entry 09:31 bar close; T3 mirror signal, long put, entry 10:00 bar close; all exit at the 16:00 close.

## 11. Leveraged-ETF close rebalancing (A38, owner's option C) — pre-registered 2026-09-13, 1 trial

Waits for `data/ext/letf_aum_2006_2026.csv`; the unit skipped.
