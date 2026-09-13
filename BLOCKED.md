# BLOCKED.md — the goal cannot be advanced further from inside this environment

> **Update 2026-09-13 08:54 UTC — option A taken.** The owner pushed the four `data/ext/` files (commit
> 781180b). The block is lifted; this file stays as the record. Two real-data defects surfaced at once
> (dividend stamps with DST-varying offsets crashed `load_ext`; the DST probe's statistic failed on a feed
> with pre-market bars) and are being repaired before the holdout runs; the feed begins 2020-07-27, so
> the holdout's first eight weeks have no minute data and are reported as absent (DATA.md).
>
> **Closed 2026-09-13 10:10 UTC:** the holdout ran; both pre-registered signals FAILED (ASSESSMENT.md). This file is kept as the record of the block and its resolution.

Written 2026-09-13 after judge round 3 (DONE for the data that exists) and a final data-acquisition
sweep. This file exists because the Crucible protocol forbids silent shipping: the mission's
decisive question — does the reconciled last-hour signal survive 2020-06 → 2026-09 — has not been
answered, and nothing left in scope can answer it without one action by the owner.

## The gap

| What is missing | Why it matters | Named in |
|---|---|---|
| `data/ext/spx_1min_2020-05_2026-09.csv.gz` + `data/ext/ext_manifest.json` (+ `spy_dividends.csv` if SPY) | D2 holdout verdict, D4 headline, D3 holdout execution, the 15 POST-SELECTION rows, the full-sample table | DATA.md (spec), `tools/fetch_ext_local.py` (fetch script) |
| `data/ext/etf_daily_2017-11_2026-09.csv.gz` (29 tickers incl. VXX/VXZ/VIXY/VIXM) | D5: sleeves S2/S3/S6/S13 stop at 2017-11-10; VXX/VXZ bridge to the Series B notes | DATA.md |

Everything else in the contract is done or correctly labelled: `make all` on the current tree
regenerates 66 files byte-identically; with the two files present it regenerates 126, including the
holdout verdict (proven twice on a synthetic feed by fresh-context judges).

## Root cause

The container's network policy allows only GitHub and PyPI. Every market-data vendor returns 403 at
the proxy, and yfinance cannot serve 1-minute history older than 7 days even where reachable. The
pre-2020 data all came from GitHub mirrors; no GitHub mirror of post-2020 minute bars or of this
ETF universe exists.

## What was tried (so nobody repeats it)

1. Plan mode (2026-09-12): Yahoo, Alpaca, Databento, Polygon, Kaggle, CBOE, FRED, stooq, Tiingo,
   TwelveData, HuggingFace, Dukascopy — all 403 at the proxy.
2. 2026-09-13 sweep (two Sonnet agents, web search + `git ls-remote` + shallow clones):
   - Minute bars: the only genuine 1-minute S&P series on GitHub is a broker CFD feed
     (`USA500IDXUSD_M1`, Feb–Sep 2023, capped at 200,000 bars, placeholder volume) — wrong
     instrument, wrong range. Every SPY 1-minute file found is a single yfinance day. Kaggle's
     2008–2021 SPY 1-minute set is referenced by repos but never committed. FutureSharks still ends
     2020-05.
   - ETF panel: nothing covers the 29 tickers; the best partial source is a personal automation
     repo whose README asks not to be read by AI tools — not used, clone deleted. `big_movers`
     adds only SLV (2020→2026-03, no adjusted close).
   - Local panels: SPY to 2026-03-20 and SLV; all 27 other tickers end 2017-11-10.
