# TRACK_B.md — technical swing-start detector on range bars (Amendment A40)

Track B asks whether a stop-hunting sweep of a prior swing extreme on a range-bar chart marks the START of a swing, either by REVERSAL (price rejects back inside the level) or by CONTINUATION (price closes through it) -- a pure technical-analysis question, independent of the 0DTE prop-account constraint governing every other deliverable in this repository, but bound to the same statistical guards (block bootstrap, its own family-wide BH-FDR, a random-entry control, a deflated Sharpe). The TRAIN/TEST lock is fixed and never re-opened: SPY and XAUUSD winners are each chosen SEPARATELY, on their own TRAIN window, by the highest calendar-day Sharpe among trials with at least 100 trades (A40b), then each checked EXACTLY ONCE on their own TEST window; no parameter may be re-tuned after seeing a TEST number. Gold's windows were re-registered twice before any gold result existed: A40b found a 2006-2020 Oanda XAU_USD minute source; A40c then replaced A40b's planned TEST window (the owner's untouched 5000R export) with a second rebuild from that same minute source, since no independent minute source exists to gate the owner's file against -- the owner's 5000R export is CONTEXT ONLY throughout this report. Whatever the verdict, the pattern table at the end stands as the finding (A40's own instruction).

## Gate B-a (range-bar rebuild, SPY and gold)

Gate B-a (`pipeline.units.rangebars`, redefined as Amendment A40c mid-run) checks the SPY and XAUUSD rebuilds' OWN internal consistency (every completed bar's high-low equals its own range to the cent and threads with no gap within a session -- the NYSE trading day for SPY, the trading WEEK for gold -- and every session/week has at least as many bars as its own high-low span requires) plus determinism for both series (rebuilding twice yields byte-identical parquet) -- NOT a byte match against either owner TradingView export: A40c's own diagnostic found the SPY 34R export is not a faithful range-bar series in its own right, and no minute source exists to gate the gold 5000R export against at all (A40b). 9 of 9 checks pass, so `GATE (B-a): PASS`. The remaining rows are CONTEXT ONLY (never gating): the SPY rebuild's own and the owner 34R file's own bars-per-session and the correlation between their 5-minute-resampled close series on their overlap; and, for gold, the rebuild's own and the owner 5000R file's own bars-per-week, packed into a single row per the task brief.

| check | value | threshold | ok | counts_toward_gate | note |
|---|---|---|---|---|---|
| self_consistency_r0.34 | 0.000000 | 0.000000 | True | True | hl_bad=0/236300 completed bars, open_close_bad=0/236300 consecutive pairs |
| min_bar_count_r0.34 | 0.000000 | 0.000000 | True | True | sessions violating n_bars>=(H-L)/range: 0/1526 |
| determinism_r0.34 | 1.000000 | 1.000000 | True | True | rebuild twice, byte-identical parquet |
| self_consistency_r1.00 | 0.000000 | 0.000000 | True | True | hl_bad=0/37493 completed bars, open_close_bad=0/37493 consecutive pairs |
| min_bar_count_r1.00 | 0.000000 | 0.000000 | True | True | sessions violating n_bars>=(H-L)/range: 0/1526 |
| determinism_r1.00 | 1.000000 | 1.000000 | True | True | rebuild twice, byte-identical parquet |
| context_bars_per_session_median_rebuild_r034 | 144.000000 |  |  | False | 191 sessions in overlap |
| context_bars_per_session_median_owner_34R | 16.000000 |  |  | False | 194 sessions in overlap, 191 common with rebuild |
| context_resampled_5min_close_corr_r034_vs_owner | 0.998979 |  |  | False | 2826 common 5-min buckets in overlap |
| self_consistency_xau_r5 | 0.000000 | 0.000000 | True | True | hl_bad=0/48077 completed bars, open_close_bad=0/48077 consecutive pairs (per trading week) |
| min_bar_count_xau_r5 | 0.000000 | 0.000000 | True | True | weeks violating n_bars>=(H-L)/range: 0/741 |
| determinism_xau_r5 | 1.000000 | 1.000000 | True | True | rebuild twice, byte-identical parquet |
| context_bars_per_week_rebuild_test_vs_owner_5000R | 25.500000 |  |  | False | rebuild TEST (2017-2020, xau_r5) median bars/week=25.5 over 180 weeks; owner 5000R (2025-06..2026-03) median bars/week=175.0 over 43 weeks |

