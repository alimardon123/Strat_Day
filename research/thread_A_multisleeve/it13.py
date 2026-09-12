"""Iteration 13 — an intraday sleeve, priced at futures cost.

You trade futures/options daily, which changes two things:
  1. Leverage is margin-based, not borrowed. The "levered 2.83x" variant I
     flagged as unimplementable in iteration 8 IS implementable with futures.
  2. Round-trip friction on ES is ~0.6-0.8 bp of notional (one tick 0.25 pts on
     a ~2000-4000 index, plus ~$2.50 commission on ~$200k notional), versus the
     2 bp I charged the ETF sleeves. Cheap enough to consider intraday again.

S11 INTRADAY MOMENTUM — the first half-hour return predicts the last half-hour
return (Gao, Han, Li & Zhou, 2018). Mechanism: infrequent-rebalancing traders
and late-day informed flow push the close in the direction the open established.
It holds a position for 30 minutes a day, so it should be close to uncorrelated
with everything in the daily portfolio.

Tested on SPX 1-minute data, 2005-2020, the same feed audited in iteration 1.
"""
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")

ES_BPS_PER_SIDE = 0.35        # ES futures: ~half a tick plus commission


def intraday_momentum(rth, first_min=30, last_min=30, cost_bps=ES_BPS_PER_SIDE):
    """Long the last `last_min` minutes if the first `first_min` minutes were up."""
    d = rth.copy()
    g = d.groupby("date", sort=False)
    o = g.open.transform("first")
    d["sess_open"] = o
    first_close = d[d.bar == first_min - 1].set_index("date").close
    last_open = d[d.bar == 390 - last_min].set_index("date").open
    sess_open = d.groupby("date").open.first()
    sess_close = d.groupby("date").close.last()
    df = pd.DataFrame({"o": sess_open, "fc": first_close,
                       "lo": last_open, "c": sess_close}).dropna()
    df["first_ret"] = df.fc / df.o - 1
    df["last_ret"] = df.c / df.lo - 1
    sig = np.sign(df.first_ret)
    cost = cost_bps * 2 / 10000
    df["r"] = sig * df.last_ret - cost
    df["r_long_only"] = (sig > 0).astype(float) * df.last_ret - (sig > 0) * cost
    return df
