# SCORECARD.md — where every done-statement stands, and the trial ledger

Updated 2026-09-13 (after the Phase 4 tribunal, the Phase 6 judge round 1 and their repairs; verifier 11/11). Evidence files under `out/`; regenerate with `make all`.

## Gates

| Gate | Status | Evidence |
|---|---|---|
| (a) pinned install + fetch with manifests | PASS | `requirements.txt`, `data/raw/manifest_*.json` |
| (b) session builder: DST probe, calendar, ≥300 bars | PASS on Oanda (31/31 months) and histdata (16/16) | `out/dst_probe_*.csv`, `out/calendar_*.csv` |
| (c) reproduction of both threads' headline numbers | PASS 14/14 | `out/gate_c.csv`, `out/gate_c.log` |
| (d) run-twice byte identity | PASS (`make repeat`, re-run after every repair round; per-run tables cleared first) | Makefile |
| (e) ext (holdout) path proven on a synthetic file | PASS 6/6: identity of 850 trades, dividend, roll, manifest refusal | `out/gate_e.csv` |

## Done-statements

| # | Status | Where it stands |
|---|---|---|
| D1 | PRE-REGISTERED, holdout pending `data/ext` | 16 configurations on 2013-01→2020-05-13 (`out/reconcile_candidates.csv`). Winner after the Phase 4 tie-break repair: `15:00|both|vixmove_exp` (calendar-day Sharpe 0.49, n 145, win 63%, +3.12 pts/trade net; expanding rule, no fitted parameters). The four VIX-gated two-sided variants tie within 0.10; Thread A's magnitude/put-only variants rank 5–12. No trial passes BH-FDR at 10% across the 23-trial family. |
| D2 | BLOCKED on `data/ext` (minute file + manifest); path proven end to end on a synthetic feed by the judge (round 2) | `make all` runs `pipeline/insample.py 2020-06-01 2026-09-11 HOLDOUT`, `pipeline/reconcile.py holdout` and the full-sample D4 step automatically when `sessions.ext_present()`; verdict per signal in `out/holdout_summary.csv` (`label_final` after the family FDR in `pipeline/trials.py`, `timing_control_pct` reported); per-year rows in `out/holdout_by_year.csv` carry n, win, net pts, net %, `opt_mean_s1/s2/s3` (option return at spread 1/2/3), worst trade, `worst_day_pts`, `mae_worst_pct`, day-block p; the 15 POST-SELECTION holdout rows land in `out/reconcile_candidates.csv` (`window`, `label`); full-sample tables in `out/fullsample_*.csv`; see DATA.md |
| D2b | DONE (finding) | `out/xmarket_*.csv`: SPX +0.022%/trade (n 499, p 0.16), DAX +0.019% (n 602, p 0.27), EuroStoxx −0.033% (n 548, p 1.0) — no shrinkage on DAX, sign flip on EuroStoxx |
| D3 | IN-SAMPLE DONE, holdout pending | `out/insample_execution.csv`: improvement decomposed into cost assumption and price effect. Gap-up call: market −0.14 pts/signal → limit at 0.25/0.50 ATR +0.52/+0.70 (improvement +0.66/+0.84, of which cost part 0.34/0.30, p 0.002/0.004). Winner: +3.12 → +3.34 at 0.25 ATR (improvement +0.22 = cost 0.36 − adverse selection 0.14, p 0.38). |
| D4 | IN-SAMPLE DONE, holdout pending | `out/insample_summary.csv`, `out/insample_sizing.csv`: winner +7.3% of premium/trade (cash settlement, 1 pt), median +5.5%, 5 of 145 trades lose 100%; sizing at 4% → +5.8%/yr, worst year −2.0% (IN-SAMPLE); gap-up +1.2% at 1 pt, negative at 3 pt; k irrelevant for the last-hour leg; combined book 2%/trade (77 two-position days) |
| D5 | PARTIAL: baseline test-window EQUAL_8 Sharpe 0.99 / two-bucket 0.97 (Thread A 1.35 / 1.40; maxDD −5.4% vs −5.26%); full-window book is EQUAL_available(1-8) 0.78 because S13 starts 2009 and S2/S3 need a 252-day warm-up; extension to 2026-03 for S1/S5/S8 (3–4 sleeves, Sharpe 0.65); S2/S3/S6/S13 stop 2017-11-10 pending the ext ETF panel; VXX/VXZ bridge correlations 0.9987 / 0.9875 | `out/own_account_*.csv`, `out/own_account_bridge.csv` |
| D6 | DONE for what ran | `out/trials.csv`: 23 trials, one BH-FDR across all (0 pass); both controls and DSR at both N in `out/reconcile_candidates.csv` |
| D7 | PASS for the current steps; holdout step wired and conditional | `make all` / `make repeat` (byte-identical, 64 files) |

## Trial ledger (this run)

| Family | Trials | Where counted |
|---|---|---|
| Last-hour momentum configurations | 16 (12 rankable + 4 literal-threshold reference rows) | `out/trials.csv` |
| Gap-up call | 1 (pre-registered by Thread A; PSR at N = 1; DSR at N = 1,099) | `out/trials.csv` |
| Cross-market (SPX, DAX, EuroStoxx) | 3 | `out/trials.csv` |
| Flow-with-a-deadline candidates | 3 (all negative, killed) | `out/trials.csv` |
| Historical N for the momentum family (DSR context) | 42 = 16 + 4 it22 setups + 22 step17 tests | ACCEPTANCE rule 5 |
| Execution offsets, spreads, k, sizing limits | reporting cuts, not trials (A31) | — |

## Findings that changed the contract

- Thread B's published holdout was DST-misaligned (CRITIQUE #2); corrected rows in CHANGELOG.
- Thread A's option-level numbers reproduce only under ask-entry + intrinsic settlement (A30).
- Thread B's Sharpe convention (per-trade × √252) overstates annualised Sharpe by √(252 / trades per year); the ranking uses calendar-day Sharpe.
