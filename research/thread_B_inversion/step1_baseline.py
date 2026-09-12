"""Step 1 — build a naive breakout strategy and confirm it actually loses."""
import numpy as np
import pandas as pd
from loader import load
from engine2 import to_5m, atr, Path, run_trades, report, stats

COST_PTS = 0.50          # round-trip spread + slippage, SPX points
LOOKBACK = 20            # 5m bars = 100 minutes
STOP_ATR, TARG_ATR = 1.5, 3.0
COOLDOWN = 6             # 5m bars between signals


def build_signals(b):
    """Donchian breakout: close beyond the prior N-bar extreme."""
    hh = b["high"].shift(1).rolling(LOOKBACK).max()
    ll = b["low"].shift(1).rolling(LOOKBACK).min()
    same_sess = b["session"] == b["session"].shift(LOOKBACK)
    b["long"] = (b["close"] > hh) & same_sess
    b["short"] = (b["close"] < ll) & same_sess
    return b


def make_entries(b, m1_index):
    """One position at a time; entry at the next 1m bar's open after the 5m close."""
    entries, last = [], -999
    ts_to_idx = m1_index
    for i, row in enumerate(b.itertuples()):
        if i - last < COOLDOWN or np.isnan(row.atr) or row.atr <= 0:
            continue
        d = 1 if row.long else (-1 if row.short else 0)
        if d == 0 or row.minute_of_day > 15 * 60 + 30:
            continue
        nxt = ts_to_idx.get(row.ts, None)
        if nxt is None or nxt + 1 >= len(ts_to_idx):
            continue
        px = row.close
        entries.append(dict(path_idx=nxt + 1, direction=d, entry=px,
                            stop=px - d * STOP_ATR * row.atr,
                            target=px + d * TARG_ATR * row.atr,
                            atr=row.atr, ts=row.ts, bar_i=i))
        last = i
    return entries


if __name__ == "__main__":
    m1 = load()
    b = to_5m(m1)
    b["atr"] = atr(b)
    b = build_signals(b)

    p = Path(m1)
    idx = {t: i for i, t in enumerate(m1["ts"])}
    entries = make_entries(b, idx)
    print(f"signals: {len(entries)}  ({b['long'].sum()} raw long / {b['short'].sum()} raw short)")

    t = run_trades(entries, p, COST_PTS)
    t.to_pickle("baseline_trades.pkl")

    print()
    print(report(t, "BASELINE — naive Donchian breakout (with 0.50pt cost)"))
    print()
    print(report(t.assign(R=t["gross_pts"] / t["risk_pts"]), "  same, zero cost"))
    print("\nexit reasons:", t["reason"].value_counts().to_dict())
    print("by direction:")
    for d, g in t.groupby("direction"):
        print("  ", "long " if d > 0 else "short", stats(g))
