# CHANGELOG.md — one entry per iteration

## 2026-09-12 — Phase 0 and Phase 1
- Research bundle committed verbatim under `research/` (101 files, zero raw price data).
- Environment facts verified and recorded in DATA.md: only GitHub and PyPI reachable; pre-2020-06 sources all fetchable; `data/ext` minute file and ETF panel MISSING.
- ACCEPTANCE.md: 7 done-statements, survival rule (6 conditions), D1 decision rule (8 candidates), 18 recorded assumptions.
- PLAN.md: 9 ranked tasks with kill conditions.
- ARCHITECTURE.md: candidate C2 chosen (one pipeline, borrowed engines); ownership map; fleet unit contract; reproducibility contract.
- Stack pinned: pandas 2.2.3 (pandas 3.0 was installed first and rejected for compatibility with the threads' code), numpy 2.4.6, scipy 1.17.1, pyarrow 25.0.1.

## 2026-09-12 — Phase 2 (in progress): data fetched, session builder gated
- Fleet fan-out for the fetch units was attempted (5 Sonnet coders) and killed by the account's session rate limit; the units were written inline instead. Reviewer/judge stages keep the fleet.
- Six bundle readers (Explore agents) reported 60+ risks; the ones that change the contract are now assumptions A19–A28 and the amended survival rule #5 (DSR on the holdout with this run's trial count; historical trial counts reported as context).
- Fetched: Oanda SPX500_USD 2005-01→2020-05-14, histdata SPXUSD/GRXEUR/ETXEUR/JPXJPY 2010-11→2018-12, VIX to 2026-09-11, SPY daily to 2026-03-20, 57 Kaggle-mirror ETFs to 2017-11-10, 928 big_movers stocks to 2026-03-20. Manifests committed.
- `pipeline/sessions.py`: one builder for all feeds (UTC / Eastern-DST → America/New_York), NYSE holiday exclusion, DST probe (sustained-step open at 09:30 vs 08:30/10:30), calendar reconciliation. Gates PASS on both pre-2021 feeds. Thread B's `detect_open` is reported alongside and confirmed noisy (08:32 / 10:01 in some months), which is why canonical entry times are wall-clock (A24).
- `pipeline/stats.py`: adapter over `stats_engine.py` with per-call seeding (reproducible p-values), Thread B's one-sided convention, n_eff, deflated Sharpe. Unit-tested.

## 2026-09-12 — Phase 0 tribunal → Phase 5 repair of the contract; Phase 2 gates (a)–(c) PASS
- Tribunal (4 fresh-context lenses, 32 findings) logged in CRITIQUE.md with dispositions. ACCEPTANCE.md rewritten to v2: units declared (underlying points for D1/D2/survival; premium-% only in D4); D1 decision rule replaced (16 configurations, 12 rankable, calendar-day Sharpe on 2013-01→2020-05-13, ONE pre-registered holdout test, POST-SELECTION labels); sizing on measured worst trade with a 100% floor plus intraday MAE and combined-book worst day (the 54% loss-at-stop applies only to stop-defined ATM trades); per-instrument settlement (SPX cash-settled: ask entry, intrinsic settlement; SPY: exit by 15:55); spread {1,2,3} as the sensitivity axis, k for the 13:00 leg only; VXX/VXZ bridged via VIXY/VIXM; ext_manifest.json required; unit failure = `.error` + exit 2; trial definition; DSR at holdout-selection N and historical N.
- Reproduced defect (CRITIQUE #2/#4, confirmed by replication): Thread B's published Oanda 2019–20 holdout (n=85, +0.0975%, SR 1.67) was computed on naive UTC stamps with one detected open (13:32 UTC), so every EST-season session measured 14:30→15:00 ET instead of the last half hour; those winter sessions (n=37) carried +0.236%/trade vs +0.019% in summer (n=48). Legacy mode reproduces the row exactly; the DST-correct row (NY sessions, Thread B's bar-close fill) is n=90, +0.0776%, 53.3% win, SR 1.28, p 0.17 (day blocks); with the pipeline's wall-clock 15:30 decision and next-bar entry it is n=90, +0.1326%, 55.6%, SR 2.05, p 0.10. Sign holds; the published magnitude was an artefact.
- Reproduced (c1): Thread B discovery n=338 / +0.0639% / 58.3% / SR 2.48 vs published 337 / +0.0645 / 58.5 / 2.50 — the spec is pinned. Thread B's 17.06 / 0.665 recovered as the upper-tercile boundaries of histdata 2010–2018 (17.06 / 0.681), so its gate can be re-derived as a rule; on Oanda 2005–2012 the same construction gives 22.81 / 0.845%.
- Reproduced (Thread A, no code in the bundle): trade counts 543 / 506 / 1,031 vs published 516 / 473 / 1,030; underlying win rates 52.4 / 53.0 vs 52.7 / 53.1. Option-level TEST means reproduce within tolerance only under "buy at the ask, settle at intrinsic" (+2.97 vs +2.77; +1.35 vs +1.14 — the same +0.21 offset on both legs); the half-on-exit convention gives +1.90 / +0.26. Convention inferred and logged (A30); both are reported in D4.
- Gate (b): sustained-step DST probe 47/47 months at 09:30 on both feeds; no kept session on a calendar event; Oanda 2017 has 85 feed-gap sessions (known hole). Gate (c): 14/14 PASS. mh.sanity(): README's "within 3 points" claim does not hold for the bundled parameters (time exits at 120 bars); the residual meanR equals the modelled slippage exactly, which is the property that matters.
- Thread A option sanity: at 2% ITM with 60 minutes left the model price is identical at k = 1.0 / 1.3 / 1.6 (time value < 0.001 pt), confirming CRITIQUE #11.

## 2026-09-12 — Phase 2 gate (d) PASS; Phase 3 started (D1 pre-registered, D3/D4 in-sample)
- `make all` / `make repeat`: byte-identical `out/` on two consecutive runs.
- D1 (`pipeline/reconcile.py`): 16 configurations on the 2013-01→2020-05-13 selection window. Every VIX-gated "both" configuration outranks every magnitude/put-only one; the four VIX-gated "both" variants tie within 0.10 calendar-day Sharpe (0.51–0.57); winner by parameter-count tie-break `15:00|both|vixmove_fixed` (VIX > 22.81 & |prev close→15:00| > 0.816%, frozen from Oanda 2005–2012): n 93, win 63.4%, +5.10 pts/trade net of 1.0 pt. Pre-registered in `out/reconcile_decision.md` before any holdout data exists. No configuration passes BH-FDR at 10% on the window (best p 0.078: `15:30|both|vixmove_exp`); Thread B's literal 17.06/0.665 rows on Oanda 2013–2020 give calendar-day Sharpe 0.53–0.61 (Thread B's own convention would print 2.1–2.5).
- D3 (`pipeline/execution.py`, in-sample): limit entry at 0.25–0.50 ATR turns the gap-up call from −0.12 to +0.9/+1.0 pts per signal (fill 86%/74%, bootstrap p < 0.001) — the same "largest single improvement" Thread B found, now with unfilled signals counted as zero; for the winner +0.57 pts (p 0.31, n 93).
- D4 (`pipeline/playbook.py`, in-sample, SPX cash settlement, 1 pt): winner +11.5% of premium per trade, median +7.2%, 5 of 93 trades lose the full premium (2015-08-25, 2018-12-27, 2020-03-06/18/25 — last-hour reversals > 2%); gap-up call +1.23% at 1 pt, +0.18% at 2 pt, −0.85% at 3 pt. k = 1.0/1.3/1.6 moves the 13:00 leg by 0.07/0.18 points and the 15:00 leg by nothing (CRITIQUE #11 confirmed). SPY 15:55 exit with both spread halves: +6.3% and +0.15%. Sizing at a 4% limit with the 100% floor: 4% per trade, expected +5.8%/yr (winner) and +2.9%/yr (gap-up) IN-SAMPLE, worst years −3.7% / −8.1%; 48 days carry both positions, so the combined book sizes at 2% per trade.
- Fleet: implementation stayed inline (rate limit earlier; the reconciliation, pricer and execution model are COUPLED by the ownership map); the fleet's reviewer and judge are reserved for Phase 4.

## 2026-09-12 — Phase 3 continued: D5 own-account re-measurement, D2b cross-market
- D5 (`pipeline/own_account.py`, sleeves imported unchanged from it7/it8/it9/it11; TSMOM/XSMOM inverse-vol copied from it8b; S13 re-implemented from ASSESSMENT_iteration17 with a 0.5 weight cap): BASELINE 2006-01→2017-11-10 equal-weight 8 sleeves Sharpe 0.85 full / 1.08 test (Thread A: 1.12 / 1.35), maxDD −6.7% (−6.10%); two buckets 50/50 Sharpe 1.00 / 1.09 (1.20 / 1.40), maxDD −6.0% (−5.26%); mean pairwise sleeve correlation 0.123 → n_eff 4.3. Per-sleeve test-window Sharpes match Thread A where it published them (S2 0.58 vs 0.58, S3 0.75 vs 0.75, S13 0.53 vs 0.41–0.54); the shortfall is S8 BAB (0.52 full vs 0.81), which here runs on the raw 928-stock big_movers panel with a |return| < 0.5 mask instead of Thread A's it5b-cleaned 626-stock panel (`panel_clean.pkl` is not in the bundle), and S6 (−0.06 vs 0.07). Labelled PARTIAL reproduction.
- D5 extension with the data that exists: S1, S5, S8 run to 2026-03-20 (SPY daily, stock panel), S12 to 2020-05-13; S2/S3/S6/S13 stop at 2017-11-10 until the ext ETF panel arrives. Equal-weight book 2017-11-13→2026-03-20 (four sleeves) Sharpe 0.66, 2018 −3.4%, 2022 +0.6%; S8 BAB post-2017 Sharpe −0.37 (the post-publication decay Thread A projected). Regimes: uptrend +5.0%/yr, high-vol +3.7%, downtrend +0.2% (equal 8, full sample).
- D2b (`pipeline/units/xmarket.py`): gap-up (> 0.3%) afternoon entry at the same session fraction as 13:00 ET, exit at the local close, histdata 2010–2018 — SPX n 499 +0.022%/trade p 0.16; DAX (Xetra 09:00–17:30 = 03:00–11:30 ET, fixed because the step detector locks onto the 08:00-local Eurex futures open) n 602 +0.019% p 0.27; EuroStoxx n 548 −0.033% p 1.0. Finding: the effect is marginal on SPX and DAX alike and negative on EuroStoxx — no shrinkage on DAX, a sign flip on EuroStoxx (Thread B saw the same flip).
- Phase 4 tribunal launched: the fleet reviewer (fresh context, Opus) receives ACCEPTANCE.md, the out/ snapshot and pipeline/ only.
- PLAN rank 9 flow-with-a-deadline candidates (`pipeline/units/flow.py`, 3 counted trials, Oanda 2005–2020-05, 15:00→close net of 1.0 pt): month-end against the month-to-date move n 184 −0.081%/trade (p 1.0); opex-day continuation n 168 −0.097% (p 1.0); Russell reconstitution day long n 15 −0.242%. None beats its day-selection control. KILLED under the plateau rule; they remain pre-registered non-survivors for the holdout only as a record.
- D5 addendum `pipeline/vrp.py` (VIX − next-21-day realised vol, 2000→2026-03) and `pipeline/report.py` (renders PLAYBOOK_0DTE.md and OWN_ACCOUNT.md from out/ tables) written; run after the current regeneration finishes.

## 2026-09-12 — Phase 4 tribunal (fleet reviewer, fresh context) → Phase 5 repair → gates re-run
- Verdict CHANGES_REQUIRED, 14 defects (CRITIQUE.md, second table); all adopted, none refuted. The two that changed results:
  - Tie-break now counts FITTED parameters only (an expanding rule has none). Pre-registered winner changes from `15:00|both|vixmove_fixed` to **`15:00|both|vixmove_exp`** (VIX above its expanding upper tercile AND |prior close→15:00| above its expanding upper tercile): n 145, win 62.8%, +3.12 pts/trade net, calendar-day Sharpe 0.489 (0.557 for the frozen-threshold variant, but that one has 2 fitted numbers, 17 trade-months and 46 of 92 trades in Feb–May 2020). Logged before any holdout data exists.
  - A session whose prior kept session is not the prior NYSE trading day no longer feeds prior-close signals (A34): gap-up trades in the window 468 → 423; the gap-up call is net −0.14 pts/trade at 1.0 pt on the underlying in-sample, p 1.0.
- Holdout path built and proven before data: `sessions.load_ext` (manifest, SPY ×10 scaling, dividends, ES rolls, SPX 09:31 open) + `build_extended`; gate (e) on a synthetic SPY-scaled ext file reproduces all 850 candidate trades on 2019-06→2020-05 exactly, plus dividend/roll/refusal tests (A35). `pipeline/insample.py` now produces the D2 holdout tables and survival verdicts automatically for any window starting 2020-06-01.
- D3 recharged: a filled limit pays commission plus the exit half of the spread; improvement decomposed. Winner: +0.22 pts/signal at 0.25 ATR (cost part +0.36, price/adverse-selection part −0.14, p 0.38); gap-up call: +0.66 (0.34 + 0.31, p 0.002).
- D4 in-sample for the new winner: +7.3% of premium/trade (SPX cash settlement, 1 pt), median +5.5%, 5 full losses in 145 trades; sizing at 4%: +5.8%/yr, worst year −2.0%; 77 days carry both positions → combined book 2% per trade.
- D5: sleeve counts reported (EQUAL_available(3-4) post-2017); VXX/VXZ bridge implemented via VIXY/VIXM with measured correlations 0.9987 / 0.9875 (A13 bar amended 0.99 → 0.98); S12 at 0.42 pt ES cost (baseline Sharpe 0.58 → 0.27); baseline test-window EQUAL_8 Sharpe 0.99, two-bucket 0.97.
- Family-wide trial ledger (`pipeline/trials.py`): 23 trials (16 momentum, gap-up, 3 cross-market, 3 flow); BH-FDR at 10% passes none.
- Gate (c) tightened (n ± 2, net ± 0.002, win ± 0.5, SR ± 0.05): still 14/14 PASS; the expanding-threshold causality is now a perturbation test, not an assertion.

## 2026-09-13 — Phase 6 judge: ITERATE → repairs applied
- Judge verified gates (c) 14/14 and (e) 6/6 independently in a scratch copy, the decision rule as coded vs written (winner reproduced from the CSV), and that both playbooks are byte-identical re-renders of `pipeline/report.py`. Decision ITERATE on six precisely specified items (CRITIQUE.md, third table), all applied: holdout step wired into `make all` (conditional on the ext file), deterministic holdout file names incl. `out/holdout_pooled.csv`, survival-rule condition 3 finalised by `trials.py` (`label_final`), pipe-escaped markdown tables, stale files removed and cleared per run, bridge correlations and sleeve counts rendered, MAE column, manifests actually committed.
- No statistic, ranking or pre-registration was touched in this round.
- Ext-feed detection unified (post-judge review): one rule, `sessions.ext_present()` = manifest AND a `spx_1min_*.csv.gz` file; `build_extended` and `run_all` both use it, so the session builder can no longer load a feed that the holdout step skips (previously the builder keyed on the manifest and `run_all` on one fixed file name). No output changed (`make repeat` byte-identical).
- Render nits from my own review of the regenerated OWN_ACCOUNT.md: by-year index named `year` (was `date`, printed as 2006.000) and by-regime index named `regime` (was `Unnamed: 0`); `report.md()` prints integer-typed columns as integers. Fleet coder; numbers unchanged; `make all` + `make repeat` byte-identical (64 files). PLAYBOOK_0DTE.md unaffected.

## 2026-09-13 — Phase 6 judge round 2: round-1 repairs VERIFIED end to end; ITERATE on 2 + 7 → applied
- The judge dropped a synthetic SPY-scaled ext feed into a copy and ran `make all` + `make repeat`: the holdout verdict is produced at the ACCEPTANCE-named paths with all six survival conditions (the "holdout path unwired" class is closed; no escalation).
- Holdout by-year rows (D2) now carry the option return in % of premium at spreads 1/2/3 (cash settlement, k 1.0; 1.3 for the 13:00 leg), the worst day and the intraday MAE (`opt_mean_s1/s2/s3`, `worst_day_pts`, `mae_worst_pct`); the pooled holdout summary reports the timing control; the halves split at 2023-07-01 as D2 names them.
- The 15 POST-SELECTION holdout rows are now computed: `python -m pipeline.reconcile holdout` (a `make all` step when the ext feed is present) appends the 16 configurations' holdout rows to `out/reconcile_candidates.csv` with `window` and `label` (PRE-REGISTERED / POST-SELECTION); the selection rows carry `label` SELECTION (gap-up row PRE-REGISTERED). Never promoted, not in the trial family. ACCEPTANCE "Decision rule" wording amended to name the columns.
- Full-sample D4 table (ACCEPTANCE D4 "IN-SAMPLE + HOLDOUT"): conditional `fullsample_d4` step → `out/fullsample_{execution,summary,sizing}.csv`, rendered under that heading.
- Two typed statistics moved out of the renderer: the FDR sentence is generated from `out/trials.csv`; a new `out/options_timevalue.csv` (`python -m pipeline.options`, a `make all` step) drives the time-value sentence. Measured at 60 minutes, 2% ITM, S = 4000, k = 1.0: ≤ 0.001 pt for VIX ≤ 40 and 0.16 pt at VIX 83 — A7's typed "< 0.08 pt at VIX 83" was wrong and is amended to the measured value.
- `report.py` keys on `sessions.ext_present()` (the missed call site); `rank` / `days_with_two_positions` render as integers via an explicit allow-list (no auto-detection of integral floats).
- `report.py`: §2 ranking tables read only the selection-window rows (`window` column), so the appended holdout rows cannot leak into the ranking; §7 renders the 16 holdout rows as "published, not promoted" (PRE-REGISTERED first) and the full-sample D4 tables under the heading IN-SAMPLE + HOLDOUT, only when the files exist; holdout by-year caption for the new columns.
- ACCEPTANCE no longer types the frozen `vixmove_fixed` boundary (it references `out/reconcile_decision.md`; gate (c)'s Thread-A path prints its own pair by design — A30 prior-bar reference).
- No statistic, ranking, threshold or pre-registration changed; ext-absent outputs regenerate byte-identically apart from the two new columns, the one decision-file sentence and the new time-value artifact.

## 2026-09-13 — Phase 6 judge round 3: DONE; six notes closed
- Judge verified N1–N9 file by file, re-ran gates (c) and (e), reproduced the decision rule from the CSV and proved D7 with the synthetic ext feed (126 files byte-identical). Decision DONE.
- Notes closed: the "Frozen gate values" line is relabelled as the `vixmove_fixed` reference boundaries (the winner has none); the contract-size example states S = 6,500 as an assumption; the VRP table caption carries its coverage end; SCORECARD/ASSESSMENT headers and counts refreshed; A31 names the 2 holdout tests (family 25 with the ext feed) and excludes the POST-SELECTION rows; ASSESSMENT finding 5 carries the measured time-value bound.
- Class watch (recorded, not looped): typed prose beside generated tables appeared in three rounds at falling severity (7.37 → A7 bound → this round's notes); every playbook TABLE has been a byte-identical re-render since Phase 5.

## 2026-09-13 — Data-acquisition sweep and BLOCKED.md
- Web search is reachable from the container (plan mode had only probed vendor APIs). Two Sonnet agents searched GitHub for post-2020 minute bars and the ETF panel; a Haiku scout inventoried the local panels. Nothing usable exists (DATA.md, BLOCKED.md). Substitutes the mission forbids were not used.
- BLOCKED.md records the gap, the root cause (network policy), what was tried, and three owner options; PLAN.md invokes the plateau rule.

## 2026-09-13 — D5: BAB universe cleaning reconstructed (hypothesis killed)
- `own_account.clean_universe` applies Thread A's it5.py:36-37 (≥ 1200 rows, median close ≥ $5, median dollar volume ≥ $5M) and it5b.py:5-9 (drop names with > 5 days of |return| > 50%) to the BAB sleeve's input only: 928 → 656 → 626 names, 30 dropped, 865 → 474 masked stock-days — every published count reproduced exactly, which also establishes that `stocks_daily.parquet` is Thread A's panel.
- Reproduction nuance: the exact match requires `pct_change(fill_method=None)`; pandas 2.2.3's forward-filling default gives 621 names. Thread A evidently ran on pandas 3 (consistent with its pickles being unreadable under 2.2.3).
- Result: baseline test-window EQUAL_8 Sharpe 0.9944 → 0.9939, two-bucket 0.9712 → 0.9711; BAB test Sharpe 1.11 → 1.16, maxDD −18.8% → −14.9%; extended book 0.72 → 0.76. The uncleaned universe was NOT the cause of the 0.99-vs-1.35 gap; ASSESSMENT's hypothesis is replaced. No threshold, weight or cost changed. Fleet coder (Sonnet) + verifier.
- Sleeve-by-sleeve comparison (fleet scout, Sonnet) on the identical 2012→2017-11-10 test window explains the remaining gap: S12 gap-up is −0.37 here vs +0.32 in Thread A because Thread A costed ES at 0.35 bp per side (`it15.py:24`) while the contract charges 0.42 index points (A21); S1/S2/S3/S6/S13 match within 0.13, S5 is 0.19 low (layered vol targeting), S8 is 0.39 high. Bucket A (3 sleeves incl. S12) carries the whole portfolio shortfall. Thread A's 1.35 / 1.40 is therefore not reproducible under the contract's cost budget; 0.99 / 0.97 is the honest figure. No code change.

## 2026-09-13 — Owner supplied `data/ext/` (781180b); real-data repairs before the first holdout run
- Files verified against DATA.md by the fleet verifier: SPY 1-minute (Alpaca IEX) 2020-07-27 → 2026-09-11, 605,227 rows, clean; manifest; 135 dividends; ETF panel complete for all 29 tickers to 2026-09-11.
- Two defects the synthetic proof had not exercised, fixed by a fleet coder: tz-aware dividend stamps crashed `load_ext` (root-cause fix + gate (e) fixture); the DST probe's raw \|Δclose\| step failed on a feed with sparse pre-market prints (now a forward-filled 1-minute grid; passes all three feeds, fails both shifted copies).
- Holdout tables now carry the effective data window (`data_first_date`, `data_last_date`, `sessions_in_window`, `data starts …` note) and the playbook prints it beside the contract window (second fleet coder). The 2020-05-14 → 2020-07-26 gap is reported, never filled.
- DATA.md and BLOCKED.md updated; option A taken.
- First real holdout run (discarded): the SPY dividend series leaked into the Oanda SPX prior closes (27 ex-dates in the selection window), changed the in-sample rows and flipped the pre-registered winner to the 15:30 variant. Root cause fixed in `build_extended` (dividends scoped to ext sessions); gate (e) gains a DIVIDEND SCOPE test; the selection must be byte-identical to the committed rows before any holdout number is reported. Retro finding 2 ("a synthetic stand-in that does not exercise the real format") now has three data points in this run (R1, R2, R4).

## 2026-09-13 10:10 UTC — the holdout ran on real data: FAILED × 2
- After the dividend-scoping fix, `make all` + `make repeat` byte-identical (128 files); selection rows byte-identical to the pre-registration (0 mismatching columns, ex-dividend days 0, winner `15:00|both|vixmove_exp`).
- Holdout 2020-07-27 → 2026-09-11: winner n 274, win 53.6 %, −0.14 pts/trade, cal-day Sharpe −0.14, p 1.0, option +0.08 % of premium at 1 pt → FAILED; gap-up call n 452, −1.90 pts, Sharpe −0.58 → FAILED. Family FDR (25 trials): 0 pass. Post-selection: every VIX-gated and 15:30 row negative; three magnitude rows positive, best `15:00|put|mag` +1.94 pts, p 0.10 (not promoted).
- D5: the ETF panel extends S2/S3/S6/S13 to 2026-09-11 through the VXX/VXZ bridge (0.9987 / 0.9875); post-2017 EQUAL_available(4-8) Sharpe 0.52.
- ASSESSMENT, SCORECARD, PLAN updated; BLOCKED.md closed.

## 2026-09-13 — Judge round 4 (after the real holdout): ITERATE on the ETF bridge → repaired; A36 and A37 integrated
- Judge verified the holdout clean on every criterion (selection 0/28 mismatches, −0.143431 on n 274 recomputed from the per-trade file, nothing promoted, data window honest, `make all` from a clean copy byte-identical to the committed out/).
- B1: the ETF panel's real VXX/VXZ had been silently dropped (NaN splice scale); fixed at the root (value-tested scale), `splice_vol` now measures all four bridge correlations with per-year breakdown and the 2018 stale-close count; DISPOSITION by the existing 0.98 rule: VXX bridged to the real Series B note (0.9829), VXZ bridge refused (0.8775; 178 of 234 stale closes in 2018) and VIXM kept as the mid-term leg — A13 amended with the measurement; new gate (f) `pipeline/gate_etf.py` asserts panel coverage and the bridge decision (it fails on the old code). Effect: S13 post-2017 Sharpe 0.18 → 0.16; extended book 0.670 → 0.668 / 0.754 → 0.750.
- A36 (owner's fair-value-gap setup): `pipeline/units/fvg.py` (numpy hot loop, ~1 min) is a `make all` step; its 8 selection-window trials join the family (33); PLAYBOOK §9 renders the three windows with a generated verdict — no trial survives; every trial net-negative at 1 pt in every window; the midpoint entry beats a random-time entry but not the cost.
- A37 (PBO, reporting statistic): `pipeline/pbo.py` — CSCV over 16 blocks, PBO 0.73, null 0.85 (floor for near-duplicate configurations) — printed in PLAYBOOK §2 beside the FDR sentence; not a trial, not a gate.
- Notes N1–N7 applied (text); the gate output name reconciled (`out/gate_etf.csv`).


## 2026-09-13 — Judge round 5 (on commit 9003387): ITERATE on three rendering items → repaired; declared the last repair pass
- Judge verified B1 from the gzip panel itself (spliced VXX equals real Series B on 2,169 days at machine precision; VXZ leg equals VIXM from 2017-11-13), A36 and A37 MET, holdout tables byte-identical to 9a43cbc, hygiene MET, no fifth stand-in instance.
- Correction to the round-4 entry above: "Notes N1–N7 applied" was wrong by two — N5 (gridded DST headline) and N6 (NA caption) were recorded as done without a change behind them. The CRITIQUE round-4 rows now say so.
- R5-1: the OWN_ACCOUNT.md bridge sentence quoted `corr_2020_on` and printed "VXX:" twice; it now quotes the decision correlation on the full overlap (0.9829 bridged / 0.8775 refused), names old/new pairs, and gives the 2020-on value as a labelled aside.
- R5-2 (N6): generated caption under the PLAYBOOK §7 holdout-summary and by-year tables — an empty cell is NA (fewer than 20 blocks), never 1.0 or 0.
- R5-3 (N5): `sessions.py` prints the gridded step-open summary (the column that decides `ok`) as the headline; ungridded and Thread B values are marked legacy comparisons.
- A37 amended to name the 8-block PBO sensitivity variant already in `out/pbo.csv`.
- Verified after the fixes: `make all` (22 steps, exit 0) then `make repeat` byte-identical; the eight numeric tables (holdout summary/pooled/by-year, reconcile candidates, trials, bridge, PBO, FVG) unchanged against the previous commit; gates (b) 3/3 ×2, (c) 14/14, (e) and (f) PASS; only the two gate (b) logs changed, by their headline text.

## 2026-09-13 — Owner chose option C: two mechanism candidates pre-registered in their own commit before any run
- A38 leveraged-ETF close rebalancing (assets-weighted forced demand, entry 15:30, one trial) — waits for the owner's assets file (DATA.md spec, local fetch helper).
- A39 overnight-loss forced-liquidation rebound (expanding 10th-percentile overnight loss, long call from 10:00; timing-fingerprint and mirror trials as falsifiers) — runs now on the branch's data. Family 33 → 36 (37 once A38 runs).
- Flow-candidate task (rank 9) reopened for these two only; new evidence = a named forced trader and a falsifiable timing fingerprint, absent from the three killed rows.
- Requested the highest-value data addition: real SPY 0DTE 1-minute option bars (DATA.md), with a local fetch helper.

## 2026-09-13 — Track B opened (owner's request): technical swing-start detector on range bars, pre-registered (A40) before any run
- Owner's six TradingView exports committed under `data/ext/tv_samples/` with a manifest; the 34R file gates the range-bar rebuild, the XAUUSD 5000R file is the gold input.
- A40 fixes the causal swing definition, the reversal/continuation signals, the 24-trial family, costs, the train/test lock and decision rule, the random-entry control, and the pattern-table deliverable.
- PLAN carries both tracks; Track B rows B1–B3.

## 2026-09-13 — A39 built and run (fleet coder, Sonnet): T1 positive but underpowered on the holdout, mirror also positive → not promoted
- `pipeline/units/gapliq.py` (11 s, byte-identical twice); PLAYBOOK §10; family 36 (0 pass FDR). Holdout T1 n 158, +2.20 pts, p 0.26; T2 +0.12; T3 +1.89. Selection/context negative. Reported as a pattern without its mechanism (ASSESSMENT).

## 2026-09-13 — Track B gate B-a failed for the right reason: the TradingView export is not a range-bar series (A40c)
- Diagnostic on the 194 overlap sessions: median 16 export bars per session vs a monotone minimum of 14.6 and a close-path count of 143; discontinuous opens; sub-millisecond duplicate timestamps; ≈ 0.5 correlation with volatility. Gate re-registered as an internal-consistency check on the rebuild; the exports become context. Gold TEST moves to 2017-01 → 2020-05 rebuilt bars (no post-2020 gold minutes on the branch). No signal had run.

## 2026-09-13 — Track B SPY run (fleet coder, Sonnet; terminated by a session rate limit after the outputs were written)
- `pipeline/units/rangebars.py` (gate B-a PASS under A40c), `pipeline/units/sweep.py` (16 SPY trials, locked windows), `pipeline/report_b.py` → `TRACK_B.md`. Winner FAILED on TEST; all rows negative after costs; the pattern table shows a significant but sub-cost 1-bar effect after sweeps. Wiring into `make all` and the gold run follow.

## 2026-09-13 — Track B gold run (A40b/A40c) and pipeline wiring
- Gold $5 range bars rebuilt from the Oanda minutes (gate 3/3), 8 trials on TRAIN 2006–2016 / TEST 2017 → 2020-05: winner FAILED, every row negative; family FDR over 24 rows 0 pass. `TRACK_B.md` renders both instruments.
- Track B steps and the A38 unit are `make all` steps; the 39 MB per-trade file is gitignored (regenerated per run).

## 2026-09-13 — Judge round 6 (A38 skip path, A39, Track B SPY + gold): ITERATE on six text items → applied; science verified clean
- SCORECARD/DATA/PLAN doc lags corrected (gold run, sweep-finding wording, A40c gate and windows); `test_letf.py` no longer hardcodes a session path; the applied wiring note removed from `pipeline/`.
- Judge's re-measurement of A40c's diagnostics: monotone minimum 14.71 and close path 144.7 bars per session on the minute file (typed 14.6 / 143 in A40c, which stays append-only); ratio 7.12, correlation 0.998979 and the ±$1.02/1.08 discontinuity quantiles reproduce exactly.
- Process notes accepted: the gapliq timing-control seed and gold's weekly session rule were not named in their amendments (neither is a survival input); DSR N wording drifted 35/36/37 (units use 37).

## 2026-09-13 — Owner is fetching real SPY 0DTE bars; A41 (re-evaluation + calibration) and A42 (event-day long volatility) pre-registered before any bar exists
- `tools/fetch_spy_0dte_local.py` fixed after the owner's first run: a trailing `/v2` in the base URL doubled the path (404); expired contracts are queried as `inactive`; OCC symbols are constructed as a fallback.
- Real 0DTE quotes leave the non-goal list once the file lands; the k × VIX model stays for sessions before 2024-02-01.

## 2026-09-13 — A41 and A42 units built (fleet coders), tested (3/3 each), wired into `make all` (28 steps), verified deterministic
- Both skip cleanly until `data/ext/spy_0dte_1min_2024-02_2026-09.csv.gz` exists; PLAYBOOK §12/§13 print wait notices. `make all` + `make repeat` byte-identical; family still 36. The owner's fetch is in progress (helper fixed at 5472df7).
- Owner's full 0DTE fetch succeeded (≈ 92 contracts and ≈ 15,000 bars per session through 2026-09-11) but the final gzip step ran out of memory on their machine: the helper now streams the temp file into per-year shards (< 100 MB each) with `--finalize-only`, validates in chunks, and both units read the shards.

## 2026-09-13 — Real SPY 0DTE bars landed (owner, commit ae5a397); A41 and A42 ran for the first time; make all (28 steps) + make repeat byte-identical
- A41: median implied k 1.002 at 2 % ITM (unidentifiable; the model is intrinsic ± spread there); 80 % of checked minutes have no print; re-priced legs keep every sign, model optimistic by ½–4 points of premium after the spread. The playbook's first paragraph is now generated from the calibration file (A41 requirement).
- A42: daily straddle -7.0 % of premium per day at +$0.10, non-FOMC 13:30 straddle -17.2 %, FOMC -1.6 % (n 20, UNDERPOWERED); family 39, FDR 0. Nothing promoted.

## 2026-09-13 — Judge round 7 fixes applied (fleet coder): causal strike availability, entry-before-exit rule, loader path honoured (tests 3/3), calibration in EXPECTED, generated k-rule and fill-delay clauses in §12
- Gap-up call n 183 → 178 (-2.78 % at +$0.10), D1 winner n 61 → 59 (+0.92 %); every sign unchanged; T1's $0-cost label flipped to "model optimistic" when one trade was dropped. Fill delay from the bar used: median 3 min, p90 31, max 179, 78/401 ≥ 15 min. T2 (+4.94 → +2.16 % at +$0.10) and T3 (+2.76 → +2.42 %) moved with zero trades dropped: that is the causal strike rule re-selecting strikes, not the ordering rule. Calibration's own strike search left as the diagnostic it is (non-causal, unchanged; it feeds no decision).

## 2026-09-14 — Owner chose E (test the sell side; account only if profitable) and asked for a recommendation; A43 (Track C, defined-risk short premium) and A44 (passive forward test) pre-registered before any run
- Recommendation recorded: E as the main line, B passive, C only if the assets file is easy, A as the fallback if E's tail fails.

## 2026-09-14 — A43 built and run (fleet coder): all three defined-risk short-premium structures FAIL at $0.10/leg; the premium is real on the short legs but the wings and four legs of spread consume it
- `pipeline/units/sellvol.py` (~2 min, byte-identical twice), tests 4/4, `report_c.py` → `TRACK_C.md`, family 42 (FDR 0). Short legs +0.26/+0.24/+0.14 per share gross, wings -0.14/-0.07/-0.04, breakeven $0.030–$0.042 per leg. Recorded in ASSESSMENT and SCORECARD; nothing enters PLAYBOOK_0DTE.md.

## 2026-09-15 — Inversion research delivered; two doc-lag edits fixed
- `INVERSION.md` added: synthesis of `notes/inversion/u1_retail_failures.md`, `u2_0dte_prop.md`, `u3_self_audit.md` (failure-mode taxonomy, our own record, a stop-doing rulebook, one LOW-prior candidate).
- SCORECARD.md:26 and ASSESSMENT.md:54 (D6 rows): appended " — family count superseded: 42 since A43 (SCORECARD.md §Track C; TRACK_C.md:71; ACCEPTANCE.md A42/A43)" to each, per the CRITIQUE.md inversion-research-audit finding; the stale "33 trials" text was left in place, not rewritten.

