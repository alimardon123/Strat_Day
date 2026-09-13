# RETRO.md — Crucible retro of this run (confirmed ledger)

Run: trading-research continuation, branch `claude/modest-pasteur-oyzqyh`, judged at `9efc78d`
(judge round 3 DONE for the data that exists), blocked at `4a78e44` (BLOCKED.md). Owner confirmed
all six findings on 2026-09-13 ("confirm all") and chose option A (push `data/ext/`, then resume).

## Verdict (cold, against ACCEPTANCE.md)

| Done-statement | Verdict | Observation |
|---|---|---|
| D1 reconciled specification | PARTIAL | Selection rule fixed and reproduced from the CSV; winner logged before any holdout data; the confirmation half cannot run without `data/ext` |
| D2 holdout by year | MISSED (blocked on input) | Path proven twice on a synthetic feed; zero real holdout trades |
| D2b cross-market | HELD | Three markets measured; EuroStoxx sign flip recorded |
| D3 execution model | PARTIAL | In-sample decomposition done; holdout table only in the synthetic run |
| D4 playbook | PARTIAL | Every table a byte-identical re-render; §7 reads PENDING |
| D5 own account | PARTIAL | Baseline 0.99 vs Thread A's 1.35, gap explained by the gap-up sleeve's cost model; four sleeves stop 2017 without the ETF panel |
| D6 statistical bookkeeping | HELD | 23 trials, one FDR, both controls, DSR at both N |
| D7 reproducibility | HELD | 66 files byte-identical; 126 with the synthetic feed |

Stranger's first impression: a careful, fully reproducible pipeline whose headline section says
PENDING, because the input that decides the question never arrived.

## Ledger (confirmed 2026-09-13; occurrence counts start at this run)

| # | Class | Finding | Evidence | Counterfactual edit | Count |
|---|---|---|---|---|---|
| 1 | PROMPT | A blocking input known unobtainable at plan time was scheduled after the build instead of before it | Plan mode established on day one that post-2020 minute bars could not be fetched here; the prompt carried two conflicting stop rules ("stop at end of Phase 2" vs "finish every unit that does not need it"), so seven phases and three judge rounds ran on in-sample data | One rule: first output = the exact file spec plus the local fetch script and a hard stop for the owner; the build resumes only when the files land | 1 |
| 2 | FRAMEWORK | Gate (e) tested loading, not the whole path; "holdout path unwired" survived two tribunal rounds until a judge built a synthetic feed and ran `make all` on it | CRITIQUE Phase 4 #1 → judge round 1 #1/#2 → closed in round 2 by the judge's own synthetic run | When a required input is absent, the harness phase must run the full pipeline on a synthetic stand-in with byte-identical repeat before any tribunal | 1 |
| 3 | PROMPT | "Tables are generated, never typed" was met from Phase 5, but typed numbers in prose beside those tables recurred in three rounds at falling severity, including a bound wrong by 2× | Phase 4 #14 (7.37), judge round 2 N5 (A7 bound 0.08 vs measured 0.16), round 3 J3-1/2/4/5 | Extend D7 to "every number in a playbook cites an out/ file or is generated" | 1 (×3 within the run) |
| 4 | FRAMEWORK (positive) | Reproduction gates on the prior threads' published numbers caught the three defects that mattered most | Thread B's DST-misaligned holdout, its 2.6× Sharpe convention, Thread A's settlement convention — all found by gate (c) before any new result was reported | Keep; generalise to "reproduce the prior under its own conventions, then restate under yours" | 1 |
| 5 | FRAMEWORK (positive) | `make repeat` byte-identity plus per-run clearing caught orphan files, a superseded winner's stale tables and a hard-coded FDR sentence | judge round 1 #5, round 2 N5 | Keep | 1 |
| 6 | EXECUTION (observation) | The account rate limit killed the first fleet fan-out (5 coders, 4 critics); the second half of the run delegated all implementation to Sonnet coders and a verifier without incident | ASSESSMENT gap table; CHANGELOG | None (budgeting note) | 1 |

Fold-in rule: framework edits wait for a second occurrence of the same finding in a later run.

## Addendum 2026-09-13 (after the owner's data landed)

Finding 2 ("a synthetic stand-in that did not exercise the real format") recurred three times inside this run once real data arrived: tz-aware dividend stamps crashed the loader (R1), the DST probe's statistic failed on a feed with sparse pre-market prints (R2), and the SPY dividend series leaked into the SPX-index era and flipped the pre-registered winner (R4, severity 8, the class the Phase 4 tribunal had named). Occurrence count for finding 2 becomes 2 (one per run-phase where it bit: synthetic proof, real data). Counterfactual edit sharpened: a synthetic stand-in must be built from a real sample of the supplied format (a real dividends file, a real single-venue minute file) and the gate must assert that the native era is byte-identical with and without the stand-in.

Judge round 5 (2026-09-13) added a process finding for the ledger: twice in this run a close-out claim outran the diff (round-3 doc lag; round-4 notes N5/N6 recorded ADOPTED with no change behind them, caught by the next fresh-context judge). Candidate framework rule, pending a second run: the verifier diffs the claim against the change set, not only the tests. Count 1.

