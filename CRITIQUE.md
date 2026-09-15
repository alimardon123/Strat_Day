# CRITIQUE.md — open and resolved findings

Phase 0 tribunal (2026-09-12): four fresh-context hostile lenses (statistician, 0DTE
practitioner, infrastructure engineer, mission-fidelity) attacked the upgraded prompt,
ACCEPTANCE.md v1, DATA.md and PLAN.md. 32 findings. Dispositions below; ADOPTED items are
already in ACCEPTANCE.md v2 and the pipeline. Root cause precedes every fix.

| # | Sev | Lens | Finding (short) | Root cause | Disposition |
|---|---|---|---|---|---|
| 1 | 9 | practitioner | 54% loss-at-stop used to size trades that have no stop; max loss is 100% of premium | Thread B's 53.8% was measured on ATM calls with a 1.5-ATR stop | ADOPTED: size on measured worst trade with a 100% floor; MAE; combined-book worst day (budgets, A17) |
| 2 | 9 | statistician | Thread B's Oanda holdout (n=85, SR 1.67) is DST-misaligned and not produced by step17 | step17 detects one open minute on naive UTC stamps | CONFIRMED by replication (legacy mode reproduces n=85/+0.0975/1.67 exactly; winter sessions measured 14:30→15:00 ET and carried +0.236 vs summer +0.019). ADOPTED as A22 (c1/c2) |
| 3 | 8 | statistician | Holdout p<0.10 across all 8 candidates is a second selection | Rule conflated confirmation with filtering | ADOPTED: rank in-sample, ONE holdout test, others POST-SELECTION |
| 4 | 8 | engineer | Same as #2 from the code side | — | ADOPTED with #2 |
| 5 | 8 | engineer | Largest-|Δclose|-minute DST probe is dominated by 08:30/10:00 releases | Wrong statistic | REFUTED as of Phase 2: the probe was already replaced by the sustained 15-minute activity step at 08:30/09:30/10:30, which passes 47/47 months; the Sunday-first-bar anchor is added as an informational column |
| 6 | 7 | practitioner | ES continuous roll jumps and SPX stale open have no rule | Only SPY got a cleaning rule | ADOPTED: ext_manifest.json, roll handling, SPX open/close definitions (A6) |
| 7 | 7 | statistician | DSR undefined (V[SR], T, trial definition) | Under-specified | ADOPTED: A15, A31, survival rule 5 |
| 8 | 7 | statistician | Thread A ±0.3 tolerance on an option return with unpinned conventions | it22 script missing | ADOPTED: hard/soft gate (A30); convention inferred from evidence and logged |
| 9 | 7 | mission | 2013→2020-05 is Thread B's fit window; ranking rigged | 17.06/0.665 fitted on 2010–2018 | ADOPTED: vixmove gate re-derived as an expanding rule and as a frozen pre-2013 fit; literal thresholds reported, not ranked |
| 10 | 7 | engineer | Month blocks give p=1.0 for every per-year row | 20-block guard | ADOPTED: day blocks per year, NA below 20 blocks (rule 2, A26) |
| 11 | 6 | practitioner | k-sensitivity is null at 2% ITM with <1 h; spread is the real axis | Time value ≈ 0 | ADOPTED (confirmed by options sanity: identical premium at k=1.0/1.3/1.6): spread {1,2,3}; k for 13:00 leg only |
| 12 | 6 | practitioner | SPY 0DTE is physically settled → overnight shares; SPX cash-settled | Settlement unstated | ADOPTED: A28 per-instrument settlement; SPY exits by 15:55 |
| 13 | 6 | statistician | block_bootstrap_p is two-sided, 20-block floor, module RNG | Function semantics | ADOPTED (already in stats.py: per-call seed, one-sided convention); halves with month blocks |
| 14 | 6 | statistician | Same-day random-minute control collapses into "mean > 0" | Wrong null | ADOPTED: day-selection control is the survival test; timing control reported (A16) |
| 15 | 6 | mission | "extended data" vs "holdout" ambiguity lets full-sample numbers into the playbook | Loose wording | ADOPTED: D4 headline = holdout only |
| 16 | 6 | engineer | Old and new VXX never overlap; splice cannot be proven | Series B relaunch 2018 | ADOPTED: bridge via VIXY/VIXM (A13) |
| 17 | 5 | practitioner | Decision price = fill price in step17 | Bar-close fill | ALREADY HANDLED: pipeline enters at the next bar's open (A11); step17's convention only in the gate; difference logged |
| 18 | 5 | practitioner | Worst day per signal, not per book | Overlapping positions | ADOPTED (A17) |
| 19 | 5 | statistician | Asymmetric fitting; net Sharpe undefined across frequencies | — | ADOPTED: pre-2013 derivation; calendar-day Sharpe metric |
| 20 | 5 | statistician | "Frozen" vs "expanding" contradiction for the magnitude gate | — | ADOPTED: expanding is a rule; frozen variant is a counted trial |
| 21 | 5 | mission | Gate (c) references a table step17 cannot print; seed/one-sided claims mismatch the function | — | ADOPTED via A22 and stats.py |
| 22 | 5 | mission | P&L unit undeclared | — | ADOPTED: Units section |
| 23 | 5 | engineer | Price level cannot separate SPX from ES | — | ADOPTED: manifest (A6) |
| 24 | 5 | engineer | k=1.3 in A7 would be applied to the reproduction | — | ADOPTED: k=1.0 for every reproduction (A7) |
| 25 | 5 | engineer | Empty-output-exit-0 hides failed units | Contract | ADOPTED: `.error` + exit 2; run_all fails on empties (A32) |
| 26 | 4 | practitioner | Strike rounding to nearest can land < 2% ITM; SPY grid | — | ADOPTED (A8) |
| 27 | 4 | mission | VRP sleeve and cross-market silently dropped from D-list | — | ADOPTED: non-goal stated; D2b and D5 extended |
| 28 | 4 | mission | DSR N must include the trials that produced the candidate | — | ADOPTED (rule 5, A15) |
| 29 | 4 | engineer | Running step17 in place would dirty research/ | — | ADOPTED: never run in place (reproduce.py is a separate path); git-status check (A33) |
| 30 | 3 | statistician | Oanda 2017 feed hole and CFD-only sessions need a category | — | ADOPTED (A27 "feed gap"; VIX-calendar filter A4) |
| 31 | 3 | mission | `research/unified/CLAUDE.md` path, "2022 and 2024 holiday changes" placeholder, first output lacks commit hash | — | ADOPTED: paths corrected (A2); explicit calendar list in sessions.py; commit hash in every status |
| 32 | 3 | engineer | Oanda ends 2020-05-13, not 05-29 | Stated from HANDOFF, not the file | ADOPTED (A1; ext file from 2020-05-14) |

