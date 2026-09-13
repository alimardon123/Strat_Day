# ASSESSMENT.md — the bar, where each done-statement landed, every gap with a root cause

Status: Phase 7 SHIPPED WITH THE HOLDOUT RUN (2026-09-13 10:10 UTC). The owner supplied `data/ext/`
(commit 781180b); three real-data defects were repaired and gated first (CRITIQUE R1, R2, R4); the
selection rows were proven byte-identical to the pre-registered state; then `make all` produced the
holdout. Verdict: **both pre-registered signals FAILED the survival rule on 2020-07-27 → 2026-09-11.**
D1's contractual outcome is "no reconciled specification survives". This file states what is and is not
established; nothing below is softened.

## Holdout result (the headline; every number from `out/holdout_*.csv`, rendered in PLAYBOOK_0DTE.md §7)

| Signal | n | win % | net pts/trade (1 pt) | net % | cal-day Sharpe | p (month / day) | excess over control | option, % of premium (1 pt / 2 pt, cash) | label |
|---|---|---|---|---|---|---|---|---|---|
| `15:00\|both\|vixmove_exp` (pre-registered winner) | 274 | 53.6 | −0.14 | −0.011 | −0.14 | 1.00 / 1.00 | +0.002 % | +0.08 / −0.48 | FAILED |
| `13:00\|call\|gap>0.3%` (Thread A) | 452 | 50.9 | −1.90 | −0.038 | −0.58 | 1.00 / 1.00 | −0.019 % | −1.28 / −1.78 | FAILED |

Data window: minute data present 2020-07-27 → 2026-09-11 (1,526 sessions; the feed starts after the
contract window's 2020-06-01, DATA.md). Winner by year (net pts/trade): 2020 −5.6, 2021 −7.3, 2022 +3.2
(n 119, p 0.08), 2023 +7.2 (n 10), 2024 −0.9 (n 11), 2025 +2.6, 2026 −0.9. At the 4 % daily limit the
winner's expected annual return on the holdout is +0.15 % with a worst year of −13.7 %; the combined book
is −2.2 %/yr. The execution model makes the winner worse out of sample (limit entries −0.56 to −1.45 pts
per signal: adverse selection, not cost).

The 15 POST-SELECTION rows (`out/reconcile_candidates.csv`, never promoted): every VIX-gated configuration and every 15:30 configuration except `15:30\|put\|mag` (+0.05 pts) is
negative on the holdout; the only positive rows are the three magnitude-gated ones, led by Thread A's original `15:00\|put\|mag` (+1.94 pts, Sharpe 0.48, p 0.10 / 0.11, excess
+0.046 %). It ranked 9th of 12 in-sample; one of 16 rows at p ≈ 0.1 is what chance produces; it is
reported, not promoted, and would need its own pre-registration on data that does not yet exist.

Most likely reason (as the contract asks): the reconciled edge was crisis-loaded in-sample (2008–2012 and
Feb–May 2020 carried most of it); out of sample the high-VIX years 2020 H2 and 2021 were the worst
years; 2022 carried the gains (119 of 274 trades), 2023 and 2025 are positive on 10 and 32 trades, and at a
1-point cost the mean over the window is zero. Thread B's construction (the
VIX gate, prior-close move, both directions) did not carry; Thread A's magnitude/put-only shape did
marginally better but not significantly. What research/CLAUDE.md §6.6 suggests next — flows with a
deadline — was already tested here (month-end, opex, Russell day: all negative). The owner's own
fair-value-gap setup is pre-registered (A36) and being tested as a separate family.

## The bar

ACCEPTANCE.md v2: seven done-statements, a six-condition survival rule, a fixed decision rule with
one pre-registered holdout test, López de Prado + both threads' guards, every number generated
from `out/` by `make all` and byte-identical on `make repeat`.

## Where each done-statement landed

