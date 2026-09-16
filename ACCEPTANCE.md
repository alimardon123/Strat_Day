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
| A31 | A trial is one (signal rule, parameter set, target series) tested for an edge. Reporting cuts (by year, spread, k, sizing) and execution variants of an already-counted signal are not trials. The family for BH-FDR is every trial this run tests: the 16 momentum configurations, the gap-up call, the 3 cross-market runs and the 3 flow candidates (23), plus the 2 pre-registered holdout tests when the ext feed is present (25); the 15 POST-SELECTION holdout rows are published, not tested, and are not in the family (`pipeline/trials.py`, `out/trials.csv`) | CRITIQUE #7; Phase 4 defect 8 |
| A32 | Fleet unit failure: empty output AND `<out>.error` with the traceback, exit code 2; `run_all` and the gates fail on any empty expected output or any `*.error` | CRITIQUE #25 |
| A33 | Reproduction runs never execute Thread B's scripts in place; `git status --porcelain research/` must be empty after every gate | CRITIQUE #29 |

## Amendment A36 — owner-proposed fair-value-gap setup, pre-registered 2026-09-13 09:58 UTC (before any result was seen)

Owner's description (5-minute SPY): after a breakout / break of structure the displacement leaves a three-bar
fair value gap; draw the gap, extend the box to the close of the candle before the displacement, enter on a
retrace to the box MIDPOINT, stop beyond the box, take profit on the other side. Fixed reading, implemented in
`pipeline/units/fvg.py` (fleet unit, INDEPENDENT):

- 5-minute bars from the 1-minute frame, regular session only, ≥ 3 minutes per bar; ATR = mean true range of
  the previous 20 five-minute bars.
- Bearish FVG at bar t: high[t] < low[t−2]; bullish: low[t] > high[t−2]. Displacement: |close − open| of bar
  t−1 ≥ 1.5 × ATR. Break of structure (variant on): close[t−1] below the previous 12 bars' low (bearish) /
  above their high (bullish); variant off: displacement only.
- Box (bearish): bottom = high[t], top = max(low[t−2], close[t−2]); mirror for bullish; height ≥ 0.05 × ATR.
- Entry: resting limit at the box midpoint after bar t closes, filled on the first later bar touching it, same
  session, not after 15:30 ET; unfilled setups count as no-trade and are reported.
- Stop: box top + 0.1 × ATR (mirror); take profit at R × the stop distance, R ∈ {1, 2}; stop assumed first
  when both touch in one bar; otherwise exit at the close. One position per side at a time.
- Cost 1.0 SPX point round trip (2.0 reported). Trials: side {short, long} × R {1, 2} × BOS {on, off} = 8,
  all counted in the family (25 + 8 = 33 for DSR). Windows: selection 2013-01-01 → 2020-05-13; holdout
  2020-07-27 → 2026-09-11; 2005–2012 for context. Controls: same-day random-bar entry with the same stop/TP
  (200 seeds), day-block bootstrap p, month-block p where ≥ 20 months, calendar-day Sharpe, DSR at N = 33.
- Survival rule unchanged. No parameter is varied beyond the eight trials; the ATR multiple, lookback, buffer,
  minimum height and midpoint entry are fixed here and may not be re-tuned on any window.

## Amendment A13 (second amendment, 2026-09-13, judge round 4 B1) — measured bridge outcome

With the owner's ETF panel present, the bridge correlations are measured on the real overlaps: old-VXX ↔ VIXY
0.9987, old-VXZ ↔ VIXM 0.9875, new-VXX ↔ VIXY 0.9829, new-VXZ ↔ VIXM 0.8775 (2018: 178 of 234 Series B VXZ
closes are stale zero-return prints; 2019 onward 0.92–0.99). Disposition, by the existing 0.98 rule and not by
choice: VXX is bridged to the real Series B note from 2018-01-25 (VIXY returns fill 2017-11-11 → 2018-01-24);
the VXZ bridge is REFUSED and the mid-term leg uses VIXM's returns from 2017-11-13 onward, labelled as such in
`out/own_account_bridge.csv` and OWN_ACCOUNT.md. Gate (f) `pipeline/gate_etf.py` asserts that every panel
ticker survives to the panel's last date and that the bridge decision is applied as printed.

## Amendment A37 — probability of backtest overfitting (D6 reporting statistic, 2026-09-13)

`pipeline/pbo.py` reports the CSCV probability of backtest overfitting of the D1 selection procedure (Bailey,
Borwein, López de Prado, Zhu 2015): the 12 rankable configurations' calendar-day P&L on 2013-01-01 → 2020-05-13,
16 contiguous blocks, all 12,870 balanced splits, PBO = share of splits in which the in-sample best ranks below
the out-of-sample median. It is REPORTED in PLAYBOOK §2 and SCORECARD, never a survival condition, and its
per-column shuffled null is printed beside it with the caveat that this null preserves each configuration's own
mean and variance and is therefore a floor for near-duplicate configurations, not 0.5.
`out/pbo.csv` also carries an 8-block sensitivity variant (70 splits; PBO 0.91 actual, 0.80 null) so the reader can see how
block count moves the estimate; only the 16-block headline is quoted in the playbook (judge round 5, note 5).


## Amendment A38 — leveraged-ETF close-rebalancing candidate (owner's option C, pre-registered 2026-09-13 12:19 UTC, before any run)

Owner decision 2026-09-13: "Go with option C, pre-register the leveraged-ETF candidate." Everything below is fixed
now; the unit runs only once the assets file exists (DATA.md), and no number here may be changed after the first run.

- Mechanism (who must trade, when): daily-reset leveraged and inverse S&P 500 funds must trade
  (L² − L) × AUM × (day return) in the last part of the session to reset leverage before the 16:00 NAV
  (Cheng & Madhavan 2009; Tuzun 2013). The size is forced; the sign is the sign of the day's move for
  long AND inverse funds alike, so the aggregate demand is
  D_t = Σ_i (L_i² − L_i) · NetAssets_{i,t−1} · r_t, with r_t = SPX prior close → 15:30 ET.