## Open

None from this round. Next tribunal: Phase 4, on the Phase 3 build.

## Phase 4 tribunal (fleet reviewer, fresh context, Opus) — verdict CHANGES_REQUIRED, 14 defects

| # | Sev | Finding (short) | Root cause | Disposition |
|---|---|---|---|---|
| 1 | 8 | Holdout (ext) path unwired: no manifest check, no instrument scaling, no dividend adjustment, no ES roll rule, no concatenation onto the Oanda history | Deferred because data/ext was absent | ADOPTED: `sessions.load_ext` + `build_extended`, SPY ×10 scaling, dividend-adjusted reference close, roll exclusion, SPX 09:31 open; proven by gate (e) on a synthetic file (identity of 850 trades) — A35 |
| 2 | 7 | Tie-break counted conditions, not fitted parameters; flips the pre-registered candidate | Conflated "condition" with "parameter" | ADOPTED: params = fitted numbers only; winner is now `15:00\|both\|vixmove_exp` (logged before any holdout data) |
| 3 | 6 | Limit entry charged commission only; the exit half of the spread still applies | Mis-read of A20 | ADOPTED: limit pays 0.10 + 0.5; improvement decomposed into cost part and price part |
| 4 | 5 | EQUAL_8 silently becomes a 4- then 3-sleeve book | Re-normalisation over survivors | ADOPTED: sleeve counts per window; label EQUAL_available(min-max) whenever fewer than 8 |
| 5 | 5 | A13 bridge referenced but not implemented | Docstring outran code | ADOPTED: `splice_vol` via VIXY/VIXM; correlations printed (0.9987 / 0.9875); bar amended to 0.98 with the measurement |
| 6 | 4 | SPY strike grid applied as 1 SPX point | Unit slip | ADOPTED: GRID SPY = 10 SPX points |
| 7 | 4 | S12 cost 0.7 bp instead of 0.33–0.50 pts | Thread A's bp constant | ADOPTED: 0.42 pt / entry price (S12 baseline Sharpe 0.58 → 0.27) |
| 8 | 4 | FDR family = 16, not every trial; gap-up DSR at N = 1,099 missing | Family scoped per module | ADOPTED: `pipeline/trials.py` (23 trials); gap-up row with PSR and DSR at N = 1,099 |
| 9 | 3 | Control direction base mismatched the VIX gates | Single base | ADOPTED: base per gate |
| 10 | 3 | `np.resize` made SR0 order-dependent | Shortcut | ADOPTED: explicit N with observed dispersion |
| 11 | 3 | Calendar-day denominator = feed sessions | Convenience | ADOPTED: NYSE trading days (VIX calendar) |
| 12 | 3 | prev_close spanned missing sessions (45 of 468 gap-up trades) | `gap_days` unused | ADOPTED: reference must be the prior NYSE trading day; counted (A34) |
| 13 | 3 | Gate c1 tolerance loose | — | ADOPTED: n ± 2, net ± 0.002, win ± 0.5, SR ± 0.05 (still PASS) |
| 14 | 2 | Nits: timing-control crash on 13:00, hard-coded observability check, missing timing column, A7 bound, NA printed as nan, typed 7.37, window 954, ranking unit | — | ADOPTED all: timing window [decision − 120, decision), perturbation test for causality, timing column printed, A7 bound 0.08 pt, "NA (< 20 blocks)", years computed, window ends 15:55, Units section amended (rank verified identical under points) |

Refuted: none. Unverified by the reviewer and now covered: `make repeat` byte-identity is re-run after the repairs; PLAYBOOK/OWN_ACCOUNT are rendered by `pipeline/report.py`.

## Phase 6 judge (fleet judge, fresh context) — decision ITERATE (round 1), 6 items

| # | Finding (short) | Root cause | Disposition |
|---|---|---|---|
| 1 | `make all` had no holdout step; ASSESSMENT's "when the file lands, make all produces the holdout tables" was false as coded | Deferred wiring | ADOPTED: conditional `holdout_d2` step in `run_all.py` when the ext minute file exists; holdout outputs added to EXPECTED |
| 2 | Holdout prefix mangled to `out/holdout_holdout_*`; `out/holdout_pooled.csv` never written | Prefix arithmetic | ADOPTED: D2 tables at fixed names `out/holdout_{summary,by_year,pooled}.csv`; D3/D4 holdout tables at `out/holdout_d4_*` |
| 3 | Survival-rule condition 3 (family-wide FDR) absent from the coded verdict | Verdict computed before the family exists | ADOPTED: label "SURVIVES (pending FDR)" from insample; `trials.py` adds the holdout rows to the family FDR and writes `label_final` |
| 4 | Markdown tables mis-render candidate labels containing `\|` | No escaping | ADOPTED: `md()` escapes pipes |
| 5 | Six stale per-trade files of the superseded winner still tracked; `make repeat` cannot see orphans | Copy-before-run | ADOPTED: files removed; `run_all` clears `out/insample_*` and `out/holdout_*` first |
| 6 | Bridge correlations not printed; by-year/by-regime columns still headed EQUAL_8; MAE missing from the playbook table; manifests never committed (`data/raw/` shadowed the negation); docstring 0.99 | Partial repairs | ADOPTED all: bridge table in OWN_ACCOUNT.md; `EQUAL_available` + `sleeves_mean` columns; `mae_worst` column; `.gitignore` uses `data/raw/*` + `!manifest`; docstring fixed |

