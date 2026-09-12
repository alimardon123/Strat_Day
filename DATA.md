# DATA.md — what is present, what is missing, and the exact spec of anything missing

Updated 2026-09-12 (Phase 0).

## Environment facts (verified)

- Reachable: `raw.githubusercontent.com`, `git clone` of public GitHub repos through the
  session proxy, `pypi.org`.
- Blocked at the proxy (403): Yahoo chart API, stooq, cdn.cboe.com, hist.databento.com,
  data.alpaca.markets, api.polygon.io, kaggle.com, FRED, data.nasdaq.com, Tiingo,
  TwelveData, HuggingFace, Dukascopy.
- yfinance cannot serve 1-minute bars older than 7 days even where reachable.
- No git-lfs; supplied files must be plain files under 100 MB each.

## Present (fetchable in Phase 2 by `pipeline/fetch.py`, cached under `data/raw/`)

| Dataset | Source | Coverage | Timestamp convention |
|---|---|---|---|
| SPX 1-min (Oanda CFD SPX500_USD) | `FutureSharks/financial-data` `pyfinancialdata/data/currencies/oanda/SPX500_USD/{year}/oanda-SPX500_USD-{year}-{month}.csv` | 2005-01 → 2020-05 | UTC (2018-07-08 first bar 22:00 = 18:00 EDT) |
| SPX / DAX / EuroStoxx / Nikkei 1-min (histdata) | same repo, `pyfinancialdata/data/stocks/histdata/{SPXUSD,GRXEUR,ETXEUR,JPXJPY}/DAT_ASCII_*_M1_{year}.csv` | 2010 → 2018 | Eastern **with** DST (Sunday open 18:01 in Jan and Jul 2018); volume column is 0 |
| 25 other Oanda instruments 1-min | same repo, `currencies/oanda/*` | 2005 → 2020 | UTC |
| VIX daily OHLC | `datasets/finance-vix` `data/vix-daily.csv` | 1990-01-02 → 2026-09-11 | date |
| SPY daily, 928 stocks daily | `willhjw/big_movers` | 2000 → 2026-03 | date |
| 1,344 ETFs daily incl. VXX, VXZ, VIXY, VIXM | `neo-zhao/CMSC320_Final_Tutorial_Huge_Stock_Market_Dataset` `ETFs/{ticker}.us.txt` | → 2017-11-10 | date |

## Missing — must be supplied under `data/ext/` (committed to the branch)

| File | Status | Spec |
|---|---|---|
| `data/ext/spx_1min_2020-06_2026-09.csv.gz` | **MISSING** | columns `ts,open,high,low,close,volume`; `ts` in UTC as `YYYY-MM-DD HH:MM:SS`; at least 09:30–16:00 ET each session (extended hours allowed, filtered out); SPX index or ES front-month continuous (unadjusted) preferred; SPY accepted together with `data/ext/spy_dividends.csv` (`ex_date,amount`) |
| `data/ext/etf_daily_2017-11_2026-09.csv.gz` | **MISSING** | columns `ticker,date,open,high,low,close,adj_close,volume` for spy efa eem ewj ewz ewa tlt ief lqd hyg tip gld slv gdx dbc dba uso xop uup fxe fxy fxb vnq rwx iyr vxx vxz vixy vixm from 2017-11-01 |

`tools/fetch_ext_local.py` produces both files on a machine with internet access
(yfinance for the ETF panel; Alpaca free plan for SPY 1-minute; Databento or IBKR are
one-block swaps for ES or SPX).

## What each phase needs

| Phase | Needs `data/ext`? |
|---|---|
| 0–1 (documents) | no |
| 2 (harness, reproduction gates on pre-2020-06 data) | no |
| 3+ (reconciliation holdout, execution, playbook, own-account) | **yes — both files** |

If Phase 3 starts without them, the run stops at the end of Phase 2 with everything
committed and this file updated.
