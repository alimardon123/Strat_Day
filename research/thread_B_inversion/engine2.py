"""Bracket-trade simulator: signals on 5m bars, stop/target resolved on the 1m path.

Hot loop is numpy-only so we can afford thousands of bootstrap replications.
"""
import numpy as np
import pandas as pd

SESSION_END = 15 * 60 + 55


def to_5m(df):
    g = df.set_index("ts").resample("5min", label="right", closed="right")
    out = g.agg(open=("open", "first"), high=("high", "max"),
                low=("low", "min"), close=("close", "last")).dropna().reset_index()
    out["session"] = out["ts"].dt.date
    out["minute_of_day"] = out["ts"].dt.hour * 60 + out["ts"].dt.minute
    out = out[(out["minute_of_day"] >= 570) & (out["minute_of_day"] <= 960)]
    return out.reset_index(drop=True)


def atr(bars, period=14):
    h, l, c = bars["high"], bars["low"], bars["close"]
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    new = bars["session"] != bars["session"].shift(1)
    tr[new] = (h - l)[new]
    return tr.rolling(period).mean()


class Path:
    """1-minute bars as flat numpy arrays."""

    def __init__(self, df):
        self.open = df["open"].to_numpy(float)
        self.high = df["high"].to_numpy(float)
        self.low = df["low"].to_numpy(float)
        self.close = df["close"].to_numpy(float)
        self.mod = df["minute_of_day"].to_numpy(np.int32)
        self.sess = pd.factorize(df["session"])[0].astype(np.int32)
        self.n = len(df)


def resolve(p, start, direction, entry, stop, target, max_bars):
    """Walk forward from `start`. Returns (exit_price, bars_held, reason_code).
    reason_code: 0=stop 1=target 2=session_end/timeout
    Stop is checked before target inside a bar (pessimistic)."""
    s0 = p.sess[start]
    end = min(start + max_bars, p.n - 1)
    for i in range(start, end + 1):
        if p.sess[i] != s0:
            return p.close[i - 1], i - start, 2
        if direction > 0:
            if p.low[i] <= stop:
                return stop, i - start, 0
            if p.high[i] >= target:
                return target, i - start, 1
        else:
            if p.high[i] >= stop:
                return stop, i - start, 0
            if p.low[i] <= target:
                return target, i - start, 1
        if p.mod[i] >= SESSION_END:
            return p.close[i], i - start, 2
    return p.close[end], end - start, 2


REASON = {0: "stop", 1: "target", 2: "flat"}


def run_trades(entries, p, cost_pts, max_bars=240):
    rows = []
    for e in entries:
        px, held, why = resolve(p, e["path_idx"], e["direction"],
                                e["entry"], e["stop"], e["target"], max_bars)
        gross = (px - e["entry"]) * e["direction"]
        risk = abs(e["entry"] - e["stop"])
        rows.append({**e, "exit": px, "bars_held": held, "reason": REASON[why],
                     "gross_pts": gross, "net_pts": gross - cost_pts,
                     "risk_pts": risk, "R": (gross - cost_pts) / risk})
    return pd.DataFrame(rows)


def stats(t):
    R = t["R"].dropna()
    if len(R) == 0:
        return {}
    w, l = R[R > 0], R[R <= 0]
    aw = w.mean() if len(w) else 0.0
    al = abs(l.mean()) if len(l) else 0.0
    curve = R.cumsum()
    return {
        "trades": len(R),
        "win_pct": 100 * len(w) / len(R),
        "rr": aw / al if al else np.inf,
        "exp_R": R.mean(),
        "total_R": R.sum(),
        "pf": w.sum() / abs(l.sum()) if l.sum() != 0 else np.inf,
        "t": R.mean() / (R.std() / np.sqrt(len(R))) if R.std() > 0 else 0.0,
        "maxDD_R": (curve - curve.cummax()).min(),
    }


def report(t, label):
    s = stats(t)
    if not s:
        return f"{label}: no trades"
    return (f"{label}\n"
            f"   trades {s['trades']:>6d} | win {s['win_pct']:5.1f}% | avg R:R 1:{s['rr']:.2f}\n"
            f"   expectancy {s['exp_R']:+.4f}R | total {s['total_R']:+8.1f}R | PF {s['pf']:.2f}\n"
            f"   t-stat {s['t']:+6.2f} | maxDD {s['maxDD_R']:8.1f}R")