- Funds (S&P 500 only; Nasdaq-100 funds are excluded because no NDX/QQQ minute data is on the branch):
  SSO (2×, coefficient 2), SDS (−2×, 6), UPRO (3×, 6), SPXU (−3×, 12), SPXL (3×, 6), SPXS (−3×, 12), SH (−1×, 2).
- Trial (exactly one): entry 15:30 ET at the bar close, direction = sign(r_t) (call if positive, put if
  negative), gate = |D_t| ≥ the expanding 70th percentile of |D| over all prior sessions with assets data
  (minimum 250 sessions before the first signal; no fitted parameter), exit at the 16:00 close. Costs 1.0 and
  2.0 pts; option leg 2 % ITM at k × VIX as in D4.
- Data: SPY/SPX minute bars already on the branch; MISSING `data/ext/letf_aum_2006_2026.csv` (spec in DATA.md).
  The candidate runs on every session with assets data for at least one fund; sessions without are absent,
  not filled. If only a partial history is obtainable the windows are reported as they fall and the verdict
  is on the post-2020-07-27 sessions only.
- Scoring: the six-condition survival rule; day-block bootstrap p (n_boot 2000, seed 11); day-selection control
  (same count of random non-signal sessions, same direction rule, 200 seeds) and the on-file magnitude control
  (the price-only `15:30|both|mag` row of `out/reconcile_candidates.csv`, which this candidate must beat);
  calendar-day Sharpe; DSR at N = the family size at the time of the run (35 with A39, counted in `pipeline/trials.py`).
- Kill: net ≤ 0 at 1 pt on the holdout, or not above the day-selection control, or not above the price-only
  magnitude row. Honest prior MEDIUM-LOW: the price-only proxy of this mechanism failed this holdout; the
  assets weighting changes only which sessions pass the gate.

## Amendment A39 — overnight-loss forced-liquidation rebound (mechanism candidate runnable now, pre-registered 2026-09-13 12:19 UTC, before any run)

Owner's standing instruction: keep looking for mechanism-based opportunities. This is the only candidate the scout's
screen left that needs no new data and can reach 200 holdout trades. It is one hypothesis with a mechanism
fingerprint, not a search; every parameter below is fixed before the first run.

- Mechanism (who must trade, when): after a large overnight loss, margin calls issued on the prior close and
  broker-forced liquidations of levered longs execute at and just after the open (Reg T calls are met or
  liquidated before/at the next session's open; Brunnermeier & Pedersen 2009 funding spirals). The forced
  selling is front-loaded in the first 30 minutes and then exhausted; the mechanism therefore predicts (i) a
  positive drift from 10:00 to the close on those days, (ii) a LARGER drift from 10:00 than from 09:31 (the
  liquidation window is adverse for a 09:31 entry), and (iii) NO mirror effect after large overnight gains
  (no forced buyer). Related evidence: overnight-versus-intraday return reversal (Lou, Polk & Skouras 2019).
- Signal day: overnight return (prior 16:00 close → 09:30 open) ≤ the expanding 10th percentile of overnight
  returns over all prior sessions (minimum 250 sessions; no fitted parameter).
- Trials (exactly three, all counted): T1 = long call, entry 10:00 bar close, exit 16:00 close (the
  hypothesis); T2 = long call, entry 09:31 bar close, exit 16:00 (timing fingerprint; must be worse than T1);
  T3 = mirror — overnight return ≥ the expanding 90th percentile, long put, entry 10:00 (must NOT be
  positive if the mechanism, rather than a symmetric pattern, is at work). Costs 1.0 and 2.0 pts; option leg
  2 % ITM at k × VIX as in D4.
- Windows: CONTEXT 2005-01-01 → 2012-12-31, SELECTION 2013-01-01 → 2020-05-13, HOLDOUT 2020-07-27 → 2026-09-11
  (as A36). SELECTION rows join the trial family (33 + 3 = 36; 37 with A38). The verdict is on the HOLDOUT.
- Scoring: the six-condition survival rule; day-block bootstrap p (n_boot 2000, seed 11), month-block p where
  ≥ 20 months; day-selection control (random non-signal sessions, same entry/exit, 200 seeds); timing control
  (same days, random entry minute 09:31–15:00, 200 seeds); calendar-day Sharpe; DSR at N = 37.
- Kill / promotion rule: T1 is promotable only if it passes all six conditions AND T2 < T1 AND T3 ≤ 0 at 1 pt.
  A positive T1 with a failed fingerprint is reported as "pattern without its mechanism" and never promoted.
  Honest prior LOW-MEDIUM: index-level overnight/intraday reversal is weak; the forced-liquidation timing is
  the only part that could survive 1 pt.

## Amendment A40 — Track B: technical swing-start detector on range bars (owner's request, pre-registered 2026-09-13 12:26 UTC, before any run)

Owner 2026-09-13: two tracks. **Track A** is everything above (mechanism-based 0DTE edges under the prop-account
constraint). **Track B** is a technical-analysis tool: does a "liquidation" of a prior swing extreme (a sweep of
the stops beyond it) mark the START of a swing, either by reversal (price rejects back inside) or by continuation
(price closes through), on range charts? The owner supplied six TradingView exports (`data/ext/tv_samples/`,
manifest inside). Track B is NOT bound to the 0DTE constraint; it is bound to the same statistical guards.

- Data. SPY: range bars REBUILT from the branch's 1-minute SPY (2020-07-27 → 2026-09-11) at $0.34 (the owner's
  34R) and $1.00; the rebuild is gated against the owner's 34R file on their overlap (2025-06-09 → 2026-03-17):
  bars per session within ±15 %, and the 5-minute-resampled close series correlation ≥ 0.999 (gate B-a). XAUUSD:
  the owner's 5000R ($5) file only, unless a longer minute source is found on GitHub (DATA.md); the 2000R file
  (10 days) is context only. TradingView 1-minute/5-minute/1D files are cross-checks, never inputs (the branch
  already carries longer series of each).
- Causal swing level: prior swing high = max(high) over the previous L bars (excluding the current bar); prior
  swing low symmetric. No forward-looking pivot.
