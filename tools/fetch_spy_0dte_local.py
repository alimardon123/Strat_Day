"""Run this on YOUR machine (Alpaca's options market-data host is blocked from the
cloud container; UNTESTED FROM THE RESEARCH CONTAINER -- the proxy 403s
data.alpaca.markets and api.alpaca.markets, so nothing below has ever executed).
Produces data/ext/spy_0dte_1min_2024-02_2026-09.csv.gz: 1-minute bars of SPY same-day-
expiry option contracts within +/-3% of that day's 09:30 ET print, for every trading
day from 2024-02-01 (Alpaca's options-bars history starts here) through 2026-09-11.
Columns: ts,expiry,strike,right,open,high,low,close,volume (ts UTC "YYYY-MM-DD HH:MM:SS",
right "C"/"P"). The free/basic plan is rate-limited and may throttle a run covering
~650 trading days; use --resume/--start/--end to split the work across invocations.
  export APCA_API_KEY_ID=... APCA_API_SECRET_KEY=...
Contract listing hits the Trading API, which is account-type specific: this script
defaults to the paper endpoint and lets APCA_API_BASE_URL override it (use
https://api.alpaca.markets for a live account) -- verify which one your keys accept.
09:30 price for the +/-3% window comes from a local data/ext/sp*_1min_*.csv.gz file if
one is present (first bar of the day), else the first 1-minute SPY bar of the session
fetched fresh from Alpaca's stocks-bars endpoint.
    python tools/fetch_spy_0dte_local.py --resume
    python tools/fetch_spy_0dte_local.py --validate-only
"""
import argparse
import glob
import os
import time
import pandas as pd
import requests

OUT = "data/ext/spy_0dte_1min_2024-02_2026-09.csv.gz"
START, END = "2024-02-01", "2026-09-11"
TRADING_BASE = os.environ.get("APCA_API_BASE_URL", "https://paper-api.alpaca.markets")
COLS = ["ts", "expiry", "strike", "right", "open", "high", "low", "close", "volume"]


def _headers():
    key, sec = os.environ.get("APCA_API_KEY_ID"), os.environ.get("APCA_API_SECRET_KEY")
    if not key or not sec:
        raise SystemExit("set APCA_API_KEY_ID and APCA_API_SECRET_KEY before running fetch()")
    return {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec}


def _get(url, headers, params, what):
    """GET with retry on 429/5xx; raises naming what+url on final failure."""
    last = None
    for attempt in range(3):
        try:
            r = requests.get(url, headers=headers, params=params, timeout=60)
        except requests.RequestException as e:
            last = e
        else:
            if r.status_code == 429 or r.status_code >= 500:
                last = RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
            else:
                r.raise_for_status()
                return r.json()
        time.sleep(1 + attempt)
    raise RuntimeError(f"failed to fetch {what} from {url}: {last}")


def trading_days(start, end):
    # Weekday approximation of the NYSE calendar; a holiday costs one wasted request.
    return [d.strftime("%Y-%m-%d") for d in pd.bdate_range(start, end)]


def load_spy_minute():
    hits = sorted(glob.glob("data/ext/sp*_1min_*.csv.gz"))
    if not hits:
        return None
    print("using local minute file for 09:30 prices:", hits[0])
    return pd.read_csv(hits[0], usecols=["ts", "close"], dtype={"ts": str})


def open_utc(day):
    """09:30 America/New_York on `day`, as a UTC timestamp (the minute file carries pre-market bars,
    so the first bar of the UTC day is NOT the 09:30 print)."""
    return pd.Timestamp(f"{day} 09:30", tz="America/New_York").tz_convert("UTC")