Same-defect-class watch: "holdout path unwired" (Phase 4 defect 1 → judge item 1/2) is at its second appearance; if it survives the next judge pass the protocol says ESCALATE, not loop.

## Phase 6 judge round 2 (fleet judge, fresh context) — decision ITERATE (2 blocking, 7 notes)

The judge re-ran gates (c) 14/14 and (e) 6/6, re-rendered both playbooks byte-identically, reproduced the decision rule from the CSV, and proved the holdout path end to end by dropping a synthetic SPY-scaled `data/ext` into a copy and running `make all` + `make repeat` (95 files, byte-identical): the six round-1 items are VERIFIED and the "holdout path unwired" class is closed (no escalation).

| # | Sev | Finding (short) | Root cause | Disposition |
|---|---|---|---|---|
| N1 | 5 | `out/holdout_by_year.csv` lacks three of D2's per-year quantities (option return at spreads 1/2/3, worst day, MAE) | Per-year loop written before the option layer existed | ADOPTED: `opt_mean_s1/s2/s3`, `worst_day_pts`, `mae_worst_pct` per (signal, year) via `playbook.price_table/summarise/mae` |
| N2 | 5 | The 15 POST-SELECTION holdout rows promised at ACCEPTANCE "Decision rule" are computed by nothing | `reconcile.py` clips to the selection window; no holdout mode | ADOPTED: `python -m pipeline.reconcile holdout` (conditional step after `holdout_d2`) appends the 16 holdout rows with `window` and `label` (PRE-REGISTERED / POST-SELECTION) to `out/reconcile_candidates.csv`; not in the trial family; ACCEPTANCE wording amended to name the columns |
| N3 | 3 | Timing control not reported on the holdout summary; `frame` parameter dead | Omission | ADOPTED: `timing_control_pct` column |
| N4 | 3 | `report.py` still keyed on one fixed ext file name | Missed call site in the unification | ADOPTED: `sessions.ext_present()` |
| N5 | 3 | Two asserted statistics live in the renderer (FDR sentence; time-value bound) and A7's "< 0.08 pt at VIX 83" is below the model's own value | Prose typed from a one-off check | ADOPTED: FDR sentence generated from `out/trials.csv`; new `out/options_timevalue.csv` (`python -m pipeline.options`) drives the time-value sentence; A7 amended to the measured value |
| N6 | 2 | Three printed values for the frozen `vixmove_fixed` boundary (ACCEPTANCE, decision file, gate c log) | ACCEPTANCE typed a Phase-3 value; gate (c)'s Thread-A path uses Thread A's prior-bar reference (A30), not A34's | ADOPTED doc-side: ACCEPTANCE now references the generated file and explains the gate-(c) pair; code unchanged (the reproduction must keep Thread A's convention to reproduce Thread A's numbers) |
| N7 | 2 | Holdout halves split at the arithmetic midpoint, not at 2023-07-01 | Convenience | ADOPTED: fixed split date |
| N8 | 2 | D4's "IN-SAMPLE + HOLDOUT" full-sample table not produced | Step never added | ADOPTED: conditional `fullsample_d4` step (`out/fullsample_*`) rendered in the playbook |
| N9 | 1 | `rank` and `days_with_two_positions` render as floats | NaNs elsewhere in the column | ADOPTED: explicit `int_cols` allow-list in `report.md()` (no auto-detection of integral floats) |

Refuted: none. Open after this round: none (judge round 3 is the done-gate).

## Phase 6 judge round 3 (fleet judge, fresh context) — decision DONE, 6 notes

N1–N9 all VERIFIED (file:line); gates c 14/14 and e 6/6 re-run; decision rule reproduced from the CSV; `make all` + `make repeat` byte-identical in a copy with the synthetic ext feed (126 files) and the ext-absent repo; on the synthetic holdout the pre-registration held (a POST-SELECTION row scored higher and stayed unpromoted). No escalation: the two closed classes did not recur; the "typed prose beside a generated table" class has appeared three times at decreasing severity and is recorded here rather than looped on.

| # | Sev | Finding (short) | Root cause | Disposition |
|---|---|---|---|---|
| J3-1 | 5 | "Frozen gate values" line under the winner shows the `vixmove_fixed` boundaries, which the expanding-rule winner does not have | Generated line attached to the wrong configuration | ADOPTED: relabelled as the reference boundaries of a different, non-winning configuration; winner stated to have no frozen thresholds |
| J3-2 | 2 | SCORECARD file count (64) and both headers stale | Doc drift | ADOPTED |
| J3-3 | 2 | A31 family enumerates 23; `trials.py` builds 25 with the ext feed | Amendment lag | ADOPTED: A31 names the 2 holdout tests (25) and excludes the 15 POST-SELECTION rows |
| J3-4 | 2 | ASSESSMENT finding 5 time-value bound unqualified | Not updated with A7 | ADOPTED |
| J3-5 | 2 | "S = 6,500" contract-size example has no source in `out/` | Illustrative level | ADOPTED: stated as an assumption in the sentence (every dollar figure scales with S) |
| J3-6 | 1 | VRP table's coverage end not on the table | Caption | ADOPTED: caption derived from the CSV's last row |

