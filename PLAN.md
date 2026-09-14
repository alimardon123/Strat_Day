# PLAN.md — ranked task list (living; updated at the end of every iteration)

Source ranking: `research/CLAUDE.md` §6, re-ordered by risk (hardest first) per Phase 3.

| Rank | Task | Phase | Owner | What would kill it |
|---|---|---|---|---|
| 1 | Harness: session builder for every feed (UTC / Eastern-DST → America/New_York), DST probe, calendar reconciliation, reproduction gates (step17 table; re-implemented it22 numbers; `mh.sanity()`; observability clock), run-twice reproducibility | 2 | single owner | A reproduction gate that cannot be met within tolerance → ESCALATE (spec or data differs from the threads') |
| 2 | Fetch pre-2020-06 data from the four GitHub sources into `data/raw/` with a manifest | 2 | fleet (one unit per source) | Proxy blocks a source that answered `ls-remote` in Phase 0 → DATA.md, stop |
| 3 | Reconcile the momentum spec: 16 configurations (12 rankable), ranked on 2013-01→2020-05-13 by calendar-day Sharpe, ONE pre-registered holdout test (ACCEPTANCE "Decision rule for D1" v2) | 3 | single owner | Top-ranked configuration fails the survival rule on the holdout → "no reconciled specification survives" is the D1 outcome; the other 15 rows are published POST-SELECTION |
| 4 | Holdout by year for the reconciled spec and the gap-up call, thresholds frozen | 3 | fleet (one unit per year) | `data/ext` minute file absent → stop after Phase 2 |
| 5 | Execution model (step8 method) on every surviving signal | 3 | single owner | No survivor → apply to the reconciled winner for information, labelled |
| 6 | 0DTE pricing and sizing: BS at k×VIX, k ∈ {1.0,1.3,1.6} × spread ∈ {1.0,2.0}, worst day/year at 3/4/5% limits | 3 | single owner | Any Sharpe > 3 → bug hunt before reporting |
| 7 | Own-account: 8 sleeves through 2026-09, VXX/VXZ bridge, S13 cap, VIX−RV extension — baseline and partial extension DONE inline; ETF-dependent sleeves wait for data/ext | 3 | single owner (fleet unavailable) | ETF panel absent → S2/S3/S6/S13 stop at 2017-11-10 |
| 8 | D2b: cross-market check of the gap-up call on DAX/EuroStoxx 2010–2018 (histdata) | 3 | fleet (one unit per market) | Effect shrinks > 50% or flips sign → recorded as a finding, not a kill of D2 |
| 7b | D5 addendum: VIX − realised vol through 2026-09 (Thread B step11 method), labelled not-tradeable-as-measured; the defined-risk VRP sleeve with real option prices is a recorded non-goal | 3 | single owner | — |
| 9 | Flow-with-a-deadline candidates, last hour only — KILLED 2026-09-12: month-end, opex and Russell-day last-hour trades are all negative in-sample and below their controls (`out/flow_candidates.csv`); the 15:50 imbalance needs data that is unobtainable | 3 | single owner | — |
| 10 | Owner-proposed fair-value-gap midpoint setup on 5-minute bars (A36; pre-registered 2026-09-13 before any run; 8 trials; fleet unit `pipeline/units/fvg.py`) | 3 | fleet (one unit) | Fails the survival rule on the selection window → reported and killed; passes selection but fails 2020-07→2026-09 → reported, never promoted |
| 11 | Owner's option C: leveraged-ETF close-rebalancing candidate (A38; pre-registered 2026-09-13 before any run; 1 trial; waits for `data/ext/letf_aum_2006_2026.csv` — NOT on GitHub, owner supplies via `tools/fetch_letf_aum_local.py`; the unit skips cleanly until then) | 3 | fleet (one unit) | Net ≤ 0 at 1 pt on the holdout, or not above the day-selection control or the price-only magnitude row |
| 12 | Overnight-loss forced-liquidation rebound (A39; pre-registered 2026-09-13 before any run; 3 trials incl. timing fingerprint and mirror; runs on data on the branch) | 3 | fleet (one unit) | T1 fails any survival condition, or the fingerprint fails (T2 ≥ T1 or T3 > 0) |
| 13 | A41 real-price re-evaluation and k calibration on the owner's SPY 0DTE bars (pre-registered before any bar exists; waits for `data/ext/spy_0dte_1min_2024-02_2026-09.csv.gz`) | 3 | fleet (one unit) | Nothing promoted on the sub-window; model labelled optimistic/pessimistic per row |
| 14 | A42 event-day long volatility (E1 daily baseline, E2 FOMC 13:30, E3 non-event control; family 39) | 3 | fleet (one unit) | E2 − E3 ≤ 0; E2 is UNDERPOWERED by construction |
| 15 | Track C (A43, owner's option E): defined-risk short 0DTE premium on the real bars — S1/S2 iron butterfly 09:31/13:30, S3 iron condor 09:31; tail statistics, MAE, sizing at a 4 % daily limit; promotion needs drawdown < 20 %, worst month > −10 %, p < 0.01 | 3 | fleet (one unit) | Fails the tail conditions → reported, not promoted; the account decision is the owner's |
| 16 | A44 forward test of the symmetric overnight-gap trade (owner's option B): passive; runs only on sessions after 2026-09-11 when the owner refreshes the minute file | — | single owner | n < 200 → no verdict |
| — | GEX filter, post-2018 cross-market | non-goal | — | Unobtainable in this environment (recorded in ACCEPTANCE.md) |

## Two tracks (owner, 2026-09-13)

**Track A — mechanism-based 0DTE edge (ranks 1–12 above).** Open items: A38 (waits for the assets file), A39 (running).
**Track B — technical swing-start detector on range bars (A40).**

| Rank | Task | Phase | Owner | What would kill it |
|---|---|---|---|---|
| B1 | Range-bar rebuild from 1-minute SPY at $0.34 and $1.00 (and gold at $5 from the Oanda minutes); gate B-a per A40c: exact range to the cent, continuity, per-session count ≥ the monotone minimum, determinism — PASS 9/9. The original ±15 %/0.999 gate against the owner's 34R export failed because that export is not a range-bar series (A40c); the rebuild rule was never changed | 2 | fleet (one coder) | Any A40c check failing → rebuild rule wrong, fix before any signal runs |
| B2 | Sweep/continuation family (24 trials, A40) — KILLED 2026-09-13: SPY winner FAILED on TEST (all 16 rows negative after costs), gold winner FAILED (all 8 rows negative), FDR 0/24; the pattern tables stand as the finding (a sub-cost 1-bar effect after sweeps on SPY, after close-throughs on gold) | 3 | fleet (one unit) | No trial passes on TEST → killed; the pattern table stays as the finding |
| B3 | `TRACK_B.md` generated from `out/trackB_*.csv`; tribunal (reviewer + judge, fresh context) | 4–7 | single owner | Any typed number, any parameter changed after the lock |

## Status log

- 2026-09-12 Phase 0: files written; `data/ext` both MISSING; Phases 0–2 proceed without them.

- 2026-09-12 Phase 3: D1 pre-registered; D3/D4 in-sample; D5 baseline + partial extension; D2b done; rank 9 killed; Phase 4 tribunal running.
- 2026-09-12 Phase 4 tribunal (14 defects) → Phase 5 repairs: winner re-pre-registered as 15:00|both|vixmove_exp; ext path proven (gate e); family-wide FDR (23 trials, 0 pass). Phase 6/7: regeneration + judge.
- 2026-09-13 Phase 6 judge round 1: ITERATE (6 items: holdout step unwired in `make all`, holdout file names, FDR finalisation, pipe escaping, orphans, render gaps) → all repaired, verified by the fleet verifier 11/11, committed 6789be7. Judge round 2 next; the "holdout path unwired" class is at its second appearance (escalate if it recurs).
- 2026-09-13 Phase 6 judge round 2: the round-1 repairs VERIFIED end to end on a synthetic ext feed; escalation class closed. ITERATE on two blocking items (holdout by-year option columns; the 15 POST-SELECTION holdout rows) + 7 notes — all adopted, implemented by two fleet coders (Sonnet), verifier next, then judge round 3.
- 2026-09-13 Phase 6 judge round 3: DONE (all nine round-2 items verified; six notes ≤ sev 5, all closed the same day). Phase 7 shipped for the data that exists; D2, the D4 headline and the ETF-dependent sleeves wait on `data/ext/` (DATA.md).
- 2026-09-13 Post-judge data sweep (2 Sonnet agents + 1 Haiku scout): no public source for the post-2020 minute bars or the ETF panel; BLOCKED.md written with options A/B/C. Plateau rule: no in-scope task can improve without the owner's input; nothing further is started.
- 2026-09-13 D5 fidelity: BAB universe cleaning reconstructed (626 names exact); portfolio Sharpe unchanged → hypothesis killed, next hypothesis recorded in ASSESSMENT. Plateau rule stands for everything holdout-dependent.
- 2026-09-13 Stop-hook loop (3×): condition unsatisfiable without owner input; no further agents launched (plateau rule + BLOCKED.md). Option D (daily open-to-close 0DTE search) recorded as owner-only because it overrides a mission non-goal.
- 2026-09-13 Owner decision: retro findings confirmed (RETRO.md); option A chosen — the owner pushes `data/ext/` to this branch, then the run resumes at the holdout (`make all`, verifier, judge). A watch on the branch is armed.
- 2026-09-13 10:10 UTC HOLDOUT RUN (real data): both pre-registered signals FAILED (winner n 274, −0.14 pts, Sharpe −0.14, p 1.0; gap-up n 452, −1.90 pts). D1 outcome: no reconciled specification survives. Only the magnitude-gated post-selection rows are positive (best p 0.10), reported, never promoted. Judge round 4 next; A36 fair-value-gap test running.
- 2026-09-13 Judge round 4: holdout MET; ITERATE on the ETF bridge (B1) → fixed with gate (f); A36 tested (no trial survives; killed) and A37 reported; verifier regeneration → judge round 5.
- 2026-09-13 Judge round 5: ITERATE on three rendering items only (bridge sentence column, NA caption, DST headline print) — no statistic, label or pre-registration moved; declared the last repair pass. Fixes applied; full regeneration + repeat run to the verifier, then the judge's confirmation.
- 2026-09-13 Judge round 5 confirmation: DONE on f28b5a3 after the three rendering fixes; the run is closed. Final state: D1 no reconciled specification survives; D2 both pre-registered signals FAILED on the real holdout; D3/D4/D6/D7 done; D5 done with the VXZ bridge refused by rule; A36 killed (no trial survives); A37 reported. Open only as owner decisions: a new pre-registered mechanism-based candidate (RETRO/ASSESSMENT next steps), never a re-tune on the holdout.
- 2026-09-13 Judge round 6: DONE on b7d4772 after six text fixes. Track A: A39 tested (positive but underpowered on the holdout, mirror also positive, not promoted); A38 built and waiting for the owner's assets file; Track B: SPY and gold both FAILED under the lock, killed with the pattern tables as the finding. Open owner items: supply `data/ext/letf_aum_2006_2026.csv` (A38) and, for the real-quote path, `data/ext/spy_0dte_1min_2024-02_2026-09.csv.gz` (tools/ helpers).
- 2026-09-13 A41/A42 ran on the owner's real 0DTE bars: the k × VIX model is confirmed honest at 2 % ITM (k unidentifiable, liquidity is the real deviation); every re-priced sign unchanged; the 0DTE variance risk premium is large and on the sell side; FOMC straddles underpowered. Nothing promoted; judge round 7 next.
- 2026-09-13 Judge round 7: ITERATE (ordering defect, loader path, EXPECTED, two stale numbers, two sentences) → fixed with a pre-committed A41 clarification → confirmed DONE on d684bf9. Real-price batch closed: the k × VIX model is honest at 2 % ITM, liquidity (prints missing in 80 % of named minutes, fills a median 3 minutes late) is the real deviation, the 0DTE variance premium lives on the sell side, nothing promoted. Family 39.
- 2026-09-14 Judge round 8: ITERATE (docs; then one run_all wiring defect of my own) → confirmed DONE on ef2c113. Track C killed: the 0DTE variance premium is real on the short legs but consumed by the wings and four legs of spread; the tail breaches the daily limit and the defined-risk cap; no account is worth opening. Open by owner choice only: A (stop), B (A44 passive forward test), C (assets file).

