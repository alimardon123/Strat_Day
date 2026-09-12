# SCORECARD.md — where every done-statement stands, and the trial ledger

Updated 2026-09-12 (end of Phase 3, first pass). Evidence files under `out/`; regenerate with `make all`.

## Gates

| Gate | Status | Evidence |
|---|---|---|
| (a) pinned install + fetch with manifests | PASS | `requirements.txt`, `data/raw/manifest_*.json` |
| (b) session builder: DST probe, calendar, ≥300 bars | PASS on Oanda (31/31 months) and histdata (16/16) | `out/dst_probe_*.csv`, `out/calendar_*.csv` |
| (c) reproduction of both threads' headline numbers | PASS 14/14 | `out/gate_c.csv`, `out/gate_c.log` |
| (d) run-twice byte identity | PASS (`make repeat`) | Makefile |

## Done-statements

| # | Status | Where it stands |
|---|---|---|
| D1 | PRE-REGISTERED, holdout pending `data/ext` | 16 configurations scored on 2013-01→2020-05-13 (`out/reconcile_candidates.csv`). Winner `15:00|both|vixmove_fixed` (calendar-day Sharpe 0.57, n 93, win 63%, +5.10 pts/trade net). All four VIX-gated "both" variants tie within 0.10; Thread A's magnitude/put-only variants rank 5–12. No configuration passes BH-FDR at 10% on the selection window (best p 0.078). |
| D2 | BLOCKED on `data/ext` minute file | Holdout code path = `pipeline/insample.py` with the holdout window; see DATA.md |
| D2b | DONE (finding) | `out/xmarket_*.csv`: SPX +0.022%/trade (n 499, p 0.16), DAX +0.019% (n 602, p 0.27), EuroStoxx −0.033% (n 548, p 1.0) — no shrinkage on DAX, sign flip on EuroStoxx |
| D3 | IN-SAMPLE DONE, holdout pending | `out/insample_execution.csv`: gap-up call market −0.12 pts/signal → limit at 0.25/0.50 ATR +0.91/+1.04 pts (fill 86%/74%, p < 0.001); winner +5.10 → +5.67 (p 0.31, n 93) |
| D4 | IN-SAMPLE DONE, holdout pending | `out/insample_summary.csv`, `out/insample_sizing.csv`: winner +11.5% of premium/trade (cash settlement, 1 pt), 5 of 93 trades lose 100%; gap-up call +1.23% at 1 pt, −0.85% at 3 pt; k moves the 13:00 leg by < 0.2 points; SPY 15:55 exit roughly halves both |
| D5 | PARTIAL: baseline reproduced (Sharpe 0.85/1.08 vs 1.12/1.35; maxDD −6.7% vs −6.10%; BAB universe differs), extension through 2026-03 for S1/S5/S8, to 2020-05 for S12; S2/S3/S6/S13 stop 2017-11-10 pending the ext ETF panel | `out/own_account_*.csv` |
| D6 | PARTIAL | trial ledger below; controls and DSR in `out/reconcile_candidates.csv` |
| D7 | PASS for the current steps | `make all` / `make repeat` |

## Trial ledger (this run)

| Family | Trials | Where counted |
|---|---|---|
| Last-hour momentum configurations | 16 (12 rankable + 4 literal-threshold reference rows) | `out/trials.csv` |
| Gap-up call | 1 (pre-registered by Thread A; historical N 1,098) | — |
| Historical N for the momentum family (DSR context) | 42 = 16 + 4 it22 setups + 22 step17 tests | ACCEPTANCE rule 5 |
| Execution offsets, spreads, k, sizing limits | reporting cuts, not trials (A31) | — |

## Findings that changed the contract

- Thread B's published holdout was DST-misaligned (CRITIQUE #2); corrected rows in CHANGELOG.
- Thread A's option-level numbers reproduce only under ask-entry + intrinsic settlement (A30).
- Thread B's Sharpe convention (per-trade × √252) overstates annualised Sharpe by √(252 / trades per year); the ranking uses calendar-day Sharpe.
