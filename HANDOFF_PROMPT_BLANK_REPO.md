# HANDOFF_PROMPT_BLANK_REPO.md — for a FRESH agent in an EMPTY repo

Generated 2026-09-19. Self-contained: references no file from the prior run.
Everything between the fences is the prompt. Paste it whole.

```
# MISSION
Build, from an empty repository, a research programme that answers one question honestly:
**is there a tradeable intraday edge my prop account can actually take?** You are not
inheriting code. You are inheriting HARD-WON KNOWLEDGE from a prior run of this same question,
stated below as given facts. Do not re-derive it, and do not re-test what it already closed —
both waste the multiple-testing budget every future result must pay for.

Reference class: Marcos Lopez de Prado's backtesting standards — a deflated Sharpe carrying the
trial count, purged/embargoed validation wherever a parameter is chosen, and multiple-testing
control across everything tested. Any result that would not survive those is not a result.

Mode: autonomous. Record assumptions in ACCEPTANCE.md rather than stalling. Never wait on me
mid-run.

# THE CONSTRAINT THAT GOVERNS EVERYTHING — restate it in your first output
My prop account permits ONLY 0DTE options, long-only, naked calls or puts. No selling, no
spreads, no futures, no shares, no overnight holds. Daily loss limit 3-5%. Every deliverable
must be tradeable under it. A separate unconstrained "own-account" track may be explored, but
it is secondary and must be labelled as such.

# WHAT IS ALREADY KNOWN — treat as given, do not spend the run rediscovering
A prior programme ran 48 pre-registered trials across three data sets under this exact
constraint. Zero passed a family-wide Benjamini-Hochberg correction at 10%. Its measured
findings, which you inherit:

1. STRIKE. Both prior research threads independently concluded the strike must be ~2% in the
   money. At-the-money loses ~53% per trade at a 17% hit rate; out-of-the-money ~50.6% median.
2. THE TRAP THAT FOLLOWS. At 2% ITM with under an hour to expiry, time value is exactly zero
   (verified against real option bars: implied k = 1.002, IQR 0.016). So vega and theta are
   both zero there and the instrument is PURE DELTA — economically a leveraged intraday index
   position with a hard 2% stop, paying 1-2 index points of spread. The constraint therefore
   forces a binary choice: a pure-delta instrument needing a directional edge, or a vol-exposed
   strike that pays the variance premium daily. There is no third option.
3. THE ONE LARGE EFFECT. The 0DTE variance risk premium: a straddle buyer loses 3.6-11% of premium per session before costs, 7-17% after a $0.10 round trip. It is on
   the SELL side, which the account forbids. Selling it with defined risk was tested and fails
   at realistic costs (-8.6%/-5.0%/-6.8% of max loss per structure at $0.10/leg; breakeven near
   $0.03/leg).
4. DIRECTIONAL SIGNALS. 48 trials across last-hour momentum, opening gaps, fair-value gaps,
   overnight-loss rebounds, intraday forced-flattening, cross-market, month-end/opex/Russell
   flows, and event-day volatility. None survived. This is empirical, not proven — directional
   prediction is not impossible, that programme did not find it.
5. BOUNDED EXITS DO NOT RESTORE POWER. Per-trade dispersion IS the barrier width (sd/b = 0.989
   at a 5-point stop). A tighter stop lowers the detection threshold and simultaneously raises
   the break-even win rate from 52.5% to 60-70%, because cost does not scale with the barrier.
   It shrinks noise and edge together. Do not propose this.
6. OPTION-FLOW SIGNALS NEED QUOTES. A tick-rule aggressor signal built from option TRADE prints
   is ~86% just the underlying's own direction (corr 0.63 with the same-minute return), because
   calls and puts are priced off spot. Aggressor inference requires NBBO quotes. Without a quote
   file, every signed-flow construct on option data is confounded. Do not propose one.
7. POWER IS THE BINDING CONSTRAINT, NOT IDEAS. A one-trade-per-day hold-to-close design on this
   instrument has per-trade dispersion of 22-51 index points, so a 200-trade sample detects
   nothing below ~4-9 points — several times the 1-2 point cost it must clear. Designs that
   reach adequate power fire MANY times per session over a SHORT horizon; the one family that
   did (intraday stop/target, 282-959 holdout trades) had dispersion of 4-7 points, detected
   effects down to ~0.4 points, looked, and found +0.026 points per trade.

**Design implication you should act on:** any candidate you register must be built to return a
VERDICT, not an "underpowered" label. Estimate its detectable effect BEFORE registering it, and
if a 200-trade sample cannot resolve an effect smaller than the trading cost, redesign it or
drop it.

# DATA — I supply it; you never substitute
Work only from files I commit under `data/ext/`. Do not substitute daily bars for minute bars,
do not synthesise data, and do not silently narrow a window. If a file is missing, finish every
phase that does not need it, write DATA.md naming the exact file, columns, timezone and date
range still needed, commit, and stop there.

Minimum to run anything: 1-minute bars of the underlying, columns `ts,open,high,low,close,volume`
with `ts` in UTC as `YYYY-MM-DD HH:MM:SS`, covering at least the 09:30-16:00 ET regular session,
plus a manifest naming the instrument. If the feed is an ETF rather than the index, I will also
supply a dividends file and you must state the point-scale conversion you applied.
Highest-value additions, in order: (a) 0DTE option NBBO quotes by contract-minute — the only
thing that makes finding 6 testable; (b) 0DTE option trade bars; (c) daily VIX.
State in DATA.md which of these you have before Phase 3.

# DEFINITION OF DONE
1. A reproducible pipeline: one command regenerates every published table and document, and a
   CLEAN CLONE of the repo reproduces them byte-identically.
2. Every configuration tested is counted as a trial in one family-wide BH-FDR at 10%, with no
   exceptions and no quiet exclusions.
3. Every candidate is pre-registered in ACCEPTANCE.md, in its own commit, BEFORE its code exists,
   naming: the mechanism (who must trade and when), every parameter, the windows, the trial
   count, the kill criterion, the honest prior, and what result would REFUTE it.
4. A playbook in which every number is generated from output files, never typed, and which states
   its pricing model in its first paragraph.
5. An honest assessment: the bar that was set, where each done-statement landed, and every gap
   with a root-cause hypothesis. Declaring success without the gap report is a failure state.

# THE SURVIVAL RULE — six conditions, ALL required
A signal survives only if all hold; otherwise report it with its p-value and the label that
applies:
1. net mean > 0 at 1.0 point round-trip cost;
2. block-bootstrap one-sided p < 0.05 (n_boot 2000, fixed seed; blocks = trading day for pooled
   intraday statistics, calendar month for one-observation-per-day series);
3. passes BH-FDR at 10% across EVERY configuration tested in the run;
4. positive excess over a matched random-entry control;
5. deflated Sharpe > 0.95 at N = the run's trial count;
6. at least 200 holdout trades — below that, report the p-value and label it UNDERPOWERED,
   never "surviving".
Implement this as ONE function that every report calls. Do not let a report re-implement a
narrower version of it.

# NUMERIC BUDGETS — measured, never estimated
- Costs: 0DTE options 0.5-2.0 index points round-trip, results always shown at 1.0 AND 2.0.
- Any Sharpe above 3.0 on price-only data triggers a mandatory bug hunt before it is reported.
- Position sizing is set by the worst single day against the daily loss limit, not by Sharpe.
- Per-trade risk 1% of account equity, giving floor(daily_limit / 1%) full-loss attempts per day.

# NON-GOALS — each carries an expiry condition; revisit ONLY when it is met
- Bounded-exit variants to restore statistical power. EXPIRES: never; this is arithmetic (fact 5).
- Signed option-flow constructs from trade prints. EXPIRES when an NBBO quote file is supplied.
- Selling premium in the constrained account. EXPIRES only if I relax the constraint in writing.
- ATM or OTM strikes on a directional signal. EXPIRES: never (fact 1).
- Conditioning or regime-switching layered on a failed signal. EXPIRES: never.
- Live or paper execution. EXPIRES when I say so.
- A UI.

# HARD RULES — from the prior run's own post-mortem. Non-negotiable.
R1. Verification must be SUFFICIENT, not merely necessary. Two Phase-2 gates are mandatory before
    any strategy runs: (a) a CLEAN CLONE reproduces all outputs byte-identically — re-running in
    place does not test this; (b) a POSITIVE control — inject a known edge of known size and confirm
    the full survival rule flags it once it is large enough. A check that cannot fail (that the injected
    mean comes back) is not a control, nor is a null control alone. Without (b), negatives are uninterpretable.
R2. The survival rule has exactly one implementation (see above). Contract and code may not drift.
R3. Every non-goal carries an explicit expiry condition. When any new data arrives, re-read the
    non-goal list and reopen anything whose stated reason has lapsed — explicitly, never silently.
R4. Before registering ANY threshold or criterion, enumerate its inputs and name, for each, what
    in the experiment actually MOVES it. Checking its limits is not enough: a criterion whose
    inputs your treatment cannot reach is unevaluable, and you must know that before the run.
R5. A completeness claim — "no X exists", "every Y is included", "nothing else was touched" —
    must be produced by ENUMERATING the set, never asserted from memory. Run `git diff` on
    anything you claim you left untouched.
R6. Every pooled statistic is DATE-CLUSTERED before it is believed, not after. In the prior run
    this turned an apparent t = 5.66 edge into -0.956 with bootstrap p 0.97 — the sign flipped.
    Overlapping windows and high-volume days manufacture significance. Never skip this, not even
    for a quick exploratory bound.
R7. Any new signal is reported with a distributional summary as a NAMED field: min, median, max,
    and the fraction of observations at the bounds. A degenerate distribution mentioned only in
    prose nearly shipped an invalid construct.
R8. Never re-tune on the holdout. Promoting a result you chose after seeing holdout data is the
    one thing this contract forbids outright, however good the number looks.

# PROTOCOL
Phase 0 — Restate the mission. List every ambiguity and resolve each with a recorded assumption.
  Write ACCEPTANCE.md (done-statements, survival rule, budgets, non-goals with expiries),
  DATA.md (what is present, what is missing and its exact spec), and PLAN.md (ranked tasks, each
  with what would kill it).
Phase 1 — ARCHITECTURE.md with an ownership map: mark every concern COUPLED (one owner,
  sequential) or INDEPENDENT (safe to parallelise). Only INDEPENDENT work goes to sub-agents.
Phase 2 — Harness before strategies, each step a gate: session/timezone builder with a DST probe
  and a holiday reconciliation; determinism; the clean-clone reproduction gate (R1a); the positive
  control (R1b). Nothing strategic runs until all pass.
Phase 3 — Build hardest-first. No stubs: an item is fully tested or explicitly moved to non-goals
  with a reason.
Phase 4 — Tribunal. A FRESH-CONTEXT adversarial reviewer receives only ACCEPTANCE.md, the outputs
  and the diff, and scores each done-statement with the exact flaw and location. Attack
  specifically for: thresholds tuned on the holdout, look-ahead at session boundaries and DST
  transitions, pooled statistics without clustering, any Sharpe above 3, and any table not
  generated from outputs.
Phase 5 — Repair. Root cause before code. Refute a wrong critique with evidence. Any change
  claimed behaviour-preserving must pass a zero-regression gate.
Phase 6 — Integration on the full sample: by year, by volatility regime, at both cost levels.
Phase 7 — Ship: the pipeline, the playbook, and the honest assessment.

Budget: 5 review rounds per task, 3 for integration. On exhaustion write BLOCKED.md with the gap,
the root cause and my options — never silently ship. Plateau rule: two rounds without improvement,
kill the task in PLAN.md with the reason and move on. Commit and push at every phase end; never
commit while the pipeline is mid-run if it regenerates its output directory.

# THE HONEST CLOSE
If nothing survives, that is a valid and important outcome, and it is the prior's most likely
one. Deliver the year-by-year evidence, the most likely reason, and what to test next. Do not
soften the bar and do not manufacture a pass. A negative result backed by a validated positive
control is worth more than a positive result backed by nothing.

# FLEET AND SKILLS
Check your available skills and commands before starting. Delegate implementation to sub-agents;
do review and judgement yourself. Use a fresh-context adversarial reviewer before anything is
published — in the prior run the reviewer caught defects that inverted a headline. Mutation-test
every new test suite: twice there a green suite was proven a tautology, once while the code read
the wrong bar and once while it understated required capital fourfold. If a `fleet` skill is
available, use it for the delegate-review-fix-judge loop. If `karpathy-guidelines` is available,
read it before writing pipeline code — surgical edits, every changed line traceable to an
amendment. If `crucible-retro` is available, run it at the end on the assessment.

# START
Phase 0 now. First output: restate the constraint, confirm which data files are present, list
your assumptions, and write ACCEPTANCE.md, DATA.md and PLAN.md. Do not fetch data or run any
strategy before Phase 2's gates pass.
```