## Sweep family — TRAIN (SPY + XAU, `out/trackB_sweep_candidates.csv`)

| series | trial | n | win | net_pct_cost1 | net_pct_cost2 | mean_bars_held | sharpe_calday | p_boot_day | p_boot_month | control_win | control_net_pct | frac_seeds_beaten | expected_rw_win | dsr_N24 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| spy034 | reversal\|L10\|R1 | 14919 | 56.0091 | -0.0284 | -0.0684 | 2.3285 | -16.2046 | 1.0000 | 1.0000 | 49.7712 | -0.0400 | 1.0000 | 50.0000 | 0.0000 |
| spy034 | reversal\|L10\|R2 | 14189 | 38.4946 | -0.0262 | -0.0662 | 4.0906 | -12.5264 | 1.0000 | 1.0000 | 34.0087 | -0.0382 | 1.0000 | 33.3333 | 0.0000 |
| spy034 | reversal\|L20\|R1 | 10659 | 55.5305 | -0.0289 | -0.0689 | 2.3572 | -14.1147 | 1.0000 | 1.0000 | 49.7643 | -0.0400 | 1.0000 | 50.0000 | 0.0000 |
| spy034 | reversal\|L20\|R2 | 10195 | 38.2246 | -0.0264 | -0.0664 | 4.1120 | -10.2744 | 1.0000 | 1.0000 | 34.0718 | -0.0380 | 1.0000 | 33.3333 | 0.0000 |
| spy034 | continuation\|L10\|R1 | 14547 | 52.6225 | -0.0294 | -0.0694 | 2.1605 | -14.4937 | 1.0000 | 1.0000 | 42.5843 | -0.0421 | 1.0000 | 50.0000 | 0.0000 |
| spy034 | continuation\|L10\|R2 | 12946 | 42.6387 | -0.0243 | -0.0643 | 3.0103 | -10.8943 | 1.0000 | 1.0000 | 32.5931 | -0.0384 | 1.0000 | 33.3333 | 0.0000 |
| spy034 | continuation\|L20\|R1 | 10578 | 53.1102 | -0.0288 | -0.0688 | 2.3054 | -12.4639 | 1.0000 | 1.0000 | 42.2717 | -0.0422 | 1.0000 | 50.0000 | 0.0000 |
| spy034 | continuation\|L20\|R2 | 9404 | 43.2582 | -0.0227 | -0.0627 | 3.2332 | -8.5845 | 1.0000 | 1.0000 | 32.5963 | -0.0383 | 1.0000 | 33.3333 | 0.0000 |
| spy100 | reversal\|L10\|R1 | 2293 | 51.7226 | -0.0275 | -0.0675 | 2.7165 | -2.8880 | 1.0000 | 1.0000 | 49.7215 | -0.0403 | 0.9800 | 50.0000 | 0.0000 |
| spy100 | reversal\|L10\|R2 | 2207 | 36.4749 | -0.0164 | -0.0564 | 4.3584 | -1.2619 | 1.0000 | 1.0000 | 34.3575 | -0.0320 | 0.9600 | 33.3333 | 0.0000 |
| spy100 | reversal\|L20\|R1 | 1632 | 51.2255 | -0.0299 | -0.0699 | 2.8419 | -2.5048 | 1.0000 | 1.0000 | 49.5787 | -0.0409 | 0.9500 | 50.0000 | 0.0000 |
| spy100 | reversal\|L20\|R2 | 1576 | 35.9137 | -0.0197 | -0.0597 | 4.4055 | -1.1778 | 1.0000 | 1.0000 | 34.1586 | -0.0332 | 0.9500 | 33.3333 | 0.0000 |
| spy100 | continuation\|L10\|R1 | 2278 | 46.0053 | -0.0195 | -0.0595 | 2.3218 | -1.9820 | 1.0000 | 1.0000 | 40.5090 | -0.0481 | 1.0000 | 50.0000 | 0.0000 |
| spy100 | continuation\|L10\|R2 | 1992 | 36.6466 | -0.0081 | -0.0481 | 3.5708 | -0.5750 | 1.0000 | 1.0000 | 30.5889 | -0.0375 | 1.0000 | 33.3333 | 0.0000 |
| spy100 | continuation\|L20\|R1 | 1653 | 46.8240 | -0.0198 | -0.0598 | 2.5094 | -1.6825 | 1.0000 | 1.0000 | 40.4065 | -0.0482 | 1.0000 | 50.0000 | 0.0000 |
| spy100 | continuation\|L20\|R2 | 1429 | 37.6487 | 0.0045 | -0.0355 | 3.8397 | 0.2586 | 0.3387 | 0.3222 | 30.3975 | -0.0374 | 1.0000 | 33.3333 | 0.0000 |
| xau5 | reversal\|L10\|R1 | 5684 | 51.4954 | -0.0091 | -0.0291 | 2.6986 | -0.4444 | 1.0000 | 1.0000 | 49.8249 | -0.0204 | 0.9800 | 50.0000 | 0.0000 |
| xau5 | reversal\|L10\|R2 | 5419 | 34.8773 | -0.0048 | -0.0248 | 4.7474 | -0.1686 | 1.0000 | 1.0000 | 33.6058 | -0.0163 | 0.8950 | 33.3333 | 0.0000 |
| xau5 | reversal\|L20\|R1 | 4021 | 51.8279 | -0.0056 | -0.0256 | 2.7177 | -0.2332 | 1.0000 | 1.0000 | 49.9459 | -0.0196 | 0.9800 | 50.0000 | 0.0000 |
| xau5 | reversal\|L20\|R2 | 3859 | 34.9313 | -0.0049 | -0.0249 | 4.7966 | -0.1383 | 1.0000 | 1.0000 | 33.6262 | -0.0161 | 0.8750 | 33.3333 | 0.0000 |
| xau5 | continuation\|L10\|R1 | 5553 | 42.6976 | -0.0254 | -0.0454 | 1.3485 | -2.1304 | 1.0000 | 1.0000 | 37.7938 | -0.0376 | 0.9950 | 50.0000 | 0.0000 |
| xau5 | continuation\|L10\|R2 | 5071 | 33.3859 | -0.0077 | -0.0277 | 1.9387 | -0.4591 | 1.0000 | 1.0000 | 28.2908 | -0.0257 | 1.0000 | 33.3333 | 0.0000 |
| xau5 | continuation\|L20\|R1 | 4071 | 43.0607 | -0.0236 | -0.0436 | 1.3402 | -1.7526 | 1.0000 | 1.0000 | 37.3315 | -0.0376 | 1.0000 | 50.0000 | 0.0000 |
| xau5 | continuation\|L20\|R2 | 3709 | 34.1602 | -0.0014 | -0.0214 | 1.9472 | -0.0716 | 1.0000 | 1.0000 | 27.9492 | -0.0265 | 1.0000 | 33.3333 | 0.0000 |