Open: none. Blocked on input: D2/D4-headline/D5-ETF sleeves (DATA.md).

## Real-data tribunal (fleet verifier on the owner's `data/ext/`, 2026-09-13) — 3 findings, 2 defects

| # | Sev | Finding (short) | Root cause | Disposition |
|---|---|---|---|---|
| R1 | 6 | `sessions.load_ext` crashed on the real dividends file (`ex_date` stamps carry DST-varying offsets `-05:00` / `-04:00`) | The synthetic gate-(e) feed used naive dates, so tz-aware parsing was never exercised | ADOPTED: parse with `utc=True`, convert to America/New_York, normalise to a naive date; gate (e)'s synthetic dividends now carry one `-05:00` and one `-04:00` row (verified the old code fails on them); gate (e) 6/6 |
| R2 | 6 | The DST probe failed on the real feed (12/12 months) although the timezone conversion was right (median 388 bars inside 09:30–16:00 ET) | The sustained-step statistic used raw per-bar \|Δclose\|; on a single-venue feed with sparse pre-market prints a bar minutes apart absorbs a multi-minute move, so 08:30/10:30 could out-step 09:30 | ADOPTED: the step is computed on a forward-filled 1-minute grid per session (`grid_step`); Oanda 31/31, histdata 16/16, ext 12/12; power test: +60 / −60 minute shifts of the ext file fail 12/12 each; a density-based statistic was tried and rejected (too noisy per month on 24-hour CFD feeds) |
| R3 | 3 | The feed begins 2020-07-27, not 2020-05-14: the holdout's first eight weeks have no minute data from any source | Alpaca's IEX history starts there | ADOPTED as a recorded gap: holdout tables carry `data_first_date`, `data_last_date`, `sessions_in_window` and a `data starts …` note; the playbook prints the contract window next to the data window; nothing is filled |

| R4 | 8 | The SPY dividend series was subtracted from the Oanda SPX index prior closes: 27 ex-dividend days inside the 2013 → 2020-05-13 selection window, in-sample trade counts moved (winner 145 → 143 trades, gap-up 423 → 435), the tie-break flipped the pre-registered winner to `15:30\|both\|vixmove_exp`, and the first real holdout ran on the wrong signal with a contaminated selection | `build_extended` handed the full 1993 → 2026 dividend series to `day_table`, which adjusts every matching date in the whole frame; the synthetic gate-(e) fixture placed its ex-dates outside the native era, so the leak was invisible — the exact "ex-dividend leakage into prior close" the Phase 4 tribunal was told to attack | ADOPTED: dividends (and roll dates) scoped to ext-feed sessions only; gate (e) gains DIVIDEND SCOPE (an ex-date in the Oanda era must leave native trades untouched; selection rows must be byte-identical to the committed ones); the holdout is re-run on the pre-registered `15:00\|both\|vixmove_exp`; the first run's numbers are discarded, not reported |

Observation (no change): 148 kept sessions have 300–369 regular-session bars ("thin"; IEX prints only where IEX traded) — 2020: 51, 2021: 22, 2022: 1, 2024: 68, 2025: 6; one ordinary Monday (2024-12-23, 47 bars) is dropped as a feed gap. Same-defect-class watch: "proven on a synthetic stand-in that did not exercise the real format" is the class behind R1 and R2 — it is retro finding 2's counterfactual, now with a second data point inside this run.

## Phase 6 judge round 4 (fleet judge, fresh context, after the real holdout) — decision ITERATE (1 blocking, 8 notes)

Holdout verified clean: selection rows 0/28 mismatches vs the pre-registration; ex-dividend days 0; winner reproduced; −0.143431 on n 274 recomputed from the per-trade file; all six survival conditions coded; family 25, 0 pass; nothing promoted; data window honest; gates re-run; `make all` + `make repeat` from a clean copy byte-identical to the committed `out/` (128 files). R1–R4 VERIFIED including the ±60-minute probe power test.

| # | Sev | Finding (short) | Root cause | Disposition |
|---|---|---|---|---|
| B1 | 6 | The ETF panel's real VXX/VXZ (Series B, from 2018-01-25) were silently discarded: the splice scale divides by the ext value on the Kaggle end date, which is NaN for the two notes; `vxx_new`/`vxz_new` never existed, only the two pre-2018 correlations were printed, and 2018 → 2026 ran on VIXY/VIXM unannounced. Measured: new-VXX ↔ VIXY 0.9829 (passes 0.98), new-VXZ ↔ VIXM 0.8775 (fails; 178 of 234 VXZ days in 2018 are stale zero-return closes) | Index-membership test instead of a value test; no gate covered the ETF panel — the "stand-in never exercised the real format" class, fourth instance (R1, R2, R4, B1) | ADOPTED: value-tested scale; `splice_vol` computes and prints all four correlations with per-year breakdown and 2018 stale-close count; DISPOSITION: VXX bridged to the real note (≥ 0.98), VXZ bridge REFUSED by the existing `BRIDGE_MIN_CORR` rule and VIXM kept as the mid-term leg from 2017-11-13, stated in the bridge table and OWN_ACCOUNT.md; new gate (f) `pipeline/gate_etf.py` asserts every panel ticker survives to the panel's last date; A13 amended with the measurement |
| N1 | 2 | ASSESSMENT/CHANGELOG: "every 15:30 configuration is negative" — `15:30\|put\|mag` is +0.05 | Loose sentence | ADOPTED |
| N2 | 2 | ASSESSMENT: "2022 was the only good one" — 2023 (n 10) and 2025 (n 32) are positive too | Loose sentence | ADOPTED |
| N3 | 2 | "23-trial family" survives in ASSESSMENT/SCORECARD; the family is 25 (33 with A36) | Doc lag (recurrence of J3-3) | ADOPTED |
| N4 | 2 | SCORECARD gate (e) "6/6" — now 7/7 | Doc lag | ADOPTED |
| N5 | 2 | Console prints the ungridded step-open summary above the gridded PASS | Legacy print | ADOPTED — recorded as done in round 4 but NOT implemented then (judge round 5 caught it); landed in round 5 |
| N6 | 2 | Blank cells for NA (< 20 blocks) unlabelled | Rendering | ADOPTED — recorded as done in round 4 but NOT implemented then (judge round 5 caught it); caption landed in round 5 |
| N7 | 1 | ASSESSMENT maxDD −8.7 % vs CSV −8.6 % | Rounding | ADOPTED |
| N8 | — | `pipeline/pbo.py` (CSCV probability of backtest overfitting) and the faster `fvg.py` were in the working tree unannounced | Concurrent fleet work | ADOPTED: A37 names PBO as a D6 reporting statistic (not a survival condition, with its null-calibration caveat); A36's unit is integrated as a `make all` step and its 8 selection-window trials join the family (33) |

