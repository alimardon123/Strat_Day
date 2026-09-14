# TRACK_C.md — defined-risk short 0DTE premium (Amendment A43, owner's option E)

Track C requires a stock account with OPTIONS APPROVAL FOR DEFINED-RISK SPREADS (iron butterflies/condors, the long wings bought so the loss is capped at entry) -- NOT the prop account that governs every other deliverable in this repository (the 0DTE buyer's side, `pipeline.units.eventvol`'s A42, and `PLAYBOOK_0DTE.md` itself). It is reported here, under its own heading, and never enters the prop-account playbook. The reference class a risk desk actually cares about for a short-premium book is the TAIL -- worst day, worst month, full-loss frequency, intraday adverse excursion -- not the mean; the tail table below exists for exactly that reason. Three trials (S1 iron butterfly at 09:31, S2 the same structure at 13:30, S3 iron condor at 09:31), each at two per-leg round-trip costs, on the owner's real SPY 0DTE 1-minute bars as one out-of-sample window (no CONTEXT/SELECTION/HOLDOUT split); every parameter was pre-registered before this unit ever ran (`ACCEPTANCE.md` Amendment A43).

## Results (`out/sellvol_candidates.csv`)

| trial | cost_per_leg | n | n_skipped | win | mean_usd | median_usd | mean_pct_maxloss | median_pct_maxloss | worst_structure_pct_maxloss | control_mean_pct_credit | contracts_median | sharpe_calday | p_boot_day | dsr_N42 | label |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 | 0.1000 | 592 | 83 | 49.6622 | -325.0186 | -16.5000 | -8.5678 | -0.4144 | -153.8462 | 3.5506 | 11.0000 | -2.3416 | 1.0000 | 0.0000 | FAILED |
| S2 | 0.1000 | 557 | 118 | 50.9874 | -186.8887 | 18.0000 | -5.0021 | 0.5017 | -128.6408 | 10.9995 | 8.0000 | -2.5114 | 1.0000 | 0.0000 | FAILED |
| S3 | 0.1000 | 443 | 232 | 51.6930 | -256.0993 | 24.0000 | -6.7629 | 0.6116 | -202.2727 | 3.5506 | 7.0000 | -2.3901 | 1.0000 | 0.0000 | FAILED |
| S1 | 0.2000 | 592 | 83 | 40.2027 | -797.9240 | -471.0000 | -20.8891 | -12.2910 | -230.7692 | 3.5506 | 11.0000 | -5.6094 | 1.0000 | 0.0000 | FAILED |
| S2 | 0.2000 | 557 | 118 | 28.0072 | -537.7684 | -306.0000 | -14.2754 | -8.1481 | -148.0583 | 10.9995 | 8.0000 | -7.0415 | 1.0000 | 0.0000 | FAILED |
| S3 | 0.2000 | 443 | 232 | 30.4740 | -569.4176 | -240.0000 | -15.0706 | -6.3969 | -232.5758 | 3.5506 | 7.0000 | -5.0404 | 1.0000 | 0.0000 | FAILED |

## Tail table (worst day/month, 5th-percentile day, full-loss share, intraday MAE shares, max drawdown, worst month as % of equity)

| trial | cost_per_leg | worst_day_usd | worst_month_usd | p05_day_usd | full_loss_share | mae_median_pct_credit | mae_share_gt100 | mae_share_gt200 | max_drawdown_pct | worst_month_pct |
|---|---|---|---|---|---|---|---|---|---|---|
| S1 | 0.1000 | -6080.0000 | -35952.0000 | -4042.5000 | 0.0794 | 31.4365 | 0.1014 | 0.0034 | 198.1801 | -35.9520 |
| S2 | 0.1000 | -5035.0000 | -12549.0000 | -2192.4000 | 0.0162 | 24.0310 | 0.1077 | 0.0000 | 104.4873 | -12.5490 |
| S3 | 0.1000 | -8010.0000 | -39060.0000 | -3139.3000 | 0.0474 | 50.0000 | 0.3318 | 0.1603 | 113.8028 | -39.0600 |
| S1 | 0.2000 | -9120.0000 | -57072.0000 | -4563.4500 | 0.1250 | 31.4365 | 0.1014 | 0.0034 | 479.8675 | -57.0720 |
| S2 | 0.2000 | -5795.0000 | -25949.0000 | -2597.4000 | 0.0287 | 24.0310 | 0.1077 | 0.0000 | 302.7794 | -25.9490 |
| S3 | 0.2000 | -9210.0000 | -52500.0000 | -3645.0000 | 0.0609 | 50.0000 | 0.3318 | 0.1603 | 254.0264 | -52.5000 |

