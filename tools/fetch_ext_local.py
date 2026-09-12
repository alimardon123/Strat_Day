"""Run this on YOUR machine (the cloud container cannot reach any market-data vendor).

Produces the two files the pipeline needs under data/ext/, then commit them:
  data/ext/etf_daily_2017-11_2026-09.csv.gz   (yfinance, no account needed)
  data/ext/spx_1min_2020-06_2026-09.csv.gz    (Alpaca free plan, IEX feed, SPY 1-min)
  data/ext/spy_dividends.csv                  (only because the minute file is SPY)

Alpaca keys: export APCA_API_KEY_ID=... APCA_API_SECRET_KEY=...
If you use Databento (ES continuous) or IBKR (SPX index) instead, write the same six
columns (ts in UTC as YYYY-MM-DD HH:MM:SS, open, high, low, close, volume) and skip the
dividends file.
"""
import os, time
import pandas as pd
import requests
import yfinance as yf

ETFS = ("spy efa eem ewj ewz ewa tlt ief lqd hyg tip gld slv gdx dbc dba uso xop uup "
        "fxe fxy fxb vnq rwx iyr vxx vxz vixy vixm").split()
START_ETF, START_MIN, END = "2017-11-01", "2020-06-01", "2026-09-12"
os.makedirs("data/ext", exist_ok=True)


def etf_panel():
    rows = []
    for t in ETFS:
        d = yf.download(t, start=START_ETF, end=END, auto_adjust=False, progress=False)
        if d.empty:
            print("no data:", t)
            continue
        d.columns = [(c[0] if isinstance(c, tuple) else c).lower().replace(" ", "_") for c in d.columns]
        d = d.reset_index().rename(columns={"Date": "date"})
        d.insert(0, "ticker", t)
        rows.append(d[["ticker", "date", "open", "high", "low", "close", "adj_close", "volume"]])
    pd.concat(rows).to_csv("data/ext/etf_daily_2017-11_2026-09.csv.gz", index=False, compression="gzip")


def spy_minute_alpaca():
    h = {"APCA-API-KEY-ID": os.environ["APCA_API_KEY_ID"],
         "APCA-API-SECRET-KEY": os.environ["APCA_API_SECRET_KEY"]}
    url = "https://data.alpaca.markets/v2/stocks/SPY/bars"
    params = dict(timeframe="1Min", start=f"{START_MIN}T00:00:00Z", end=f"{END}T00:00:00Z",
                  limit=10000, adjustment="raw", feed="iex")
    out, token = [], None
    while True:
        if token:
            params["page_token"] = token
        r = requests.get(url, headers=h, params=params, timeout=60)
        r.raise_for_status()
        j = r.json()
        out += j.get("bars", [])
        token = j.get("next_page_token")
        if not token:
            break
        time.sleep(0.3)
    b = pd.DataFrame(out).rename(columns={"t": "ts", "o": "open", "h": "high", "l": "low",
                                          "c": "close", "v": "volume"})
    b["ts"] = pd.to_datetime(b["ts"], utc=True).dt.strftime("%Y-%m-%d %H:%M:%S")
    b[["ts", "open", "high", "low", "close", "volume"]].to_csv(
        "data/ext/spx_1min_2020-06_2026-09.csv.gz", index=False, compression="gzip")
    yf.Ticker("SPY").dividends.rename_axis("ex_date").rename("amount").to_csv("data/ext/spy_dividends.csv")


if __name__ == "__main__":
    etf_panel()
    spy_minute_alpaca()
    print("done:", os.listdir("data/ext"))