## Sweep family — TEST (SPY + XAU, `out/trackB_trials.csv`, this run's own 24-row BH-FDR family)

| series | trial | n | win | net_pct_cost1 | net_pct_cost2 | mean_bars_held | sharpe_calday | p_boot_day | p_boot_month | control_win | control_net_pct | frac_seeds_beaten | expected_rw_win | dsr_N24 | fdr_pass_10pct |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| spy034 | reversal\|L10\|R1 | 18824 | 55.9339 | -0.0322 | -0.0722 | 2.4245 | -18.5080 | 1.0000 | 1.0000 | 49.7010 | -0.0401 | 1.0000 | 50.0000 | 0.0000 | False |
| spy034 | reversal\|L10\|R2 | 17895 | 38.9383 | -0.0302 | -0.0702 | 4.1967 | -16.0415 | 1.0000 | 1.0000 | 34.0007 | -0.0387 | 1.0000 | 33.3333 | 0.0000 | False |
| spy034 | reversal\|L20\|R1 | 13538 | 56.1974 | -0.0321 | -0.0721 | 2.4334 | -17.4298 | 1.0000 | 1.0000 | 49.7966 | -0.0400 | 1.0000 | 50.0000 | 0.0000 | False |
| spy034 | reversal\|L20\|R2 | 12970 | 38.8512 | -0.0307 | -0.0707 | 4.1985 | -14.6145 | 1.0000 | 1.0000 | 33.9789 | -0.0388 | 1.0000 | 33.3333 | 0.0000 | False |
| spy034 | continuation\|L10\|R1 | 18560 | 52.5431 | -0.0346 | -0.0746 | 2.2348 | -15.4083 | 1.0000 | 1.0000 | 43.0089 | -0.0413 | 1.0000 | 50.0000 | 0.0000 | False |
| spy034 | continuation\|L10\|R2 | 16616 | 42.0920 | -0.0328 | -0.0728 | 3.0520 | -13.7061 | 1.0000 | 1.0000 | 32.8687 | -0.0390 | 1.0000 | 33.3333 | 0.0000 | False |
| spy034 | continuation\|L20\|R1 | 13493 | 51.2192 | -0.0362 | -0.0762 | 2.3702 | -12.7647 | 1.0000 | 1.0000 | 42.7041 | -0.0413 | 1.0000 | 50.0000 | 0.0000 | False |
| spy034 | continuation\|L20\|R2 | 12103 | 41.2047 | -0.0343 | -0.0743 | 3.1914 | -11.0204 | 1.0000 | 1.0000 | 32.8660 | -0.0389 | 1.0000 | 33.3333 | 0.0000 | False |
| spy100 | reversal\|L10\|R1 | 3134 | 53.1270 | -0.0228 | -0.0628 | 2.6391 | -3.8331 | 1.0000 | 1.0000 | 49.7077 | -0.0406 | 1.0000 | 50.0000 | 0.0000 | False |
| spy100 | reversal\|L10\|R2 | 2989 | 36.7681 | -0.0185 | -0.0585 | 4.4871 | -2.3210 | 1.0000 | 1.0000 | 34.0656 | -0.0363 | 1.0000 | 33.3333 | 0.0000 | False |
| spy100 | reversal\|L20\|R1 | 2233 | 53.3363 | -0.0201 | -0.0601 | 2.5755 | -2.7508 | 1.0000 | 1.0000 | 49.6858 | -0.0402 | 1.0000 | 50.0000 | 0.0000 | False |
| spy100 | reversal\|L20\|R2 | 2154 | 37.4652 | -0.0133 | -0.0533 | 4.4294 | -1.2978 | 1.0000 | 1.0000 | 33.8417 | -0.0374 | 1.0000 | 33.3333 | 0.0000 | False |
| spy100 | continuation\|L10\|R1 | 2999 | 44.7482 | -0.0367 | -0.0767 | 2.6372 | -5.1515 | 1.0000 | 1.0000 | 40.9675 | -0.0452 | 0.9950 | 50.0000 | 0.0000 | False |
| spy100 | continuation\|L10\|R2 | 2651 | 35.0057 | -0.0257 | -0.0657 | 3.7808 | -2.8216 | 1.0000 | 1.0000 | 31.1692 | -0.0375 | 0.9750 | 33.3333 | 0.0000 | False |
| spy100 | continuation\|L20\|R1 | 2178 | 46.0055 | -0.0355 | -0.0755 | 2.7002 | -4.0635 | 1.0000 | 1.0000 | 40.9800 | -0.0451 | 1.0000 | 50.0000 | 0.0000 | False |
| spy100 | continuation\|L20\|R2 | 1933 | 37.0409 | -0.0238 | -0.0638 | 3.9384 | -2.0969 | 1.0000 | 1.0000 | 31.1035 | -0.0382 | 0.9900 | 33.3333 | 0.0000 | False |
| xau5 | reversal\|L10\|R1 | 1389 | 50.3960 | -0.0170 | -0.0370 | 2.8164 | -1.0211 | 1.0000 | 1.0000 | 49.4503 | -0.0214 | 0.6800 | 50.0000 | 0.0000 | False |
| xau5 | reversal\|L10\|R2 | 1301 | 33.4358 | -0.0192 | -0.0392 | 5.0407 | -0.8084 | 1.0000 | 1.0000 | 32.5749 | -0.0254 | 0.6850 | 33.3333 | 0.0000 | False |
| xau5 | reversal\|L20\|R1 | 971 | 50.1545 | -0.0198 | -0.0398 | 2.8661 | -0.9342 | 1.0000 | 1.0000 | 49.5139 | -0.0207 | 0.5050 | 50.0000 | 0.0000 | False |
| xau5 | reversal\|L20\|R2 | 924 | 34.1991 | -0.0147 | -0.0347 | 5.0812 | -0.4999 | 1.0000 | 1.0000 | 32.5720 | -0.0253 | 0.7650 | 33.3333 | 0.0000 | False |
| xau5 | continuation\|L10\|R1 | 1289 | 37.2382 | -0.0331 | -0.0531 | 1.3584 | -2.8404 | 1.0000 | 1.0000 | 36.3220 | -0.0342 | 0.5800 | 50.0000 | 0.0000 | False |
| xau5 | continuation\|L10\|R2 | 1201 | 27.5604 | -0.0343 | -0.0543 | 1.9509 | -2.0991 | 1.0000 | 1.0000 | 27.0803 | -0.0274 | 0.2000 | 33.3333 | 0.0000 | False |
| xau5 | continuation\|L20\|R1 | 925 | 37.6216 | -0.0285 | -0.0485 | 1.3005 | -2.1807 | 1.0000 | 1.0000 | 35.9286 | -0.0349 | 0.8500 | 50.0000 | 0.0000 | False |
| xau5 | continuation\|L20\|R2 | 864 | 28.0093 | -0.0275 | -0.0475 | 1.9062 | -1.5329 | 1.0000 | 1.0000 | 27.0365 | -0.0269 | 0.4700 | 33.3333 | 0.0000 | False |

