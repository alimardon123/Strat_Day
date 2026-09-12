"""Iteration 16 — many weak intraday patterns, combined instead of selected.

Iteration 15's key number was the train/test t correlation of +0.256. That says
intraday structure is REAL but roughly a quarter the size it appears in-sample.
I then did the wrong thing with it: picked the single best cell, and watched it
decay from Sharpe 1.01 to 0.32 exactly as selection bias predicts.

The right response to many weak-but-real signals is aggregation. If 200 cells
each carry a quarter of their apparent edge and their errors are partly
independent, a basket of all 200 has a far better signal-to-noise ratio than the
best single one - and it trades nearly every day, because on any given day some
subset of the patterns is active.

This iteration expands the pattern space (calendar effects, expiry weeks,
volatility regime, day of week), selects EVERY cell that looks positive on train
without cherry-picking, and holds them all.
"""
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")

ES_BPS = 0.35


def wide_conditions(T):
    """Pre-open states plus calendar structure. All knowable before the open."""
    g, pr, rg = T.gap, T.prev_ret, T.prev_range
    gq = g.abs().rolling(252, min_periods=60).quantile(0.75)
    rq = rg.rolling(252, min_periods=60).quantile(0.70)
    rv = T.prev_range.rolling(20).mean()
    rvq = rv.rolling(252, min_periods=60).quantile(0.70)
    idx = T.index
    dom = pd.Series(idx.day, index=idx)
    wom = pd.Series((idx.day - 1) // 7 + 1, index=idx)
    C = {
        "all": pd.Series(True, index=idx),
        "gap_up": g > 0, "gap_down": g < 0,
        "gap_big": g.abs() > gq, "gap_small": g.abs() <= gq,
        "prev_up": pr > 0, "prev_down": pr < 0,
        "prev_wide": rg > rq, "prev_narrow": rg <= rq,
        "gapdn_prevdn": (g < 0) & (pr < 0), "gapup_prevup": (g > 0) & (pr > 0),
        "gapdn_prevup": (g < 0) & (pr > 0), "gapup_prevdn": (g > 0) & (pr < 0),
        "highvol": rv > rvq, "lowvol": rv <= rvq,
        "turn_of_month": (dom >= 26) | (dom <= 3),
        "mid_month": (dom > 3) & (dom < 26),
        "expiry_week": wom == 3,                       # monthly option expiry
        "month_start": dom <= 5, "month_end": dom >= 24,
    }
    for i, nm in enumerate(["mon", "tue", "wed", "thu", "fri"]):
        C[f"dow_{nm}"] = pd.Series(idx.dayofweek == i, index=idx)
    return C


def scan_and_build(T, split, min_n=200, t_cut=1.5, cost_bps=ES_BPS):
    """Score every cell on TRAIN, keep all that pass, hold the whole basket."""
    W = [f"w{i}" for i in range(13)]
    R = T[W].fillna(0.0)
    CUM = R.cumsum(axis=1)
    seg = lambda i, j: CUM[f"w{j}"] - (CUM[f"w{i-1}"] if i > 0 else 0)
    C = wide_conditions(T)
    tr_mask = T.index < split
    cells = []
    for i in range(13):
        for j in range(i, 13):
            s = seg(i, j)
            for cn, cm in C.items():
                x = s[cm & tr_mask].dropna()
                if len(x) < min_n or x.std() == 0: continue
                t = x.mean() / (x.std() / np.sqrt(len(x)))
                if abs(t) < t_cut: continue
                cells.append((i, j, cn, np.sign(t), t))
    # aggregate:每 bucket position = mean sign across active cells covering it
    pos = pd.DataFrame(0.0, index=T.index, columns=W)
    cnt = pd.DataFrame(0.0, index=T.index, columns=W)
    for i, j, cn, sgn, t in cells:
        m = C[cn].reindex(T.index).fillna(False).values
        for k in range(i, j + 1):
            pos.iloc[m, k] += sgn
            cnt.iloc[m, k] += 1
    net = (pos / cnt.replace(0, np.nan)).fillna(0.0)      # in [-1, 1]
    gross = (net * R).sum(axis=1)
    turn = net.diff(axis=1).abs().sum(axis=1) + net[W[0]].abs()
    ret = gross - turn * cost_bps / 10000
    return ret, cells, net
