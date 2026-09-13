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
| — | Real 0DTE quotes, GEX filter, post-2018 cross-market | non-goal | — | Unobtainable in this environment (recorded in ACCEPTANCE.md) |

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

