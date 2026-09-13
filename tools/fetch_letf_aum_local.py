"""Run this on YOUR machine (fund-sponsor NAV downloads are blocked from the cloud
container; UNTESTED FROM THE RESEARCH CONTAINER -- the proxy has no route to
proshares.com, direxion.com, or Yahoo, so nothing below has ever actually executed).

Produces data/ext/letf_aum_2006_2026.csv: one row per fund per trading day for the
levered/inverse S&P 500 ETFs used by A38 (pipeline/units/letf.py, not yet written):
SSO, SDS, SH, UPRO, SPXU (ProShares); SPXL, SPXS (Direxion).
Columns: ticker,date,shares_outstanding,nav,net_assets[,source] -- net_assets =
shares_outstanding * nav (USD); `source` is only written for rows that fall back to the
yfinance proxy (see fetch_yfinance below), so the pipeline can drop/flag proxy rows
instead of treating them as sponsor-reported AUM.

fetch() tries each sponsor's public historical-NAV download first, then falls back to
yfinance (get_shares_full for shares outstanding, daily close as a NAV proxy) if the
sponsor download fails or is missing a needed column. A partial history (sponsor data
starting later than 2006, or a ticker missing entirely) is accepted as a gap;
validate() reports it rather than failing the whole file.

    python tools/fetch_letf_aum_local.py
    python tools/fetch_letf_aum_local.py --validate-only --out data/ext/letf_aum_2006_2026.csv
"""
import argparse
import io
import os
import time
import numpy as np
import pandas as pd
import requests

OUT = "data/ext/letf_aum_2006_2026.csv"
START = "2006-01-01"
SPONSOR = {"SSO": "proshares", "SDS": "proshares", "SH": "proshares", "UPRO": "proshares",
           "SPXU": "proshares", "SPXL": "direxion", "SPXS": "direxion"}

# Best-effort URL patterns for each sponsor's historical NAV/shares-outstanding CSV
# download, from memory of the fund pages' "Download" links -- both sponsors have
# reorganized these before; if a fetch fails, find the real link on the fund page.
PROSHARES_URL = "https://www.proshares.com/api/fund_prices/download?ticker={t}&startDate=2006-01-01"
DIREXION_URL = "https://www.direxion.com/products/download-historical-nav?symbol={t}"


def fetch_sponsor(t):
    """Try the sponsor's own NAV/shares download; None (with a printed reason) on failure."""
    url = (PROSHARES_URL if SPONSOR[t] == "proshares" else DIREXION_URL).format(t=t)
    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        d = pd.read_csv(io.StringIO(r.text))
    except Exception as e:
        print(f"sponsor download failed for {t} ({SPONSOR[t]}) at {url}: {e}")
        return None
    d.columns = [c.strip().lower().replace(" ", "_") for c in d.columns]
    if "nav_per_share" in d.columns:
        d = d.rename(columns={"nav_per_share": "nav"})
    need = {"date", "nav"}
    if not need.issubset(d.columns):
        print(f"{t}: sponsor file at {url} is missing {need - set(d.columns)}; skipping")
        return None
    if "shares_outstanding" not in d.columns:
        print(f"{t}: sponsor file at {url} has NAV but no shares outstanding; falling back")
        return None
    d["date"] = pd.to_datetime(d["date"])
    if "net_assets" not in d.columns:
        d["net_assets"] = d["shares_outstanding"] * d["nav"]
    d.insert(0, "ticker", t)
    return d[["ticker", "date", "shares_outstanding", "nav", "net_assets"]]


def fetch_yfinance(t):
    """Fallback proxy: yfinance shares (sparse, forward-filled) x daily close as NAV."""
    try:
        import yfinance as yf  # lazy: only needed here, keeps --help usable without it
        shares = yf.Ticker(t).get_shares_full(start=START)
        px = yf.download(t, start=START, auto_adjust=False, progress=False)["Close"]
    except Exception as e:
        print(f"yfinance fallback failed for {t}: {e}")
        return None
    if shares is None or shares.empty or px.empty:
        print(f"{t}: yfinance returned no usable data from any source")
        return None
    shares = shares.rename("shares_outstanding").resample("D").ffill()
    d = px.rename("nav").to_frame().join(shares, how="left")
    d["shares_outstanding"] = d["shares_outstanding"].ffill()
    d = d.dropna().reset_index().rename(columns={"Date": "date", "index": "date"})
    d.insert(0, "ticker", t)
    d["net_assets"] = d["shares_outstanding"] * d["nav"]
    d["source"] = "yfinance_proxy"
    return d[["ticker", "date", "shares_outstanding", "nav", "net_assets", "source"]]


def fetch(out):
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    frames = []
    for t in SPONSOR:
        d = fetch_sponsor(t) or fetch_yfinance(t)
        if d is None:
            print(f"{t}: no data from any source, omitted entirely")
            continue
        frames.append(d)
        time.sleep(0.3)
    if not frames:
        raise SystemExit("no ticker produced data from any source; fix the URLs/network and retry")
    panel = pd.concat(frames, ignore_index=True).sort_values(["ticker", "date"])
    panel.to_csv(out, index=False)
    print(f"wrote {out}: {len(panel)} rows, {panel['ticker'].nunique()} tickers")


def validate(path):
    df = pd.read_csv(path, parse_dates=["date"])
    need = {"ticker", "date", "shares_outstanding", "nav", "net_assets"}
    missing = need - set(df.columns)
    if missing:
        print("MISSING COLUMNS:", missing)
        return False
    ok = True
    for col in ("shares_outstanding", "nav", "net_assets"):
        if (df[col] < 0).any():
            print(f"negative values in {col}")
            ok = False
    dup = df.duplicated(["ticker", "date"]).sum()
    if dup:
        print(f"{dup} duplicate (ticker, date) rows -- expected exactly one row per fund per day")
        ok = False
    implied = df["shares_outstanding"] * df["nav"]
    off = (implied - df["net_assets"]).abs() > 0.01 * df["net_assets"].abs().clip(lower=1)
    if off.any():
        print(f"{off.sum()} rows where net_assets differs from shares_outstanding*nav by >1%")
        ok = False
    for t, g in df.sort_values("date").groupby("ticker"):
        if not g["date"].is_monotonic_increasing:
            print(f"{t}: dates not monotone")
            ok = False
        d = g["date"].dt.date.values
        gaps = [int(np.busday_count(d[i - 1], d[i])) for i in range(1, len(d))]
        big = sum(1 for x in gaps if x > 5)
        print(f"{t}: {d[0]} -> {d[-1]}, {len(g)} rows, {big} gaps > 5 trading days")
    print("VALID" if ok else "INVALID")
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=OUT, help="target CSV path")
    ap.add_argument("--validate-only", action="store_true", help="skip fetch(), just validate --out")
    a = ap.parse_args()
    if a.validate_only:
        raise SystemExit(0 if validate(a.out) else 1)
    fetch(a.out)
    validate(a.out)
