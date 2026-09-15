# SCORECARD.md — where every done-statement stands, and the trial ledger

Updated 2026-09-13 10:10 UTC — HOLDOUT RUN ON REAL DATA (owner's `data/ext/`, commit 781180b). Both pre-registered signals FAILED. Evidence files under `out/`; regenerate with `make all`.

## Gates

| Gate | Status | Evidence |
|---|---|---|
| (a) pinned install + fetch with manifests | PASS | `requirements.txt`, `data/raw/manifest_*.json` |
| (b) session builder: DST probe, calendar, ≥300 bars | PASS on Oanda (31/31 months) and histdata (16/16) | `out/dst_probe_*.csv`, `out/calendar_*.csv` |
| (c) reproduction of both threads' headline numbers | PASS 14/14 | `out/gate_c.csv`, `out/gate_c.log` |
| (d) run-twice byte identity | PASS (`make repeat`, re-run after every repair round; per-run tables cleared first) | Makefile |
| (e) ext (holdout) path proven on a synthetic file, then on the real feed | PASS 7/7: identity of 850 trades, tz-aware dividends, dividend SCOPE (native era untouched), roll, manifest refusal | `out/gate_e.csv` |
| (f) ETF panel coverage and bridge decision | see `out/gate_etf.csv` (added after judge round 4 B1) | `pipeline/gate_etf.py` |

## Done-statements

| # | Status | Where it stands |
|---|---|---|
| D1 | OUTCOME: "no reconciled specification survives" — the pre-registered winner FAILED the holdout (n 274, −0.14 pts, Sharpe −0.14, p 1.0); selection rows byte-identical to the pre-registration | 16 configurations on 2013-01→2020-05-13 (`out/reconcile_candidates.csv`). Winner after the Phase 4 tie-break repair: `15:00|both|vixmove_exp` (calendar-day Sharpe 0.49, n 145, win 63%, +3.12 pts/trade net; expanding rule, no fitted parameters). The four VIX-gated two-sided variants tie within 0.10; Thread A's magnitude/put-only variants rank 5–12. No trial passes BH-FDR at 10% across the 33-trial family (25 before the 8 A36 FVG trials joined). |
| D2 | DONE — FAILED × 2 (winner −0.14 pts/trade, gap-up −1.90; p 1.0; both n ≥ 200, so not UNDERPOWERED); data 2020-07-27 → 2026-09-11 (1,526 sessions) | `make all` runs `pipeline/insample.py 2020-06-01 2026-09-11 HOLDOUT`, `pipeline/reconcile.py holdout` and the full-sample D4 step automatically when `sessions.ext_present()`; verdict per signal in `out/holdout_summary.csv` (`label_final` after the family FDR in `pipeline/trials.py`, `timing_control_pct` reported); per-year rows in `out/holdout_by_year.csv` carry n, win, net pts, net %, `opt_mean_s1/s2/s3` (option return at spread 1/2/3), worst trade, `worst_day_pts`, `mae_worst_pct`, day-block p; the 15 POST-SELECTION holdout rows land in `out/reconcile_candidates.csv` (`window`, `label`); full-sample tables in `out/fullsample_*.csv`; see DATA.md |
| D2b | DONE (finding) | `out/xmarket_*.csv`: SPX +0.022%/trade (n 499, p 0.16), DAX +0.019% (n 602, p 0.27), EuroStoxx −0.033% (n 548, p 1.0) — no shrinkage on DAX, sign flip on EuroStoxx |
| D3 | DONE — holdout: limit entries hurt the winner (−0.56 to −1.45 pts/signal, adverse selection) and help the gap-up call by +0.25 to +0.31 pts but it stays negative | `out/insample_execution.csv`: improvement decomposed into cost assumption and price effect. Gap-up call: market −0.14 pts/signal → limit at 0.25/0.50 ATR +0.52/+0.70 (improvement +0.66/+0.84, of which cost part 0.34/0.30, p 0.002/0.004). Winner: +3.12 → +3.34 at 0.25 ATR (improvement +0.22 = cost 0.36 − adverse selection 0.14, p 0.38). |
| D4 | DONE — headline: winner +0.08 % of premium per trade (1 pt, cash), −0.48 % (2 pt); gap-up −1.3 %; worst holdout year −10 % to −17 % at 3–5 % limits; not tradeable as measured | `out/insample_summary.csv`, `out/insample_sizing.csv`: winner +7.3% of premium/trade (cash settlement, 1 pt), median +5.5%, 5 of 145 trades lose 100%; sizing at 4% → +5.8%/yr, worst year −2.0% (IN-SAMPLE); gap-up +1.2% at 1 pt, negative at 3 pt; k irrelevant for the last-hour leg; combined book 2%/trade (77 two-position days) |
| D5 | DONE for the data that exists (ETF panel to 2026-09-11; post-2017 book EQUAL_available(4-8) 0.52, two-bucket 0.56): baseline test-window EQUAL_8 Sharpe 0.99 / two-bucket 0.97 (Thread A 1.35 / 1.40; maxDD −5.6% vs −5.26%); BAB now runs on Thread A's cleaned 626-name universe (reconstructed from it5/it5b; universe count reproduced exactly; portfolio Sharpe unchanged, so the universe was not the gap); the gap is EXPLAINED: S12 gap-up at the contract's 0.42-pt ES cost (Thread A: 0.35 bp/side) is −0.37 vs +0.32 on the test window, every other sleeve matches within 0.2; full-window book is EQUAL_available(1-8) 0.78 because S13 starts 2009 and S2/S3 need a 252-day warm-up; extension to 2026-03 for S1/S5/S8 (3–4 sleeves, Sharpe 0.65); S2/S3/S6/S13 stop 2017-11-10 pending the ext ETF panel; bridge correlations old-VXX/VIXY 0.9987, old-VXZ/VIXM 0.9875, new-VXX/VIXY 0.9829 (bridged), new-VXZ/VIXM 0.8775 (refused; VIXM is the mid-term leg post-2017) | `out/own_account_*.csv`, `out/own_account_bridge.csv`, `out/gate_etf.csv` |
| D6 | DONE | `out/trials.csv`: 33 trials (23 + the 2 pre-registered holdout tests + the 8 A36 FVG trials), one BH-FDR across all (0 pass); PBO 0.73 reported per A37 (not a gate); both controls and DSR at both N in `out/reconcile_candidates.csv` — family count superseded: 42 since A43, then 45 since A46 (SCORECARD.md §Track C and §A46; TRACK_C.md:71; ACCEPTANCE.md A42/A43/A46) |
| D7 | PASS on real data | `make all` / `make repeat` byte-identical: 128 files with the owner's feed |

## Trial ledger (this run)

| Family | Trials | Where counted |
|---|---|---|
| Last-hour momentum configurations | 16 (12 rankable + 4 literal-threshold reference rows) | `out/trials.csv` |
| Gap-up call | 1 (pre-registered by Thread A; PSR at N = 1; DSR at N = 1,099) | `out/trials.csv` |
| Cross-market (SPX, DAX, EuroStoxx) | 3 | `out/trials.csv` |
| Flow-with-a-deadline candidates | 3 (all negative, killed) | `out/trials.csv` |
| Pre-registered holdout tests | 2 (both FAILED) | `out/holdout_summary.csv` |
| Owner's fair-value-gap setup (A36) | 8, pre-registered before any run; all negative on selection and holdout at 1 pt; none survives; midpoint entry beats random-time entry but not the cost | `out/fvg_candidates.csv` |
| PBO of the D1 selection (A37, reporting statistic) | CSCV 16 blocks: PBO 0.73 (null 0.85 — floor for near-duplicate configurations) | `out/pbo.csv` |
| Historical N for the momentum family (DSR context) | 42 = 16 + 4 it22 setups + 22 step17 tests | ACCEPTANCE rule 5 |
| Execution offsets, spreads, k, sizing limits | reporting cuts, not trials (A31) | — |

## Findings that changed the contract

- Thread B's published holdout was DST-misaligned (CRITIQUE #2); corrected rows in CHANGELOG.
- Thread A's option-level numbers reproduce only under ask-entry + intrinsic settlement (A30).
- Thread B's Sharpe convention (per-trade × √252) overstates annualised Sharpe by √(252 / trades per year); the ranking uses calendar-day Sharpe.

## A39 — overnight-loss liquidation rebound (3 trials, pre-registered 2026-09-13; family 36)

| Trial | Holdout n | Net pts @1 pt | p (day) | Control | Fingerprint | Verdict |
|---|---|---|---|---|---|---|
| T1 call 10:00 after overnight loss | 158 | +2.20 | 0.26 | beats day-selection and timing controls | T2 < T1 holds; T3 ≤ 0 FAILS | UNDERPOWERED, not promoted |
| T2 call 09:31 (timing fingerprint) | 158 | +0.12 | 1.00 | — | — | not a candidate |
| T3 put 10:00 after overnight gain (mirror) | 154 | +1.89 | 0.43 | — | positive → mechanism asymmetry absent | not a candidate |

Family-wide BH-FDR at 10 % over 45 trials (42 before A46's three joined): 0 pass (`out/trials.csv`).

## Track B — swing-start detector on range bars (A40/A40c; 24-trial family, FDR on its own; SPY 16 and gold 8 both run, 24 of 24 FAILED)

| Item | Result |
|---|---|
| Gate B-a (A40c: exact range, continuity, monotone minimum, determinism) | PASS on $0.34 (236,300 bars) and $1.00 (37,493 bars); the owner's export is context only |
| TRAIN winner | `spy100` continuation|L20|R2, TRAIN Sharpe 0.26 (n 1429) |
| TEST verdict | FAILED: n 1933, -0.024 %/trade, p 1.00, DSR 0.00; 0 of 16 pass FDR |
| All 16 TEST rows | net negative at 2 bp/side; win rates within 3 points of stop ÷ (stop + target) |
| Pattern finding | 1-bar move in the rejection direction after a reversal-shaped sweep: +0.16 bar-ranges vs +0.005 unconditional (p < 0.001), and +0.05 after a close-through; gone by 20 bars |
| Gold (A40c) gate | PASS 3/3 (48,077 bars, 741 weeks); context: rebuild 25.5 bars/week vs the owner's export 175 |
| Gold TRAIN winner → TEST | `continuation|L20|R2` FAILED: n 864, -0.0275 %/trade, p 1.00; all 8 gold rows negative |
| Family FDR (24 TEST rows) | 0 pass; DSR at N = 24 ≈ 0 for every row |

## A41 / A42 — real SPY 0DTE prices (2024-02-01 → 2026-09-11; family 39; nothing promoted)

| Item | Result |
|---|---|
| Calibration at 2 % ITM (`out/realopt_calibration.csv`) | median implied k 1.002, IQR 0.016; k unidentifiable at 2 % ITM; missing-minute share 80 % |
| Re-evaluation at +$0.10 (`out/realopt_reeval.csv`, after the round-7 clarification) | D1 winner +0.92 % (model +1.39; n 59); gap-up -2.78 % (-2.08; n 178); T1 +1.60 % (+3.73); all signs unchanged, all p > 0.2, sub-window; fill delay median 3 min, p90 31, 78 of 401 trades ≥ 15 min late |
| A42 E1 daily straddle 09:31 | n 646, -7.0 % of premium, p 1.00 — premium rich, as registered |
| A42 E2 FOMC 13:30 vs E3 non-FOMC | E2 n 20 -1.6 %, E3 n 608 -17.2 %, difference +15.7 pts, p 0.64; UNDERPOWERED, not promoted |

## Track C — A43 defined-risk short 0DTE premium (owner's option E; family 45; nothing promoted)

| Trial ($0.10/leg) | n | Mean % of max loss | Win % | Worst day ($100k, 4 % rule) | Max drawdown | Verdict |
|---|---|---|---|---|---|---|
| S1 iron butterfly 09:31 | 592 | -8.6 | 50 | −$6,080 | 198 % | FAILED |
| S2 iron butterfly 13:30 | 557 | -5.0 | 51 | −$5,035 | 104 % | FAILED |
| S3 iron condor 09:31 | 443 | -6.8 | 52 | −$8,010 | 114 % | FAILED |

Decomposition (per share, pre-cost): short legs +0.26 / +0.24 / +0.14; wings -0.14 / -0.07 / -0.04; breakeven cost per leg $0.030 / $0.042 / $0.025. FDR over 45 trials: 0 pass.

## A46 — intraday forced-flattening rebound (3 trials, pre-registered 2026-09-15; family 42 → 45)

| Trial | Holdout n | Net pts @1 pt | p (day) | Control | Fingerprint | Verdict |
|---|---|---|---|---|---|---|
| U1 call 11:00 after a large morning decline (the hypothesis) | 144 | -3.28 | 1.00 | below day-selection control (excess -2.96 pts); above the timing control | U2 < U1 FAILS (U2 -1.08 > U1 -3.28: the mild-decline band lost LESS than the extreme one, the opposite of the predicted dose-response); U3 <= 0 holds | UNDERPOWERED (n 144 < 200, ACCEPTANCE.md:66); net negative and dose-response fingerprint inverted; not promoted |
| U2 call 11:00, mild-decline band (A46a's causal dose-response replacement for the look-ahead 09:45 fingerprint) | 299 | -1.08 | 1.00 | — | — | not a candidate |
| U3 put 11:00 after a large morning rise (mirror) | 166 | -1.27 | 1.00 | — | negative, so the mirror does not fire as A39's did; but at n 166 and t -0.52 this is consistent with noise and does not establish the asymmetry the mechanism predicts | UNDERPOWERED (n 166 < 200, ACCEPTANCE.md:66); not a candidate |

FIX 1 (D2-class correctness fix, applied before this run's verdict was read): the "09:30 session open" base price had been read from `signals.day_table`'s first-bar-of-day open rather than the literal mod-570 bar; on 4 sessions with no mod-570 bar (2005-09-13 and the three March-2020 circuit-breaker days) the first bar was a post-halt reopen near the session low, inverting the sign of two limit-down crash mornings into large measured RISES that fired U3 and both won. Fixed to require the literal 09:30 bar and exclude sessions lacking it (`n_skipped`, not silent). Effect on the counted SELECTION U3 row (`out/flatten_candidates.csv`, `out/trials.csv`): n 107 → 105, net_pts_cost1 +1.6766 → +0.2962, p_boot_month 0.2655 → 1.0000 — the trial's own number got WORSE, the correct direction for a correctness fix; nothing else was adjusted to compensate. HOLDOUT U1 is numerically unchanged (n 144, -3.282639 pts, both before and after); HOLDOUT U3 shifts by one session (n 165 → 166, -1.4976 → -1.2696 pts) as a side effect of the same 4 corrected sessions feeding the whole-history expanding percentile pool, not because any HOLDOUT session itself starts late — this does not change U1's verdict.

The pre-registered 20-session reporting cut (A31, `ACCEPTANCE.md:491-492`) is byte-identical to the registered 250-session gate on both decision windows — every SELECTION and HOLDOUT column for U1/U2/U3 matches exactly (verified against a scratch copy of `pipeline/units/flatten.py` with only `MIN_PRIOR_SESSIONS` changed 250 → 20, run to a scratch path outside `out/`; only the CONTEXT rows move, e.g. U1 n 254 → 269, -2.30 → -2.05 pts) — because the first 250 sessions fall entirely inside the CONTEXT window (2005-2006), so the warm-up choice can only affect the background window and bought no power on either decision window.

Family-wide BH-FDR at 10 % over 45 trials: 0 pass (`out/trials.csv`).

