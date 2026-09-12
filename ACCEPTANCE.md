# ACCEPTANCE.md — definition of done, survival rule, budgets, non-goals, assumptions

Written in Phase 0 (2026-09-12). Amended only deliberately; every amendment is logged in
CHANGELOG.md.

## The constraint that governs everything

The prop account permits ONLY 0DTE options, long-only, naked calls or puts. No selling,
no spreads, no futures, no shares, no overnight holds. Daily loss limit 3–5% (base case
4%). Every deliverable must be tradeable under it. The own-account track (stock account
with options approval) is secondary.

## Reference class

López de Prado's backtesting standards (deflated Sharpe ratio with the trial count,
purged/embargoed CV wherever a parameter is chosen, multiple-testing awareness) AND the
two threads' own guards: `research/thread_B_inversion/stats_engine.py` (day-block
bootstrap + Benjamini-Hochberg FDR) and Thread A's matched random-entry control and
n_eff correlation adjustment. A result that would not survive both is not a result.
Written deliverables must stand next to `research/thread_B_inversion/SYSTEM_SPEC.md`:
every number names the script and the `out/` file it came from.

## Definition of done

| # | Statement | Evidence file |
|---|---|---|
| D1 | One reconciled last-hour momentum specification, chosen by the fixed decision rule below from the 8-candidate set, scored on identical data with stats_engine.py | `out/reconcile_candidates.csv`, `out/reconcile_decision.md` |
| D2 | The reconciled spec and Thread A's gap-up call each evaluated on the 2020-06-01→2026-09-11 holdout with thresholds frozen through 2020-05-29, reported by calendar year (2020 H2, 2021 … 2026 YTD): trades, win rate, mean net return per trade at 1.0 and 2.0 pt, worst trade, worst day, block-bootstrap p | `out/holdout_by_year.csv` |
| D3 | Thread B's execution model (resting limit at 0.25/0.50/1.00 ATR, per-signal metric, unfilled = 0, commission-only cost on fills, fill window bounded by time to close) applied to every surviving signal, improvement vs market entry with bootstrap p | `out/execution.csv` |
| D4 | `PLAYBOOK_0DTE.md` with every number measured on the extended data and priced with Black-Scholes at IV = k × prior-close VIX, k = 1.3 base, full sensitivity at k ∈ {1.0, 1.3, 1.6} × spread ∈ {1.0, 2.0} pt; strike 2% ITM; first paragraph states that real 0DTE quotes were unavailable and k×VIX is a model | `out/playbook_*.csv` |
| D5 | The 8-sleeve unconstrained portfolio re-measured through 2026-09 in `OWN_ACCOUNT.md`, by year and regime, Feb 2018 and 2020 in sample for the vol sleeves, S13 weight cap stated and applied, VXX/VXZ splice documented | `out/own_account_*.csv` |
| D6 | Every configuration tested is counted in `SCORECARD.md`; every pooled statistic date-clustered; every cross-instrument statistic correlation-adjusted; every claimed edge has a random-entry control, a block-bootstrap p and a deflated Sharpe | `SCORECARD.md`, `out/trials.csv` |
| D7 | `make all` regenerates every table in both playbooks from `data/raw` + `data/ext`; two consecutive runs yield byte-identical `out/`; playbook tables are generated, never typed | `make all && make repeat` |

## Survival rule

A signal SURVIVES the holdout only if ALL hold. Otherwise it is reported with its p-value
and the label that applies (FAILED / UNDERPOWERED / COST-KILLED).

1. Net mean > 0 at 1.0 index point round-trip.
2. Block-bootstrap one-sided p < 0.05 via `stats_engine.block_bootstrap_p`, n_boot = 2000,
   seed 11; blocks = trading day for pooled intraday statistics, calendar month for
   one-observation-per-day series (what `step17_intramom.py:75` already does).
3. Passes Benjamini-Hochberg FDR at 10% across every configuration tested in this run.
4. Positive excess over its matched random-entry control (same days, same hold window,
   random entry minute, 200 draws).
5. Deflated Sharpe ratio > 0.95 (Bailey & López de Prado 2014) with N = the number of
   trials in this run (tracked in SCORECARD.md).
6. At least 200 holdout trades. Below that: report the p-value and label UNDERPOWERED.

## Decision rule for D1 (fixed before any run)