## By calendar year (`out/sellvol_by_year.csv`, $0.10/leg row only, descriptive)

| group_value | trial | n | mean_pct_maxloss | worst_day_usd | full_loss_share |
|---|---|---|---|---|---|
| 2024 | S1 | 192 | -6.5095 | -5605.0000 | 0.0573 |
| 2025 | S1 | 233 | -11.0050 | -6080.0000 | 0.0858 |
| 2026 | S1 | 167 | -7.5337 | -5840.0000 | 0.0958 |
| 2024 | S2 | 170 | -3.5806 | -5035.0000 | 0.0235 |
| 2025 | S2 | 225 | -5.0721 | -4251.0000 | 0.0133 |
| 2026 | S2 | 162 | -6.3964 | -3952.0000 | 0.0123 |
| 2024 | S3 | 135 | -6.2768 | -4384.0000 | 0.0444 |
| 2025 | S3 | 174 | -7.5693 | -8010.0000 | 0.0575 |
| 2026 | S3 | 134 | -6.2057 | -4104.0000 | 0.0373 |

## By prior-close VIX tercile (`out/sellvol_by_year.csv`, $0.10/leg row only, descriptive)

| group_value | trial | n | mean_pct_maxloss | worst_day_usd | full_loss_share |
|---|---|---|---|---|---|
| T1 | S1 | 189 | -6.1100 | -4320.0000 | 0.0265 |
| T2 | S1 | 198 | -5.3105 | -5060.0000 | 0.0505 |
| T3 | S1 | 205 | -13.9798 | -6080.0000 | 0.1561 |
| T1 | S2 | 168 | -4.6608 | -3080.0000 | 0.0000 |
| T2 | S2 | 189 | -3.2139 | -4180.0000 | 0.0106 |
| T3 | S2 | 200 | -6.9786 | -5035.0000 | 0.0350 |
| T1 | S3 | 112 | -7.2092 | -3840.0000 | 0.0357 |
| T2 | S3 | 150 | -4.3284 | -4384.0000 | 0.0200 |
| T3 | S3 | 181 | -8.5044 | -8010.0000 | 0.0773 |

## Verdict per trial (family row = $0.10/leg, recombining the REAL family-wide BH-FDR result from `out/trials.csv` with `out/sellvol_candidates.csv`'s own five other conditions -- `pipeline.units.sellvol`'s own `survives`/`promotable` columns carry a hard-coded False FDR placeholder and are not the true verdict)

**S1 at $0.10/leg** (the family row): **does not survive**. Conditions met: beats the A42 buyer-mirror control; at least 200 trades. Conditions not met: net return (mean_pct_maxloss) > 0; day-block bootstrap p < 0.05; passes BH-FDR at 10% within the family (`out/trials.csv`); deflated Sharpe (N=42) > 0.95.

