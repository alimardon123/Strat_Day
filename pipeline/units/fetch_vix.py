"""Fetch unit: CBOE VIX daily OHLC from datasets/finance-vix (GitHub raw).

    python -m pipeline.units.fetch_vix --out data/raw/vix_daily.parquet
"""
import argparse
import hashlib
import io
import pandas as pd
import requests
from pipeline.units import _gh

URL = "https://raw.githubusercontent.com/datasets/finance-vix/main/data/vix-daily.csv"


def main(url, out):
    raw = requests.get(url, timeout=60).content
    df = pd.read_csv(io.BytesIO(raw))
    df.columns = [c.lower() for c in df.columns]
    df["date"] = pd.to_datetime(df["date"])
    df = (df[["date", "open", "high", "low", "close"]].dropna(subset=["close"])
          .sort_values("date").drop_duplicates("date").reset_index(drop=True))
    df.to_parquet(out, index=False)
    _gh.manifest("vix", url=url, sha256=hashlib.sha256(raw).hexdigest(), rows=len(df),
                 date_min=df["date"].min(), date_max=df["date"].max())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default=URL)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    _gh.run(lambda: main(a.inp, a.out), a.out)
