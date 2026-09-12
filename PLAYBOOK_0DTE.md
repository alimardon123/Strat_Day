# PLAYBOOK_0DTE.md — the constrained book, every number measured

**Account constraint.** 0DTE options only, long-only, naked calls or puts; no selling, spreads, futures, shares or overnight holds; daily loss limit 3–5% (base case 4%) on marked intraday P&L.

**Pricing model, stated first.** No real 0DTE quotes were obtainable. Every option number below is Black-Scholes with r = 0 and IV = k × prior-close VIX (both prior threads used k = 1.0 and called it generous). At 2% in the money with less than an hour to expiry that model is intrinsic value ± the spread (time value < 0.02 index points for VIX ≤ 40), so k only matters for the 13:00 leg and the spread is the real sensitivity axis. SPX/XSP are PM cash-settled: buy at the ask (half the quoted spread), settle at intrinsic. SPY is physically settled and must be sold by 15:55 with both spread halves paid; SPY rows are for that exit.

**Holdout status: PENDING.** The post-May-2020 minute file (`data/ext/spx_1min_2020-05_2026-09.csv.gz`) has not been supplied, so the holdout (2020-06-01 → 2026-09-11) has not run. Every table below is measured on the 2013-01-01 → 2020-05-13 SELECTION WINDOW and is labelled IN-SAMPLE. It is not the headline and must not be traded on. The headline block will be generated from `out/holdout_*.csv` when the file arrives.

## 1. The pre-registered specification

**Reconciled last-hour momentum signal (D1 winner):** `15:00|both|vixmove_fixed` — decision at 15:00 ET on the bar close; gate: prior-close VIX and |prior close → entry| above upper-tercile boundaries frozen from Oanda 2005–2012; direction: call on an up move, put on a down move; entry at the next bar's open; hold to the 16:00 settlement.
Frozen gate values: 15:00 → VIX > 22.81 and |move| > 0.816%; 15:30 → VIX > 22.81 and |move| > 0.845%.

**Thread A's gap-up call (pre-registered by Thread A):** open / prior close − 1 > 0.3% → 2% ITM call at the first bar after 13:00 ET, hold to settlement.

Strike: 2% in the money, rounded away from spot to the grid (5 points SPX, $1 SPY/XSP). Never at-the-money or out-of-the-money (−53% per trade at a 17% hit rate in both threads).

## 2. How the specification was chosen (selection window 2013-01 → 2020-05-13, Oanda SPX, net of 1.0 pt)

| rank | candidate | n | win | net_pts | net_pct | sharpe_calday | p_boot_month | p_boot_day | excess_over_control_pct | dsr_N12 | dsr_N42 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1.000 | 15:00|both|vixmove_fixed | 93 | 63.441 | 5.103 | 0.188 | 0.570 |  | 0.067 | 0.226 | 0.747 | 0.662 |
| 2.000 | 15:30|both|vixmove_exp | 147 | 59.864 | 2.581 | 0.099 | 0.533 | 0.078 | 0.080 | 0.128 | 0.634 | 0.515 |
| 3.000 | 15:30|both|vixmove_fixed | 93 | 59.140 | 3.770 | 0.145 | 0.530 |  | 0.083 | 0.177 | 0.707 | 0.620 |
| 4.000 | 15:00|both|vixmove_exp | 146 | 63.014 | 3.090 | 0.111 | 0.511 | 0.180 | 0.099 | 0.151 | 0.616 | 0.493 |
| 5.000 | 15:30|put|mag | 182 | 57.143 | 0.771 | 0.033 | 0.273 | 0.255 | 0.238 | 0.072 | 0.338 | 0.232 |
| 6.000 | 15:30|put|vixmove_exp | 62 | 51.613 | 1.542 | 0.054 | 0.178 |  | 0.314 | 0.094 | 0.416 | 0.343 |
| 7.000 | 15:00|put|vixmove_fixed | 42 | 54.762 | 2.412 | 0.080 | 0.167 |  | 0.335 | 0.121 | 0.449 | 0.386 |
| 8.000 | 15:00|put|vixmove_exp | 58 | 55.172 | 1.740 | 0.055 | 0.151 |  | 0.351 | 0.095 | 0.396 | 0.324 |
| 9.000 | 15:00|put|mag | 189 | 52.381 | 0.324 | 0.017 | 0.131 | 0.362 | 0.374 | 0.062 | 0.205 | 0.123 |
| 10.000 | 15:30|put|vixmove_fixed | 43 | 51.163 | 1.116 | 0.033 | 0.083 |  | 0.409 | 0.072 | 0.366 | 0.307 |
| 11.000 | 15:30|both|mag | 371 | 54.717 | 0.067 | 0.002 | 0.024 | 0.478 | 0.470 | 0.036 | 0.057 | 0.019 |
| 12.000 | 15:00|both|mag | 371 | 50.943 | -0.033 | 0.001 | 0.009 | 0.493 | 0.492 | 0.039 | 0.052 | 0.017 |

