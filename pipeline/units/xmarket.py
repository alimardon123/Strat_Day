"""D2b fleet unit — Thread A's gap-up afternoon call on another market's 2010-2018 histdata.

    python -m pipeline.units.xmarket --in GRXEUR --out out/xmarket_GRXEUR.csv

The local session is detected per month by the sustained-activity step among candidate opens
(ET minute-of-day), so DST mismatches between Europe and the US do not shift the window;
session length = 510 min (DAX/EuroStoxx 09:00-17:30 local); the entry is at the same FRACTION
of the session as 13:00 is of the US session (210/390 = 0.538), exit at the last bar; gap =
open / prior close - 1 > 0.3%. Reported with the day-block bootstrap. Running the same code on
SPXUSD gives the apples-to-apples baseline for the shrinkage comparison.
"""
import argparse

import numpy as np
import pandas as pd

from pipeline import sessions, stats
from pipeline.units import _gh

CANDIDATES = {"GRXEUR": [120, 150, 180, 210, 240], "ETXEUR": [120, 150, 180, 210, 240], "JPXJPY": [1140, 1170, 1200, 1230, 1260],
              "SPXUSD": [510, 570, 630]}
SESSION_MIN = {"GRXEUR": 510, "ETXEUR": 510, "JPXJPY": 300, "SPXUSD": 390}
# Xetra / Euronext cash session 09:00-17:30 local = 03:00-11:30 ET in both seasons (CET-EST = CEST-EDT = 6 h);
# the activity-step detector locks onto the 08:00-local Eurex futures open (02:00 ET), so the cash open is FIXED
# for the European markets and the detector is only reported. The 2-3 EU/US DST-mismatch weeks a year shift by 1 h.
FIXED_OPEN = {"GRXEUR": 180, "ETXEUR": 180}
ENTRY_FRAC = 210 / 390
GAP_MIN = 0.003


def main(inst, out):
    raw = sessions._load("histdata", f"data/raw/histdata_{inst}.parquet")
    raw["mod"] = raw["ts_ny"].dt.hour * 60 + raw["ts_ny"].dt.minute
    raw["date"] = raw["ts_ny"].dt.tz_localize(None).dt.normalize()
    raw = raw[raw["ts_ny"].dt.dayofweek < 5]
    raw["ym"] = raw["ts_ny"].dt.tz_localize(None).dt.to_period("M")
    length = SESSION_MIN[inst]
    frames = []
    for ym, g in raw.groupby("ym"):
        det, _ = sessions.open_step(g, tuple(CANDIDATES[inst]))
        win = FIXED_OPEN.get(inst, det)
        s = g[(g["mod"] >= win) & (g["mod"] < win + length)].copy()
        s["open_mod"] = win
        s["detected_open"] = det
        frames.append(s)
    d = pd.concat(frames)
    bars = d.groupby("date").size()
    d = d[d["date"].isin(bars[bars >= 0.75 * length].index)]
    g = d.groupby("date")
    day = pd.DataFrame({"open": g["open"].first(), "close": g["close"].last(), "open_mod": g["open_mod"].first(),
                        "detected_open": g["detected_open"].first()})
    day["prev_close"] = day["close"].shift(1)
    day["gap"] = day["open"] / day["prev_close"] - 1
    ent_mod = day["open_mod"] + int(round(ENTRY_FRAC * length))
    ent = d.merge(ent_mod.rename("em"), left_on="date", right_index=True)
    ent = ent[(ent["mod"] > ent["em"]) & (ent["mod"] <= ent["em"] + 5)].groupby("date")["open"].first()
    day["entry_px"] = ent
    t = day[(day["gap"] > GAP_MIN) & day["entry_px"].notna()].copy()
    t["ret_pct"] = 100 * (t["close"] / t["entry_px"] - 1)
    t["pts"] = t["close"] - t["entry_px"]
    atr = (g["high"].max() - g["low"].min()).rolling(14).mean().shift(1)
    t["ret_atr"] = t["pts"] / atr.reindex(t.index)
    row = dict(market=inst, sessions=len(day), n=len(t), win=100 * (t["pts"] > 0).mean(), mean_pct=t["ret_pct"].mean(),
               mean_atr=t["ret_atr"].mean(), uncond_pct=100 * (day["close"] / day["entry_px"] - 1).mean(),
               p_boot_day=stats.one_sided_p(t["ret_pct"].to_numpy(), stats.day_blocks(t.index)),
               open_modes=str(sorted(day["open_mod"].value_counts().head(3).to_dict().items())),
               detected_open_modes=str(sorted(day["detected_open"].value_counts().head(3).to_dict().items())))
    pd.DataFrame([row]).to_csv(out, index=False, float_format="%.6f")
    print(row)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="GRXEUR")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    _gh.run(lambda: main(a.inp, a.out), a.out)