Candidate set (8 trials): {entry 15:00, 15:30} × {put-only, both directions} ×
{magnitude gate: |open→entry| above the expanding-window 70th percentile of prior
sessions; VIX-and-move gate: prior-close VIX > 17.06 AND |prior close→entry| > 0.665%}.
Thread A's spec is (15:00, put-only, magnitude). Thread B's is (15:30, both, VIX-and-move).
Winner = highest net Sharpe at 1.0 pt on 2013-01-01→2020-05-29 (the window where both
threads' tests overlap) that is ALSO positive with block-bootstrap p < 0.10 on the
2020-06-01→2026-09-11 holdout. Ties within 0.10 Sharpe go to the candidate with fewer
parameters. Thresholds are never re-fitted on any data after 2020-05-29.

## Numeric budgets (measured, never estimated)

- Costs: 0DTE options 0.5–2.0 index points round-trip, shown at 1.0 and 2.0 (half on
  entry, half on exit); ES 0.33–0.50 pts; ETFs 2 bp/side; single stocks 5 bp/side.
- Any Sharpe above 3.0 on price-only data triggers a mandatory bug hunt before it is
  reported.
- Position size is set by the worst single day against the daily loss limit, not by
  Sharpe. Loss at stop ≈ 54% of premium for ITM 0DTE. Base 4% limit; 3% and 5% shown.
- Bootstrap: n_boot 2000; hardware 4 cores / 15 GB; fleet ≤ 3 concurrent units.

## Non-goals

No new pattern search over 2005–2020; no conditioning / regime-switching / clever
weighting on top of the portfolio; no inversion; no ATM or OTM 0DTE on a directional
signal; no UI; no live or paper execution; no GEX / dealer-positioning filters (no
positioning data obtainable); no real 0DTE quotes (unobtainable — k×VIX is the model);
no cross-market validation after 2018 (no DAX/EuroStoxx minute data obtainable); no change
to the prop-account constraint; no edits to files under `research/` (copy, then change).

## Assumptions (recorded, not asked)

| # | Assumption | Why |
|---|---|---|
| A1 | Holdout = 2020-06-01 → 2026-09-11; thresholds frozen through 2020-05-29 | In-sample minute data (Oanda SPX500_USD) ends 2020-05-29, not 2020-12-31 |
| A2 | Bundle lives verbatim at `research/` (so `research/CLAUDE.md`, `research/thread_A_multisleeve/`, `research/thread_B_inversion/`) | Zip layout kept; only the top-level folder name changed |
| A3 | "Identical data" for D1 = Oanda SPX500_USD 2005-01→2020-05 (UTC) + `data/ext` minute file from 2020-06; histdata 2010–2018 is a cross-feed check only | Oanda is the one feed both threads used (A throughout; B for its 2019–20 holdout) |
| A4 | Sessions: tz-aware America/New_York, 09:30–16:00, sessions with < 300 bars dropped and listed | Both threads' rule (`mh.py:17`, `step17_intramom.py:63`) |
| A5 | Timestamp conventions: Oanda = UTC (verified 2018-07-08 22:00 first bar); histdata = Eastern with DST (verified Sunday open 18:01 in Jan and Jul 2018) | Direct inspection of the files |
| A6 | If `data/ext` minute file is SPY: prior close adjusted by dividend on ex-dates; 1 SPX point = $0.10 SPY; instrument detected from price level | SPY ex-div gaps (~0.35%) would leak into "prior close→15:30" |
| A7 | Option pricing: Black-Scholes, r = 0, IV = k × prior-close VIX, k base 1.3; T = minutes to 16:00 / (365×24×60) | Thread B `step15_odte.py:76`; both threads called VIX-as-IV generous |
| A8 | 2% ITM: K = S_entry × 0.98 for calls, × 1.02 for puts, rounded to the nearest 5 SPX points | Thread A `it21.py:33` moneyness convention; SPX strike grid |
| A9 | Thread A it22 magnitude threshold: expanding-window 70th percentile of |open→15:00| over all prior sessions; put on down days only | `ASSESSMENT_iteration22_0DTE_NATIVE.md:57-59` |
| A10 | Thread A gap-up signal: (open / prior close − 1) > 0.3%; entry at the 13:00 bar open; 2% ITM call; hold to close | `HANDOFF.md:161`, `ZERO_DTE_PLAYBOOK.md:79-83` |
| A11 | Thread B price_1530 = last close in [15:25, 15:30]; prev_close = last RTH close; VIX prior close = previous trading day's CLOSE | `step17_intramom.py:51-58,97` |
| A12 | Thread A scripts it14, it17–it20, it22 are absent; specs re-implemented from ASSESSMENT text and must reproduce headline numbers before use | Bundle inventory |
| A13 | VXX/VXZ: Kaggle-mirror series to 2017-11-10 spliced to the post-2018 ETNs on the overlap; splice proven by return correlation; gap days reported | VXX/VXZ were relaunched in January 2018 |
| A14 | Own-account VRP sleeve: measured as VIX − realised vol through 2026 (Thread B step11 method), labelled not-tradeable-as-measured | No option prices obtainable |
| A15 | Deflated Sharpe uses the full-run trial count N and the return series' skew and kurtosis | Bailey & López de Prado 2014 |
| A16 | Random-entry control: same calendar days as the signal, random entry minute within the same window, same exit, 200 draws, excess = signal mean − control mean | Thread A methodology §7 |
| A17 | "Worst day" and "worst year" in the playbook are at the base sizing (4% limit, 54% loss-at-stop) in % of account | Mission sizing rule |
| A18 | Commit and push at the end of every phase and tribunal round to `claude/modest-pasteur-oyzqyh` | Ephemeral container |