Literal Thread B thresholds (17.06 / 0.665, in-sample on 2013–2018, reported not ranked):

| candidate | n | win | net_pts | net_pct | sharpe_calday | p_boot_month | p_boot_day |
|---|---|---|---|---|---|---|---|
| 15:00|put|vixmove_lit | 103 | 54.369 | 1.872 | 0.068 | 0.310 | 0.183 | 0.207 |
| 15:00|both|vixmove_lit | 255 | 58.431 | 2.083 | 0.081 | 0.615 | 0.134 | 0.058 |
| 15:30|put|vixmove_lit | 106 | 57.547 | 1.537 | 0.060 | 0.321 | 0.100 | 0.203 |
| 15:30|both|vixmove_lit | 257 | 59.144 | 1.472 | 0.058 | 0.528 | 0.100 | 0.089 |

Every VIX-gated two-sided configuration outranks every magnitude-gated or put-only one; the four VIX-gated two-sided variants tie within 0.10 Sharpe and the parameter-count tie-break picks the 15:00 entry with frozen thresholds. No configuration passes BH-FDR at 10% on the selection window.

## 3. Option-level results — IN-SAMPLE (% of premium per trade)

| signal | spread | settle | k | n | trades_per_year | win | mean | median | worst_trade | worst_day | full_loss_trades | premium_mean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 15:00|both|vixmove_fixed | 1.000 | cash | 1.000 | 93 | 12.637 | 63.441 | 11.481 | 7.226 | -100.000 | -100.000 | 5 | 52.589 |
| 15:00|both|vixmove_fixed | 1.000 | exit | 1.000 | 93 | 12.637 | 53.763 | 6.298 | 1.559 | -100.000 | -100.000 | 5 | 50.558 |
| 15:00|both|vixmove_fixed | 2.000 | cash | 1.000 | 93 | 12.637 | 60.215 | 10.402 | 5.991 | -100.000 | -100.000 | 5 | 53.089 |
| 15:00|both|vixmove_fixed | 2.000 | exit | 1.000 | 93 | 12.637 | 48.387 | 4.291 | -0.386 | -100.000 | -100.000 | 5 | 51.058 |
| 15:00|both|vixmove_fixed | 3.000 | cash | 1.000 | 93 | 12.637 | 59.140 | 9.344 | 4.784 | -100.000 | -100.000 | 5 | 53.589 |
| 15:00|both|vixmove_fixed | 3.000 | exit | 1.000 | 93 | 12.637 | 46.237 | 2.326 | -2.294 | -100.000 | -100.000 | 5 | 51.558 |
| 13:00|call|gap>0.3% | 1.000 | cash | 1.000 | 468 | 63.593 | 50.641 | 1.226 | 0.392 | -100.000 | -100.000 | 4 | 49.790 |
| 13:00|call|gap>0.3% | 1.000 | cash | 1.300 | 468 | 63.593 | 50.641 | 1.157 | 0.392 | -100.000 | -100.000 | 4 | 49.816 |
| 13:00|call|gap>0.3% | 1.000 | cash | 1.600 | 468 | 63.593 | 50.641 | 1.042 | 0.392 | -100.000 | -100.000 | 4 | 49.864 |
| 13:00|call|gap>0.3% | 1.000 | exit | 1.000 | 468 | 63.593 | 46.154 | 0.145 | -0.625 | -100.000 | -100.000 | 4 | 47.741 |
| 13:00|call|gap>0.3% | 1.000 | exit | 1.300 | 468 | 63.593 | 45.940 | 0.068 | -0.625 | -100.000 | -100.000 | 4 | 47.770 |
| 13:00|call|gap>0.3% | 1.000 | exit | 1.600 | 468 | 63.593 | 45.940 | -0.058 | -0.625 | -100.000 | -100.000 | 4 | 47.823 |
| 13:00|call|gap>0.3% | 2.000 | cash | 1.000 | 468 | 63.593 | 47.863 | 0.179 | -0.589 | -100.000 | -100.000 | 4 | 50.290 |
| 13:00|call|gap>0.3% | 2.000 | cash | 1.300 | 468 | 63.593 | 47.863 | 0.111 | -0.589 | -100.000 | -100.000 | 4 | 50.316 |
| 13:00|call|gap>0.3% | 2.000 | cash | 1.600 | 468 | 63.593 | 47.650 | -0.002 | -0.589 | -100.000 | -100.000 | 4 | 50.364 |
| 13:00|call|gap>0.3% | 2.000 | exit | 1.000 | 468 | 63.593 | 39.530 | -2.008 | -2.993 | -100.000 | -100.000 | 4 | 48.241 |
| 13:00|call|gap>0.3% | 2.000 | exit | 1.300 | 468 | 63.593 | 39.530 | -2.084 | -2.993 | -100.000 | -100.000 | 4 | 48.270 |
| 13:00|call|gap>0.3% | 2.000 | exit | 1.600 | 468 | 63.593 | 39.530 | -2.207 | -2.993 | -100.000 | -100.000 | 4 | 48.323 |
| 13:00|call|gap>0.3% | 3.000 | cash | 1.000 | 468 | 63.593 | 44.658 | -0.846 | -1.590 | -100.000 | -100.000 | 4 | 50.790 |
| 13:00|call|gap>0.3% | 3.000 | cash | 1.300 | 468 | 63.593 | 44.658 | -0.913 | -1.590 | -100.000 | -100.000 | 4 | 50.816 |
| 13:00|call|gap>0.3% | 3.000 | cash | 1.600 | 468 | 63.593 | 44.658 | -1.024 | -1.590 | -100.000 | -100.000 | 4 | 50.864 |
| 13:00|call|gap>0.3% | 3.000 | exit | 1.000 | 468 | 63.593 | 34.829 | -4.114 | -5.184 | -100.000 | -100.000 | 4 | 48.741 |
| 13:00|call|gap>0.3% | 3.000 | exit | 1.300 | 468 | 63.593 | 34.829 | -4.188 | -5.184 | -100.000 | -100.000 | 4 | 48.770 |
| 13:00|call|gap>0.3% | 3.000 | exit | 1.600 | 468 | 63.593 | 34.829 | -4.308 | -5.184 | -100.000 | -100.000 | 4 | 48.823 |

