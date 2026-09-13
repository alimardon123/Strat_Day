# ACCEPTANCE.md — definition of done, survival rule, budgets, non-goals, assumptions

v2, amended after the Phase 0 tribunal (four hostile lenses; findings and dispositions in
CRITIQUE.md). Every amendment is logged in CHANGELOG.md. Where this file and the plan's
upgraded prompt differ, this file governs.

## The constraint that governs everything

The prop account permits ONLY 0DTE options, long-only, naked calls or puts. No selling,
no spreads, no futures, no shares, no overnight holds. Daily loss limit 3–5% (base case
4%), evaluated on marked intraday P&L. Every deliverable must be tradeable under it. The
own-account track (stock account with options approval) is secondary.

## Reference class

López de Prado's backtesting standards (deflated Sharpe ratio with the trial count that
produced the candidate, purged/embargoed CV wherever a parameter is chosen, multiple-testing
awareness) AND the two threads' own guards: `research/thread_B_inversion/stats_engine.py`
(block bootstrap + Benjamini-Hochberg FDR) and Thread A's matched random-entry control and
n_eff correlation adjustment. A result that would not survive both is not a result. Written
deliverables must stand next to `research/thread_B_inversion/SYSTEM_SPEC.md`: every number
names the script and the `out/` file it came from.

## Units

