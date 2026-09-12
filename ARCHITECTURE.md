# ARCHITECTURE.md — components, interfaces, vocabulary, ownership map

Written in Phase 1 (2026-09-12). Settled decisions stay settled; reopen only with new
evidence logged in CHANGELOG.md.

## Candidates scored

| Candidate | Description | Verdict |
|---|---|---|
| C1 — extend in place | Add new loaders to each thread's scripts and run each thread's own engine on its own session builder | Rejected: two session builders and two timezone conventions make "identical data" impossible; edits `research/` in place; every reproduction gate would compare a moved target |
| **C2 — one pipeline, borrowed engines** | A new `pipeline/` with a single session builder producing one canonical minute frame; the threads' engines (`stats_engine.py`, `mh.backtest/sanity`, `step8.limit_test`, `step15.bs_call/bs_put`, `it8/it9/it11` sleeves) are imported or copied unchanged behind thin adapters | **Chosen**: simplest design that satisfies full functionality (identical data, one stats standard) and keeps the threads' code reproducible |
| C3 — rewrite from scratch | New engine, new stats, new pricer | Rejected: violates "do not rewrite what works"; reproduction gates become meaningless because nothing old runs |

Principle check on C2: simplicity (one frame, one builder); efficiency (parquet cache,
vectorised session ops, numpy hot loops kept); power (reuses two validated engines);
full functionality (every done-statement maps to a module below); versatility (feeds
differ only inside `sessions.py`).

## Components and interfaces

```
data/raw/                 fetched, gitignored, rebuilt by `make fetch`; MANIFEST.md lists source URL, commit/date, row counts
data/ext/                 supplied by the user, committed (spec in DATA.md)
out/                      every generated table; the only source for playbook numbers

pipeline/fetch.py         orchestrates pipeline/units/fetch_*.py → data/raw/*.parquet
pipeline/sessions.py      canonical minute frame (COUPLED)
pipeline/daily.py         daily frames: SPX from minutes; ETF/stock panels; VIX prior-close join; SPY dividend adjustment
pipeline/signals.py       the 8 momentum candidates + gap-up call → trade tables (COUPLED)
pipeline/stats.py         adapter over research/thread_B_inversion/stats_engine.py + n_eff + random-entry control + deflated Sharpe (COUPLED)
pipeline/options.py       Black-Scholes at k×VIX, 2% ITM strike, spread, P&L in % premium, sizing at 54% loss-at-stop, worst day/year (COUPLED)
pipeline/execution.py     step8 limit-entry model, per-signal metric, fill window bounded by the close
pipeline/own_account.py   8 sleeves (it8/it9/it11 + re-implemented S13), vol targeting, equal weight, regime tables; sleeves run as fleet units
pipeline/gates.py         Phase 2 gates (a)–(d); prints PASS/FAIL per gate
pipeline/run_all.py       regenerates out/ end to end; `make repeat` diffs a second run
pipeline/units/*.py       fleet units: `python -m pipeline.units.<name> --in <path> --out <file>`; empty output on failure
```

### Canonical minute frame (`sessions.build(feed, path) -> DataFrame`)

| Column | Meaning |
|---|---|
| `ts_ny` | tz-aware America/New_York timestamp of the bar start |
| `date` | NY session date |
| `mod` | minute of day (570 = 09:30 … 959 = 15:59) |
| `open high low close volume` | as supplied; `volume` may be tick count (Oanda), 0 (histdata) or IEX-only (SPY) |
| `feed` | `oanda` \| `histdata` \| `ext` |

Rules: convert by the feed's verified convention (Oanda UTC; histdata Eastern with DST;
ext UTC), keep 09:30 ≤ time < 16:00, drop sessions with < 300 bars and list them in
`out/sessions_dropped.csv`, never carry anything overnight. The DST probe and calendar
reconciliation live here.

### Vocabulary

- **session** — one NY trading date.
- **prev_close** — last RTH close of the prior session (dividend-adjusted when the feed is SPY).
- **decision bar** — the bar whose close the signal reads (15:00 or 15:30 or 13:00).
- **entry_px** — open of the bar after the decision bar (Thread A rule, applied to every candidate).
- **exit_px** — last RTH close of the session.
- **gross / net** — underlying points before / after the round-trip cost.
- **premium return** — option P&L as a fraction of premium paid.
- **trial** — any configuration whose statistic is computed; all are counted in `SCORECARD.md`.

### Fleet unit contract

`python -m pipeline.units.<name> --in <path> --out <file>`: one input path, one output
file, deterministic (seeded), writes an empty file and exits 0 on any failure.
Unit output schemas:

- `fetch_<source>` → parquet with the raw columns plus `source_url`, `fetched_at`.
- `holdout_year` → `out/holdout_<year>.csv`: signal, n, win, mean_net_1pt, mean_net_2pt, worst_trade, worst_day, p_boot.
- `xmarket_<market>` → `out/xmarket_<market>.csv`: same columns as step7's table.
- `sleeve_<name>` → `out/own_account_sleeve_<name>.csv`: date, ret (daily return at 10% vol target, net of cost).
- `flow_<candidate>` → `out/flow_<candidate>.csv`: candidate, n, mean_net, p_boot, control_mean.

## Ownership map

| Concern | Class | Owner | Why |
|---|---|---|---|
| Session builder, DST probe, calendar | COUPLED | orchestrator | Every downstream number depends on it |
| Momentum reconciliation (8 candidates, decision rule) | COUPLED | orchestrator | Candidates share thresholds, entry rules and the trial count |
| Stats adapter (bootstrap, FDR, n_eff, control, DSR) | COUPLED | orchestrator | One inference standard |
| Option pricer, sizing | COUPLED | orchestrator | One pricing model across every table |
| Execution model | COUPLED | orchestrator | Reads the reconciled trade tables |
| Playbooks, ASSESSMENT | COUPLED | orchestrator | Single voice, generated tables |
| Data acquisition per source (4) | INDEPENDENT | fleet | Disjoint outputs |
| Holdout evaluation per year | INDEPENDENT | fleet | Reads frozen trade tables, writes one file each |
| Cross-market validation per market (2010–2018) | INDEPENDENT | fleet | Disjoint inputs |
| Own-account sleeve per sleeve (8) | INDEPENDENT | fleet | Disjoint outputs; combination is orchestrator-owned |
| Flow-deadline candidate per candidate | INDEPENDENT | fleet | Disjoint |

Only INDEPENDENT rows go to `/fleet`. At most 3 units at once on this 4-core box.

## Reproducibility contract

- Seeds: `stats_engine.RNG` (seed 11) is used as-is; every other RNG is `np.random.default_rng(<fixed>)` named in the module.
- Floats are written with `float_format="%.6f"`; rows sorted by explicit keys; no dict-order dependence.
- `make all` then `make repeat` → `diff -r out/ out_repeat/` must be empty.
- Environment pinned in `requirements.txt` (pandas 2.2.3 — the threads' code predates pandas 3's copy-on-write and string-dtype changes).
