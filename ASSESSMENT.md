# ASSESSMENT.md — the bar, where each done-statement landed, every gap with a root cause

Status: Phase 7 interim (2026-09-12). The run stopped where the protocol says it must: every
phase and unit that does not need the user-supplied post-May-2020 data is complete and gated;
the holdout (D2), the headline playbook numbers (D4) and the ETF-dependent sleeves (D5) wait for
`data/ext/` (spec in DATA.md, local fetch tool in `tools/fetch_ext_local.py`). Declaring the
work done would be false; this file says exactly what is and is not established.

## The bar

ACCEPTANCE.md v2: seven done-statements, a six-condition survival rule, a fixed decision rule with
one pre-registered holdout test, López de Prado + both threads' guards, every number generated
from `out/` by `make all` and byte-identical on `make repeat`.

## Where each done-statement landed

| # | Landed | Evidence |
|---|---|---|
| D1 | Pre-registered. 16 configurations on 2013-01→2020-05-13; winner after the Phase 4 tie-break repair `15:00\|both\|vixmove_exp` (expanding-tercile rule, no fitted parameters; n 145, +3.12 pts/trade net, calendar-day Sharpe 0.49). Thread B's construction (VIX gate, move from the prior close, both directions) beats Thread A's (magnitude from the open, put-only) in every cross; the entry time (15:00 vs 15:30) is a wash. No trial passes BH-FDR at 10% across the 23-trial family — the reconciliation answers *which shape*, not yet *whether it is real*. | `out/reconcile_candidates.csv`, `out/reconcile_decision.md` |
| D2 | NOT RUN — blocked on `data/ext/spx_1min_2020-05_2026-09.csv.gz`. The path is built and proven on a synthetic file (gate e): when the file lands, `make all` produces the holdout tables and survival verdicts. | DATA.md, `out/gate_e.csv` |
| D2b | Done as a finding: the gap-up call is +0.022%/trade on SPX (p 0.16), +0.019% on DAX (p 0.27), −0.033% on EuroStoxx (p 1.0) over 2010–2018. Marginal where it exists; not universal. | `out/xmarket_*.csv` |
| D3 | Done in-sample; holdout pending. With the exit half of the spread still charged, limit entry at 0.25 ATR adds +0.66 pts per signal to the gap-up call (0.34 of it a cost assumption, 0.31 price improvement net of adverse selection, p 0.002) and only +0.22 to the winner (0.36 cost assumption minus 0.14 adverse selection, p 0.38). Thread B's "largest single improvement" is real for the 13:00 leg and mostly a cost assumption for the last-hour leg. | `out/insample_execution.csv` |
| D4 | Done in-sample; headline pending. Winner +7.3% of premium per trade (SPX cash settlement, 1 pt), median +5.5%, 5 of 145 trades lose the full premium; gap-up call +1.2% at 1 pt and negative at 3 pt; k is irrelevant for the last-hour leg; SPY's 15:55 exit roughly halves both. Sizing at a 4% limit with the 100% floor: 4% per trade (+5.8%/yr in-sample, worst year −2.0%), 2% when both signals can fire (77 such days in-sample). | `out/insample_summary.csv`, `out/insample_sizing.csv`, PLAYBOOK_0DTE.md |
| D5 | Partial. Baseline test window 2012–2017 reproduced to EQUAL_8 Sharpe 0.99 / two-bucket 0.97 (Thread A 1.35 / 1.40) with the drawdown matching (−5.4% vs −5.26%); S2/S3/S13 test-window Sharpes match Thread A's published values; the shortfall is BAB (raw 928-stock panel; Thread A's cleaned 626-stock panel is not in the bundle) and S12 at a points-based ES cost. The post-2017 book holds only 3–4 sleeves (labelled EQUAL_available) with Sharpe 0.65; BAB −0.37 post-2017. VXX/VXZ bridge implemented (correlations 0.9987 / 0.9875). VIX − RV addendum reproduces Thread A's +3.44 pts / 81.6% positive. | `out/own_account_*.csv`, OWN_ACCOUNT.md |
| D6 | Done for what ran: 23 trials in one family-wide BH-FDR (none pass); DSR at N = 12 and N = 42 (gap-up: PSR and N = 1,099); both controls with the signal's own direction base; month/day blocks. | SCORECARD.md, `out/trials.csv` |
| D7 | PASS: `make all` regenerates every table (gates b, c, e; D1; D3/D4; D5; D2b; flow; trials; report); `make repeat` byte-identical; playbook tables rendered by `pipeline/report.py`. | Makefile |

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
5. **k × VIX is not a sensitivity for last-hour ITM options** (time value < 0.001 pt at 60
   minutes). The spread is: the gap-up call flips sign between 1 and 3 points.

## Gaps, each with a root-cause hypothesis

| Gap | Root cause | What closes it |
|---|---|---|
| Holdout not run; playbook headline empty | No vendor is reachable from the container; yfinance cannot serve minute history anyway; the bundle names no other source | Commit the two `data/ext` files (DATA.md spec; `tools/fetch_ext_local.py`), then `make all` |
| No trial passes FDR at 10% in-sample | ~20–40 qualifying days a year at ~1–5 bp edges; structure at ¼ of apparent size (both threads) | Only the holdout can add power; the winner fires ≈ 20×/yr, so ≈ 125 holdout trades are likely — UNDERPOWERED is the probable honest label |
| D5 test-window Sharpe 0.99 vs Thread A's 1.35 | BAB on an uncleaned universe; S12 at a points-based cost (0.27 vs Thread A's 0.74 full-sample) | Reconstruct it5b's cleaning (documented in ASSESSMENT_iteration5) — a bounded task not attempted here |
| S2/S3/S6/S13 stop at 2017-11-10 | ETF panel ends there; VXX/VXZ relaunched 2018 | Ext ETF panel with VIXY/VIXM bridge (A13) |
| Thread A's 0DTE code is absent | Not in the bundle | Re-implementation reproduced trade counts within 10% and option returns within 0.3 points under the inferred convention (A30); residual uncertainty is the convention itself |
| Real 0DTE quotes, GEX, post-2018 cross-market, VRP with option prices | Unobtainable here | Recorded non-goals |
| Fleet fan-out not used for implementation | Account rate limit killed 5 coders and 4 critics on the first attempt; the remaining implementation was COUPLED by the ownership map | The Phase 0 tribunal (4 lenses) and the Phase 4 reviewer ran as fresh-context fleet agents and found 46 defects between them, all repaired; the judge closes the loop |

## Next step

Supply `data/ext/` (three files, DATA.md), run `make all`, read `out/holdout_summary.csv` against the
survival rule. If the pre-registered signal fails, the result is "no reconciled specification
survives 2020-06→2026-09" and the "flows with a deadline" candidates already tested here all
failed in-sample too — the honest conclusion would then be that the last-hour edge is
crisis-loaded and undetectable at prop-account sizing outside crises.
