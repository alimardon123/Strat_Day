# out/reconcile_decision.md — D1 pre-registration

Selection window 2013-01-01 → 2020-05-13, Oanda SPX500_USD, America/New_York sessions, cost 1.0 pt.
vixmove_fixed thresholds (Oanda 2005-2012 upper terciles): 15:00 VIX>22.81 & |move|>0.816%; 15:30 VIX>22.81 & |move|>0.845%.

## Ranking of the 12 rankable configurations (calendar-day Sharpe, net of cost)

               candidate   n     win  net_pts  net_pct  sharpe_calday  sharpe_threadB_conv  p_boot_month  p_boot_day  fdr_pass_10pct  excess_over_control_pct  frac_seeds_beaten  dsr_N12  dsr_N42
15:00|both|vixmove_fixed  93 63.4409   5.1032   0.1878         0.5699               2.4451           NaN      0.0673           False                   0.2257             1.0000   0.7465   0.6621
  15:30|both|vixmove_exp 147 59.8639   2.5810   0.0993         0.5330               1.8128        0.0780      0.0798           False                   0.1282             1.0000   0.6342   0.5148
15:30|both|vixmove_fixed  93 59.1398   3.7699   0.1446         0.5300               2.2701           NaN      0.0833           False                   0.1770             1.0000   0.7072   0.6197
  15:00|both|vixmove_exp 146 63.0137   3.0897   0.1115         0.5110               1.7433        0.1797      0.0985           False                   0.1507             1.0000   0.6155   0.4935
           15:30|put|mag 182 57.1429   0.7709   0.0330         0.2725               0.8297        0.2545      0.2382           False                   0.0724             1.0000   0.3377   0.2324
   15:30|put|vixmove_exp  62 51.6129   1.5419   0.0540         0.1784               0.9258           NaN      0.3142           False                   0.0940             0.9950   0.4162   0.3431
 15:00|put|vixmove_fixed  42 54.7619   2.4119   0.0800         0.1670               1.0495           NaN      0.3345           False                   0.1211             0.9800   0.4490   0.3858
   15:00|put|vixmove_exp  58 55.1724   1.7397   0.0548         0.1515               0.8122           NaN      0.3510           False                   0.0948             0.9950   0.3956   0.3242
           15:00|put|mag 189 52.3810   0.3238   0.0173         0.1308               0.3905        0.3623      0.3745           False                   0.0622             0.9950   0.2052   0.1229
 15:30|put|vixmove_fixed  43 51.1628   1.1163   0.0333         0.0828               0.5137           NaN      0.4095           False                   0.0725             0.9250   0.3660   0.3074
          15:30|both|mag 371 54.7170   0.0668   0.0019         0.0245               0.0522        0.4785      0.4700           False                   0.0356             1.0000   0.0566   0.0194
          15:00|both|mag 371 50.9434  -0.0332   0.0008         0.0086               0.0184        0.4928      0.4918           False                   0.0391             0.9900   0.0515   0.0173

p_boot_month is NA when the trades span fewer than 20 calendar months (survival rule 2); p_boot_day is the
one-observation-per-day bootstrap. sharpe_threadB_conv is per-trade Sharpe × √252 (step17_intramom.py:77), which
overstates the annualised figure by √(252 / trades per year); sharpe_calday is the ranking metric.

## Literal-threshold rows (Thread B's 17.06 / 0.665 — in-sample on 2013-2018; reported, not ranked)

             candidate   n     win  net_pts  net_pct  sharpe_calday  sharpe_threadB_conv  p_boot_month  p_boot_day
 15:00|put|vixmove_lit 103 54.3689   1.8718   0.0681         0.3101               1.2545        0.1827      0.2075
15:00|both|vixmove_lit 255 58.4314   2.0831   0.0807         0.6145               1.5866        0.1335      0.0575
 15:30|put|vixmove_lit 106 57.5472   1.5368   0.0601         0.3206               1.2787        0.1003      0.2025
15:30|both|vixmove_lit 257 59.1440   1.4716   0.0585         0.5282               1.3569        0.0998      0.0887

## PRE-REGISTERED holdout test

Winner: **15:00|both|vixmove_fixed** (rank 1; ties within 0.10 Sharpe resolved by parameter count: 4 tied).
This ONE configuration is tested on the 2020-06-01 → 2026-09-11 holdout when data/ext arrives. Thread A's gap-up call (13:00, gap > 0.3%) is the second pre-registered holdout signal. All other configurations' holdout rows will be published labelled POST-SELECTION and never promoted.

Written before any holdout data was read. Trials counted this run: 16; historical N for DSR: 42.
