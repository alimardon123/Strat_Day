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
| D1 | Pre-registered. 16 configurations on 2013-01→2020-05-13; winner `15:00\|both\|vixmove_fixed` (n 93, +5.10 pts/trade net, calendar-day Sharpe 0.57). Thread B's construction (VIX gate, move from the prior close, both directions) beats Thread A's (magnitude from the open, put-only) in every cross; the entry time (15:00 vs 15:30) is a wash. No configuration passes BH-FDR at 10% on the window — the reconciliation answers *which shape*, not yet *whether it is real*. | `out/reconcile_candidates.csv`, `out/reconcile_decision.md` |
| D2 | NOT RUN — blocked on `data/ext/spx_1min_2020-05_2026-09.csv.gz`. | DATA.md |
| D2b | Done as a finding: the gap-up call is +0.022%/trade on SPX (p 0.16), +0.019% on DAX (p 0.27), −0.033% on EuroStoxx (p 1.0) over 2010–2018. Marginal where it exists; not universal. | `out/xmarket_*.csv` |
| D3 | Done in-sample; holdout pending. Limit entry at 0.25–0.50 ATR moves the gap-up call from −0.12 to +0.9/+1.0 pts per signal with unfilled signals counted as zero (p < 0.001) — the same improvement Thread B measured; +0.57 pts on the winner (p 0.31, n 93). | `out/insample_execution.csv` |
| D4 | Done in-sample; headline pending. Winner +11.5% of premium per trade (SPX cash settlement, 1 pt), 5 of 93 trades lose the full premium; gap-up call +1.23% at 1 pt and negative at 3 pt; k is irrelevant for the last-hour legs; SPY's 15:55 exit roughly halves both. Sizing at a 4% limit with the 100% floor: 4% per trade, 2% when both signals can fire. | `out/insample_summary.csv`, `out/insample_sizing.csv`, PLAYBOOK_0DTE.md |
| D5 | Partial. Baseline 2006–2017 reproduced to Sharpe 0.85/1.08 (Thread A 1.12/1.35) with the drawdown matching (−6.7% vs −6.10%); S2/S3/S13 test-window Sharpes match Thread A's published values; the shortfall is the BAB sleeve (raw 928-stock panel, Thread A's cleaned 626-stock panel is not in the bundle). Extension: S1/S5/S8 to 2026-03, S12 to 2020-05; S2/S3/S6/S13 stop at 2017-11-10 until the ext panel arrives. Post-2017 four-sleeve book Sharpe 0.66; BAB −0.37 post-2017. VIX − RV addendum measured. | `out/own_account_*.csv`, OWN_ACCOUNT.md |
| D6 | Done for what ran: 16 + 1 + 3 trials counted; DSR at N = 12 and N = 42; both controls; month/day blocks. | SCORECARD.md, `out/trials.csv` |
| D7 | PASS: `make all` regenerates every table; `make repeat` byte-identical; playbook tables rendered by `pipeline/report.py`. | Makefile |

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
4. **The 54% loss-at-stop cannot size these trades.** They have no stop; 5 of 93 winner trades
   lost 100% of premium in-sample. Sizing uses the measured worst trade with a 100% floor.
5. **k × VIX is not a sensitivity for last-hour ITM options** (time value < 0.001 pt at 60
   minutes). The spread is: the gap-up call flips sign between 1 and 3 points.

## Gaps, each with a root-cause hypothesis

| Gap | Root cause | What closes it |
|---|---|---|
| Holdout not run; playbook headline empty | No vendor is reachable from the container; yfinance cannot serve minute history anyway; the bundle names no other source | Commit the two `data/ext` files (DATA.md spec; `tools/fetch_ext_local.py`), then `make all` |
| No configuration passes FDR at 10% in-sample | ~40 qualifying days a year at ~1–5 bp edges; structure at ¼ of apparent size (both threads) | Only the holdout can add power; UNDERPOWERED is the likely honest label even then (winner fires ≈ 13×/yr) |
| D5 Sharpe 0.85 vs Thread A's 1.12 | BAB on an uncleaned universe; S12 defined from this pipeline's signal | Reconstruct it5b's cleaning (documented in ASSESSMENT_iteration5) — a bounded task not attempted here |
| S2/S3/S6/S13 stop at 2017-11-10 | ETF panel ends there; VXX/VXZ relaunched 2018 | Ext ETF panel with VIXY/VIXM bridge (A13) |
| Thread A's 0DTE code is absent | Not in the bundle | Re-implementation reproduced trade counts within 10% and option returns within 0.3 points under the inferred convention (A30); residual uncertainty is the convention itself |
| Real 0DTE quotes, GEX, post-2018 cross-market, VRP with option prices | Unobtainable here | Recorded non-goals |
| Fleet fan-out not used for implementation | Account rate limit killed 5 coders and 4 critics on the first attempt; the remaining implementation was COUPLED by the ownership map | Reviewer and judge stages use the fleet (independent context is the mechanism) |

## Next step

Supply `data/ext/` (three files, DATA.md), run `make all`, read `out/holdout_summary.csv` against the
survival rule. If the pre-registered signal fails, the result is "no reconciled specification
survives 2020-06→2026-09" and the "flows with a deadline" candidates already tested here all
failed in-sample too — the honest conclusion would then be that the last-hour edge is
crisis-loaded and undetectable at prop-account sizing outside crises.
