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
