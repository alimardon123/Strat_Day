# PLAYBOOK_0DTE.md — the constrained book, every number measured

**Account constraint.** 0DTE options only, long-only, naked calls or puts; no selling, spreads, futures, shares or overnight holds; daily loss limit 3–5% (base case 4%) on marked intraday P&L.

**Pricing model, stated first.** No real 0DTE quotes were obtainable. Every option number below is Black-Scholes with r = 0 and IV = k × prior-close VIX (both prior threads used k = 1.0 and called it generous). At 2% in the money with less than an hour to expiry that model is intrinsic value ± the spread (time value ≤ 0.000 index points at 60 minutes for VIX ≤ 40 and ≤ 0.159 at VIX 83, `out/options_timevalue.csv`), so k only matters for the 13:00 leg and the spread is the real sensitivity axis. SPX/XSP are PM cash-settled: buy at the ask (half the quoted spread), settle at intrinsic. SPY is physically settled and must be sold by 15:55 with both spread halves paid; SPY rows are for that exit.

**Holdout status: PENDING.** The post-May-2020 minute file (`data/ext/spx_1min_2020-05_2026-09.csv.gz`) has not been supplied, so the holdout (2020-06-01 → 2026-09-11) has not run. Every table below is measured on the 2013-01-01 → 2020-05-13 SELECTION WINDOW and is labelled IN-SAMPLE. It is not the headline and must not be traded on. The headline block will be generated from `out/holdout_*.csv` when the file arrives.

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

Every VIX-gated two-sided configuration outranks every magnitude-gated or put-only one; the four VIX-gated two-sided variants tie within 0.10 Sharpe and the tie-break (fewest FITTED parameters — an expanding rule has none) picks the 15:00 entry with the expanding-tercile rule. 0 of 23 trials pass BH-FDR at 10% across the family (`out/trials.csv`).

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

PENDING `data/ext/spx_1min_2020-05_2026-09.csv.gz`. When it arrives, `make all` runs the holdout step (`python -m pipeline.insample 2020-06-01 2026-09-11 HOLDOUT`), the family-wide FDR in `pipeline/trials.py` finalises the labels, and this section is generated from `out/holdout_*.csv`. If the pre-registered signal fails, that is the result; no re-tuning.

## 8. Before any live capital (both threads' rule)

Measure ten real 2%-ITM 0DTE fills at the mid; above 1.5 index points round-trip nothing here works. Paper-trade ≥ 60 qualifying days. Real 0DTE IV runs above 30-day VIX; the 13:00 leg is the only one where that matters.
