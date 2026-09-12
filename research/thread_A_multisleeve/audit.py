import pandas as pd, numpy as np, glob, os
files = sorted(glob.glob("/home/claude/m1/**/oanda/SPX500_USD/**/*.csv", recursive=True))
print("files:", len(files))
d = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
d["time"] = pd.to_datetime(d["time"])
d = d[["time", "open", "high", "low", "close", "volume"]].sort_values("time")
d = d.drop_duplicates("time").reset_index(drop=True)
print("rows:", len(d), "|", d.time.min(), "->", d.time.max())

# --- timezone resolution: find the hour with the tick-volume spike ---
prof = d.groupby(d.time.dt.hour).volume.mean()
print("\nmean tick-volume by hour of timestamp:")
print(" ".join(f"{h:02d}:{v:.0f}" for h, v in prof.items()))
print("peak hour:", prof.idxmax())

# --- integrity ---
bad = d[(d.high < d.low) | (d.high < d[["open","close"]].max(axis=1)) |
        (d.low > d[["open","close"]].min(axis=1))]
print("\nOHLC violations:", len(bad))
print("zero-volume bars:", (d.volume == 0).sum(), f"({(d.volume==0).mean()*100:.2f}%)")
print("zero-range bars:", (d.high == d.low).sum(), f"({(d.high==d.low).mean()*100:.2f}%)")
r = d.close.pct_change()
print("minute returns |r|>2%:", (r.abs() > 0.02).sum())
print("bars per year:")
print(d.groupby(d.time.dt.year).size().to_string())
d.to_parquet("/home/claude/work/m1_raw.pkl") if False else d.to_pickle("/home/claude/work/m1_raw.pkl")
