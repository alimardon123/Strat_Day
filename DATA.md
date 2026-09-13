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
| `data/ext/spx_1min_2020-05_2026-09.csv.gz` | **MISSING → supplied 2026-09-13 (see the section below)** | columns `ts,open,high,low,close,volume`; `ts` in UTC as `YYYY-MM-DD HH:MM:SS`; from **2020-05-14** (the Oanda series ends 2020-05-13; 2020-05-14→05-29 is warm-up, the holdout starts 2020-06-01); at least 09:30–16:00 ET each session (extended hours allowed, filtered out). Instrument: SPY (with `data/ext/spy_dividends.csv`: `ex_date,amount`), or ES front-month with a `contract` column or roll dates in the manifest, or SPX cash index |
| `data/ext/ext_manifest.json` | **MISSING → supplied 2026-09-13 (see the section below)** | `{"instrument": "SPY" \| "ES" \| "SPX", "source": "...", "adjusted": false, "roll_dates": [...] (ES only)}` — the session builder refuses to run without it and checks the declared instrument against the price level (ACCEPTANCE A6). ES: signals whose reference price and decision price straddle a roll are dropped and listed. SPX cash: open = first print at or after 09:31, close = last print before 16:00 |
| `data/ext/etf_daily_2017-11_2026-09.csv.gz` | **MISSING → supplied 2026-09-13 (see the section below)** | columns `ticker,date,open,high,low,close,adj_close,volume` for spy efa eem ewj ewz ewa tlt ief lqd hyg tip gld slv gdx dbc dba uso xop uup fxe fxy fxb vnq rwx iyr vxx vxz vixy vixm from 2017-11-01. Today's VXX/VXZ are the 2018 Series B notes with no pre-2018 history; the bridge to the Kaggle-mirror series runs through VIXY/VIXM (A13), so those two must be present from 2017-11-01 |

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

## 2026-09-13 — the owner supplied `data/ext/` (commit 781180b)

