# out/reconcile_decision.md — D1 pre-registration

Selection window 2013-01-01 → 2020-05-13, Oanda SPX500_USD, America/New_York sessions, cost 1.0 pt; calendar-day Sharpe over 1854 NYSE trading days.
vixmove_fixed thresholds (Oanda 2005-2012 upper terciles): 15:00 VIX>22.87 & |move|>0.815%; 15:30 VIX>22.87 & |move|>0.845%.
Sessions with a valid prior-close reference in the window: {'sessions': 1691, 'ref_ok': 1603, 'not_prior_trading_day': 88, 'roll_days': 0, 'ex_dividend_days': 0}.

## Ranking of the 12 rankable configurations (calendar-day Sharpe, net of cost)

               candidate  params   n     win  net_pts  net_pct  sharpe_calday  sharpe_threadB_conv  p_boot_month  p_boot_day fdr_pass_10pct_within16  excess_over_control_pct  frac_seeds_beaten  timing_control_pct  dsr_N12  dsr_N42
15:00|both|vixmove_fixed       2  92 64.1304   5.2717   0.1941         0.5568               2.5167           NaN      0.0630                   False                   0.2062             1.0000              0.4165   0.7980   0.7275
15:30|both|vixmove_fixed       2  92 59.7826   3.8804   0.1488         0.5154               2.3252           NaN      0.0833                   False                   0.1681             1.0000              0.4251   0.7591   0.6839
  15:00|both|vixmove_exp       0 145 62.7586   3.1152   0.1124         0.4887               1.7518        0.1795      0.0953                   False                   0.1237             1.0000              0.3026   0.6794   0.5697
           15:30|put|mag       0 181 57.4586   1.2536   0.0538         0.4701               1.5070        0.0745      0.0953                   False                   0.0941             1.0000              0.2692   0.6038   0.4947
  15:30|both|vixmove_exp       0 146 59.5890   2.3822   0.0911         0.4672               1.6682        0.1153      0.1022                   False                   0.1113             1.0000              0.3024   0.6541   0.5436
          15:30|both|mag       0 368 55.1630   0.5228   0.0207         0.2838               0.6366        0.1575      0.2188                   False                   0.0506             1.0000              0.2324   0.2771   0.1528
          15:00|both|mag       0 368 51.3587   0.4826   0.0217         0.2485               0.5573        0.2018      0.2515                   False                   0.0557             1.0000              0.2087   0.2420   0.1264
           15:00|put|mag       0 188 52.6596   0.6622   0.0318         0.2376               0.7451        0.2225      0.2555                   False                   0.0783             1.0000              0.2441   0.3693   0.2600
   15:30|put|vixmove_exp       0  62 51.6129   1.5419   0.0540         0.1703               0.9258           NaN      0.3142                   False                   0.0861             0.9950              0.2875   0.4571   0.3864
 15:00|put|vixmove_fixed       2  42 54.7619   2.4119   0.0800         0.1595               1.0495           NaN      0.3345                   False                   0.1156             0.9700              0.3419   0.4838   0.4235
   15:00|put|vixmove_exp       0  58 55.1724   1.7397   0.0548         0.1447               0.8122           NaN      0.3510                   False                   0.0846             0.9700              0.2858   0.4359   0.3664
 15:30|put|vixmove_fixed       2  43 51.1628   1.1163   0.0333         0.0791               0.5137           NaN      0.4095                   False                   0.0743             0.9500              0.3121   0.3991   0.3420

p_boot_month is NA when the trades span fewer than 20 calendar months (survival rule 2); p_boot_day is the
one-observation-per-day bootstrap. sharpe_threadB_conv is per-trade Sharpe × √252 (step17_intramom.py:77), which
overstates the annualised figure by √(252 / trades per year); sharpe_calday is the ranking metric. The timing control
enters at a random minute in the two hours before the decision on the same days and so captures the pre-decision
drift as well; it is reported, not a survival test (A16). params counts FITTED numbers only.

## Literal-threshold rows (Thread B's 17.06 / 0.665 — in-sample on 2013-2018; reported, not ranked)

             candidate  params   n     win  net_pts  net_pct  sharpe_calday  sharpe_threadB_conv  p_boot_month  p_boot_day fdr_pass_10pct_within16  excess_over_control_pct  frac_seeds_beaten  timing_control_pct  dsr_N12  dsr_N42
 15:00|put|vixmove_lit       2 101 55.4455   2.1109   0.0796         0.3407               1.4587        0.1415      0.1747                   False                   0.1237             0.9900              0.2630   0.5779   0.4832
15:00|both|vixmove_lit       2 251 58.5657   2.1681   0.0839         0.6027               1.6428        0.1165      0.0465                   False                   0.0983             1.0000              0.2447   0.6932   0.5480
 15:30|put|vixmove_lit       2 104 58.6538   1.7702   0.0714         0.3596               1.5178        0.0585      0.1630                   False                   0.1131             1.0000              0.2731   0.5893   0.4983
15:30|both|vixmove_lit       2 252 59.1270   1.4254   0.0566         0.4843               1.3153        0.1140      0.0882                   False                   0.0784             1.0000              0.2393   0.5666   0.4160

## Thread A's gap-up call (pre-registered by Thread A; dsr_N12 column = PSR at N = 1, dsr_N42 column = DSR at N = 1,099)

          candidate  params   n     win  net_pts  net_pct  sharpe_calday  sharpe_threadB_conv  p_boot_month  p_boot_day fdr_pass_10pct_within16  excess_over_control_pct  frac_seeds_beaten  timing_control_pct  dsr_N12  dsr_N42
13:00|call|gap>0.3%       1 423 52.7187  -0.1378  -0.0042        -0.0469              -0.0981        1.0000      1.0000                     NaN                   0.0185             0.7850              0.0263   0.4497   0.0012

## PRE-REGISTERED holdout test

Tie set within 0.10 Sharpe of the top: 15:00|both|vixmove_fixed (params 2), 15:30|both|vixmove_fixed (params 2), 15:00|both|vixmove_exp (params 0), 15:30|put|mag (params 0), 15:30|both|vixmove_exp (params 0).
Winner: **15:00|both|vixmove_exp** (fewest fitted parameters among the tied, then highest Sharpe).
This ONE configuration is tested on the 2020-06-01 → 2026-09-11 holdout when data/ext arrives. Thread A's gap-up call (13:00, gap > 0.3%) is the second pre-registered holdout signal. The other 15 holdout rows are published in `out/reconcile_candidates.csv` (`label` column: POST-SELECTION, `window` column: 2020-06-01..2026-09-11) by `python -m pipeline.reconcile holdout` when data/ext arrives, and never promoted.

Written before any holdout data was read. Momentum trials this run: 16; historical N for DSR: 42 (gap-up: 1099).
