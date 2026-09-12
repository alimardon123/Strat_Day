"""Iteration 2 — multi-day holds resolved on the MINUTE path.

The daily study could only say "stop or target, tie goes to the stop" once per
day. Here the same 5-day trade is resolved minute by minute across sessions, so
the stop/target sequencing is real rather than assumed. That is the one thing
minute data can genuinely add to a multi-day system.
"""
import numpy as np, pandas as pd

SLIP_BPS = 0.5
COST_PTS = 0.004


def backtest_md(d, entries, stop_pts, targ_pts, max_days, direction=1, label=""):
    """entries: bool on a minute bar -> enter at the NEXT minute bar's open.
    Exit when the minute path touches stop or target (stop wins same-bar ties),
    or at the close of the max_days-th session."""
    o, h, l, c = d.open.values, d.high.values, d.low.values, d.close.values
    dayid = d.dayid.values
    e = np.asarray(entries, bool)
    sp, tp = np.asarray(stop_pts, float), np.asarray(targ_pts, float)
    n = len(d)
    out = []
    i = 0
    while i < n - 1:
        if not e[i] or not np.isfinite(sp[i]) or sp[i] <= 0:
            i += 1; continue
        j0 = i + 1
        entry = o[j0]; risk = sp[i]
        stop = entry - direction * risk
        targ = entry + direction * tp[i]
        last_day = dayid[i] + max_days
        px = rsn = None; j = j0
        while j < n and dayid[j] <= last_day:
            if direction == 1:
                if l[j] <= stop: px, rsn = stop, "stop"
                elif h[j] >= targ: px, rsn = targ, "target"
            else:
                if h[j] >= stop: px, rsn = stop, "stop"
                elif l[j] <= targ: px, rsn = targ, "target"
            if px is not None: break
            j += 1
        if px is None:
            j = min(j, n - 1)
            while j > j0 and dayid[j] > last_day: j -= 1
            px, rsn = c[j], "time"
        gross = direction * (px - entry)
        pnl = gross - COST_PTS - entry * SLIP_BPS / 10000.0 * 2
        out.append((label, d.date.values[i], d.bar.values[i], entry, px, rsn,
                    dayid[j] - dayid[i], pnl, pnl / risk, risk))
        i = j + 1
    return pd.DataFrame(out, columns=["setup", "date", "bar", "entry", "exit", "reason",
                                      "days", "pnl_pts", "r", "risk_pts"])
