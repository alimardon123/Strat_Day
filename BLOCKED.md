# BLOCKED.md — the goal cannot be advanced further from inside this environment

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
