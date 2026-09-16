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

Judge round 8 (2026-09-14) added a process finding: an orchestrator edit to run_all's step list appended a path to the wrong occurrence (the command line, not EXPECTED) and a clean `git status` hid it because out/ was not regenerated; caught only by the judge's confirmation pass. Standing guard: import run_all and execute the touched step once before committing any STEPS/EXPECTED edit. Count 1.


## Addendum 2026-09-15 (A45-propagation round) — two findings reach count 2, so both qualify for a framework edit

**"A close-out claim outran the diff" reaches count 2.** Judge round 5 (2026-09-13) logged this at count 1. It
recurred here as the review's highest-severity defect: the write-up asserted in `PLAYBOOK_0DTE.md` §15 that "the
pre-A45 minimum account in §6 are NOT restated" while the same commit restated it ($325k → $382,070), and it
published that new figure at the retired x = 4 % convention after A45 had taken force. Note the shape: the earlier
instances were a claim outrunning an evidence FILE; this one outran the DIFF, in a sentence specifically about what
the change did. Framework edit now earned, cheap and mechanical: **before asserting in any deliverable that
something was left untouched, run `git diff` on that thing.** One command would have caught this. Count 2.

**"A `run_all` list edit that a clean `git status` hides" reaches count 2.** Judge round 8 (2026-09-14) logged this
at count 1 with the guard "import run_all and execute the touched step once before committing any STEPS/EXPECTED
edit". It recurred here in a new form: `out/sizing_forward.csv` was added to the unconditional `EXPECTED` list while
the unit writes a zero-byte file when `data/ext` is absent, and `EXPECTED` fails on empty files — so `make all`
would have failed on a no-ext checkout. Caught by orchestrator review before the reviewer saw it. The round-8 guard
would NOT have caught it: executing the touched step passes, because this container HAS `data/ext`. Guard sharpened:
**a `run_all` STEPS/EXPECTED edit must be reasoned about, and where cheap exercised, in BOTH data configurations —
with and without `data/ext` — because `EXPECTED` and `EXPECTED_HOLDOUT` encode exactly that distinction and the
present configuration only ever exercises one of them.** Count 2.

Both findings share a root: the checks that ran were the checks the change made easy to run. The two edits above are
deliberately mechanical for that reason — `git diff` on the thing you claim you did not touch, and the configuration
you are not currently in.

Observation, not a finding: the round's largest defect was found by an adversarial reviewer that re-derived every
published number and mutation-tested the new unit test, which proved two mutants survived a green suite (a wrong-bar
level read, and a 4× understatement of required capital). A suite that only restates the implementation reports PASS
on both. Mutation-testing a new test suite is now the cheapest known way to tell a real test from a tautology here.

## Addendum 2026-09-16 (A47 round) — "the claim outran the evidence" reaches count 3, twice in one amendment chain

The finding folded in on 2026-09-15 at count 2 recurred twice more within a single day, and the second time
inside the very amendment written to correct the first.

**Occurrence 3a — a scope claim asserted, never checked.** `pipeline/units/power.py` stated in a docstring that
no candidate existed with a published summary row but no trade-level series. The FVG family was exactly that,
and its omission inverted the headline of the analysis that shipped on it. One `ls out/*trades*.csv` compared
against the families in `out/trials.csv` would have caught it. The 2026-09-15 guard ("run `git diff` on anything
you claim you left untouched") is the same shape but does not cover this case, so it is generalised:
**a completeness claim — "no X exists", "every Y is included", "nothing else was touched" — must be produced by
enumerating the set, never asserted from memory of having looked.** Count 3.

**Occurrence 3b — the correction repeated the sin.** A47a was written partly to withdraw hand-typed numbers that
breached A47's own "generated, none typed" rule. A47a then hand-typed two numbers of its own, one of which
reported a range whose upper end had the wrong sign (-0.004 where the generated maximum is +0.026). This is
worth its own line because the failure survived heightened attention: the amendment's author knew the rule, was
actively enforcing it against a previous draft, and still typed. Guard: **when an amendment withdraws a typed
number, the replacement text may cite only a generated column by name, or state no number at all.** Count 4 for
the class; it is now the most frequent finding in this ledger by a wide margin.

**Observation on what did work.** The adversarial reviewer that found 3a re-derived every published formula
independently, reproduced all 37 rows from raw inputs, and mutation-tested the new test suite (23 mutants, 11
killed, 12 survived). The 12 survivors included the cost convention — the precise failure the suite's docstring
claimed to guard. Mutation testing has now twice in two days distinguished a real suite from a tautology where
a green run could not. It is cheap and it should be standard for any new test file in this repo, not an
occasional reviewer's initiative.

## Addendum 2026-09-16 (A48 round) — a new finding: a pre-registration can be wrong in a way pre-registration does not protect against

The Crucible's central guard is that a criterion fixed before the run cannot be bent to fit the result. A48
honoured that completely: the answer condition, the exit grid, the scope and the refutation clause were all
fixed in a commit before any code existed, and none was touched afterwards. The criterion was still wrong,
because it compared a quantity that SCALES with the treatment (minimum detectable effect, which tracks the stop
width) against a bar that does not (a fixed cost in index points). Pre-registration made the error immovable; it
did not make it visible.

This is a different failure from the ledger's dominant one. "A claim outran the evidence" (now count 4) is a
reporting failure caught by checking the claim against the artifact. This is a DESIGN failure: the artifact and
the claim agreed perfectly, and both were wrong together. An adversarial reviewer checking the output against
the amendment would have passed it, because the output DID satisfy the amendment.

Counterfactual guard, offered for a second occurrence before it becomes a framework rule: **before registering a
threshold, ask what happens to it in the limit of the treatment.** Here, "what is the MDE as the stop goes to
zero?" answers itself immediately — it goes to zero, so the criterion is vacuous. A one-line limit check on any
registered threshold would have caught this before the commit. Count 1.

**What saved the round was a different guard entirely**, and it is worth naming because it was chosen for an
unrelated reason. A48 forbade the unit from computing any profitability statistic, to prevent a re-tune on the
holdout. That restriction meant that when the criterion turned out to be vacuous, there was nothing to walk
back: no candidate had been ranked, no exit rule chosen, no mean seen. A safeguard against one failure mode
contained the blast radius of another. The general form is worth keeping in mind: a restriction that keeps a
result from being *actionable* until it is *understood* is cheap insurance against criteria that turn out not to
mean what they appeared to mean.