Escalation watch: the stand-in class is at four instances; the judge and the orchestrator agree that a fifth in the own-account/ETF path escalates instead of looping.

## Phase 6 judge round 5 (fleet judge, fresh context, on commit 9003387) — decision ITERATE (0 blocking, 3 rendering fixes, 5 notes)

B1 verified independently from the gzip panel: spliced VXX equals real Series B on 2,169 days (max abs diff 2.2e-16), VIXY fills 2017-11-13 → 2018-01-24, the VXZ leg equals VIXM from 2017-11-13 (2,217 days); 0.9829 / 0.8775 and the 178 stale 2018 closes reproduce exactly. A36 and A37 MET; holdout tables byte-identical to 9a43cbc; spot-checked steps leave `out/` clean; hygiene MET; no fifth stand-in instance (the B1 repair is value-tested on the real panel). "This is the last repair pass: if these three land, the run is done."

| # | Sev | Finding (short) | Root cause | Disposition |
|---|---|---|---|---|
| R5-1 | 2 | OWN_ACCOUNT.md bridge sentence quotes `corr_2020_on` (0.9836 / 0.9714) and prints "VXX:" twice, while the decisions were made on `daily_return_corr` (0.9829 / 0.8775) | Renderer picked the wrong column and a coarse label | ADOPTED: sentence quotes the decision correlation on the full overlap, names old/new pairs, 2020-on as a labelled aside |
| R5-2 | 2 | N6 not implemented: no caption explains the empty p-value cells in PLAYBOOK §7 (holdout summary, by-year) | Round-4 note marked ADOPTED without a change | ADOPTED: generated caption under both tables |
| R5-3 | 2 | N5 not implemented: `sessions.py` still prints the ungridded `step_open` distribution as the headline above the gridded `[PASS]` | Round-4 note marked ADOPTED without a change | ADOPTED: gridded summary is the headline, ungridded and Thread B values marked legacy comparisons |
| R5-N1 | 2 | CHANGELOG "Notes N1–N7 applied" overstated the round-4 close-out by two items | Orchestrator recorded the coder's claim without checking the diff | ADOPTED: round-4 rows corrected above; CHANGELOG entry names the miss |
| R5-N2 | 2 | A36 pre-registration time has no artifact stamped at that minute; ordering rests on the 9a43cbc SCORECARD/PLAN "result pending" entries | Pre-registration not its own commit | ACCEPTED as a process rule for future pre-registrations (own commit before the first run) |
| R5-N3 | 1 | `fvg.py` numpy rewrite has no committed equivalence run against the first draft | First draft was overwritten before its output was committed | ACCEPTED as residual: constants provably untouched, the judge found no parameter moved |
| R5-N4 | 1 | `out/fvg_candidates_trades.csv` (5 MB) committed and not in EXPECTED | Per-trade artifact | ACCEPTED: cleared per run by the `out/fvg_*` pattern, cannot go stale |
| R5-N5 | 1 | `out/pbo.csv` 8-block variant undocumented | Sensitivity generated, not described | ADOPTED: A37 names it |

Round 5 confirmation (same judge, on commit f28b5a3): **DONE**. Items 1–3 MET with every quoted bridge figure re-derived from the gzip panel; `pipeline.report`, both `pipeline.sessions` gates and `pipeline.gate_etf` re-run on the commit leave the whole repo clean; `git diff 9003387 HEAD` touches only the two gate (b) logs under `out/`; both pre-registered signals remain FAILED, nothing promoted, family 33 with 0 FDR passes, PBO outside the survival rule. Remaining notes (sev ≤ 2, no further pass): A36 pre-registration should have been its own commit; the `fvg.py` numpy rewrite has no committed equivalence run; the 5 MB per-trade FVG file is outside EXPECTED; and a process observation — twice in this run a close-out claim outran the diff (round 3 doc lag, round 4 N5/N6), so a successor programme should make the verifier diff the claim, not just the tests.

## Phase 6 judge round 6 (fleet judge, fresh context, on commit 2b2b449: A38 skip path, A39, Track B SPY + gold) — decision ITERATE (0 blocking, 6 text-level items, 5 notes)

Science verified clean: every pre-registration committed before its first run (ACCEPTANCE append-only, zero deleted lines since d287925; first gold row only at 4ef6723, after A40b/A40c); A39 T1 recomputed from the per-trade file to the last digit (n 158, +2.2016), fingerprint T2 < T1 holds, T3 > 0 fails, not promoted, holdout labels unchanged; A38 skips cleanly, test passes, no fixture under out/ or data/, formula and gate as registered; Track B gate 9/9 with the walk function hash-identical across the gate change, A40c's diagnostics reproduced (ratio 7.12, corr 0.998979, discontinuity −1.02/+1.08); 24 TEST rows, FDR 0/24, DSR N = 24, both winners chosen by the registered rule and FAILED, train/test lock verified on 303,018 trades (zero violations), costs and controls as registered; pattern table signed correctly with a day-block two-sample bootstrap; lookahead audit clean.