**S1 at $0.20/leg** (a cost-sensitivity row, not the family row): FDR -- and therefore survives/promotable -- is UNDETERMINED at this cost (only the $0.10/leg row feeds `pipeline/trials.py`'s family ledger). Other conditions met: beats the A42 buyer-mirror control; at least 200 trades. Other conditions not met: net return (mean_pct_maxloss) > 0; day-block bootstrap p < 0.05; deflated Sharpe (N=42) > 0.95.

**S2 at $0.10/leg** (the family row): **does not survive**. Conditions met: at least 200 trades. Conditions not met: net return (mean_pct_maxloss) > 0; day-block bootstrap p < 0.05; passes BH-FDR at 10% within the family (`out/trials.csv`); beats the A42 buyer-mirror control; deflated Sharpe (N=42) > 0.95.

**S2 at $0.20/leg** (a cost-sensitivity row, not the family row): FDR -- and therefore survives/promotable -- is UNDETERMINED at this cost (only the $0.10/leg row feeds `pipeline/trials.py`'s family ledger). Other conditions met: at least 200 trades. Other conditions not met: net return (mean_pct_maxloss) > 0; day-block bootstrap p < 0.05; beats the A42 buyer-mirror control; deflated Sharpe (N=42) > 0.95.

**S3 at $0.10/leg** (the family row): **does not survive**. Conditions met: beats the A42 buyer-mirror control; at least 200 trades. Conditions not met: net return (mean_pct_maxloss) > 0; day-block bootstrap p < 0.05; passes BH-FDR at 10% within the family (`out/trials.csv`); deflated Sharpe (N=42) > 0.95.

**S3 at $0.20/leg** (a cost-sensitivity row, not the family row): FDR -- and therefore survives/promotable -- is UNDETERMINED at this cost (only the $0.10/leg row feeds `pipeline/trials.py`'s family ledger). Other conditions met: beats the A42 buyer-mirror control; at least 200 trades. Other conditions not met: net return (mean_pct_maxloss) > 0; day-block bootstrap p < 0.05; deflated Sharpe (N=42) > 0.95.

## FIXED parameters (pre-registration, never re-tuned on any window)

FIXED (pre-registration, A43): S1 iron butterfly at 09:31 (shared ATM body strike, wings at +/-1% of the 09:31 SPY price); S2 the same structure at 13:30; S3 iron condor at 09:31 (short legs at +/-0.5%, wings at +/-1.5%, four independent strikes). Reference/ATM-body strike: eventvol's SPX-point/10 reference and nearest-either-right rule; every other leg is priced independently per right with realopt.nearest_listed. Causal availability (A41 clarification, reused verbatim): a strike is a candidate only if it has a print at or before that trial's own entry minute. Entry = the leg's bar close at the entry minute, else the next print within 5 minutes; exit = the 15:59 close, else the last print within the previous 10 minutes ('print' read as that bar's own close both sides); a leg with neither, or whose entry bar actually used is not strictly before its exit bar actually used, skips and counts the WHOLE structure (n_skipped), never a partial structure. max_loss = wing_width - credit, wing_width = the WIDER of the two independently-priced sides (the true worst case at expiry); a non-positive credit or max_loss also skips and counts. Costs: $0.10 / $0.20 PER LEG round trip (4 legs => $0.40 / $0.80 per structure), two rows, no $0 row. Sizing: contracts = floor(4% of a FIXED $100,000 account / (max_loss x 100)), recomputed fresh each day, never compounded. worst_day/worst_month/p05_day/full_loss_share are over TRADED days only; sharpe_calday/max_drawdown_pct are on the equity curve over the FULL window day population, zero-filled on skipped/non-trading days. MAE: worst minute-by-minute mark (all four legs, EXACT prints only, strictly between entry and 15:59) of credit-minus-debit-to-close, floored at 0, in % of credit and of max_loss; NaN excluded from the >100%/>200% share denominators. Control ('positive excess over control'): the seller's GROSS P&L on the shared two legs is the NEGATIVE of eventvol's (A42) own GROSS mean_pct for the day-matched buyer trial (E1 for S1/S3's 09:31 entries, E3 -- not E2 union E3 -- for S2's 13:30, non-FOMC-restricted entries), both sides pre-cost. survives/promotable: the family-wide BH-FDR condition is a hard-coded False placeholder here (this standalone unit cannot know it; pipeline/trials.py computes it downstream across the whole ledger) -- both columns are therefore ALWAYS False in this file; the cond_* columns and label report the other conditions honestly for pipeline.report_c to recombine with the real FDR result after pipeline/trials.py has run. DSR at N=42 (family 39->42) per cost row, using this run's own three trials' per-trade Sharpe AT THAT COST as the SR0 pool (this codebase's usual 'this run's own trials only' convention). By-year/VIX-tercile table: the $0.10/leg cost row only; terciles over the window's own day population (realopt.vix_terciles), prior-close VIX via signals.day_table's own merge_asof convention. On ANY exception (including the 0DTE file being absent) this unit writes header-only outputs and exits 0, exactly pipeline.units.letf's (A38) contract, like eventvol.py/realopt.py -- this pre-registered candidate must never fail `make all`.
