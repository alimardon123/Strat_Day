"""Iteration 10 — three ideas that are different in KIND.

IDEA A — SESSION DECOMPOSITION.
Every strategy so far treated a day as one object. But a day is two different
markets: the overnight session (close -> next open), where the tape is closed,
liquidity is thin, and positioning happens via futures and news; and the intraday
session (open -> close), where the auction runs. These have very different
return and risk characteristics, and the equity risk premium is documented to
accrue almost entirely overnight. Nobody in this study has looked at that split.
If it holds, it is the closest thing to a genuine structural asymmetry available
here.

IDEA B — CORRELATION-SCALED GROSS EXPOSURE.
Derived from iteration 7's failure. The system's diversification is not a
constant: realised strategy correlation moves, and when it spikes the portfolio
silently becomes one bet. So measure effective independent bets in a trailing
window and scale gross exposure by it. Cut risk exactly when diversification
stops working, rather than when volatility rises. To my knowledge this is not a
standard construction and it falls straight out of this programme's own result.

IDEA C — STRATEGY MOMENTUM.
Allocate across sleeves by their own trailing performance instead of equally.
Factor/strategy momentum is documented. Iteration 9 showed sleeve SELECTION is
noise; this asks whether continuous WEIGHTING does better than a binary keep/drop.
"""
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
from it8 import load_prices, vol_target, perf, show, COST_BPS


def session_returns(raw):
    """Split each asset's daily return into overnight and intraday legs."""
    ov, it, tot = {}, {}, {}
    for s, d in raw.items():
        o, c = d.open, d.close
        ov[s] = o / c.shift(1) - 1          # close -> next open
        it[s] = c / o - 1                   # open -> close
        tot[s] = c.pct_change()
    return pd.DataFrame(ov), pd.DataFrame(it), pd.DataFrame(tot)


def effective_bets(V, lb=126):
    """Trailing effective number of independent bets across sleeve return streams."""
    n = V.shape[1]
    out = pd.Series(index=V.index, dtype=float)
    vals = V.values
    for i in range(lb, len(V)):
        w = vals[i - lb:i]
        c = np.corrcoef(w, rowvar=False)
        iu = np.triu_indices(n, 1)
        rho = np.nanmean(c[iu])
        out.iloc[i] = n / (1 + (n - 1) * max(rho, 0.0))
    return out.shift(1)                      # lag: no lookahead


def strategy_momentum_weights(V, lb=126, floor=0.0):
    """Weight sleeves by trailing Sharpe, floored at zero, renormalised monthly."""
    W = pd.DataFrame(index=V.index, columns=V.columns, dtype=float)
    last, cur = None, None
    for i, dt in enumerate(V.index):
        if i < lb: continue
        if last is None or dt.month != last.month:
            w = V.iloc[i - lb:i]
            sh = (w.mean() / w.std().replace(0, np.nan)).fillna(0.0)
            ww = sh.clip(lower=floor).values
            ww = np.full(len(ww), 1/len(ww)) if ww.sum() <= 0 else ww / ww.sum()
            last, cur = dt, ww
        W.iloc[i] = cur
    return W.shift(1).ffill()
