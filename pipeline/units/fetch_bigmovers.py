"""Fetch unit: daily bars from willhjw/big_movers — `--in spy` (SPY Historical Data.csv) or
`--in stocks` (collected_stocks/*.csv, long format). Parsing follows Thread A
(research/thread_A_multisleeve/it5.py, fleet_worker.py): investing.com-style files with
Date, Price/Close, Open, High, Low, Vol. columns, thousands separators and K/M suffixes.

    python -m pipeline.units.fetch_bigmovers --in spy --out data/raw/spy_daily.parquet
    python -m pipeline.units.fetch_bigmovers --in stocks --out data/raw/stocks_daily.parquet
"""
import argparse
import io
import os
import pandas as pd
from pipeline.units import _gh

REPO = "willhjw/big_movers"
NAMES = {"price": "close", "close/last": "close", "vol.": "volume", "vol": "volume"}


def _num(s):
    s = s.astype(str).str.replace(",", "", regex=False).str.replace("$", "", regex=False).str.strip()
    mult = s.str[-1].map({"K": 1e3, "M": 1e6, "B": 1e9})
    val = pd.to_numeric(s.where(mult.isna(), s.str[:-1]), errors="coerce")
    return val * mult.fillna(1.0)


def parse(txt):
    d = pd.read_csv(io.StringIO(txt))
    d.columns = [NAMES.get(c.strip().lower(), c.strip().lower()) for c in d.columns]
    if "datetime" in d.columns:
        d = d.rename(columns={"datetime": "date"})
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    for c in ["open", "high", "low", "close", "volume"]:
        d[c] = _num(d[c]) if c in d.columns else float("nan")
    d = d.dropna(subset=["date", "close"]).sort_values("date").drop_duplicates("date")
    return d[["date", "open", "high", "low", "close", "volume"]].reset_index(drop=True)


def main(mode, out):
    path = _gh.clone(REPO, "big_movers")
    files = _gh.tree(path)
    if mode == "spy":
        f = next(x for x in files if x.lower().endswith("spy historical data.csv"))
        df = parse(_gh.show(path, f))
        read, skipped = [f], []
    else:
        read, skipped, frames = [], [], []
        for f in sorted(x for x in files if "collected_stocks/" in x and x.lower().endswith(".csv")):
            try:
                d = parse(_gh.show(path, f))
                d.insert(0, "ticker", os.path.basename(f)[:-4].upper())
                frames.append(d)
                read.append(f)
            except Exception as e:  # noqa: BLE001 — a bad symbol must not kill the panel
                skipped.append(f"{f}: {e}")
        df = pd.concat(frames, ignore_index=True).sort_values(["ticker", "date"]).drop_duplicates(["ticker", "date"])
    df.to_parquet(out, index=False)
    _gh.manifest(f"bigmovers_{mode}", repo=REPO, commit=_gh.commit(path), files_read=len(read),
                 files_skipped=skipped, rows=len(df), date_min=df["date"].min(), date_max=df["date"].max(),
                 tickers=int(df["ticker"].nunique()) if "ticker" in df else 1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", choices=["spy", "stocks"], default="spy")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    _gh.run(lambda: main(a.inp, a.out), a.out)
