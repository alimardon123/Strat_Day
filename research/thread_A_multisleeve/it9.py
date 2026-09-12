"""Iteration 9 — hit the 60% win / 1:1.5+ target where it is actually reachable.

The frontier result from eight iterations: at the level of a SINGLE TRADE, win
rate and payoff are locked together by expectancy. 60% at 1:2 means +0.80R per
trade, which does not exist.

But the target is not actually about single trades — it is about how often the
ACCOUNT is up and by how much relative to down periods. And that quantity is a
function of Sharpe and horizon, not of the trade geometry:

    win rate at horizon T  =  Phi( Sharpe * sqrt(T) )
    payoff ratio           =  E[up] / |E[down]| for that same distribution

A Sharpe of 1.0 gives roughly 61% winning months at about 1:1.4, and roughly 68%
winning quarters at about 1:1.9. So the target is reachable — by raising
portfolio Sharpe, which means more uncorrelated sleeves, not a better rule.

Iteration 8 reached 0.68 full-sample / 1.05 held-out with four sleeves. This
iteration adds two more genuinely different return drivers and measures the
result against the target at every horizon.

  S5 VOLMANAGED  Scale equity exposure inversely to trailing variance
                 (Moreira & Muir). Mechanism: volatility is persistent but
                 expected return is not, so risk-scaling raises Sharpe.
  S6 STREV       Cross-sectional SHORT-TERM reversal: long the past week's
                 losers, short its winners, market-neutral. Mechanism is
                 liquidity provision to flow-driven moves — structurally
                 opposite to the 12-month momentum sleeve.
"""
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
from scipy.stats import norm
from it8 import load_prices, vol_target, s4_turn_of_month, perf, show, COST_BPS


def s5_volmanaged(C, sym="spy", lb=21, target=0.12, cap=2.5):
    r = C[sym].pct_change()
    v = r.rolling(lb).std().shift(1) * np.sqrt(252)
    w = (target / v).clip(upper=cap).fillna(0.0)
    turn = w.diff().abs().fillna(0.0)
    return (w * r).fillna(0.0) - turn * COST_BPS / 10000.0


def s6_strev(C, lb=5, frac=3):
    R = C.pct_change()
    iv = (1.0 / R.rolling(60).std().shift(1)).replace([np.inf, -np.inf], np.nan)
    past = (C / C.shift(lb) - 1).shift(1)
    rk = past.rank(axis=1, pct=True)
    n = past.notna().sum(axis=1)
    lw = ((rk < 1/frac).astype(float) * iv)      # buy the losers
    sw = ((rk > 1 - 1/frac).astype(float) * iv)  # sell the winners
    lw = lw.div(lw.sum(axis=1).replace(0, np.nan), axis=0)
    sw = sw.div(sw.sum(axis=1).replace(0, np.nan), axis=0)
    w = (lw.fillna(0) - sw.fillna(0)).where(n >= 8, 0.0)
    turn = w.diff().abs().sum(axis=1).fillna(0.0)
    return (w * R).sum(axis=1) - turn * COST_BPS / 10000.0


def horizon_stats(r, label, freq):
    """Win rate and payoff ratio at a given aggregation horizon."""
    p = (1 + r).resample(freq).prod() - 1
    p = p[p.notna()]
    if len(p) < 8: return None
    up, dn = p[p > 0], p[p <= 0]
    ratio = up.mean() / abs(dn.mean()) if len(dn) and dn.mean() != 0 else np.inf
    return dict(label=label, freq=freq, n=len(p), win=(p > 0).mean() * 100,
                ratio=ratio, mean=p.mean() * 100, worst=p.min() * 100)


def theoretical(sharpe, periods_per_year):
    """Win rate and payoff a given Sharpe implies at a given horizon."""
    s = sharpe / np.sqrt(periods_per_year)
    win = norm.cdf(s)
    # E[X|X>0] and E[X|X<0] for X ~ N(s,1) in units of sd
    up = s + norm.pdf(s) / (1 - norm.cdf(-s))
    dn = abs(s - norm.pdf(s) / norm.cdf(-s))
    return win * 100, up / dn