3. 2026-09-13 reachability probe of every host not tested in plan mode: histdata.com (the original
   source of Thread B's SPXUSD 1-minute series, still published monthly), alphavantage.co,
   financialmodelingprep.com, eodhd.com, api.marketdata.app, firstratedata.com, forexsb.com,
   barchart.com, investing.com, api.tradingview.com — all refused by the proxy
   (`CONNECT tunnel failed, response 403`) while github.com answers. The network policy, not the
   vendors, is the wall; option B below is the only in-environment fix.
4. Substitutes explicitly refused by the mission: daily bars, synthetic data, 5-minute bars, a CFD
   proxy, re-tuning on pre-2020 data, a new pattern search over 2005–2020.

## Options (owner's decision)

| # | Option | Effort | What it unlocks |
|---|---|---|---|
| A | Run `tools/fetch_ext_local.py` on a machine with internet (Alpaca free plan for SPY 1-min; or Databento / IBKR for ES / SPX) and commit the files under `data/ext/` on this branch | ~20 min + one commit | `make all` produces the holdout verdict, the headline playbook, the post-selection rows, the full-sample table, the four ETF sleeves and the VXX/VXZ bridge |
| B | Change this cloud environment's network policy to allow one data host (e.g. `data.alpaca.markets` with `APCA_API_KEY_ID` / `APCA_API_SECRET_KEY` as environment variables, or `stooq.com` for the daily panel); then ask for the fetch to run here | Settings change; docs: https://code.claude.com/docs/en/claude-code-on-the-web | Same as A, without a local run |
| D | Authorise a search the mission currently forbids: an open-to-close 0DTE study on DAILY bars 2000→2026-03 (entry at the open print, settlement at the close, both present in daily OHLC — SPY and VIX are available here through 2026). This is a NEW pattern search over data both threads already exhausted, with a 6.5-hour time-value cost that both threads measured as fatal for directional 0DTE; it would need its own pre-registration, trial count and family FDR, and cannot touch the prop-account playbook's last-hour signals. Recorded so the option is visible; NOT started, because the mission's non-goals rule it out and only the owner can change them | one sentence from the owner | A holdout-era (2020→2026) test of a different, weaker idea — not the reconciled signal |
| C | Accept the in-sample result as final | none | Nothing tradeable: the honest label is "no reconciled specification is confirmed; small, crisis-loaded in-sample edge; 0 of 23 trials pass the family FDR" |

## What the result will most likely be (so expectations are set before the data lands)

The winner fires ≈ 20 times a year; the holdout window yields ≈ 125–160 trades, below the
200-trade floor in the survival rule. The probable honest label is UNDERPOWERED even if the sign
holds. A "loophole" was never on the table: both prior threads and this run measured the last-hour
effect at a few basis points per trade, concentrated in crises, at the edge of what 0DTE spreads
allow. The playbook's section 8 (ten real fills, sixty paper days) is the only way to learn what
the model cannot.

---

## Reopened 2026-09-13 12:05 UTC — the goal condition, not the data, is now the block

The session's standing goal reads "a highly successful trading system … that can find a loophole or really
strong edge in the market". The contract (ACCEPTANCE.md) was written so that this could only be claimed
after a pre-registered signal survived the post-2020 holdout. It did not:

| Evidence | Value | File |
|---|---|---|
| Reconciled last-hour winner on the holdout | n 274, −0.14 pts/trade at 1 pt, p 1.00, FAILED | `out/holdout_pooled.csv` |
| Thread A gap-up call on the holdout | n 452, −1.90 pts/trade, p 1.00, FAILED | `out/holdout_pooled.csv` |
| Family-wide BH-FDR at 10 % | 0 of 33 trials | `out/trials.csv` |
| Owner's fair-value-gap family (A36) | 0 of 8 survive on any window | `out/fvg_candidates.csv` |
| Flow-with-a-deadline candidates (month-end, opex, Russell) | all negative, below control | `out/flow_candidates.csv` |
| Probability of backtest overfitting of the selection | 0.73 (null 0.85) | `out/pbo.csv` |
| Judge round 5 | DONE on f28b5a3; nothing promoted | CRITIQUE.md |

### Why more iterations inside this session cannot satisfy the condition

1. Every remaining positive number sits on the holdout (three magnitude-gated post-selection rows, best
   `15:00|put|mag` +1.94 pts, p 0.10). Promoting any of them is a re-tune on the holdout — the one
   thing the contract forbids ("do not manufacture a pass"). It can only be a *new* pre-registration
   judged on data after 2026-09-11 or on real fills.
2. A fresh pattern search over 2005–2020 is a recorded non-goal (both threads exhausted it; PBO 0.73
   says the selection procedure itself over-fits at this trial count).
3. The plateau rule (two iterations without improvement) has been hit on every in-scope task; the
   tribunal budget (5 rounds) is spent with a DONE verdict on a negative result.
4. The stop hook is automated; it cannot pre-register, supply data, or choose among the options below.
   Continuing to fire agents against it would spend budget on tests nobody registered.

### Options for the owner (choose one; each is a new pre-registration in its own commit)

- **A. Stop here.** The deliverable is the finding: the last-hour edge both threads found is not there
  at prop-account costs after 2020. Everything is reproducible (`make all`, byte-identical twice).
- **B. Forward test, no new backtest.** Pre-register `15:00|put|mag` (Thread A's rule, unchanged) and
  judge it only on sessions after 2026-09-11 — paper fills logged by the owner, or the next data drop.
  Survival rule unchanged (n ≥ 200 means roughly two years of signals).
- **C. One new mechanism candidate.** From the table below (drafted by a scout, to be appended), pick
  one that names who must trade and when; pre-register entry, direction, gate and every parameter in
  its own commit; test once on 2005→2020 as selection and 2020-07→2026-09 as holdout; report under the
  same six-condition survival rule; kill if it fails. No second candidate until the first is judged.
- **D. Supply the missing mechanism data.** If the chosen candidate needs a file that is not on the
  branch (e.g. leveraged-ETF AUM by day, VIX settlement dates), commit it under `data/ext/` with a
  manifest, as with the minute bars.

The run stays closed until one of these is chosen; no agent will be launched against the stop hook.
