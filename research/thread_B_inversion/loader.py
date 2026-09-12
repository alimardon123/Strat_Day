"""Load Histdata SPXUSD 1-minute bars into a clean session-tagged DataFrame."""
import glob
import numpy as np
import pandas as pd

COLS = ["ts", "open", "high", "low", "close", "vol"]


def load(pattern="data/spx_*.csv", rth_only=True):
    frames = []
    for f in sorted(glob.glob(pattern)):
        d = pd.read_csv(f, sep=";", header=None, names=COLS)
        frames.append(d)
    df = pd.concat(frames, ignore_index=True)
    df["ts"] = pd.to_datetime(df["ts"], format="%Y%m%d %H%M%S")
    df = df.sort_values("ts").drop_duplicates("ts").reset_index(drop=True)

    if rth_only:  # histdata stamps are US Eastern (no DST shift)
        t = df["ts"].dt.time
        df = df[(t >= pd.Timestamp("09:30").time()) & (t <= pd.Timestamp("16:00").time())]

    df = df[df["ts"].dt.dayofweek < 5].reset_index(drop=True)
    df["session"] = df["ts"].dt.date
    df["minute_of_day"] = df["ts"].dt.hour * 60 + df["ts"].dt.minute
    return df


def add_atr(df, period=14):
    h, l, c = df["high"], df["low"], df["close"]
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    # reset TR across session boundaries so overnight gaps don't leak in
    tr[df["session"] != df["session"].shift(1)] = (h - l)[df["session"] != df["session"].shift(1)]
    df["atr"] = tr.rolling(period).mean()
    return df


if __name__ == "__main__":
    df = add_atr(load())
    print(df.shape)
    print(df.head(3).to_string())
    print("\nsessions:", df["session"].nunique())
    print("bars/session:", df.groupby("session").size().describe()[["mean", "min", "max"]].to_dict())
    print("date range:", df["ts"].min(), "->", df["ts"].max())
    print("median ATR:", df["atr"].median().round(3), "| median close:", df["close"].median().round(1))
    print("ATR as % of price:", (100 * df["atr"] / df["close"]).median().round(4))
