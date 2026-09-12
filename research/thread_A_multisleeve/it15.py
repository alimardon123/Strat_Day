"""Iteration 15 — exhaustive intraday scan, properly deflated.

Previous intraday work tested ideas one at a time: opening range, sweeps, VWAP
bands, first-30/last-30, overnight split. Each failed, but that is weak evidence
- it only rules out the ideas I happened to think of.

This iteration searches the intraday space SYSTEMATICALLY instead. Every
combination of:

    entry window   x   holding window   x   day of week   x   pre-open state

on SPX 1-minute data, 2005-2020. Then applies the correct multiple-testing
threshold, so "we found a cell with t=3" means something rather than nothing.

The point is a trustworthy answer in EITHER direction. If a real intraday
window exists, an exhaustive scan finds it. If the scan finds only what a scan
of random data would find, that is a much stronger negative than ten failed
hand-picked ideas.
"""
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
from scipy.stats import norm

ES_BPS = 0.35          # per side, ES futures


def build_day_table(rth):
    """One row per session, with 30-minute bucket returns and pre-open state."""
    d = rth.copy()
    d["b30"] = (d.bar // 30).clip(upper=12)
    px = d.groupby(["date", "b30"]).agg(o=("open", "first"), c=("close", "last"),
                                        h=("high", "max"), l=("low", "min"))
    ret = (px.c / px.o - 1).unstack()          # 13 buckets per day
    ret.columns = [f"w{c}" for c in ret.columns]
    day = d.groupby("date").agg(o=("open", "first"), c=("close", "last"),
                                h=("high", "max"), l=("low", "min"))
    day["prev_c"] = day.c.shift(1)
    day["gap"] = day.o / day.prev_c - 1
    day["prev_ret"] = day.c.pct_change().shift(1)
    day["prev_range"] = ((day.h - day.l) / day.c).shift(1)
    T = ret.join(day[["gap", "prev_ret", "prev_range"]])
    T.index = pd.to_datetime(T.index)
    T["dow"] = T.index.dayofweek
    return T.dropna(subset=["gap"])


def conditions(T):
    """Pre-open states, all knowable before the session starts."""
    g, pr, rg = T.gap, T.prev_ret, T.prev_range
    gq = g.abs().rolling(252, min_periods=60).quantile(0.75)
    rq = rg.rolling(252, min_periods=60).quantile(0.75)
    return {
        "all":            pd.Series(True, index=T.index),
        "gap_up":         g > 0,
        "gap_down":       g < 0,
        "gap_big":        g.abs() > gq,
        "gap_small":      g.abs() <= gq,
        "prev_up":        pr > 0,
        "prev_down":      pr < 0,
        "prev_wide":      rg > rq,
        "prev_narrow":    rg <= rq,
        "gapdn_prevdn":   (g < 0) & (pr < 0),
        "gapup_prevup":   (g > 0) & (pr > 0),
        "gapdn_prevup":   (g < 0) & (pr > 0),
    }


def expected_max_t(N):
    """Expected maximum |t| across N independent trials under the null."""
    g = 0.5772156649
    return (1 - g) * norm.ppf(1 - 1/(2*N)) + g * norm.ppf(1 - 1/(2*N*np.e))