| # | Sev | Finding (short) | Root cause | Disposition |
|---|---|---|---|---|
| R6-1 | 2 | SCORECARD Track B heading said "gold 8 pending" above its own gold results | Doc lag | ADOPTED |
| R6-2 | 2 | SCORECARD called the sweep finding a "1-bar continuation", colliding with the table's `continuation` pattern | Loose wording | ADOPTED: "move in the rejection direction after a reversal-shaped sweep", continuation figure added |
| R6-3 | 2 | DATA.md still called the 34R export "ground truth" and the owner's gold file "the TEST" (both reversed by A40c) | Doc lag | ADOPTED |
| R6-4 | 2 | PLAN B1 kill column stated the superseded ±15 %/0.999 gate | Doc lag | ADOPTED: A40c checks stated, original failure explained |
| R6-5 | 2 | `test_letf.py` hardcoded this session's scratchpad path; the owner could not run the test | Coder convenience | ADOPTED: plain `tempfile.mkdtemp()`; 2/2 PASS |
| R6-6 | 1 | `pipeline/units/letf_wiring.md` (coder-to-coder patch note) left in `pipeline/` after its hunks landed | Handoff scaffolding | ADOPTED: removed |
| R6-N1 | 2 | A40c's typed diagnostics "monotone minimum 14.6 / close path 143" measure 14.71 / 144.7 on the minute file (14.78 on the export); the other three numbers reproduce exactly | Rounded from a first pass | ACCEPTED: ACCEPTANCE is append-only; recorded here and in CHANGELOG; no decision turns on it |
| R6-N2 | 1 | `gapliq.py` timing-control seed 7 is not named in A39 (A39 names 200 seeds and seed 11 for the bootstrap/day-selection control) | Under-specified pre-registration | ACCEPTED: disclosed in docstring and spec; the timing control is not a survival condition |
| R6-N3 | 2 | Gold's "session" = trading week via a > 12-hour gap is a construction choice in no amendment, committed with the gold results | Pre-registration silent on gold sessions | ACCEPTED: not a tuning knob (feeds only the self-consistency gate; 741 segments ≈ calendar weeks); recorded for the process ledger |
| R6-N4 | 1 | DSR N wording: A38 says 35, A39 says 37, actual family 36, both units use 37 | Count drift across amendments | ACCEPTED: no result turns on it; the units' N = 37 is the conservative (larger) value |
| R6-N5 | 1 | The `spec` prose column of the SPY TEST rows was rewritten when gold joined; the coder's "no column except fdr/dsr" claim omitted it | Imprecise claim | ACCEPTED: no numeric column changed |

Round 6 confirmation (same judge, on commit b7d4772): **DONE** for the option C batch (A38 skip path, A39, Track B SPY + gold). All six items verified with evidence; no output, label, window or pre-registration moved; ACCEPTANCE diff empty; TRACK_B.md byte-identical under re-render; tree clean. One severity-1 note (a stale docstring phrase in test_letf.py) swept into this commit.

## Phase 6 judge round 7 (fleet judge, fresh context, on commit 3bddd9b: A41 and A42 on the owner's real 0DTE bars) — decision ITERATE (2 defects, 2 stale numbers, 2 sentences; 5 notes)

Science verified: pre-registration order by commit timestamps (amendments 15:40 → units 15:58/15:59 → shards 16:44 → first data rows 17:14; neither unit touched after the data landed); FOMC list equal to A42's; data integrity on 9,476,392 rows (expiry = date of ts everywhere; session-bounded timestamps; 0.44 % legacy fractional strikes); three calibration rows and all nine summary rows recomputed to 1e-6; every re-eval row and all 409 entry/exit prices re-derived from the shards with 0 mismatches; A42 populations partition exactly (675 = 646 + 29 = 20 + 608 + 47) and every statistic recomputed; family 39, holdout labels unchanged; lookahead audit clean on prices.

| # | Sev | Finding (short) | Root cause | Disposition |
|---|---|---|---|---|
| R7-1 | 4 | 2 of 183 gap-up re-pricings had the fallback entry bar (a post-16:00 print) AFTER the exit bar (last bar before 15:59): they sold before they bought; 7 more had entry bar = exit bar | Uncapped "next later bar" entry fallback met an at-or-before exit fallback | ADOPTED: entry bar must precede exit bar or the trade is skipped and counted; used bar minutes written to the per-trade file (A41 clarification, committed before the re-run) |
| R7-2 | 3 | `option_shards()` ignored its path argument after the sharding change, so both skip-path unit tests ran on the real shards (2/3 each) | Loader globbed unconditionally; the tests are not a `make all` step | ADOPTED: the path argument is honoured; tests back to 3/3 |
| R7-3 | 2 | `out/realopt_calibration.csv` (an A41 output) missing from run_all EXPECTED | Wiring omission | ADOPTED |
| R7-4 | 1 | SCORECARD said "36 trials" beside a 39-row file; CHANGELOG said "27 steps" for a 28-step run | Doc lag | ADOPTED |
| R7-5 | 2 | ASSESSMENT gave the delay from the signal minute to the NEXT print (median 1 min) but not from the signal to the bar actually used (median 4, p90 40, max 349 min; 95 of 409 ≥ 15 min late) | Two different delays; only the smaller was reported | ADOPTED: both reported; the sentence is generated in PLAYBOOK §12 from the new columns |
| R7-6 | 1 | The k = 1.3 re-label conditional was evaluated (0.299 vs 0.3, did not fire) but not stated | Omission | ADOPTED: generated clause in §12 |
| R7-N1 | 2 | 282 of 409 exits and 318 of 409 entries needed a fallback bar: the re-pricing blends the strategy with a materially later one (T3 on-time +7.05 % vs late −3.65 %) | The 2 %-ITM chain rarely prints at the minute | ADOPTED as a sentence in §12; this IS the liquidity finding |
| R7-N2 | 2 | Strike choice conditioned on ex-post print availability (43 of 409 trades chose a strike that had not yet printed) | "Available in the file that day" read non-causally | ADOPTED before the re-run: causal availability (A41 clarification) |
| R7-N3 | 1 | One-trade rounding difference in `win` at $0.10 (a gross of exactly $0.10) | Float round-trip | ACCEPTED |
| R7-N4 | — | The real prices retire the k question rather than answer it: at 2 % ITM the premium is intrinsic, the 1.0/1.3/1.6 axis has no width for the 15:00/15:30 legs, and the measurable deviation is whether a print exists in the named minute | Finding | ACCEPTED; stated in §12 and the first paragraph |
| R7-N5 | — | The straddle bleed grows toward the close (−7.0 % at 09:31, −17.2 % at 13:30, n 608); E2 − E3 has the "events underpriced" sign but is a lottery profile (20 % hit rate, median −45.7 %) carried by two or three repricings; the durable result is the sell-side variance premium the account forbids | Finding | ACCEPTED; nothing promoted |

