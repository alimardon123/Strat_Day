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

## Fetched in Phase 2 (`data/raw/`, manifests committed as `data/raw/manifest_*.json`)

| File | Rows | Coverage | Notes |
|---|---|---|---|
| `oanda_SPX500_USD.parquet` | 4,011,719 | 2005-01-02 → 2020-05-14 (UTC) | 3,661 RTH sessions kept; 2017 thin (182,748 rows vs ~290k normal); sparse stretches 2005–2006 and March 2012 |
| `histdata_SPXUSD.parquet` | 2,117,667 | 2010-11-14 → 2018-12-31 (ET, DST) | 1,935 RTH sessions kept; December 2010 sparse |
| `histdata_GRXEUR / ETXEUR / JPXJPY.parquet` | 1.7M / 1.3M / 1.9M | 2010-11 → 2018-12 | cross-market checks only |
| `vix_daily.parquet` | 9,271 | 1990-01-02 → 2026-09-11 | sha256 in manifest |
| `spy_daily.parquet` | 6,593 | 2000-01-03 → 2026-03-20 | big_movers, unadjusted |
| `etf_daily_kaggle.parquet` | 169,844 | → 2017-11-10 | 57 tickers, none missing; VXX 2009-01-30 →, VXZ 2009-01-29 →, VIXY 2011-01-07 → |
| `stocks_daily.parquet` | pending | 2000 → 2026 | big_movers collected_stocks (928 files) |

## Missing — must be supplied under `data/ext/` (committed to the branch)

| File | Status | Spec |
|---|---|---|
| `data/ext/spx_1min_2020-05_2026-09.csv.gz` | **MISSING** | columns `ts,open,high,low,close,volume`; `ts` in UTC as `YYYY-MM-DD HH:MM:SS`; from **2020-05-14** (the Oanda series ends 2020-05-13; 2020-05-14→05-29 is warm-up, the holdout starts 2020-06-01); at least 09:30–16:00 ET each session (extended hours allowed, filtered out). Instrument: SPY (with `data/ext/spy_dividends.csv`: `ex_date,amount`), or ES front-month with a `contract` column or roll dates in the manifest, or SPX cash index |
| `data/ext/ext_manifest.json` | **MISSING** | `{"instrument": "SPY" \| "ES" \| "SPX", "source": "...", "adjusted": false, "roll_dates": [...] (ES only)}` — the session builder refuses to run without it and checks the declared instrument against the price level (ACCEPTANCE A6). ES: signals whose reference price and decision price straddle a roll are dropped and listed. SPX cash: open = first print at or after 09:31, close = last print before 16:00 |
| `data/ext/etf_daily_2017-11_2026-09.csv.gz` | **MISSING** | columns `ticker,date,open,high,low,close,adj_close,volume` for spy efa eem ewj ewz ewa tlt ief lqd hyg tip gld slv gdx dbc dba uso xop uup fxe fxy fxb vnq rwx iyr vxx vxz vixy vixm from 2017-11-01. Today's VXX/VXZ are the 2018 Series B notes with no pre-2018 history; the bridge to the Kaggle-mirror series runs through VIXY/VIXM (A13), so those two must be present from 2017-11-01 |

Note: the bundle's `*.pkl` intermediates were written by pandas 3 and do not load under the
pinned pandas 2.2.3; nothing in the pipeline reads them (every number is regenerated).

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

## Acquisition sweep of 2026-09-13 (post-judge) — nothing usable found

Two Sonnet agents searched GitHub (web search, `git ls-remote`, shallow clones) for the two missing
files. Minute bars: only a broker CFD feed (`USA500IDXUSD_M1`, Feb–Sep 2023, 200,000-bar cap,
placeholder volume) and single-day yfinance dumps exist; no SPY/SPX/ES 1-minute series covers any
part of 2020-05 → 2026-09. ETF panel: no repository carries the 29 tickers; the local panels hold
only SPY (to 2026-03-20) and SLV after 2017-11-10. Vendor hosts remain 403. The block stands; see
BLOCKED.md for the owner's options.
Additional hosts probed 2026-09-13 and refused by the proxy (403 on CONNECT): histdata.com, alphavantage.co, financialmodelingprep.com, eodhd.com, api.marketdata.app, firstratedata.com, forexsb.com, barchart.com, investing.com, api.tradingview.com.