## 4. Sizing — IN-SAMPLE, % of account

Position size = daily limit ÷ worst-trade loss with a 100% floor (a hold-to-close option has no stop). The combined book sizes on the worst day when both signals fire.

| signal | limit | size_pct | worst_trade_loss_pct | exp_annual_pct | worst_year_pct | best_year_pct | days_with_two_positions | worst_day_both_positions_pct |
|---|---|---|---|---|---|---|---|---|
| 15:00|both|vixmove_fixed | 3.000 | 3.000 | 100.000 | 4.352 | -2.776 | 28.828 |  |  |
| 15:00|both|vixmove_fixed | 4.000 | 4.000 | 100.000 | 5.803 | -3.702 | 38.437 |  |  |
| 15:00|both|vixmove_fixed | 5.000 | 5.000 | 100.000 | 7.254 | -4.627 | 48.047 |  |  |
| 13:00|call|gap>0.3% | 3.000 | 3.000 | 100.000 | 2.206 | -6.090 | 10.339 |  |  |
| 13:00|call|gap>0.3% | 4.000 | 4.000 | 100.000 | 2.942 | -8.120 | 13.786 |  |  |
| 13:00|call|gap>0.3% | 5.000 | 5.000 | 100.000 | 3.677 | -10.150 | 17.232 |  |  |
| COMBINED BOOK | 3.000 | 1.500 | 200.000 | 3.279 |  |  | 48.000 | -200.000 |
| COMBINED BOOK | 4.000 | 2.000 | 200.000 | 4.373 |  |  | 48.000 | -200.000 |
| COMBINED BOOK | 5.000 | 2.500 | 200.000 | 5.466 |  |  | 48.000 | -200.000 |