- Signals (all bar-close decisions, fill at the next bar's open):
  REVERSAL: high > prior swing high AND close < prior swing high → short; low < prior swing low AND close >
  prior swing low → long. Stop = the sweep extreme; target = R × risk; time stop 50 bars.
  CONTINUATION: close > prior swing high (no sweep-and-reject) → long; close < prior swing low → short.
  Stop = the broken level; target = R × risk; time stop 50 bars. One position per side at a time.
- Family (all counted, none dropped): type {reversal, continuation} × L {10, 20} × R {1, 2} × range
  {SPY $0.34, SPY $1.00, XAUUSD $5} = 24 trials. Costs: SPY 2 bp/side (the contract's ETF budget), XAUUSD
  1 bp/side; results also at 2× cost.
- Train/test lock (the validator skill's one rule): SPY TRAIN 2020-07-27 → 2023-06-30, TEST 2023-07-01 →
  2026-09-11; XAUUSD TRAIN 2025-06-08 → 2025-12-31, TEST 2026-01-01 → 2026-03-18. Decision rule fixed now:
  the SPY winner is the trial with the highest net calendar-day Sharpe on TRAIN with n ≥ 100; it is confirmed
  only if on TEST it passes every survival condition (net > 0 after costs, day-block p < 0.05, BH-FDR at 10 %
  within the 24-trial B family, positive excess over the random-entry control, DSR > 0.95 at N = 24, n ≥ 200).
  XAUUSD is reported under the same rule and labelled UNDERPOWERED where n < 200. Track B's family is FDR-
  controlled on its own (it answers a different question from Track A); both counts are stated in SCORECARD.
- Controls: random-entry control with the same stop/target structure (200 seeds; for a random walk the win
  rate ≈ stop ÷ (stop + target), the mh.sanity check); the actual win rate and net must beat it.
- Deliverable whatever the verdict: `TRACK_B.md` generated from `out/trackB_*.csv` — the 24 rows on TRAIN and
  TEST, the decision, and the pattern table the owner asked for: the conditional distribution of the next
  1/5/20-bar return after a sweep (reversal-shaped and continuation-shaped) versus the unconditional one, by
  instrument, so the "liquidate then reverse or continue" claim is measured even when no trade survives costs.
- Kill: no trial passes on TEST → Track B is killed in PLAN with the pattern table as the finding.

### A40b — gold windows re-registered 2026-09-13 12:32 UTC, before any gold result was computed or read

A GitHub search (fleet agent, WebSearch + verified clones) found Oanda XAU_USD 1-minute bars 2006-03-19 → 2020-05-14
in FutureSharks/financial-data — the same provenance as the SPX500_USD series already used — and nothing else usable
(a 90-day Dukascopy file for 2026-02 → 2026-05 is a different vendor and is not used). The owner's 5000R file is
OANDA:XAUUSD, so the two are the same broker's prices. Gold is therefore re-registered as follows, replacing A40's
gold windows; the Track B coder was instructed to exclude gold from the first run before any gold row existed:
- TRAIN = $5 range bars rebuilt (same rule as SPY, gated by B-a) from Oanda XAU_USD 1-minute 2006-03-19 → 2020-05-14,
  all trading hours; TEST = the owner's `OANDA_XAUUSD_5000R.csv` in full (2025-06-08 → 2026-03-18), never touched
  before the single TEST run. The 8 gold trials (type × L × R at $5) keep their place in the 24-trial family;
  DSR N = 24 unchanged; BH-FDR runs once over all 24 TEST rows when both halves exist.
- Gold decision rule: the gold winner is the trial with the highest net calendar-day Sharpe on TRAIN with n ≥ 100,
  confirmed on TEST under the same six conditions (n ≥ 200 on TEST or UNDERPOWERED). Gold and SPY are decided
  separately (different instruments, same family for FDR).
- Rebuild gate for gold: no overlap exists between the two sources, so the rule is validated on SPY (B-a) and
  gold gets a self-consistency check only: every rebuilt bar's high − low equals $5 and bars per day on the
  TRAIN side are reported next to the owner's file's bars per day (2025–26) as context, not a gate.

### A40c — gate B-a re-registered 2026-09-13 12:49 UTC, before any Track B signal run (the reference file is not a range-bar series)

Gate B-a as written assumed the owner's TradingView 34R export is a faithful $0.34 range-bar series. Measured on the
194 overlap sessions it is not: median 16 bars per session (mean 52) although the session's own high-to-low alone
spans a median 14.6 bars of $0.34 and the 1-minute close path 143; consecutive bars are discontinuous (next open −
close has 5th/95th percentiles of −$1.02/+$1.08, extremes ±$11); several bars share one minute with sub-millisecond
offsets; the per-session bar count correlates only ≈ 0.5 with every volatility measure. TradingView built the export
from 1-minute history with phantom bars and a bar cap. The first rebuild therefore FAILED the gate (median ratio 7.1,
resampled-close correlation 0.99898) for the wrong reason, and no signal was run.
Re-registered gate B-a (replaces the two numeric checks; the signal logic, family, costs, windows, lock and
decision rule of A40/A40b are untouched):
1. every completed rebuilt bar has high − low equal to the range to the cent, and open_{i+1} equals close_i within one
   session (continuity);
2. every session's bar count is ≥ its (high − low) ÷ range (the count can never be below the monotone minimum);
3. the rebuild is deterministic (two runs byte-identical);
4. context, not a gate: bars per session of the rebuild and of the owner's export are both reported with their
   correlation, so the reader sees how far the export is from a true range series.
The owner's 34R and 5000R exports are demoted to context. For gold this means TEST must also be rebuilt from minute
data — none exists after 2020-05 on the branch — so gold TRAIN/TEST become: TRAIN = Oanda XAU_USD 2006-03-19 →
2016-12-31, TEST = 2017-01-01 → 2020-05-14 (rebuilt $5 bars, same rule), decided before any gold row exists.

## Amendment A41 — real 0DTE prices: re-evaluation and model calibration (pre-registered 2026-09-13 15:40 UTC, before any real option bar exists on the branch)

Input: `data/ext/spy_0dte_1min_2024-02_2026-09.csv.gz` (1-minute bars of same-day-expiry SPY contracts within ±3 % of
the 09:30 price; UTC). SPY dollars; 1 SPX point = $0.10.
- Calibration (diagnostic, no decision): for every session and every minute in {09:31, 10:00, 13:00, 15:00, 15:30}, the
  nearest-to-2 %-ITM call and put: real bar close ÷ Black-Scholes premium at k = 1 × prior-close VIX (D4's model with
  k = 1) = the implied k. Report the median and interquartile range of k by VIX tercile and by minute, and the share
  of contracts with no bar in that minute (illiquidity). Output `out/realopt_calibration.csv`. If the median k at
  15:00/15:30 differs from 1.3 by more than 0.3, the playbook's k = 1.3 base case is re-labelled with the measured
  value; the 1.0/1.3/1.6 sensitivity table stays.
- Re-evaluation (the decision): every option leg previously priced by the model on sessions ≥ 2024-02-01 is re-priced
  with real bars — the D4 holdout rows (both pre-registered signals, 2 % ITM), the 15 POST-SELECTION rows, A39 T1/T2/T3 —
  entry = close of the option's 1-minute bar at the entry minute (next bar's open where the entry bar is missing; the
  trade is skipped and counted if neither exists), exit = the 15:59 bar close (SPY 0DTE settle physically at 16:00; the
  15:59 close is the last tradable print), costs: the same 1 and 2 SPX-point round trips ($0.10 / $0.20) on top of the
  bar prices, plus a third row at zero added cost since bar closes already sit inside the spread. Same survival rule,
  same labels; the trial count does not grow (these are re-pricings of counted trials, not new trials). Output
  `out/realopt_reeval.csv`, PLAYBOOK §12.
- Kill / promotion: nothing is promoted on the sub-window alone; a re-priced row that is positive where the model row was
  negative is reported as "model pessimistic here" and the reverse as "model optimistic here". The playbook's first
  paragraph is rewritten to state which numbers are real-priced and from which date.

## Amendment A42 — event-day long volatility on real 0DTE prices (pre-registered 2026-09-13 15:40 UTC, before any real option bar exists)

Question: does a long call plus a long put (two separate long positions; the owner must confirm the account treats them
as two naked longs, not a spread — if not, A42 is reported for the own-account track only) bought before a scheduled
announcement earn more than its premium, i.e. is 0DTE implied volatility too LOW into events? Mechanism: the announcement
forces repricing at a known minute; the counterparty is the 0DTE premium seller.
- Trials (exactly three, all counted; family 36 → 39):
  E1 baseline: every session, nearest-ATM call and put bought at the 09:31 bar close, held to the 15:59 close.
  E2 FOMC: statement days only (14:00 ET), bought at the 13:30 bar close, held to the 15:59 close. FOMC dates are the
  published schedule (2024: Jan 31, Mar 20, May 1, Jun 12, Jul 31, Sep 18, Nov 7, Dec 18; 2025: Jan 29, Mar 19, May 7,
  Jun 18, Jul 30, Sep 17, Oct 29, Dec 10; 2026: Jan 28, Mar 18, Apr 29, Jun 17, Jul 29). n ≈ 20 → UNDERPOWERED by
  construction; reported, never promoted on this sample.
  E3 non-event control: E2's rule on every non-FOMC session (the matched day-selection control, also a trial).
- Scoring: P&L in % of premium and in SPY dollars, costs as A41; day-block bootstrap p; calendar-day Sharpe; DSR at
  N = 39; the six-condition survival rule (E2 fails n ≥ 200 by construction and is reported as UNDERPOWERED).
- Prior LOW for E1 (0DTE premium is on average rich; the baseline is expected negative) and LOW-MEDIUM for E2 minus E3.
- Kill: E2 − E3 ≤ 0, or E1 alone claimed as anything.

### A41/A42 data-layout note (2026-09-13, before any real option bar exists on the branch)
The owner's full fetch (2024-02-01 → 2026-09-11, ≈ 9.5 M bars) exceeds GitHub's 100 MB single-file limit, so the helper writes per-year shards `data/ext/spy_0dte_1min_<year>.csv.gz` with identical columns; the A41/A42 units read one file or the shards. No parameter changes.


### A41 clarification (2026-09-13 17:32 UTC, judge round 7, before the re-run)
"Nearest listed strike … available in the file that day" is read causally: the candidate strikes for a trade are the contracts
with at least one printed bar at or before the entry minute on that session, never a contract whose first print comes later.
The entry bar actually used must precede the exit bar actually used; otherwise the trade is skipped and counted in
n_skipped_missing. The used entry-bar minute is written to the per-trade file so both rules are auditable. No other parameter
changes; the judge showed the P&L effect is small and adverse (the honest direction).

## Amendment A43 — Track C: defined-risk short 0DTE premium (owner's option E, pre-registered 2026-09-14 14:57 UTC, before any run)

Owner 2026-09-14: "for E I don't have my own options account I think. But you can test it and strategize it too; if it is
profitable I can get one." This track is for a stock account with options approval for defined-risk spreads, NOT the prop
account; it is reported under its own heading and never enters the prop-account playbook. Reference class: the tail
statistics a risk desk demands before allowing a short-premium book — worst day, worst month, full-loss frequency,
intraday adverse excursion — not the mean. Everything below is fixed now.

- Data: the owner's real SPY 0DTE 1-minute bars (2024-02-01 → 2026-09-11) as one out-of-sample window; no parameter is
  fitted anywhere; results are also shown by calendar year and by prior-close VIX tercile (descriptive only).
- Structures (three trials, family 39 → 42), all four legs are SPY same-day-expiry contracts:
  S1 iron butterfly at 09:31: sell the nearest-ATM call and put, buy the call at +1 % and the put at −1 % of the 09:31
     SPY price (nearest listed strikes); hold to the 15:59 bar and close all four legs there.
  S2 the same structure sold at 13:30.
  S3 iron condor at 09:31: sell the call at +0.5 % and the put at −0.5 %, buy the wings at +1.5 % and −1.5 %; close at 15:59.
- Prices: a leg's entry price is its bar close at the entry minute, else the next print within 5 minutes; exit is the 15:59
  bar close, else the last print within the previous 10 minutes; a structure with any leg missing is skipped and counted.
  Every leg must have printed at or before the entry minute (causal). Costs: $0.10 per leg round trip ($0.40 per
  structure), also at $0.20 per leg.
- Defined risk: max loss = wing width − net credit (per share × 100 per contract), known at entry. Sizing rule for the
  equity curve: contracts = floor(4 % of a $100,000 account ÷ max loss), so the worst possible day is the daily limit.
- Scoring, per trial: n, n_skipped, win rate, mean and median net P&L per structure in $ and in % of max loss, worst
  structure, worst day, worst month, 5th-percentile day, full-loss frequency (P&L ≤ −90 % of max loss), intraday MAE
  (the worst minute-by-minute mark of the four legs' bar closes, in % of credit and of max loss) and the share of days
  whose MAE exceeds 100 % and 200 % of the credit; calendar-day Sharpe at the sizing rule; maximum drawdown of that
  equity curve; day-block bootstrap p (n_boot 2000, seed 11); DSR at N = 42; the six-condition survival rule.
- Promotion rule (stricter than the survival rule, because the tail is the risk): a trial is promotable only if it passes
  all six conditions AND its equity curve's maximum drawdown at the sizing rule is under 20 % AND the worst month is
  better than −10 % AND the day-block p of the mean is < 0.01. Otherwise it is reported with the tail table and the
  label that applies.
- Non-goals: intraday adjustments, stops, delta hedging, VIX or event conditioning (each would be a new family), SPX or
  XSP contracts (no bars on the branch), any claim for the prop account.
- Honest prior: the mean is HIGH (buyers lost 7 % of premium at 09:31 and 17 % at 13:30 on average); the tail is
  unknown and is the whole question; the window contains the August 2024 volatility spike and the April 2025 crash.

## Amendment A44 — forward test of the overnight-gap trade (owner's option B, passive, pre-registered 2026-09-14 14:57 UTC)

Symmetric spec, fixed now, judged only on sessions after 2026-09-11 as data accrues (the owner refreshes the minute
file; nothing runs on existing data): overnight return ≤ expanding 10th percentile → long 2 % ITM call at the 10:00 bar
close; ≥ expanding 90th percentile → long 2 % ITM put at 10:00; exit at the 16:00 close; costs 1 and 2 pts; the six
conditions with n ≥ 200 before any verdict (≈ two years). Counted as one trial when it first runs (family 43).

## Amendment A45 — the owner's trading rulebook (owner's option F, adopted 2026-09-15)

The owner adopted the "stop doing" list in `INVERSION.md` §4. It is recorded here as a contract, not a
finding. Rules 2, 3, 6, 8 are already in force in this programme; rules 1, 4, 5, 7 are new. Rule 1 is an
amendment to the per-trade sizing in the numeric budgets (`ACCEPTANCE.md:108-112`) and is named as such.

1. **Per-trade risk and attempts cap (AMENDS the numeric budget).** The budget's rule (daily loss limit ÷
   worst-trade loss in % of premium, floor 100 %) implies x = 4 % of account per trade at the 4 % base limit,
   i.e. N = floor(D/x) = 1 full-loss attempt per day. From now on, for forward trading and for every sizing
   table published after this amendment, x = 1 % of account equity per trade, giving N = 4 attempts at the 4 %
   base limit (N = 3 at 3 %, N = 5 at 5 %). Sizing tables already published under the prior convention (D4 in
   `PLAYBOOK_0DTE.md`, A43 in `TRACK_C.md`) are NOT restated; they remain labelled under the rule in force when
   they were computed. Evidence: `U2` §3 Rule 1 arithmetic, `U2-S28` (Kelly, variance drag).
2. **No entries in the first 30 minutes** (no entry before 10:00 ET). NEW for the prop account: A39 T1 and A44
   enter at 10:00, but A42 E1 (`SCORECARD.md:78`) and A43 S1/S3 (`SCORECARD.md:85,87`) entered at 09:31, and
   A39's own 09:31 fingerprint T2 was weaker than T1 (`SCORECARD.md:54` vs `:53`). Evidence: `U2-S27`.
3. **ITM-only strikes; no ATM or OTM contracts.** Already codified as a non-goal (`ACCEPTANCE.md:118`);
   ATM −53 %/trade at 17 % win, OTM median −50.6 % (`research/CLAUDE.md:59`).
4. **No increase in size or trade frequency after a loss.** NEW. Evidence: `U2-S29` (SURVEY-grade).
5. **Resting limit orders at the mid, not marketable orders.** NEW and NOT measurable inside this pipeline: the
   0DTE shards carry trade prints only, no quotes, and "no live or paper execution" is a codified non-goal
   (`ACCEPTANCE.md:118-119`). No slippage-versus-mid number may be reported until that non-goal is relaxed by
   its own amendment. Evidence: `U1-S5`, `U2-S01`, `U2-S07`.
6. **Every rule and candidate is pre-registered and counted in the trial family before any run.** Already in
   force (survival-rule condition 3, `ACCEPTANCE.md:58`; trial definition A31, `ACCEPTANCE.md:162`).
7. **No trade taken only to satisfy a consistency or minimum-days rule.** NEW. Evidence: `U2` §3 Rules 3 and 5.
8. **Unaudited prop-firm statistics are never used as facts.** Already in force. The figures `U2` §5 marks
   UNVERIFIED ("5-10 % pass", "95 % fail", FTMO's "99.8 %") are not used to size or gate anything.

Measurement: rules 2, 3, 6, 8 are checkable by the pipeline and by A44 (entry time, strike moneyness, family
inclusion, source tags). Rules 1, 4, 5, 7 govern the owner's own discretionary trading and can only be audited
in an owner-kept journal outside this repository (`INVERSION.md` §4 preamble). Every candidate registered from
now on must comply with rules 2 and 3 at registration time.

## Amendment A46 — intraday forced-flattening rebound (owner's option G, pre-registered 2026-09-15, before any run)

The only candidate that survived the five-part screen in `INVERSION.md` §5. One hypothesis with a mechanism
fingerprint, not a search; every parameter below is fixed before the first run.

- **Mechanism (who must trade, when).** Accounts under daily loss limits and margin calls are forced to flatten
  longs after a large morning decline; the forced selling pushes price further down and then exhausts, so the
  mechanism predicts (i) a positive drift from late morning to the close on those days, (ii) a LARGER drift from
  11:00 than from 09:45 (the liquidation window is still running at 09:45), and (iii) NO mirror effect after a
  large morning RISE (no forced buyer). This is the intraday analogue of A39's overnight version and shares its
  template; it is a distinct trial on a disjoint trigger (current session's open→11:00 move, not the prior
  session's close→open gap).
- **Signal day.** Open→11:00 return (09:30 bar open → 11:00 bar close) ≤ the expanding 10th percentile of the
  same measure over all PRIOR sessions, minimum 250 prior sessions, no fitted parameter. The 250-session warm-up
  matches A39 (`ACCEPTANCE.md:254`) rather than the A29 floor of 20 (`ACCEPTANCE.md:160`): at 20 the 10th
  percentile is a 2-of-20 order statistic, and since n falls short of the 200 floor under BOTH warm-ups
  (≈128 at 250, ≈151 at 20) the choice cannot be made to buy power. The 20-session variant is reported as a
  pre-registered reporting cut (A31), never as a second trial.
- **Trials (exactly three, all counted).** U1 = long 2 % ITM call, entry at the 11:00 bar close, exit at the
  16:00 session close (the hypothesis). U2 = same, entry at the 09:45 bar close (timing fingerprint; must be
  worse than U1). U3 = mirror — open→11:00 return ≥ the expanding 90th percentile, long 2 % ITM put, entry
  11:00, exit 16:00 (must NOT be positive if a mechanism rather than a symmetric pattern is at work).
  Costs 1.0 and 2.0 pts; option leg priced at k × VIX as in D4.
- **Windows.** SELECTION 2013-01-01 → 2020-05-13 (Oanda). HOLDOUT 2020-07-27 → 2026-09-11 (the owner's minute
  feed). The verdict is on the HOLDOUT. A real-priced re-evaluation on the 0DTE shards (2024-02-01 →
  2026-09-11, ≈630-650 sessions) is reported as a sub-window check under the A41 convention, not as a verdict
  and not as a new trial.
- **Scoring.** The six-condition survival rule; day-block bootstrap p (n_boot 2000, seed 11), month-block p
  where ≥ 20 months; day-selection control (random non-signal sessions, same entry/exit, 200 seeds); timing
  control (random entry minute 09:31-15:00, 200 seeds); calendar-day Sharpe; DSR at N = 45.
- **Family.** Three trials join the Track-A family: 42 → 45 now, or 43 → 46 if A44 runs first.
- **Compliance with A45.** Entry 11:00 satisfies rule 2 (no entry before 10:00); 2 % ITM satisfies rule 3; the
  sizing table for this candidate is computed under A45 rule 1 (x = 1 %, N = 4 at the 4 % limit).
- **Kill / promotion rule.** U1 is promotable only if it passes all six conditions AND U2 < U1 AND U3 ≤ 0 at
  1 pt. A positive U1 with a failed fingerprint is reported as "pattern without its mechanism" and never
  promoted — the outcome A39 itself had when its mirror T3 came back positive (`ASSESSMENT.md:74-83`).
- **Honest prior: LOW.** No source in `notes/inversion/` quantifies prop-firm or margin-call-driven forced
  selling at index level; the mechanism is analogical, the 11:00 entry time has no cited evidence behind it
  (09:45 is its only timing test), and A39's mirror already failed for the closely related overnight version.
  n ≈ 128 modelled on the holdout means the expected label is UNDERPOWERED, not a verdict.

### A46a clarification (2026-09-15, minutes after A46, before any code exists and before any result is computed)

Reviewing A46 against the unit it will copy, the registered timing fingerprint is defective and is replaced
here, before a single number has been produced.

- **The defect.** A39's fingerprint compared a 09:31 entry with a 10:00 entry on a signal that was complete at
  09:30, so both entries were causal. A46's gate does not complete until the 11:00 bar closes, so the
  registered U2 (entry 09:45) could not be traded on that signal at all: it would be look-ahead, not a weaker
  entry. No causal "earlier entry" fingerprint exists for this gate.
- **The replacement (dose-response, causal).** U2 becomes the mild-decline band: open→11:00 return at or below
  the expanding 30th percentile but ABOVE the expanding 10th percentile, long 2 % ITM call at the 11:00 bar
  close, exit at the 16:00 close. The mechanism claims forced flattening happens on EXTREME mornings, so a
  milder decline must show a weaker effect. Prediction: U1 > U2. Everything else in A46 is unchanged, including
  U1, U3, the windows, the controls, the costs, the 250-session warm-up and the kill rule (which now reads:
  U1 promotable only if it passes all six conditions AND U2 < U1 AND U3 ≤ 0 at 1 pt).
- Still exactly three trials; family 42 → 45; DSR at N = 45. The bands are disjoint, so a session feeds at most
  one of U1, U2, U3.

## Amendment A47 — the detectability floor (pre-registered 2026-09-15, before any code; ZERO new trials)

This is an ANALYSIS of measurements already published, not a test. It computes no new signal, opens no new
window, fits no parameter and can promote nothing. It adds **zero** trials: the family stays at 45 and every
published p-value, BH-FDR decision and DSR is untouched. It is registered here only because the Crucible
protocol requires anything that will be reported to be specified before it is run.

**The question.** Every result in this programme has been judged against the six-condition survival rule, whose
condition 6 is a floor of n ≥ 200 holdout trades. That floor has never been checked against the per-trade
dispersion actually observed. So the programme has never stated what size of effect its own design is CAPABLE
of detecting. Without that number, "UNDERPOWERED" is a label rather than a quantity, and the owner cannot tell
whether option B (forward-test A44 to n = 200) is a two-year path to an answer or a path to the same label.

**What is computed**, for each candidate that already has a published per-trade series, on its published window:
1. n, mean and standard deviation of net index points per trade, and the standard error and t. (All already
   published or directly derivable; nothing is re-fitted.)
2. The minimum detectable effect at the observed n and at the survival rule's n = 200 floor, one-sided at
   α = 0.05 with 80 % power: `MDE = (z_0.95 + z_0.80) × sd / sqrt(n)`.
3. The n required to detect a 1.0-point and a 2.0-point per-trade edge at the same α and power — the two cost
   levels every result in this programme is already reported at (`ACCEPTANCE.md:104-106`).
4. Signals per year on the published window, hence the YEARS required to reach each n above.
5. The MDE expressed as a percentage of premium, where premium = the 2 %-ITM contract cost in index points at
   the measured level in `out/sizing_forward.csv` (A45/§15), so it is comparable to the percent-of-premium
   figures A41/A42/A43 report.

**Assumptions, stated before the run.** Independent and identically distributed per-trade returns within a
candidate (the same assumption the normal-approximation MDE formula carries; the programme's own p-values come
from a day-block bootstrap precisely because that assumption is imperfect, so every MDE here is a LOWER bound on
what is truly required — clustering inflates it). Normal approximation for the MDE. No adjustment for
multiplicity: these are per-candidate detectability figures, not test statistics.

**What would make this analysis wrong, stated before the run.** If the observed per-trade standard deviations
are small enough that the n = 200 floor detects effects at or below the 1-2 point cost band, then the survival
rule is adequately powered, the UNDERPOWERED labels reflect a genuine shortage of signals rather than a design
limit, and option B is worth running. That is the outcome that would REFUTE the concern motivating this
amendment, and it will be reported as such if it is what the numbers say.

**Reporting.** `out/power_analysis.csv` (generated), a new `PLAYBOOK_0DTE.md` §16 appended at the end (no line
at or before playbook line 125 moves), and a narrative section in `ASSESSMENT.md`. Every number generated, none
typed. Labelled throughout as an analysis of existing measurements, never as a trial or a result.

### A47a correction (2026-09-15, after the first A47 run, before any corrected number is published)

A fresh-context adversarial review found two errors in A47 as registered and as first run. Both are recorded
here rather than by editing A47 (this file is append-only). Neither adds a trial; the family stays at 45.

**1. Scope error — the FVG family was silently omitted, and including it INVERTS the headline.** A47 scoped
itself to "each candidate that already has a published per-trade series". `out/fvg_candidates_trades.csv` (A36,
8 trials, 24 window/trial groups) carries a `pts` column on the same `COST1 = 1.0` convention every other series
uses, and its group means reproduce the published `net_pts_cost1` in `out/fvg_candidates.csv` to six decimals
(verified). It qualifies on every clause and was excluded by an implementation defect, not by a scope decision.
`pipeline/units/power.py` additionally asserted in a docstring that no such candidate existed, which was false.
Restoring it moves the headline statistics AGAINST A47's first conclusion — the direction a correctness fix
should move:

| statistic | as first published (37 rows) | corrected (61 rows) |
|---|---|---|
| best MDE at n = 200 | 1.68 pts | 0.22 pts |
| median | 4.16 pts | 2.80 pts |
| rows with MDE ≤ 2.0 pts | 1 of 37 | 25 of 61 |
| HOLDOUT rows with MDE ≤ 2.0 pts | 0 of 8 | 8 of 16 |

**A47's pre-registered refutation condition is therefore MET for one family and NOT met for the others, and it
is reported as such.** The corrected finding is two-sided and narrower than the first one: for hold-to-close,
one-trade-per-day, option-style candidates the n = 200 floor cannot resolve a 1-2 point effect (0 of 8 holdout
rows); for the intraday stop/target family it can, with holdout MDE 0.78-1.27 pts INSIDE the cost band and
actual holdout n of 282-959 already past the floor — so for that family the design did resolve the question and
the answer was flat to negative (-0.004 to -1.14 pts/trade). Any claim that "the n = 200 floor cannot resolve
the effects this programme is looking for" is withdrawn as overstated.

**2. The i.i.d./clustering assumption's stated DIRECTION is withdrawn as unsupported.** A47's Assumptions
paragraph asserted that because the programme's p-values come from a day-block bootstrap, "every MDE here is a
LOWER bound on what is truly required — clustering inflates it". The review probed this and falsified it for the
data in the table: every series feeding the first run is one trade per day, so each day block is a singleton and
the day-block bootstrap degenerates to an i.i.d. bootstrap over trades; there is no within-day clustering to
inflate anything. Measured across-day dependence runs the other way — lag-1 autocorrelation is negative in 22 of
37 groups and a Newey-West variance-inflation factor over lags 1-5 is below 1.0 in 25 of 37 (median 0.89), so
for most rows the true required n is slightly SMALLER than the i.i.d. figure, not larger. Magnitude is about
±5 % on MDE and does not move any conclusion. The claim is replaced by the measured statement: dependence is
weak and mostly mildly negative, so the i.i.d. MDE is a good approximation and not a bound in either direction.
(The FVG family restored under correction 1 does carry up to 4 trades per day, so its rows — and only its rows —
are the ones where a clustering adjustment could matter; this is stated, not corrected for, and no FVG
conclusion rests on a margin smaller than that.)

**3. Reporting discipline reasserted.** A47 required "every number generated, none typed". The first write-up
breached this with a hand-typed window-mean standard deviation that was 12 % wrong and three hand-typed
holding-hours correlations that do not reproduce (their duration map mis-stated A46a's U2 entry as 09:45 when
A46a moved it to 11:00). All four are withdrawn. Any window-level or duration-level statement republished must
come from a generated column or not appear.

### A47b correction (2026-09-16) — two typed figures in A47a were themselves wrong

A47a was written to correct A47 for, among other things, publishing hand-typed numbers in breach of its own
"every number generated, none typed" rule. A47a then did the same thing twice. Both are corrected here, and the
generated CSV is authoritative over any prose in this file.

1. **The FVG holdout mean range.** A47a's prose gives it as "-0.004 to -1.14 pts/trade". The true range across
   all 8 FVG HOLDOUT groups is **-1.1434 to +0.0263** (`out/power_analysis.csv`): the upper end is slightly
   POSITIVE, not slightly negative. The -0.004 figure is one particular group (`short|R1|bos_on`), not the
   maximum. The qualitative reading is unchanged — the largest positive is +0.026 pts/trade against a 1.0-2.0 pt
   cost, i.e. indistinguishable from zero and far below cost — but "flat to negative" must not be stated as if
   every group were negative. `PLAYBOOK_0DTE.md` §16 reports the generated range and is correct.
2. **"Inside the 1-2 point cost band."** The FVG holdout MDE range is 0.78-1.27 pts, whose lower end is BELOW
   the band, not inside it. The accurate phrasing is "at or below the 1-2 point cost band". Being below it means
   MORE power, not less, so the conclusion is unaffected; the wording is corrected wherever it is republished.

Recorded for the ledger, since this is the third instance in this programme of a claim outran its evidence and
the second inside a single amendment chain (`RETRO.md`).

**One figure worth adding to the record, generated not typed** (`out/power_analysis.csv`): A39's gapliq family
has POSITIVE holdout means (+0.117 to +2.202 pts/trade, including T1's published +2.20 at n 158) against a
detection threshold at the n = 200 floor of 7.96-8.94 pts. So T1's positive result sits roughly a quarter of the
way to what this design could distinguish from zero. That is the quantitative content of its UNDERPOWERED label,
which until now was only a word.

## Amendment A48 — does a bounded exit make these questions answerable? (pre-registered 2026-09-16, before any code; ZERO new trials)

A47 established that the four hold-to-close, one-trade-per-day families cannot resolve a 1-2 point effect at the
survival rule's n = 200 floor (holdout MDE 3.85-8.94 pts/trade), while the one bounded-exit family can
(0.78-1.27 pts at n 282-959). The difference is per-trade dispersion: 4.4-7.2 pts against 21.9-50.9. That is a
DESIGN property, not a market property, and it gates every remaining option on this branch — including option B,
whose four-year price A47 just established.

**The question.** For each already-registered hold-to-close candidate, what would its per-trade DISPERSION be
under a bounded exit, and would the resulting detectability bring its minimum detectable effect at or below the
1-2 point cost band? If yes, questions currently answerable only after ~4 years of new signals become answerable
on data already on the branch. If no, those questions are unanswerable here and option A is the honest end.

**This is an analysis, not a test, and the distinction is enforced in code.** It adds ZERO trials; the family
stays at 45. The unit computes and emits DISPERSION ONLY: standard deviation of per-trade net points, the
implied MDE at the observed n and at n = 200, and the trade count. It MUST NOT compute, emit, log or report a
mean, a win rate, a Sharpe, a p-value, a cumulative P&L or any other location or profitability statistic, for
any candidate or exit rule. `pipeline/units/test_bexit.py` must assert that the output carries no such column
and that no such quantity is computed anywhere in the module. The reason is explicit: every candidate here has a
KNOWN holdout result, so computing profitability under a new exit rule and then choosing among the results would
be a re-tune on the holdout, which the contract forbids (`BLOCKED.md`, "promoting any of them is a re-tune on
the holdout"). Dispersion is chosen because it is a second moment: it does not identify which exit rule PAYS,
only which makes a question ANSWERABLE.

**Scope — every hold-to-close registered candidate, no cherry-picking.** All 8: A39's T1/T2/T3 (`gapliq`),
A46's U1/U2/U3 (`flatten`), and the two pre-registered signals (D1's `15:00|both|vixmove_exp`, Thread A's
`13:00|call|gap>0.3%`). Selecting a subset would be selection on A47's own published means and is forbidden.
Windows as already registered for each candidate; the HOLDOUT figures are the ones that matter.

**Exit grid, fixed now.** Stop and target placed symmetrically at m × the session's opening-range ATR proxy
already used by `pipeline/execution.py`, for m in {0.5, 1.0, 1.5, 2.0}, plus a fixed-points variant at
{5, 10, 20} index points, each evaluated against the minute path between the registered entry and the
registered exit; whichever triggers first ends the trade, otherwise the registered exit stands. Costs 1.0 and
2.0 pts as always. No other parameter, and the grid is not extended after seeing results.

**The answer condition, stated before the run.** For a candidate/exit pair, the question becomes ANSWERABLE if
its MDE at that candidate's OBSERVED holdout n falls at or below 2.0 index points. Report, per candidate, the
best (smallest) MDE over the grid and whether any grid point clears 2.0. Aggregate verdict: if NO candidate has
any grid point clearing 2.0, bounded exits do not rescue detectability on this branch and that is reported as
the finding, reinforcing option A. If SOME do, the finding is that those specific questions could be made
answerable, and the owner may then choose to authorise the corresponding trials — which would be a SEPARATE
pre-registration with its own trial count and family FDR, never this one.

**Honest prior: MIXED.** The bounded-exit family's low dispersion comes partly from tight stops on a small
reference box; a stop placed on a full-session directional signal will not shrink dispersion as far. A stop at
±10 pts caps per-trade outcomes near 10 pts, implying MDE ≈ 2.0 at n = 158 — marginal, on the boundary of the
answer condition. The plausible outcome is that some candidates clear and some do not, which is why the verdict
is reported per candidate and not as a single yes.

**What would make this analysis worthless, stated before the run.** If a bounded exit shrinks dispersion only by
truncating the same distribution without raising the number of independent observations, the MDE gain is real
but the economic question changes underneath it: a stopped-out trade is a different trade. This analysis
therefore licenses NOTHING about profitability and its write-up must say so. It answers only whether a
measurement could be made, never whether it would come out positive.

**Reporting.** `out/bexit_detectability.csv`, a `PLAYBOOK_0DTE.md` §17 appended at the end (nothing at or before
playbook line 125 moves), and a narrative in `ASSESSMENT.md`. Every number generated, none typed — and per
A47b, any withdrawn figure may be replaced only by a named generated column.
