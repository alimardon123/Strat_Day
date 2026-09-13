# out/reconcile_decision.md — D1 pre-registration

Selection window 2013-01-01 → 2020-05-13, Oanda SPX500_USD, America/New_York sessions, cost 1.0 pt; calendar-day Sharpe over 1854 NYSE trading days.
vixmove_fixed thresholds (Oanda 2005-2012 upper terciles): 15:00 VIX>22.87 & |move|>0.815%; 15:30 VIX>22.87 & |move|>0.845%.
Sessions with a valid prior-close reference in the window: {'sessions': 1691, 'ref_ok': 1603, 'not_prior_trading_day': 88, 'roll_days': 0, 'ex_dividend_days': 0}.

## Ranking of the 12 rankable configurations (calendar-day Sharpe, net of cost)

               candidate  params   n     win  net_pts  net_pct  sharpe_calday  sharpe_threadB_conv  p_boot_month  p_boot_day fdr_pass_10pct_within16  excess_over_control_pct  frac_seeds_beaten  timing_control_pct  dsr_N12  dsr_N42
15:00|both|vixmove_fixed       2  92 64.1304   5.2717   0.1941         0.5568               2.5167           NaN      0.0630                   False                   0.2062             1.0000              0.4165   0.7562   0.6625
15:30|both|vixmove_fixed       2  92 59.7826   3.8804   0.1488         0.5154               2.3252           NaN      0.0833                   False                   0.1681             1.0000              0.4251   0.7143   0.6165
  15:00|both|vixmove_exp       0 145 62.7586   3.1152   0.1124         0.4887               1.7518        0.1795      0.0953                   False                   0.1237             1.0000              0.3026   0.6134   0.4759
  15:30|both|vixmove_exp       0 146 59.5890   2.3822   0.0911         0.4672               1.6682        0.1153      0.1022                   False                   0.1113             1.0000              0.3024   0.5874   0.4509
           15:30|put|mag       0 182 57.1429   0.7709   0.0330         0.2603               0.8297        0.2545      0.2382                   False                   0.0724             1.0000              0.2412   0.3337   0.2170
   15:30|put|vixmove_exp       0  62 51.6129   1.5419   0.0540         0.1703               0.9258           NaN      0.3142                   False                   0.0861             0.9950              0.2875   0.4135   0.3315
 15:00|put|vixmove_fixed       2  42 54.7619   2.4119   0.0800         0.1595               1.0495           NaN      0.3345                   False                   0.1156             0.9700              0.3419   0.4467   0.3757
   15:00|put|vixmove_exp       0  58 55.1724   1.7397   0.0548         0.1447               0.8122           NaN      0.3510                   False                   0.0846             0.9700              0.2858   0.3930   0.3130
           15:00|put|mag       0 189 52.3810   0.3238   0.0173         0.1250               0.3905        0.3623      0.3745                   False                   0.0622             0.9950              0.2262   0.2018   0.1120
 15:30|put|vixmove_fixed       2  43 51.1628   1.1163   0.0333         0.0791               0.5137           NaN      0.4095                   False                   0.0743             0.9500              0.3121   0.3638   0.2982
          15:30|both|mag       0 371 54.7170   0.0668   0.0019         0.0234               0.0522        0.4785      0.4700                   False                   0.0356             1.0000              0.2108   0.0546   0.0160
          15:00|both|mag       0 371 50.9434  -0.0332   0.0008         0.0082               0.0184        0.4928      0.4918                   False                   0.0391             0.9900              0.1884   0.0497   0.0142

p_boot_month is NA when the trades span fewer than 20 calendar months (survival rule 2); p_boot_day is the
one-observation-per-day bootstrap. sharpe_threadB_conv is per-trade Sharpe × √252 (step17_intramom.py:77), which
overstates the annualised figure by √(252 / trades per year); sharpe_calday is the ranking metric. The timing control
enters at a random minute in the two hours before the decision on the same days and so captures the pre-decision
drift as well; it is reported, not a survival test (A16). params counts FITTED numbers only.

## Literal-threshold rows (Thread B's 17.06 / 0.665 — in-sample on 2013-2018; reported, not ranked)

             candidate  params   n     win  net_pts  net_pct  sharpe_calday  sharpe_threadB_conv  p_boot_month  p_boot_day fdr_pass_10pct_within16  excess_over_control_pct  frac_seeds_beaten  timing_control_pct  dsr_N12  dsr_N42
 15:00|put|vixmove_lit       2 101 55.4455   2.1109   0.0796         0.3407               1.4587        0.1415      0.1747                   False                   0.1237             0.9900              0.2630   0.5201   0.4069
15:00|both|vixmove_lit       2 251 58.5657   2.1681   0.0839         0.6027               1.6428        0.1165      0.0465                   False                   0.0983             1.0000              0.2447   0.6063   0.4241
 15:30|put|vixmove_lit       2 104 58.6538   1.7702   0.0714         0.3596               1.5178        0.0585      0.1630                   False                   0.1131             1.0000              0.2731   0.5338   0.4242
15:30|both|vixmove_lit       2 252 59.1270   1.4254   0.0566         0.4843               1.3153        0.1140      0.0882                   False                   0.0784             1.0000              0.2393   0.4742   0.3014

## Thread A's gap-up call (pre-registered by Thread A; dsr_N12 column = PSR at N = 1, dsr_N42 column = DSR at N = 1,099)

          candidate  params   n     win  net_pts  net_pct  sharpe_calday  sharpe_threadB_conv  p_boot_month  p_boot_day fdr_pass_10pct_within16  excess_over_control_pct  frac_seeds_beaten  timing_control_pct  dsr_N12  dsr_N42
13:00|call|gap>0.3%       1 423 52.7187  -0.1378  -0.0042        -0.0469              -0.0981        1.0000      1.0000                     NaN                   0.0185             0.7850              0.0263   0.4497   0.0001

## PRE-REGISTERED holdout test

Tie set within 0.10 Sharpe of the top: 15:00|both|vixmove_fixed (params 2), 15:30|both|vixmove_fixed (params 2), 15:00|both|vixmove_exp (params 0), 15:30|both|vixmove_exp (params 0).
Winner: **15:00|both|vixmove_exp** (fewest fitted parameters among the tied, then highest Sharpe).
This ONE configuration is tested on the 2020-06-01 → 2026-09-11 holdout when data/ext arrives. Thread A's gap-up call (13:00, gap > 0.3%) is the second pre-registered holdout signal. The other 15 holdout rows are published in `out/reconcile_candidates.csv` (`label` column: POST-SELECTION, `window` column: 2020-06-01..2026-09-11) by `python -m pipeline.reconcile holdout` when data/ext arrives, and never promoted.

Written before any holdout data was read. Momentum trials this run: 16; historical N for DSR: 42 (gap-up: 1099).