| # | Landed | Evidence |
|---|---|---|
| D1 | Pre-registered. 16 configurations on 2013-01→2020-05-13; winner after the Phase 4 tie-break repair `15:00\|both\|vixmove_exp` (expanding-tercile rule, no fitted parameters; n 145, +3.12 pts/trade net, calendar-day Sharpe 0.49). Thread B's construction (VIX gate, move from the prior close, both directions) beats Thread A's (magnitude from the open, put-only) in every cross; the entry time (15:00 vs 15:30) is a wash. No trial passes BH-FDR at 10% across the 33-trial family (25 before the A36 FVG trials joined) — the reconciliation answers *which shape*, not yet *whether it is real*. | `out/reconcile_candidates.csv`, `out/reconcile_decision.md` |
| D2 | DONE on real data: FAILED for both signals (table above); per-year rows with option returns at spreads 1/2/3, worst day and MAE in `out/holdout_by_year.csv`; the 15 post-selection rows published; data window reported, not filled. | `out/holdout_summary.csv`, `out/holdout_by_year.csv`, PLAYBOOK §7 |
| D2b | Done as a finding: the gap-up call is +0.022%/trade on SPX (p 0.16), +0.019% on DAX (p 0.27), −0.033% on EuroStoxx (p 1.0) over 2010–2018. Marginal where it exists; not universal. | `out/xmarket_*.csv` |
| D3 | Done in-sample; holdout pending. With the exit half of the spread still charged, limit entry at 0.25 ATR adds +0.66 pts per signal to the gap-up call (0.34 of it a cost assumption, 0.31 price improvement net of adverse selection, p 0.002) and only +0.22 to the winner (0.36 cost assumption minus 0.14 adverse selection, p 0.38). Thread B's "largest single improvement" is real for the 13:00 leg and mostly a cost assumption for the last-hour leg. | `out/insample_execution.csv` |
| D4 | DONE: the headline is the holdout table (+0.08 % of premium per trade at 1 pt for the winner, −0.48 % at 2 pt; gap-up −1.3 %); sizing at 3/4/5 % limits shows worst years of −10 % to −17 %; full-sample tables rendered under IN-SAMPLE + HOLDOUT. Nothing in the playbook is tradeable as measured. | PLAYBOOK_0DTE.md §7, `out/holdout_d4_*.csv` |
| D5 | DONE for the data that now exists: the ETF panel extends S2/S3/S6/S13 to 2026-09-11. Bridge (A13, measured on the real overlaps, `out/own_account_bridge.csv`): old-VXX ↔ VIXY 0.9987, old-VXZ ↔ VIXM 0.9875, new-VXX ↔ VIXY 0.9829 → VXX bridged to the real Series B note; new-VXZ ↔ VIXM 0.8775 → the VXZ bridge is REFUSED by the 0.98 rule (178 of 234 Series B closes in 2018 are stale) and VIXM is the mid-term leg from 2017-11-13, labelled as such. Judge round 4 found that the first run had silently dropped both real notes (a NaN in the splice scale); gate (f) now asserts panel coverage and the bridge decision. Baseline 0.99 vs Thread A's 1.35 explained by the gap-up sleeve's cost model; BAB on Thread A's cleaned 626-name universe. | `out/own_account_*.csv`, `out/gate_etf.csv`, OWN_ACCOUNT.md |
| D6 | Done for what ran: 33 trials in one family-wide BH-FDR (none pass; 16 momentum + gap-up + 3 cross-market + 3 flow + 2 holdout + 8 FVG); DSR at N = 12 and N = 42 (FVG: N = 33); PBO reported per A37 (gap-up: PSR and N = 1,099); both controls with the signal's own direction base; month/day blocks. | SCORECARD.md, `out/trials.csv` |
| D7 | PASS: `make all` regenerates every table (gates b, c, e; D1; D3/D4; [D2 when ext present]; D5; D2b; VRP; flow; trials; report), clears per-run tables first so orphans cannot survive, fails on empty outputs; `make repeat` byte-identical after every repair round; both playbooks are re-renders of `pipeline/report.py` (verified by the fleet verifier and the judge). | Makefile, `pipeline/run_all.py` |

## Owner-proposed fair-value-gap setup (A36) — pre-registered, tested, no trial survives

`pipeline/units/fvg.py`, 8 trials (side × R × break-of-structure), 5-minute bars, entry at the box
midpoint, stop beyond the box, take profit at 1× or 2× the stop distance, 1.0-point cost
(`out/fvg_candidates.csv`). Every trial is net negative in every window: on the selection window
(2013 → 2020-05) the eight means run from −0.23 to −0.73 points per trade (win rates 63–66 % at R = 1,
37–40 % at R = 2, n 307–859); on the holdout (2020-07 → 2026-09) from +0.03 to −1.14 (the one positive
row, `short\|R1\|bos_off`, is +0.03 pts at p 0.48 on 959 trades). Block-bootstrap p is 1.0 for every
row but that one; DSR at N = 33 is 0. What the test does say in the owner's favour: the midpoint entry
beats a same-day random-time entry with the same stop and target in almost every row (`frac_seeds_beaten`
≈ 1.0), so the box has location value — but the gross edge is below one index point per trade, which is
the round-trip cost of the cheapest 0DTE contract. Verdict: no trial survives; the setup is reported and
killed under the plateau rule. Fill rates 46–65 %: a third to a half of boxes are never touched at the
midpoint.

