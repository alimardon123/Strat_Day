# PLAN.md — ranked task list (living; updated at the end of every iteration)

Source ranking: `research/CLAUDE.md` §6, re-ordered by risk (hardest first) per Phase 3.

| Rank | Task | Phase | Owner | What would kill it |
|---|---|---|---|---|
| 1 | Harness: session builder for every feed (UTC / Eastern-DST → America/New_York), DST probe, calendar reconciliation, reproduction gates (step17 table; re-implemented it22 numbers; `mh.sanity()`; observability clock), run-twice reproducibility | 2 | single owner | A reproduction gate that cannot be met within tolerance → ESCALATE (spec or data differs from the threads') |
| 2 | Fetch pre-2020-06 data from the four GitHub sources into `data/raw/` with a manifest | 2 | fleet (one unit per source) | Proxy blocks a source that answered `ls-remote` in Phase 0 → DATA.md, stop |
| 3 | Reconcile the momentum spec: 8 candidates, fixed decision rule, stats_engine + random-entry + n_eff + DSR | 3 | single owner | No candidate positive on the holdout at p < 0.10 → valid outcome, report year-by-year and the likely reason |
| 4 | Holdout by year for the reconciled spec and the gap-up call, thresholds frozen | 3 | fleet (one unit per year) | `data/ext` minute file absent → stop after Phase 2 |
| 5 | Execution model (step8 method) on every surviving signal | 3 | single owner | No survivor → apply to the reconciled winner for information, labelled |
| 6 | 0DTE pricing and sizing: BS at k×VIX, k ∈ {1.0,1.3,1.6} × spread ∈ {1.0,2.0}, worst day/year at 3/4/5% limits | 3 | single owner | Any Sharpe > 3 → bug hunt before reporting |
| 7 | Own-account: 8 sleeves through 2026-09, VXX/VXZ splice, S13 cap, VIX−RV extension | 3 | fleet (one unit per sleeve) | ETF panel absent → stop; splice correlation < 0.95 on overlap → report the seam, do not splice |
| 8 | Cross-market check of the gap-up call on DAX/EuroStoxx 2010–2018 (histdata) | 3 | fleet (one unit per market) | Effect shrinks > 50% or flips sign → recorded as a finding, not a kill of D2 |
| 9 | Flow-with-a-deadline candidates, last hour only: Russell reconstitution, S&P quarterly rebalance, opex pin/unpin, month-end, 15:50 imbalance | 3 (budget permitting) | fleet (one unit per candidate) | Plateau rule; < 200 trades → UNDERPOWERED |
| — | Real 0DTE quotes, GEX filter, post-2018 cross-market | non-goal | — | Unobtainable in this environment (recorded in ACCEPTANCE.md) |

## Status log

- 2026-09-12 Phase 0: files written; `data/ext` both MISSING; Phases 0–2 proceed without them.
