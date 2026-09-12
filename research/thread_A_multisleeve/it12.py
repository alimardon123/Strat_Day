"""Iteration 12 — attack the PAYOFF leg with positive skew.

Iteration 11 diagnosed why the payoff ratio is stuck at ~1:1.44 while the win
rate climbs freely: every sleeve in the portfolio is negatively skewed. They are
all, in different costumes, short some form of tail risk. Adding Sharpe raises
the hit rate efficiently and the payoff ratio barely at all.

The fix has to be a POSITIVELY skewed return stream: many small losses, rare
large gains. That is the classic breakout / managed-futures profile — cut losers
quickly at a stop, never take profit, let the rare big trend pay for everything.

S10 DONCHIAN: enter long on a 50-day high, short on a 50-day low; exit on a
20-day counter-extreme. No profit target at all - that is the whole point.
Inverse-vol sized across the 25-ETF panel. This is structurally different from
S2 TSMOM, which is a monthly binary in/out with no stop and therefore only mildly
skewed.
"""
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
from it8 import load_prices, COST_BPS


def donchian(C, entry_lb=50, exit_lb=20, longshort=True):
    R = C.pct_change()
    hi_e = C.rolling(entry_lb).max().shift(1)
    lo_e = C.rolling(entry_lb).min().shift(1)
    hi_x = C.rolling(exit_lb).max().shift(1)
    lo_x = C.rolling(exit_lb).min().shift(1)
    pos = pd.DataFrame(0.0, index=C.index, columns=C.columns)
    for s in C.columns:
        c = C[s].values; he = hi_e[s].values; le = lo_e[s].values
        hx = hi_x[s].values; lx = lo_x[s].values
        p = np.zeros(len(c)); cur = 0.0
        for i in range(len(c)):
            if not np.isfinite(he[i]):
                p[i] = 0.0; continue
            if cur == 0:
                if c[i] > he[i]: cur = 1.0
                elif longshort and c[i] < le[i]: cur = -1.0
            elif cur > 0:
                if c[i] < lx[i]: cur = 0.0            # trailing exit, no target
            else:
                if c[i] > hx[i]: cur = 0.0
            p[i] = cur
        pos[s] = p
    iv = (1/R.rolling(60).std().shift(1)).replace([np.inf, -np.inf], np.nan)
    w = (pos.shift(1) * iv)
    w = w.div(w.abs().sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    turn = w.diff().abs().sum(axis=1).fillna(0.0)
    return (w * R).sum(axis=1).fillna(0.0) - turn * COST_BPS / 10000