D1, D2 and the survival rule are scored on the UNDERLYING in SPX index points per trade net
of the round-trip cost (Thread B's unit, with cost fixed in points). The D1 ranking metric (the
calendar-day Sharpe) is computed on the net return in % of the underlying so that a price level
that doubled over the selection window does not weight late trades (Phase 5 amendment; rank
verified identical under points). Option-premium returns (Thread A's unit, % of premium) appear
only in D4 and are derived from the same trades.

## Definition of done

| # | Statement | Evidence file |
|---|---|---|
| D1 | One reconciled last-hour momentum specification, chosen by the fixed decision rule below; all 16 configurations published | `out/reconcile_candidates.csv`, `out/reconcile_decision.md` |
| D2 | The reconciled spec (single pre-registered holdout test) and Thread A's gap-up call each evaluated on the 2020-06-01→2026-09-11 holdout; per calendar year (2020 H2, 2021 … 2026 YTD): trades, win rate, mean net points and % of premium at quoted spreads 1.0/2.0/3.0, worst trade, worst day, intraday MAE; bootstrap p on the pooled holdout and on its two halves (2020-06→2023-06, 2023-07→2026-09) with month blocks | `out/holdout_by_year.csv`, `out/holdout_pooled.csv` |
| D2b | Thread A's gap-up call re-run on histdata GRXEUR and ETXEUR 2010–2018 (entry at the same fraction of the local session) with Thread B's bootstrap; shrinkage > 50% or a sign flip is recorded as a finding, not a kill | `out/xmarket_*.csv` |
| D3 | Execution model (A20) applied to every surviving signal; improvement vs market entry with bootstrap p | `out/execution.csv` |
| D4 | `PLAYBOOK_0DTE.md`: every headline number measured on the 2020-06→2026-09 holdout only (full-sample figures in a separate table headed IN-SAMPLE + HOLDOUT); pricing per A7/A28; sensitivity = quoted spread ∈ {1.0, 2.0, 3.0} pt for every leg, k ∈ {1.0, 1.3, 1.6} for the 13:00 leg only (at 2% ITM with < 1 h to expiry the model is intrinsic ± spread — stated in the first paragraph); per-instrument settlement rules and per-contract premium / minimum account (A28); max positions per day and the combined-book worst day (A17) | `out/playbook_*.csv` |
| D5 | The 8-sleeve unconstrained portfolio re-measured through 2026-09 in `OWN_ACCOUNT.md`, by year and regime, Feb 2018 and 2020 in sample for the vol sleeves, S13 weight cap applied, VXX/VXZ bridged through VIXY/VIXM (A13) with the three bridge correlations printed; plus the VIX − realised-vol series through 2026-09 labelled not-tradeable-as-measured (A14) | `out/own_account_*.csv` |
| D6 | Every trial (A31) counted in `SCORECARD.md`; every pooled statistic date-clustered; every cross-instrument statistic correlation-adjusted; every claimed edge has both controls (A16), a block-bootstrap p and a deflated Sharpe at both trial counts (A15) | `SCORECARD.md`, `out/trials.csv` |
| D7 | `make all` regenerates every table from `data/raw` + `data/ext`; `make repeat` yields byte-identical `out/`; `make all` exits non-zero if any expected output is empty or any `*.error` file exists; playbook tables are generated, never typed | `Makefile` |

## Survival rule

A signal SURVIVES the holdout only if ALL hold; otherwise it is reported with its p-value and
the label that applies (FAILED / UNDERPOWERED / COST-KILLED / POST-SELECTION).

1. Net mean > 0 in index points at 1.0 pt round-trip cost.
2. One-sided block-bootstrap p < 0.05: `pipeline/stats.one_sided_p` (stats_engine's
   algorithm, generator re-seeded with 11 per call, n_boot 2000, p/2 when the mean is
   positive else 1.0 — Thread B's convention). Pooled holdout and each half use calendar-month
   blocks (≥ 20 months each); per-year rows use trading-day blocks (one observation per day,
   i.e. the iid bootstrap, which the 20-block guard permits); any statistic with < 20 blocks
   is printed NA, never 1.0.
3. Passes Benjamini-Hochberg FDR at 10% across every trial in this run (A31).
4. Positive excess over the day-selection control (A16); the timing control is reported.
5. Deflated Sharpe > 0.95 on the holdout trade series (per-trade Sharpe, T = trades, trade-
   return skew and kurtosis) with N = the number of candidates among which the reported one
   was chosen ON THE HOLDOUT (N = 1 for a pre-registered signal, so this is the probabilistic
   Sharpe ratio; N = the family size for exploratory flow candidates). The in-sample DSR with
   the historical trial counts (momentum: 16 this run + 4 it22 setups + 22 step17 tests = 42;
   gap-up call: 1,092 scan cells + 6 conditions + 1 = 1,099) is reported in SCORECARD.md.
6. At least 200 holdout trades. Below that: report the p-value and label UNDERPOWERED.

## Decision rule for D1 (fixed before any run; CRITIQUE #3, #9, #19, #20)

Configurations (16 = entry × direction × gate): entry ∈ {15:00, 15:30}; direction ∈
{put-only, both}; gate ∈
- `mag` — |open → entry| above the expanding 70th percentile of strictly prior sessions
  (Thread A's rule, unfitted; min 20 prior sessions);
- `vixmove_exp` — prior-close VIX above its expanding upper-tercile boundary AND
  |prev_close → entry| above its expanding upper-tercile boundary (Thread B's construction —
  its 17.06 / 0.665 are exactly the upper-tercile boundaries of histdata 2010–2018, verified
  in Phase 2 — turned into a rule that uses only prior sessions);
- `vixmove_fixed` — the same boundaries computed once on Oanda 2005-01→2012-12 and frozen
  (the values are generated, not typed: `out/reconcile_decision.md`, line "vixmove_fixed
  thresholds"; gate (c)'s Thread-A reproduction path prints its own pair because it uses Thread
  A's prior-bar reference rather than A34's prior-NYSE-day reference — by design, A30);
- `vixmove_lit` — Thread B's literal 17.06 / 0.665, which are in-sample on 2013–2018;
  REPORTED, never ranked.

Ranking: the 12 rankable configurations are ranked on 2013-01-01→2020-05-13 (genuine test
data for all of them: Thread A's split is < 2013 / ≥ 2013 and the vixmove rules use only
pre-2013 information) by net Sharpe on the CALENDAR-DAY P&L series over NYSE trading days
(zeros on non-trade days, × √252), so candidates with different trade frequencies are
comparable; ties within 0.10 go to the configuration with fewer FITTED parameters — an expanding
rule has none (mag 0, vixmove_exp 0), frozen boundaries count (vixmove_fixed 2) — then the
higher Sharpe (Phase 4 defect 2). Exactly ONE configuration — the top-ranked — is
tested on the 2020-06-01→2026-09-11 holdout. If it fails the survival rule, D1's outcome is
"no reconciled specification survives". The other 15 holdout rows are still published in
`out/reconcile_candidates.csv` (rows with `window` = 2020-06-01..2026-09-11, `label` =
POST-SELECTION; the winner's row is labelled PRE-REGISTERED; the selection rows carry `label` =
SELECTION), written by `python -m pipeline.reconcile holdout` when the ext feed is present, never
promoted and not counted in the trial family (they are published, not tested). Expanding rules
keep expanding through the holdout using strictly prior sessions (a rule, not a fitted
parameter); the variant with thresholds frozen at 2020-05-13 is a separate, counted trial if
run.

## Numeric budgets (measured, never estimated)

- Costs: 0DTE options quoted bid-ask 1.0 / 2.0 / 3.0 index points (charged per A28); ES
  0.33–0.50 pts; ETFs 2 bp/side; single stocks 5 bp/side. Percent-of-price costs are derived
  per trade from the actual price level (A21).
- Any Sharpe above 3.0 on price-only data triggers a mandatory bug hunt before it is reported.
- Position size = daily loss limit ÷ worst-trade loss in % of premium measured on the holdout,
  with a floor of 100% (a hold-to-close trade has no stop; Thread B's 54% loss-at-stop was
  measured on ATM calls with a 1.5-ATR stop and is not used). Worst trade and worst day are
  also reported on intraday MAE from minute highs/lows. The sizing denominator is the worst
  day of the COMBINED book (both signals on the same day). Base 4% limit; 3% and 5% shown.
- Bootstrap n_boot 2000; hardware 4 cores / 15 GB; fleet ≤ 3 concurrent units.

## Non-goals

No new pattern search over 2005–2020; no conditioning / regime-switching / clever weighting
on top of the portfolio; no inversion; no ATM or OTM 0DTE on a directional signal; no UI; no
live or paper execution; no GEX / dealer-positioning filters (no positioning data obtainable);
no real 0DTE quotes (unobtainable — k×VIX is the model); no defined-risk 30–45 DTE VRP sleeve
backtested with real option prices and margin (no option data obtainable; VRP is measured as
VIX − realised vol and labelled not-tradeable-as-measured); no cross-market validation after
2018 (no DAX/EuroStoxx minute data obtainable); no change to the prop-account constraint; no
edits to files under `research/` (copy, then change).

## Assumptions (recorded, not asked)

| # | Assumption | Why |
|---|---|---|
| A1 | In-sample minute data ends 2020-05-13 (Oanda file ts_max 2020-05-14 07:59 UTC). The ext minute file starts 2020-05-14; 2020-05-14→05-29 is warm-up only; holdout = 2020-06-01→2026-09-11; thresholds frozen through 2020-05-13 | Verified file coverage (CRITIQUE #32) |
| A2 | Bundle lives verbatim at `research/` (`research/CLAUDE.md`, `research/thread_A_multisleeve/`, `research/thread_B_inversion/`) | Zip layout kept; only the top-level folder name changed |
| A3 | "Identical data" for D1 = Oanda SPX500_USD 2005-01→2020-05 (UTC) + `data/ext` minute file from 2020-05-14; histdata 2010–2018 is a cross-feed check only | Oanda is the one feed both threads used |
| A4 | Sessions: tz-aware America/New_York, 09:30–16:00, sessions with < 300 bars dropped and listed; sessions whose date is not an NYSE trading day (VIX daily calendar, current to 2026-09-11) dropped and listed | Both threads' rule; CFD feeds print bars on some closed days |
| A5 | Timestamp conventions: Oanda = UTC; histdata = Eastern with DST (both verified by the sustained-step DST probe: open at 09:30 in every Jan/Jul month, 47 of 47) | Direct inspection |
| A6 | `data/ext/ext_manifest.json` declares instrument (SPX / ES / SPY), source, `adjusted`, and for ES the roll dates or a contract column; the session builder refuses to run without it and checks the declared instrument against the price level. SPY: prior close adjusted by the dividend on ex-dates; 1 SPX point = $0.10 SPY. ES: any signal whose reference price and decision price come from different contracts is dropped and listed. SPX cash: open = first print at or after 09:31, close = last print before 16:00 (the official close is not in a bar file), recorded in DATA.md | CRITIQUE #6, #23 |
| A7 | Option pricing: Black-Scholes, r = 0, IV = k × prior-close VIX, T = minutes to 16:00 / (365×24×60); k = 1.0 for every reproduction, k = 1.3 base for the playbook's 13:00 leg with 1.0 / 1.6 shown; for the 15:00 and 15:30 legs the model is intrinsic ± spread (time value at 60 minutes, 2% ITM, S = 4000, k = 1.0: ≤ 0.001 pt for VIX ≤ 40 and 0.16 pt at VIX 83 — generated in `out/options_timevalue.csv` by `python -m pipeline.options`; judge round 2 corrected the earlier typed "< 0.08 pt"; the book mean moves 11.48% → 11.31% between k = 1.0 and 1.6) and k is not a sensitivity axis | `step15_odte.py:76`; `out/options_timevalue.csv`; Phase 4; judge round 2 N5 |
| A8 | 2% ITM: K = S × 0.98 (calls) / S × 1.02 (puts), rounded AWAY from spot to the instrument's grid (5 pts SPX, $1 SPY/XSP); unrounded for the Thread A reproduction | CRITIQUE #26 |
| A9 | Thread A it22 magnitude gate: expanding 70th percentile of \|open → 15:00\| over strictly prior sessions; put on down days only | `ASSESSMENT_iteration22:57-59` |
| A10 | Thread A gap-up signal: open / prior close − 1 > 0.3%; entry at the first bar open after 13:00; 2% ITM call; hold to settlement | `HANDOFF.md:161` |
| A11 | Decision price = close of the last bar within 5 min at or before the decision minute; entry = open of the next bar; Thread B's bar-close fill is reproduced only inside the reproduction gate and the difference is logged | CRITIQUE #17 |
| A12 | Thread A scripts it14, it17–it20, it22 are absent; specs re-implemented from ASSESSMENT text; reproduction gates in A30 | Bundle inventory |
| A34 | A session whose prior kept session is not the prior NYSE trading day (feed gap) contributes no prior-close signal (gap-up, VIX-and-move gates) and is counted in `out/reconcile_ref_report.csv`; the magnitude gate (open-based) is unaffected | Phase 4 defect 12 |
| A35 | The ext feed is proven before it arrives: gate (e) rebuilds a synthetic SPY-scaled ext file from the Oanda feed and requires every candidate's trade table on 2019-06→2020-05 to be identical through the ext path, plus dividend, roll and manifest-refusal tests | Phase 4 defect 1 |
| A13 | VXX/VXZ: the Kaggle-mirror series are the original ETNs (end 2017-11-10); today's VXX/VXZ are the 2018 Series B notes; there is no overlap. Bridge through VIXY / VIXM (same indices, continuous since 2011, in both panels): prove old-VXX ≈ VIXY (2011→2017-11) and new-VXX ≈ VIXY (2018→2026), and the same for VXZ via VIXM, at daily-return corr ≥ 0.98 (measured: VXX/VIXY 0.9987, VXZ/VIXM 0.9875 — an ETN and an ETF on the same index; the bar was 0.99 in v2 and is amended to 0.98 with the measurement logged), fill 2017-11-11→2018-01 with the proxy's returns | CRITIQUE #16; Phase 5 |
| A14 | Own-account VRP sleeve: VIX − realised vol through 2026 (Thread B step11 method), labelled not-tradeable-as-measured | No option prices obtainable |
| A15 | Deflated Sharpe per-trade (T = trades); SR0 from the empirical dispersion of the competing trials' per-trade Sharpes; reported at N = holdout-selection count and at the historical N | CRITIQUE #7, #28 |
| A16 | Day-selection control: the same number of trades drawn uniformly from random holdout sessions, same entry time, same direction rule (put-only → short; both → sign of the move on that day), same exit, 200 seeds; excess = signal mean − mean of control means; also the fraction of seeds beaten. Timing control (reported only): same days, same direction, random entry minute in the two hours before the decision ([decision − 120 min, decision)); it holds longer than the signal and so also captures the pre-decision drift, which is why it is reported and not a survival test | CRITIQUE #14; Phase 4 nit |
| A17 | Sizing per the numeric budget (100% floor, MAE, combined-book worst day); "worst day" and "worst year" at base sizing in % of account | CRITIQUE #1, #18 |
| A18 | Commit and push at the end of every phase and tribunal round to `claude/modest-pasteur-oyzqyh` | Ephemeral container |
| A19 | `pipeline/stats.py` re-seeds the bootstrap generator per call and takes the split as a parameter; Thread B's one-sided convention kept | `stats_engine.py` has one module-level RNG and a hardcoded 2017 split |
| A20 | Execution model for hold-to-close signals: resting limit at k × ATR against the trade direction (k ∈ {0.25, 0.50, 1.00}); ATR = 14-bar rolling mean of 5-minute (high − low) from bars that have already closed; fill window = min(30 min, minutes-to-close − 5), i.e. no fill after 15:55; unfilled signals count as zero per signal; a filled limit pays commission 0.10 pt on entry PLUS the exit half of the quoted spread (the position is still liquidated at the close), against the market row's full 1.0 pt; the improvement is decomposed into its cost-assumption part (fill rate × 0.40) and its price/adverse-selection part; puts/shorts mirrored (fill if high ≥ limit) | `step8_execution.py` is long-only, its 30-min window would outrun a 15:30 entry, and its resample leaks one minute; Phase 4 defect 3 |
| A21 | Costs fixed in index points; percent-of-price derived per trade | Thread B's 0.0157% assumes SPX ≈ 2100 |
| A22 | Thread B reproduction: (c1) DATA IDENTITY — Thread B's own conventions (detected open + 360, bar-close fill, month blocks, its cost constant) on histdata 2010–2018 must give n = 337 / +0.0645% / 58.5% / SR 2.50 within rounding, and its LEGACY holdout mode (single open minute detected on naive UTC stamps, as `step17_intramom.py:34-42` does) must give n = 85 / +0.0975% / SR 1.67 exactly; (c2) CORRECTED holdout on the America/New_York session builder is the reference row downstream, with the difference logged as a reproduced defect | Phase 2 finding: the published holdout was DST-misaligned for winter sessions |
| A23 | Thread A it22 split: train < 2013-01-01, test ≥ 2013-01-01 | `HANDOFF.md:157`; it15 |
| A24 | Canonical entry times are wall-clock America/New_York | Thread B's "15:30" is detected-open + 360 |
| A25 | VIX prior close = last VIX close strictly before the session date (as-of merge) | `step17:97` row shift; `step15:58` same-day VIX |
| A26 | Blocks as in survival rule 2 | `block_bootstrap_p` returns 1.0 below 20 blocks |
| A27 | Calendar: NYSE holidays excluded even when a CFD prints bars; early closes fall out by bar count; a dropped ordinary weekday is a "feed gap" and is counted in the session-denominator report (Oanda 2017: 85 feed-gap sessions) | Verified in Phase 2 |
| A28 | Settlement and cost per instrument: SPX / XSP — buy at the ask (half the quoted spread), hold to PM cash settlement, proceeds = intrinsic at the 16:00 print, no exit spread; SPY — physically settled, so sell by 15:55 with both spread halves charged; SPY figures are for a 15:55 exit only. Per-contract premium ≈ 2% × S × multiplier and the minimum account for one contract at base sizing are printed in the playbook | CRITIQUE #12 |
| A29 | Expanding thresholds need ≥ 20 prior sessions | Same floor as the bootstrap |
| A30 | Thread A reproduction gate: HARD (pricing-independent) — re-implemented trade counts within ±10% of it22's 516 big-down puts, 473 big-up calls and 1,030 gap-up calls on Oanda 2005-01→2020-05, underlying win rates within 1 point; SOFT — TEST (≥ 2013) mean within 0.3 percentage points of premium at k = 1.0, 2% ITM unrounded, r = 0, quoted spread 1.0 pt, under Thread A's inferred convention (entry at the ask, settlement at intrinsic — the only convention within tolerance for BOTH legs, offset +0.21 on each); the half-on-exit alternative is reported beside it. A miss is a logged finding, never a tuning target | Phase 2 convention probe |
| A31 | A trial is one (signal rule, parameter set, target series) tested for an edge. Reporting cuts (by year, spread, k, sizing) and execution variants of an already-counted signal are not trials. The family for BH-FDR is every trial this run tests: the 16 momentum configurations, the gap-up call, the 3 cross-market runs and the 3 flow candidates (`pipeline/trials.py`, `out/trials.csv`) | CRITIQUE #7; Phase 4 defect 8 |
| A32 | Fleet unit failure: empty output AND `<out>.error` with the traceback, exit code 2; `run_all` and the gates fail on any empty expected output or any `*.error` | CRITIQUE #25 |
| A33 | Reproduction runs never execute Thread B's scripts in place; `git status --porcelain research/` must be empty after every gate | CRITIQUE #29 |