## Overnight-loss forced-liquidation rebound (A39) — pre-registered, tested, not promoted

Three trials (`out/gapliq_candidates.csv`, PLAYBOOK §10). On the holdout the hypothesis trade T1 (call from 10:00 after an
overnight loss below the expanding 10th percentile) is positive: n 158, win 54.4 %, +2.20 pts at
1 pt (+1.20 at 2 pt), day-block p 0.26, above its day-selection control (-1.07)
and its timing control (+0.02); the timing fingerprint holds (T2 from 09:31: +0.12 pts < T1).
But n < 200 → UNDERPOWERED, p is far from 0.05, and the mirror T3 (put from 10:00 after an overnight GAIN) is also positive
(+1.89 pts, p 0.43) — the asymmetry the forced-liquidation mechanism predicts is absent, so what the
holdout shows is symmetric post-2020 reversal of large overnight gaps, not liquidation exhaustion. In the selection window T1
is negative (-2.41 pts, n 121) and in the context window too. Per the A39 rule T1 is "a pattern
without its mechanism": reported, never promoted. It is the only Track A candidate with a positive holdout row above both
controls; the honest reading is a candidate for a forward test (option B) with a symmetric spec, not a trade.

## Track B — swing-start detector on range bars (A40/A40c): SPY tested, no trial survives; the sweep effect is real but a fraction of a bar

Range bars rebuilt from the branch's 1-minute SPY at $0.34 and $1.00 (gate B-a PASS on internal consistency; the owner's
TradingView export proved not to be a range-bar series, A40c). 16 SPY trials, train/test locked at 2023-07-01. Every TEST row
is net negative at 2 bp/side (best -0.013 %/trade, worst -0.037 %); each is slightly better than
its random-entry control (controls ≈ -0.040 %) and every win rate sits within a few points of the random-walk
expectation stop ÷ (stop + target). The pre-registered TRAIN winner (`spy100` continuation|L20|R2, TRAIN Sharpe
0.26) FAILED on TEST (n 1933, -0.024 %, p 1.00); FDR 0 of 16.
The pattern table (`out/trackB_pattern_table.csv`) answers the owner's question directly: after a reversal-shaped sweep of the
prior 10-bar extreme on $0.34 bars the NEXT bar moves +0.16 bar-ranges in the rejection's direction
(+0.011 %) against +0.005 unconditional, p < 0.001, and after a close-through
+0.05 bar-ranges; by 20 bars the difference is gone. The swing start is measurable, but its
size (≈ $0.05–0.07 on SPY) is a quarter of the round-trip cost, so it is a description of price, not a trade. Gold runs under A40b/A40c.

## Probability of backtest overfitting of the selection itself (A37)

`out/pbo.csv`: with 12 rankable configurations on the selection window, CSCV over 16 blocks (12,870
splits) gives PBO 0.73 — the in-sample best configuration ranks below the out-of-sample median in 73 %
of splits, and its out-of-sample Sharpe is 0.05 against 0.25 for the average configuration
(degradation slope −1.04). The per-column shuffled null gives 0.85, not 0.5, because the twelve
configurations are near-duplicates whose own means and variances survive the shuffle; the statistic is
reported, not used as a gate. It says what the holdout then confirmed: the ranking among these
configurations carried no out-of-sample information.

## Findings that matter more than the tables

1. **Thread B's published holdout was mis-timed.** Its Oanda 2019–20 code detected one open
   minute on naive UTC stamps; every winter session measured 14:30→15:00 ET instead of the last
   half hour, and those sessions carried almost all of the +0.0975%/trade. The DST-correct row is
   n 90, +0.078% (bar-close fill) / +0.133% (next-bar fill), Sharpe 1.28 / 2.05 by Thread B's
   convention, p 0.17 / 0.10 — the sign holds, the published magnitude was an artefact. Reproduced
   exactly in legacy mode (`out/gate_c.log`).
2. **Thread B's Sharpe convention inflates.** Per-trade Sharpe × √252 on ~37 trades a year
   overstates the annualised figure by ≈ 2.6×; its 2.50 discovery Sharpe is ≈ 0.96 in calendar-day
   terms. Every Sharpe here is calendar-day.