| File | Status | Verified facts (fleet verifier) |
|---|---|---|
| `data/ext/spx_1min_2020-05_2026-09.csv.gz` | PRESENT, partial coverage | SPY, Alpaca IEX 1-minute, UTC `YYYY-MM-DD HH:MM:SS`, 605,227 rows, sorted, no duplicates, no bad prices; **data begins 2020-07-27** (Alpaca's IEX history starts there) and ends 2026-09-11; 1,539 NY dates, median 388 regular-session bars, 1,526 dates with ≥ 300; extended-hours bars present (17,653) and filtered by the session builder. Consequence: 2020-05-14 → 2020-07-26 has no minute data from any source; the holdout's first eight weeks are absent and are reported as such, never filled |
| `data/ext/ext_manifest.json` | PRESENT | `{"instrument": "SPY", "source": "Alpaca IEX feed, 1Min bars, adjustment=raw", "adjusted": false, "roll_dates": []}` |
| `data/ext/spy_dividends.csv` | PRESENT | 135 ex-dates 1993 → 2026-06-18, 25 after 2020-05-14; stamps carry DST-varying offsets (`-05:00` / `-04:00`), which exposed a parsing defect in `sessions.load_ext` (fixed the same day; gate (e) now covers tz-aware stamps) |
| `data/ext/etf_daily_2017-11_2026-09.csv.gz` | PRESENT, complete | all 29 tickers 2017-11-01 → 2026-09-11 (VXX/VXZ from 2018-01-25, the Series B relaunch), `adj_close` present, no NaN |

## Acquisition sweep of 2026-09-13 (post-judge) — nothing usable found

Two Sonnet agents searched GitHub (web search, `git ls-remote`, shallow clones) for the two missing
files. Minute bars: only a broker CFD feed (`USA500IDXUSD_M1`, Feb–Sep 2023, 200,000-bar cap,
placeholder volume) and single-day yfinance dumps exist; no SPY/SPX/ES 1-minute series covers any
part of 2020-05 → 2026-09. ETF panel: no repository carries the 29 tickers; the local panels hold
only SPY (to 2026-03-20) and SLV after 2017-11-10. Vendor hosts remain 403. The block stands; see
BLOCKED.md for the owner's options.
Additional hosts probed 2026-09-13 and refused by the proxy (403 on CONNECT): histdata.com, alphavantage.co, financialmodelingprep.com, eodhd.com, api.marketdata.app, firstratedata.com, forexsb.com, barchart.com, investing.com, api.tradingview.com.

## Requested 2026-09-13 for the owner's option C (A38) and the real-quote path — supplied under `data/ext/`

| File | Columns | Coverage | Source the owner can use locally | Used by |
|---|---|---|---|---|
| `data/ext/letf_aum_2006_2026.csv` | `ticker,date,shares_outstanding,nav,net_assets` (net_assets = shares × NAV, USD; one row per fund per trading day) | SSO, SDS, SH from 2006-06; SPXL, SPXS from 2008-11; UPRO, SPXU from 2009-06; all to 2026-09-11 | Each sponsor's historical NAV / shares-outstanding download (ProShares and Direxion fund pages); `tools/fetch_letf_aum_local.py` documents the columns and validates the file. A partial history is accepted and labelled | A38 (`pipeline/units/letf.py`, to be written after the file lands) |
| `data/ext/spy_0dte_1min_2024-02_2026-09.csv.gz` | `ts,expiry,strike,right,open,high,low,close,volume` — 1-minute bars of SPY same-day-expiry contracts within ±3 % of the 09:30 price, `ts` UTC | From the first date the owner's options feed serves history (Alpaca options bars: February 2024) to 2026-09-11 | `tools/fetch_spy_0dte_local.py` (Alpaca options data API; untested from this container — the proxy blocks the host) | Replaces the k × VIX model with real 0DTE prices for every candidate; enables an event-day long-volatility test that the model cannot price (recorded as the highest-value data addition) |

## 2026-09-13 — owner's TradingView exports for Track B (`data/ext/tv_samples/`, manifest.json)

Six CSVs (time = Unix seconds UTC; TradingView caps each export near 10,000 bars): SPY 1-min 2026-02-17 → 2026-03-25; SPY 5-min 2025-09 → 2026-03; SPY 1D 1993 → 2026-03-13; SPY 34R range bars ($0.34) 2025-06-09 → 2026-03-17; XAUUSD 5000R ($5) 2025-06-08 → 2026-03-18; XAUUSD 2000R ($2) 2026-03-08 → 2026-03-18. Use (per A40c): the 34R file is CONTEXT only — it proved not to be a faithful range-bar series (median 16 bars per session, discontinuous opens), so gate B-a checks the rebuild's internal consistency instead; the XAUUSD 5000R file is context too; the time-based SPY files are cross-checks only — the branch carries longer series of each.

## 2026-09-13 — searches for A38 assets history and gold minute data (two fleet agents, GitHub only)

- Leveraged-ETF shares outstanding / net assets (A38): NOT FOUND on GitHub after 12 web-search queries and verified clones of every lead (price-only leveraged-ETF repos, a semiconductor-ETF AUM tracker, Chinese ETF flows, scraper tools without committed history). A38 waits for the owner's `data/ext/letf_aum_2006_2026.csv`; sponsors' own downloads or a terminal are the realistic sources; SEC N-PORT gives monthly, not daily, values.
- Gold: FutureSharks/financial-data carries Oanda XAU_USD 1-minute 2006-03-19 → 2020-05-14 (`pyfinancialdata/data/currencies/oanda/XAU_USD/<year>/oanda-XAU_USD-<year>-<month>.csv`, columns time,close,high,low,open,volume; ≈ 1.5–1.8 M rows). Track B gold windows (A40c): TRAIN 2006-03-19 → 2016-12-31, TEST 2017-01-01 → 2020-05-14, both rebuilt $5 range bars from this feed; the owner's TradingView file is context only. Note for future fetches: a blobless clone of that repository grows past 5 GB once blobs are pulled on demand — fetch the XAU_USD directory only.
- Fetched 2026-09-13: `data/raw/oanda_XAU_USD.parquet` (4,884,366 rows, 2006-03-19 20:29 → 2020-05-14 07:59 UTC, 171 monthly files, none missing, `pipeline/units/fetch_oanda_xau.py`, manifest committed). Clock verified as UTC by the weekly open/close: Sunday first bar 22:00 UTC and Friday last bar 20:59 UTC in every year except 2011 (00:46 / 22:59, a source quirk), matching the SPX500_USD feed's 22:00 UTC weekly open. Minutes with high − low ≥ $5: 0.05 %.

