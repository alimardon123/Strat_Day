"""Fetch unit: Oanda 1-minute bars for one instrument (FutureSharks/financial-data).
Stamps are UTC (verified: 2018-07-08 first bar 22:00 UTC = 18:00 EDT Sunday open).

    python -m pipeline.units.fetch_oanda --in SPX500_USD --out data/raw/oanda_SPX500_USD.parquet
"""
import argparse
import io
import pandas as pd
from pipeline.units import _gh

REPO = "FutureSharks/financial-data"
BASE = "pyfinancialdata/data/currencies/oanda"


def main(instrument, out):
    path = _gh.clone(REPO, "financial-data")
    files = sorted(f for f in _gh.tree(path) if f.startswith(f"{BASE}/{instrument}/") and f.endswith(".csv"))
    frames = []
    for f in files:
        txt = _gh.show(path, f)
        if txt:
            frames.append(pd.read_csv(io.StringIO(txt), usecols=["time", "open", "high", "low", "close", "volume"]))
    df = pd.concat(frames, ignore_index=True)
    df["ts_utc"] = pd.to_datetime(df["time"], utc=True)
    df = (df[["ts_utc", "open", "high", "low", "close", "volume"]]
          .dropna(subset=["open", "high", "low", "close"])
          .sort_values("ts_utc").drop_duplicates("ts_utc").reset_index(drop=True))
    df["volume"] = df["volume"].fillna(0).astype("int64")
    df.to_parquet(out, index=False)
    years = df["ts_utc"].dt.year.value_counts().sort_index()
    _gh.manifest(f"oanda_{instrument}", repo=REPO, commit=_gh.commit(path), files_read=len(files),
                 rows=len(df), ts_min=df["ts_utc"].min(), ts_max=df["ts_utc"].max(),
                 rows_per_year={int(k): int(v) for k, v in years.items()})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="SPX500_USD")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    _gh.run(lambda: main(a.inp, a.out), a.out)