## Decision (`out/trackB_decision.csv`)

| instrument | winner_series | winner_trial | train_n | train_sharpe_calday | test_n | test_net_pct_cost1 | test_p_boot_day | test_control_net_pct | test_dsr_N24 | cond_net_pos | cond_p_boot_day | cond_fdr_pass_10pct | cond_beats_control | cond_dsr_gt_095 | cond_n_ge_200 | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SPY | spy100 | continuation\|L20\|R2 | 1429 | 0.2586 | 1933 | -0.0238 | 1.0000 | -0.0382 | 0.0000 | False | False | False | True | False | True | FAILED |
| XAU | xau5 | continuation\|L20\|R2 | 3709 | -0.0716 | 864 | -0.0275 | 1.0000 | -0.0269 | 0.0000 | False | False | False | False | False | True | FAILED |

**SPY**: the pre-registered TRAIN winner (highest calendar-day Sharpe among that instrument's own TRAIN trials with at least 100 trades) is `spy100 continuation|L20|R2`, checked exactly once on TEST: **verdict FAILED**. Conditions met: beats the random-entry control; at least 200 TEST trades. Conditions not met: net_pct_cost1 > 0 at 1x cost; day-block bootstrap p < 0.05; passes BH-FDR at 10% within the 24-trial TEST family; deflated Sharpe (N=24) > 0.95.

**XAU**: the pre-registered TRAIN winner (highest calendar-day Sharpe among that instrument's own TRAIN trials with at least 100 trades) is `xau5 continuation|L20|R2`, checked exactly once on TEST: **verdict FAILED**. Conditions met: at least 200 TEST trades. Conditions not met: net_pct_cost1 > 0 at 1x cost; day-block bootstrap p < 0.05; passes BH-FDR at 10% within the 24-trial TEST family; beats the random-entry control; deflated Sharpe (N=24) > 0.95.

## Pattern table (`out/trackB_pattern_table.csv`) — sweeps vs the unconditional baseline

mean/median_range are in bar-range units (the series' own fixed $ range); mean/median_pct are in %; both are HYPOTHESIS-DIRECTION-signed for the reversal/continuation rows (short instances flipped so they combine with long instances instead of cancelling) and UN-signed for the unconditional row (the series' own raw per-bar drift); p_vs_unconditional is a day-block bootstrap p for the gap against that same row's unconditional baseline (blank for the unconditional rows themselves).

| series | L | horizon | pattern | n | mean_range | median_range | mean_pct | median_pct | p_vs_unconditional |
|---|---|---|---|---|---|---|---|---|---|
| spy034 | 10 | 1 | reversal | 38684 | 0.161931 | 0.235294 | 0.011123 | 0.015712 | 0.000000 |
| spy034 | 10 | 1 | continuation | 54964 | 0.052744 | -0.058824 | 0.003826 | -0.003705 | 0.000000 |
| spy034 | 10 | 1 | unconditional | 237825 | 0.005477 | 0.014706 | 0.000400 | 0.000973 |  |
| spy034 | 10 | 5 | reversal | 38683 | 0.191590 | 0.147059 | 0.013229 | 0.009752 | 0.000000 |
| spy034 | 10 | 5 | continuation | 54963 | 0.053868 | 0.073529 | 0.004168 | 0.005036 | 0.069750 |
| spy034 | 10 | 5 | unconditional | 237821 | 0.027404 | 0.029412 | 0.002000 | 0.001664 |  |
| spy034 | 10 | 20 | reversal | 38681 | 0.201941 | 0.132353 | 0.014237 | 0.008801 | 0.067500 |
| spy034 | 10 | 20 | continuation | 54959 | 0.092934 | 0.147059 | 0.007470 | 0.010181 | 1.000000 |
| spy034 | 10 | 20 | unconditional | 237806 | 0.109605 | 0.102941 | 0.007980 | 0.006632 |  |
| spy034 | 20 | 1 | reversal | 27627 | 0.154732 | 0.235294 | 0.010540 | 0.014274 | 0.000000 |
| spy034 | 20 | 1 | continuation | 39784 | 0.048947 | -0.058824 | 0.003617 | -0.004387 | 0.000000 |
| spy034 | 20 | 1 | unconditional | 237825 | 0.005477 | 0.014706 | 0.000400 | 0.000973 |  |
| spy034 | 20 | 5 | reversal | 27626 | 0.174321 | 0.117647 | 0.011831 | 0.008350 | 0.000000 |
| spy034 | 20 | 5 | continuation | 39783 | 0.046617 | 0.088235 | 0.003761 | 0.005532 | 0.143250 |
| spy034 | 20 | 5 | unconditional | 237821 | 0.027404 | 0.029412 | 0.002000 | 0.001664 |  |
| spy034 | 20 | 20 | reversal | 27624 | 0.184642 | 0.088235 | 0.012633 | 0.006774 | 0.165000 |
| spy034 | 20 | 20 | continuation | 39782 | 0.098086 | 0.147059 | 0.008145 | 0.010702 | 0.487250 |
| spy034 | 20 | 20 | unconditional | 237806 | 0.109605 | 0.102941 | 0.007980 | 0.006632 |  |
| spy100 | 10 | 1 | reversal | 6357 | 0.057798 | -0.010000 | 0.011667 | -0.001340 | 0.001000 |
| spy100 | 10 | 1 | continuation | 9244 | 0.034727 | 0.077500 | 0.008185 | 0.014123 | 0.005750 |
| spy100 | 10 | 1 | unconditional | 39018 | 0.011336 | 0.030000 | 0.002424 | 0.005430 |  |
| spy100 | 10 | 5 | reversal | 6356 | 0.056366 | 0.090000 | 0.011029 | 0.016748 | 1.000000 |
| spy100 | 10 | 5 | continuation | 9244 | 0.066562 | 0.130000 | 0.014971 | 0.023736 | 0.374750 |
| spy100 | 10 | 5 | unconditional | 39014 | 0.056701 | 0.055000 | 0.012152 | 0.010635 |  |
| spy100 | 10 | 20 | reversal | 6353 | 0.107147 | 0.070000 | 0.022067 | 0.011603 | 1.000000 |
| spy100 | 10 | 20 | continuation | 9242 | 0.166829 | 0.230000 | 0.031492 | 0.041918 | 1.000000 |
| spy100 | 10 | 20 | unconditional | 38999 | 0.226619 | 0.170000 | 0.048676 | 0.032838 |  |
| spy100 | 20 | 1 | reversal | 4522 | 0.046199 | -0.030000 | 0.009325 | -0.006610 | 0.018000 |
| spy100 | 20 | 1 | continuation | 6684 | 0.043025 | 0.085000 | 0.010276 | 0.015935 | 0.002000 |
| spy100 | 20 | 1 | unconditional | 39018 | 0.011336 | 0.030000 | 0.002424 | 0.005430 |  |
| spy100 | 20 | 5 | reversal | 4522 | 0.037134 | 0.040000 | 0.007485 | 0.007667 | 1.000000 |
| spy100 | 20 | 5 | continuation | 6684 | 0.083761 | 0.140000 | 0.019528 | 0.025727 | 0.219750 |
| spy100 | 20 | 5 | unconditional | 39014 | 0.056701 | 0.055000 | 0.012152 | 0.010635 |  |
| spy100 | 20 | 20 | reversal | 4521 | 0.156016 | 0.160000 | 0.031794 | 0.029872 | 1.000000 |
| spy100 | 20 | 20 | continuation | 6684 | 0.155149 | 0.210000 | 0.030196 | 0.039746 | 1.000000 |
| spy100 | 20 | 20 | unconditional | 38999 | 0.226619 | 0.170000 | 0.048676 | 0.032838 |  |
| xau5 | 10 | 1 | reversal | 8211 | 0.007557 | -0.017200 | 0.001637 | -0.005171 | 1.000000 |
| xau5 | 10 | 1 | continuation | 10711 | 0.022495 | -0.092000 | 0.009160 | -0.032681 | 0.031500 |
| xau5 | 10 | 1 | unconditional | 48817 | 0.004769 | 0.057400 | 0.002806 | 0.021152 |  |
| xau5 | 10 | 5 | reversal | 8210 | -0.021444 | 0.037500 | -0.009979 | 0.014512 | 1.000000 |
| xau5 | 10 | 5 | continuation | 10710 | 0.068153 | 0.028600 | 0.027951 | 0.010553 | 0.115500 |
| xau5 | 10 | 5 | unconditional | 48813 | 0.023848 | 0.026000 | 0.014027 | 0.009564 |  |
| xau5 | 10 | 20 | reversal | 8209 | -0.029120 | -0.026200 | -0.016904 | -0.011085 | 1.000000 |
| xau5 | 10 | 20 | continuation | 10708 | 0.111643 | 0.109800 | 0.045814 | 0.039998 | 1.000000 |
| xau5 | 10 | 20 | unconditional | 48798 | 0.094675 | 0.096100 | 0.056022 | 0.036077 |  |
| xau5 | 20 | 1 | reversal | 5774 | 0.013122 | 0.032900 | 0.003564 | 0.011940 | 0.432500 |
| xau5 | 20 | 1 | continuation | 7853 | 0.026646 | -0.070000 | 0.009694 | -0.025720 | 0.041250 |
| xau5 | 20 | 1 | unconditional | 48817 | 0.004769 | 0.057400 | 0.002806 | 0.021152 |  |
| xau5 | 20 | 5 | reversal | 5773 | -0.016064 | 0.055400 | -0.007889 | 0.021439 | 1.000000 |
| xau5 | 20 | 5 | continuation | 7852 | 0.074127 | 0.027500 | 0.030369 | 0.009905 | 0.104500 |
| xau5 | 20 | 5 | unconditional | 48813 | 0.023848 | 0.026000 | 0.014027 | 0.009564 |  |
| xau5 | 20 | 20 | reversal | 5772 | -0.050517 | -0.060400 | -0.027015 | -0.023748 | 1.000000 |
| xau5 | 20 | 20 | continuation | 7850 | 0.118734 | 0.119100 | 0.046755 | 0.044759 | 1.000000 |
| xau5 | 20 | 20 | unconditional | 48798 | 0.094675 | 0.096100 | 0.056022 | 0.036077 |  |

**spy034**: a reversal-shaped sweep carries directional content beyond the unconditional baseline at 4 of 6 (L x horizon) combinations tested (day-block bootstrap p<0.05); a continuation-shaped close-through carries directional content beyond the unconditional baseline at 2 of 6 (L x horizon) combinations tested (day-block bootstrap p<0.05).

**spy100**: a reversal-shaped sweep carries directional content beyond the unconditional baseline at 2 of 6 (L x horizon) combinations tested (day-block bootstrap p<0.05); a continuation-shaped close-through carries directional content beyond the unconditional baseline at 2 of 6 (L x horizon) combinations tested (day-block bootstrap p<0.05).

**xau5**: a reversal-shaped sweep does not carry directional content beyond the unconditional baseline at any of the 6 (L x horizon) combinations tested; a continuation-shaped close-through carries directional content beyond the unconditional baseline at 2 of 6 (L x horizon) combinations tested (day-block bootstrap p<0.05).

## FIXED parameters (pre-registration, never re-tuned on any window)

FIXED (pre-registration, A40; gold ENABLED per A40c re-registration 2026-09-13, before any gold row existed -- all 24 trials run: 16 SPY + 8 XAU). Causal swing: prior swing high/low = rolling max/min of the L bars strictly before bar t (shift(1) then rolling(L)), computed continuously across the whole series (no session reset -- range bars are event-driven; only the BUILD resets at sessions). REVERSAL: high>prior_high & close<prior_high -> short (stop=high[t]); low<prior_low & close>prior_low -> long (stop=low[t]). CONTINUATION: close>prior_high -> long (stop=prior_high[t]); close<prior_low -> short (stop=prior_low[t]). Side is not a family dimension; one busy-until tracker per direction, continuous across the whole series (trades are simulated once, then split TRAIN/TEST by the SIGNAL bar's ts_close). Entry = next bar's open (always filled); target = entry +/- R*|entry-stop|; time stop 50 bars counting the entry bar as bar 1; a same-bar stop/target tie goes to the stop; P&L/calendar attribution uses the ENTRY bar's date (always inside the trade's own window; a multi-day hold's exit date routinely is not). Costs: SPY 2bp/side, XAU 1bp/side, round trip = 2 sides; cost2 = 2x cost1. Random-entry control: 200 draws from one generator seeded 11, without replacement, from the SAME window's bars, same direction/stop-distance/R as the matched real trade, net of cost1 only. DSR at N=24 uses the per-trade-Sharpe dispersion of ALL 24 TRIALS (16 SPY + 8 gold) in the same window as SR0's pool -- N=24 is both the pre-registered family size and, now that gold is enabled, the exact size of the pool. Windows: SPY TRAIN 2020-07-27..2023-06-30, TEST 2023-07-01..2026-09-11; XAU TRAIN 2006-03-19..2016-12-31, TEST 2017-01-01..2020-05-14 (A40c, both rebuilt from minute data, same rule as SPY). Decision: SPY and gold decided SEPARATELY (A40b) -- on each instrument's own TRAIN, winner = highest sharpe_calday among n>=100 trials; TEST verdict = SURVIVES iff net_pct_cost1>0 & p_boot_day<0.05 & BH-FDR pass @10% (the full 24-row TEST family, both instruments) & net_pct_cost1>control_net_pct & dsr_N24>0.95 & n>=200; n<200 forces UNDERPOWERED regardless of the other five. Exception handling for this unit only: header-only outputs, exit 0 (not _gh.run's usual empty-file/exit 2 -- see module docstring).