3. **Thread A's option numbers reproduce only under "buy at the ask, settle at intrinsic"**
   (+2.97 vs +2.77; +1.35 vs +1.14, the same +0.21 offset on both legs). That convention is
   legitimate for PM-cash-settled SPX and is what the playbook uses; the half-on-exit convention
   (SPY) gives +1.90 / +0.26.
4. **The 54% loss-at-stop cannot size these trades.** They have no stop; 5 of 145 winner trades
   lost 100% of premium in-sample. Sizing uses the measured worst trade with a 100% floor.
5. **k × VIX is not a sensitivity for last-hour ITM options** (time value ≤ 0.001 pt at 60
   minutes for VIX ≤ 40 and 0.16 pt at VIX 83, `out/options_timevalue.csv`; the earlier typed
   bound was wrong). The spread is: the gap-up call flips sign between 1 and 3 points.

## Gaps, each with a root-cause hypothesis

| Gap | Root cause | What closes it |
|---|---|---|
| Holdout not run; playbook headline empty | No vendor is reachable from the container; yfinance cannot serve minute history anyway; the bundle names no other source | Commit the two `data/ext` files (DATA.md spec; `tools/fetch_ext_local.py`), then `make all` |
| No trial passes FDR at 10% in-sample | ~20–40 qualifying days a year at ~1–5 bp edges; structure at ¼ of apparent size (both threads) | Only the holdout can add power; the winner fires ≈ 20×/yr, so ≈ 125 holdout trades are likely — UNDERPOWERED is the probable honest label |
| D5 test-window Sharpe 0.99 vs Thread A's 1.35 | EXPLAINED 2026-09-13 (two fleet rounds). (i) Hypothesis "BAB on an uncleaned universe" killed: Thread A's it5/it5b cleaning reconstructed rule by rule reproduces its 626-name universe exactly, portfolio test Sharpe moves < 0.001. (ii) Sleeve-by-sleeve comparison on the identical 2012→2017-11-10 test window: S1 0.86 vs 0.87, S2 0.58 vs 0.58, S3 0.75 vs 0.75, S6 −0.29 vs −0.29, S13 0.53 vs 0.41, S5 0.74 vs 0.93, S8 1.16 vs 0.77 — and S12 (gap-up) −0.37 vs +0.32. S12 is the gap: Thread A charged 0.35 bp per side (`it15.py:24`, ≈ 0.7 bp round trip) and its own sensitivity table goes negative at 3 bp; this contract charges 0.42 index points (A21, Phase 4 defect 7), ≈ 30× more. S12 sits in the 3-sleeve bucket A, so the 50/50 book loses 0.43 and EQUAL_8 0.36. | Nothing to fix: the 0.99 is the honest figure under the cost budget; Thread A's 1.35 / 1.40 needs a sub-1 bp ES round trip that does not exist. Residual: S5's 0.19 shortfall (layered vol targeting, it9 inside `it8.vol_target`) is noted, below the 0.2 flag |
| S2/S3/S6/S13 stop at 2017-11-10 | ETF panel ends there; VXX/VXZ relaunched 2018 | Ext ETF panel with VIXY/VIXM bridge (A13) |
| Thread A's 0DTE code is absent | Not in the bundle | Re-implementation reproduced trade counts within 10% and option returns within 0.3 points under the inferred convention (A30); residual uncertainty is the convention itself |
| Real 0DTE quotes, GEX, post-2018 cross-market, VRP with option prices | Unobtainable here | Recorded non-goals |
| Fleet fan-out limited on the first build | Account rate limit killed 5 coders and 4 critics on the first attempt; the remaining Phase 3 implementation was COUPLED by the ownership map | The Phase 0 tribunal (4 lenses), the Phase 4 reviewer and the Phase 6 judge ran as fresh-context fleet agents and found 52 defects between them, all repaired; the post-judge repairs were implemented by fleet coders and re-verified by the fleet verifier (11/11) |

## Next step

There is no signal to trade. The honest options are: (1) stop here — the two threads' last-hour edge is
not there at prop-account costs after 2020; (2) if the owner wants to test Thread A's magnitude put
rule, it must be pre-registered now and judged only on data after 2026-09-11 (or on real fills per
PLAYBOOK §8), never on this holdout; (3) the owner's fair-value-gap family (A36) was tested under the same rule and no trial survives
(§ above); (4) a NEW mechanism-based candidate — one that names who must trade and when — pre-registered in its own
commit before any run and judged on data after 2026-09-11 (BLOCKED.md lists the candidates with their priors).