def day_open_price(day, minute_df, headers):
    if minute_df is not None:
        sub = minute_df[minute_df["ts"].str.startswith(day)]
        if not sub.empty:
            t0 = open_utc(day).strftime("%Y-%m-%d %H:%M:%S")
            at_open = sub[sub["ts"] >= t0].sort_values("ts")
            if not at_open.empty:
                return float(at_open.iloc[0]["close"])
    t0 = open_utc(day)
    j = _get("https://data.alpaca.markets/v2/stocks/SPY/bars", headers,
              dict(timeframe="1Min", start=t0.strftime("%Y-%m-%dT%H:%M:%SZ"),
                   end=(t0 + pd.Timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   limit=1, feed="iex"), f"SPY 09:30 bar for {day}")
    bars = (j or {}).get("bars") or []
    if not bars:
        raise RuntimeError(f"no SPY bar for {day}; cannot size the +/-3% strike window")
    return float(bars[0]["o"])


def list_contracts(day, headers):
    url = f"{TRADING_BASE}/v2/options/contracts"
    params = dict(underlying_symbols="SPY", expiration_date=day, limit=1000)
    out, token = [], None
    while True:
        if token:
            params["page_token"] = token
        j = _get(url, headers, params, f"option contracts for {day}")
        out += j.get("option_contracts", [])
        token = j.get("next_page_token")
        if not token:
            return out
        time.sleep(0.3)


def strike_window(contracts, lo, hi):
    """{symbol: (expiry, strike, right)} for contracts within [lo, hi]."""
    kept = {}
    for c in contracts:
        try:
            strike = float(c["strike_price"])
        except (KeyError, TypeError, ValueError):
            continue
        if lo <= strike <= hi:
            right = "C" if str(c.get("type", "")).lower().startswith("c") else "P"
            kept[c["symbol"]] = (c.get("expiration_date"), strike, right)
    return kept


def fetch_bars(contract_map, day, headers):
    symbols, url, rows = list(contract_map), "https://data.alpaca.markets/v1beta1/options/bars", []
    for i in range(0, len(symbols), 100):
        params = dict(symbols=",".join(symbols[i:i + 100]), timeframe="1Min",
                      start=f"{day}T13:00:00Z", end=f"{day}T21:00:00Z", limit=10000)
        token = None
        while True:
            if token:
                params["page_token"] = token
            j = _get(url, headers, params, f"options bars batch {i // 100} for {day}")
            for sym, bars in (j.get("bars") or {}).items():
                expiry, strike, right = contract_map.get(sym, (None, None, None))
                if strike is None:
                    continue
                rows += [dict(ts=b["t"], expiry=expiry, strike=strike, right=right, open=b["o"],
                               high=b["h"], low=b["l"], close=b["c"], volume=b["v"]) for b in bars]
            token = j.get("next_page_token")
            if not token:
                break
            time.sleep(0.3)
    return rows


def fetch(start, end, out, resume):
    headers = _headers()
    tmp = (out[:-len(".csv.gz")] if out.endswith(".csv.gz") else out) + ".tmp.csv"
    if resume and os.path.exists(out) and not os.path.exists(tmp):
        pd.read_csv(out).to_csv(tmp, index=False)
    done = (set(pd.read_csv(tmp, usecols=["expiry"])["expiry"].astype(str))
             if resume and os.path.exists(tmp) else set())
    write_header, minute_df = not os.path.exists(tmp), load_spy_minute()
    for day in trading_days(start, end):
        if day in done:
            continue
        try:
            price = day_open_price(day, minute_df, headers)
            wanted = strike_window(list_contracts(day, headers), price * 0.97, price * 1.03)
            rows = fetch_bars(wanted, day, headers) if wanted else []
        except Exception as e:
            print(f"SKIP {day}: {e}")
            continue
        df = pd.DataFrame(rows, columns=COLS)
        if not df.empty:
            df["ts"] = pd.to_datetime(df["ts"], utc=True).dt.strftime("%Y-%m-%d %H:%M:%S")
        df.to_csv(tmp, mode="a", index=False, header=write_header)
        write_header = False
        print(f"{day}: {len(wanted)} contracts, {len(df)} bars")
    if os.path.exists(tmp):
        pd.read_csv(tmp).to_csv(out, index=False, compression="gzip")
        os.remove(tmp)
    print("done:", out)


def validate(path):
    df = pd.read_csv(path)
    if set(COLS) - set(df.columns):
        print("MISSING COLUMNS:", set(COLS) - set(df.columns))
        return False
    ok = True
    df["ts_dt"] = pd.to_datetime(df["ts"])
    for key, g in df.groupby(["expiry", "strike", "right"]):
        if not g["ts_dt"].is_monotonic_increasing:
            print("NOT MONOTONE within contract:", key)
            ok = False
    bad = df["ts_dt"].dt.strftime("%Y-%m-%d") != df["expiry"].astype(str)
    if bad.any():
        print(f"{bad.sum()} rows where expiry != date(ts) (must be 0 for same-day expiry)")
        ok = False
    cov = df.assign(month=df["ts_dt"].dt.strftime("%Y-%m")).groupby("month").size()
    print("coverage by month:\n", cov.to_string())
    print(f"rows: {len(df)}", "VALID" if ok else "INVALID")
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=OUT, help="target .csv.gz path")
    ap.add_argument("--start", default=START)
    ap.add_argument("--end", default=END)
    ap.add_argument("--resume", action="store_true", help="skip days already in --out or its temp file")
    ap.add_argument("--validate-only", action="store_true", help="skip fetch(), just validate --out")
    a = ap.parse_args()
    if a.validate_only:
        raise SystemExit(0 if validate(a.out) else 1)
    fetch(a.start, a.end, a.out, a.resume)
    validate(a.out)
