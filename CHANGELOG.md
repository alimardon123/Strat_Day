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