## 5. Execution — IN-SAMPLE (underlying index points per signal; unfilled limits count as zero)

| candidate | entry | fill_rate | n_signals | mean_net_per_signal | mean_net_if_filled | improvement | p_improvement |
|---|---|---|---|---|---|---|---|
| 13:00|call|gap>0.3% | market | 1.000 | 468 | -0.123 | -0.123 | 0.000 |  |
| 13:00|call|gap>0.3% | limit -0.25 ATR | 0.857 | 468 | 0.905 | 1.056 | 1.028 | 0.000 |
| 13:00|call|gap>0.3% | limit -0.50 ATR | 0.744 | 468 | 1.037 | 1.394 | 1.160 | 0.000 |
| 13:00|call|gap>0.3% | limit -1.00 ATR | 0.562 | 468 | 0.537 | 0.955 | 0.660 | 0.123 |
| 15:00|both|vixmove_fixed | market | 1.000 | 93 | 5.103 | 5.103 | 0.000 |  |
| 15:00|both|vixmove_fixed | limit -0.25 ATR | 0.914 | 93 | 5.671 | 6.204 | 0.567 | 0.309 |
| 15:00|both|vixmove_fixed | limit -0.50 ATR | 0.796 | 93 | 5.674 | 7.130 | 0.570 | 0.363 |
| 15:00|both|vixmove_fixed | limit -1.00 ATR | 0.538 | 93 | 5.721 | 10.640 | 0.617 | 0.397 |

## 6. Contract size and minimum account

A 2% ITM SPX option costs ≈ 2% × S × 100 ≈ $13,000 at S = 6,500; XSP is one tenth. At the base size (4% of account per trade) one SPX contract needs ≈ $325k of account, one XSP contract ≈ $32.5k, one SPY contract ≈ $32.5k with the 15:55 exit. Max positions per day: 2 (the two signals can coincide).

## 7. Holdout — what decides whether this is tradeable

PENDING `data/ext/spx_1min_2020-05_2026-09.csv.gz`. When it arrives: `python -m pipeline.insample 2020-06-01 2026-09-11 HOLDOUT out/holdout` and the survival rule in ACCEPTANCE.md decides. If the pre-registered signal fails, that is the result; no re-tuning.

## 8. Before any live capital (both threads' rule)

Measure ten real 2%-ITM 0DTE fills at the mid; above 1.5 index points round-trip nothing here works. Paper-trade ≥ 60 qualifying days. Real 0DTE IV runs above 30-day VIX; the 13:00 leg is the only one where that matters.
