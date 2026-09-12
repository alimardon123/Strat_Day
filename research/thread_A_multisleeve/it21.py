"""Iteration 21 — the system under a LONG-OPTIONS-ONLY constraint.

The prop account can only BUY calls and BUY puts. That eliminates most of the
portfolio outright: betting-against-beta, cross-sectional momentum and
short-term reversal all require short legs; time-series momentum and
volatility-managed equity require holding 25 ETFs; the volatility term-structure
sleeve requires short VXX. None can be done with long options.

What remains is directional index exposure - which is exactly the DipScore
sleeve and the intraday gap-up sleeve. So the question becomes narrow and
answerable: does a +0.13R edge on the underlying survive being expressed as a
long option, after theta and bid-ask?

Options are priced with Black-Scholes using the VIX close as the implied
volatility input. VIX is 30-day ATM implied vol on the S&P, so it is the right
order of magnitude and it moves correctly with regime - which is the part that
matters for this question.
"""
import numpy as np, pandas as pd
from scipy.stats import norm


def bs(S, K, T, r, sigma, kind="c"):
    if T <= 0:
        return max(S - K, 0.0) if kind == "c" else max(K - S, 0.0)
    d1 = (np.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
    d2 = d1 - sigma*np.sqrt(T)
    if kind == "c":
        return S*norm.cdf(d1) - K*np.exp(-r*T)*norm.cdf(d2)
    return K*np.exp(-r*T)*norm.cdf(-d2) - S*norm.cdf(-d1)


def option_trade(S0, S1, iv0, iv1, days_held, dte, moneyness=1.0,
                 kind="c", spread_pct=0.02, r=0.02):
    """Buy at entry, sell at exit. spread_pct is round-trip bid-ask as a
    fraction of premium - 2% is realistic for liquid SPY/SPX near-the-money."""
    K = S0 * moneyness
    T0 = dte/365.0
    T1 = max(dte - days_held, 0)/365.0
    p0 = bs(S0, K, T0, r, iv0, kind)
    p1 = bs(S1, K, T1, r, iv1, kind)
    if p0 <= 0.01:
        return np.nan
    return (p1 * (1 - spread_pct/2) - p0 * (1 + spread_pct/2)) / p0
