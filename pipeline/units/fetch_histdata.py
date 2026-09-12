"""Fetch unit: histdata 1-minute bars for one instrument (FutureSharks/financial-data).
Format: `YYYYMMDD HHMMSS;open;high;low;close;vol`, no header, volume always 0.
Stamps are naive US Eastern WITH daylight saving (verified: Sunday Globex open prints 18:01 on
both 2018-01-07 and 2018-07-08 for SPXUSD).

    python -m pipeline.units.fetch_histdata --in SPXUSD --out data/raw/histdata_SPXUSD.parquet
"""
import argparse
import io
import pandas as pd
from pipeline.units import _gh

REPO = "FutureSharks/financial-data"
BASE = "pyfinancialdata/data/stocks/histdata"
COLS = ["ts", "open", "high", "low", "close", "volume"]


def main(instrument, out):
    path = _gh.clone(REPO, "financial-data")
    files = sorted(f for f in _gh.tree(path) if f.startswith(f"{BASE}/{instrument}/") and f.endswith(".csv"))
    frames = []
    for f in files:
        txt = _gh.show(path, f)
        if txt:
            frames.append(pd.read_csv(io.StringIO(txt), sep=";", header=None, names=COLS))
    df = pd.concat(frames, ignore_index=True)
    df["ts_et"] = pd.to_datetime(df["ts"], format="%Y%m%d %H%M%S")
    df = (df[["ts_et", "open", "high", "low", "close", "volume"]]
          .dropna(subset=["open", "high", "low", "close"])
          .sort_values("ts_et").drop_duplicates("ts_et").reset_index(drop=True))
    df["volume"] = df["volume"].fillna(0).astype("int64")
    df.to_parquet(out, index=False)
    years = df["ts_et"].dt.year.value_counts().sort_index()
    _gh.manifest(f"histdata_{instrument}", repo=REPO, commit=_gh.commit(path), files_read=len(files),
                 rows=len(df), ts_min=df["ts_et"].min(), ts_max=df["ts_et"].max(),
                 rows_per_year={int(k): int(v) for k, v in years.items()})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="SPXUSD")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    _gh.run(lambda: main(a.inp, a.out), a.out)