Round 7 confirmation (same judge, on commit d684bf9): **DONE** for A41 and A42 on real prices. All 401 re-priced trades re-derived from the shards: 0 ordering violations (was 9), 0 non-causal strikes (was 43), 0 mismatches in the used bars or the 15 summary rows; clarification committed 16 minutes before the re-run; effect adverse on both headline signals (honest direction); tests 3/3; EXPECTED complete; stale numbers fixed; fill-delay and k-rule clauses reproduce exactly; eventvol, trials, holdout and calibration outputs byte-identical to 3bddd9b. Calibration's non-causal strike search judged not blocking (diagnostic, never read by a trade). One severity-1 note (T2/T3 moved via strike re-selection, not dropped trades) swept into CHANGELOG in this commit.

## Phase 6 judge round 8 (fleet judge, fresh context, on commit 23fe567: A43 Track C, defined-risk short 0DTE premium) — decision ITERATE (docs only; 2 wrong numbers, 2 missing sentences; 5 notes)

Science verified by a full independent rebuild of all 1,592 structures from the raw shards: 0.0 max difference in strikes, credit, wing width, max loss and gross P&L; entry-before-exit on all 6,368 legs; contracts rule on all 1,592 rows; every tail statistic, the equity curves, the BH-FDR (0 of 42) and the buyer-mirror identity (short legs = −E1 on 588 of 592 dates, the 4 others ≤ $0.05 from the documented fallback asymmetry) reproduced. Lookahead audit clean. Separation from the prop playbook confirmed.

| # | Sev | Finding (short) | Root cause | Disposition |
|---|---|---|---|---|
| R8-1 | 1 | BLOCKED said "drawdowns 198–198 %" (range is 104–198) | Typo in a generated f-string (same variable twice) | ADOPTED |
| R8-2 | 1 | SCORECARD FDR sentence still said 39 trials beside a 42-row file | Doc lag | ADOPTED |
| R8-3 | 2 | The "worst possible day is the daily limit" premise is falsified and was unstated: 39/8/19 structures lost more than max loss (15/2/7 before costs, from legs marked up to 10 minutes apart) and 32/5/14 days breached −$4,000 | Non-synchronous exit marks and $0.40 of cost on structures with max loss as small as $0.52 | ADOPTED: stated in ASSESSMENT with the counts recomputed from the trades file |
| R8-4 | 2 | Skip selection: S1 dropped 83 sessions for missing wing prints; on the 54 E1 traded, the buyer's gross was +36.5 % vs −7.2 % on kept days — the seller's mean is flattered, the FAIL conservative | Wings do not print on calm days? No — on the largest-move days at 09:31 | ADOPTED: stated in ASSESSMENT |
| R8-5 | 1 | `net_pnl_cost0` means $0.10 here but `net_usd_cost0` means $0.00 in eventvol's trades file | Column naming | ACCEPTED (documented in the spec column); renaming would change a committed schema for no numeric gain |
| R8-N1 | 2 | The control condition compares the structure's % of its own credit with the buyer's mean over a different day set; day-matched, S1/S3 would fail it too | Convenience control | ACCEPTED: only makes the FAIL cleaner; disclosed in the spec note |
| R8-N2 | 2 | At the registered costs S1's equity on a fixed $100,000 goes negative on 372 of 675 days and ends near −$92k; "198 % drawdown" means the account was lost about twice | Fixed sizing keeps trading after ruin | ADOPTED as a sentence in ASSESSMENT; a risk desk would still want settlement-based P&L, bid/ask-sourced costs (breakeven $0.030 sits inside the plausible spread band), margin and assignment mechanics, and the 12 % of dropped sessions |
| R8-N3 | 1 | Loose prose: "(7 % of credit)" attached to a $0.20 figure that is 5.8 % of the straddle premium; a naked-straddle P&L quoted at an unregistered cost row | Illustrative arithmetic | ADOPTED: sentence rewritten to label it as arithmetic at an unregistered cost, no claim |
| R8-N4 | 1 | Docstring said no randomness is drawn (the bootstrap draws 2,000 seeded samples); drawdown definition differs between the candidates file (running peak) and the equity file (peak seeded at $100k), identical at $0.10 for S1/S2, up to 4.9 pp apart at $0.20; `sellvol_by_year.csv` missing from EXPECTED | Small inconsistencies | ADOPTED: docstring fixed, EXPECTED extended; drawdown definitions left as documented (no verdict depends on them) |
| R8-6 | 3 | My own round-8 fix appended `out/sellvol_by_year.csv` to the sellvol COMMAND LINE instead of EXPECTED (a string replace hit the first occurrence); argparse would have exited 2 before the header-only contract and broken the next `make all` | Orchestrator edit without running the step | ADOPTED at the judge's confirmation pass: command restored, EXPECTED extended, the step re-run (exit 0, outputs byte-identical); the verifier re-proves `make all` |

Round 8 confirmation (same judge, on commit ef2c113): **DONE** for A43 / Track C. All 1,592 structures rebuilt independently from the shards with 0.0 difference; every tail statistic, equity curve, the BH-FDR (0 of 42) and the buyer-mirror identity reproduced; the run_all defect fixed and re-proven by a full make all + make repeat (byte-identical, tree clean); all reporting numbers reproduce. Standing guard adopted from the judge's note: any edit to run_all STEPS or EXPECTED is followed by `python -c "from pipeline import run_all"` and one execution of the touched step before commit. Accepted-as-documented by choice: the cost0/cost1 column naming, the two drawdown definitions, the non-day-matched control (none affects a verdict). Verdict for the owner: no options account should be opened for option E on this evidence.

## Inversion research audit (2026-09-15)

| Finding | Disposition |
|---|---|
| U3 self-audit: D6 rows in SCORECARD.md:26 and ASSESSMENT.md:54 carried the stale 33-trial count after A42/A43 raised the family to 42 — doc-lag class (see RETRO.md); fixed by an appended superseded-clause, not a rewrite. | FIXED |

### Review round 1 (fresh-context reviewer, 2026-09-15): 13 defects in INVERSION.md, per u5_citation_audit.md

| # | Finding | Disposition |
|---|---|---|
| D1 | Rule 8 cited an unsourced "FINRA 72%" figure; replaced with u2 §5's own two quoted UNVERIFIED examples ("5–10% pass"/"95% fail", FTMO "99.8%") and added a §1/file reference. | FIXED |
| D2 | Row 6/Rule 2 wrongly credited `U2-S11` with the near-the-open timing claim (u2 §5 attributes it to S27) and wrongly claimed the programme "never fires at the open" (A42 E1, A43 S1/S3, A39 T2 all enter at 09:31); reattributed the citation and restated Rule 2 as NEW, not already-followed. | FIXED |
| D3 | Row 5 stated "$241,000–$358,000/day" as an illegitimate range and row 3 invented a "Tuesday/Thursday-only" explanation with no source; replaced both with u5's resolution (two tagged figures from two paper versions, plus the $184,000/day original) and added u5 to §7 with its counts. | FIXED |
| D4 | §5's n estimate mixed a full-window gate with shard-only option pricing; split into a PRIMARY (modelled pricing, full window) and SECONDARY (real-priced, shard sub-window) route, each with its own n, and dropped the "second selection" mischaracterization of counting gate triggers. | FIXED |
| D5 | §5 undercounted the candidate as one trial; restated as three (main/mirror/timing fingerprint) per the A39 precedent, with corrected family totals (42→45 / 43→46) and DSR N. | FIXED |
| D6 | Rule 1 read as if the prop account had no sizing rule; restated as a PROPOSED AMENDMENT naming the account's existing rule it would override (`ACCEPTANCE.md:108-112`, x=4%/N=1), and removed the own-account `TRACK_C.md:71` citation as prop-account status evidence in Rules 1 and 4. | FIXED |
| D7 | Rules 1, 4, 5, 7 implied A44 measures owner-discretionary behaviour it structurally cannot observe; added a preamble stating these four are forward-journal-only and that Rule 5 additionally needs the no-live-execution non-goal relaxed first. | FIXED |
| D8 | `U1-S21` and `U2-S08` are the same paper (SSRN 4682388) cited unmerged; added a merge line, cited both ids together in rows 1/3/4/18, and reported the $20bn-vs-$15bn dataset-size disagreement. | FIXED |
| D9 | Rows 10–11 were labelled AVOID-ONLY for mechanisms this single-index account cannot structurally enact at all; reclassified NO with a "structurally inapplicable" reason, and updated the §1 and §6 counts to 3 YES / 11 AVOID-ONLY / 10 NO. | FIXED |
| D10 | §5's gate used an unregistered 250-session warm-up instead of the programme's own ≥20-session A29 floor; switched to the A29 floor as the registered default, kept 250 as a labelled sensitivity only, and added a sentence noting the 11:00 entry time has no cited evidence behind it. | FIXED |
| D11 | Several line citations were wrong (A39 T2 cited at T1's SCORECARD line, "FDR 0/42" citing `TRACK_C.md:71` instead of the line that actually states it, A42's "25 years" citing an unrelated `ACCEPTANCE.md` range); corrected each in place. | FIXED |
| D12 | Rows 17/20 lacked a reason in the reachability cell, and rows 5/7/14/24 didn't name the branch file a completed test used; added both. | FIXED |
| D13 | §7 undercounted u2's "what I could not verify" list at 6 items; corrected to 7, naming the missing item (S02's exact sample dates). | FIXED |

Root cause noted on D1: the "FINRA 72%" clause did not originate in any evidence file. It entered
`INVERSION.md` via the orchestrator's synthesis spec, itself relaying the U2 agent's verbal report,
and was never grounded in `u1_retail_failures.md`, `u2_0dte_prop.md`, or `u3_self_audit.md`. This is
the same failure class already logged in `RETRO.md:40` ("a close-out claim outran the diff") —
here, a synthesis instruction outran the evidence file rather than a close-out claim outrunning a
code diff, but it is the identical "claim outran the evidence" pattern.

