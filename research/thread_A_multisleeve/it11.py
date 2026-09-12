"""Iteration 11 — act on the two recommendations that survived iteration 10.

Iteration 10 concluded: more conditioning fails, only new UNCORRELATED sleeves
have ever moved Sharpe (n_eff 1.78 -> 2.42 -> 2.89 tracked Sharpe 0.46 -> 0.68
-> 0.77). So build two sleeves from a data source the portfolio has never
touched: the 626-name single-stock panel, 2000-2026.

Both are market-neutral by construction, so neither can inherit the long-equity
factor that iteration 7 showed contaminates everything else.

  S8 BAB    Betting-against-beta / low-volatility. Long low-vol stocks, short
            high-vol stocks, beta-balanced. Mechanism: leverage-constrained
            investors bid up high-beta names, so low-beta names are
            systematically cheap. Documented since Black (1972).
  S9 STREV  Stock-level short-term reversal: long last week's losers, short its
            winners. Mechanism: compensation for providing liquidity to
            flow-driven moves. Much stronger in single names than across assets,
            where iteration 9's S6 version failed.
"""
import numpy as np, pandas as pd, pickle, warnings
warnings.filterwarnings("ignore")

COST_BPS = 5.0     # single stocks, both legs


def load_stock_panel():
    O, H, L, C = pickle.load(open("panel_clean.pkl", "rb"))
    return C


def build_sleeves(C, mkt):
    R = C.pct_change()
    R = R.where(R.abs() < 0.5)                      # artifact mask, as iteration 5
    out = {}

    # --- S8 BAB: rank by trailing 252d beta to the equal-weight market ---
    m = mkt.reindex(R.index)
    cov = R.rolling(252).cov(m)
    var = m.rolling(252).var()
    beta = (cov.div(var, axis=0)).shift(1)
    rk = beta.rank(axis=1, pct=True)
    n = beta.notna().sum(axis=1)
    lo = (rk < 0.30).astype(float)                  # low beta -> long
    hi = (rk > 0.70).astype(float)                  # high beta -> short
    # beta-balance the two legs so the sleeve is market-neutral
    bl = (lo * beta).sum(axis=1) / lo.sum(axis=1).replace(0, np.nan)
    bh = (hi * beta).sum(axis=1) / hi.sum(axis=1).replace(0, np.nan)
    lw = lo.div(lo.sum(axis=1).replace(0, np.nan), axis=0).div(bl.abs().clip(0.2), axis=0)
    sw = hi.div(hi.sum(axis=1).replace(0, np.nan), axis=0).div(bh.abs().clip(0.2), axis=0)
    w = (lw.fillna(0) - sw.fillna(0)).where(n >= 100, 0.0)
    w = w.div(w.abs().sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    mo = ~w.index.to_period("M").duplicated()       # monthly rebalance keeps costs sane
    w = w.where(pd.Series(mo, index=w.index)).ffill().fillna(0.0)
    turn = w.diff().abs().sum(axis=1).fillna(0.0)
    out["S8_BAB"] = (w * R).sum(axis=1).fillna(0) - turn * COST_BPS / 10000

    # --- S9 stock-level short-term reversal, weekly rebalance ---
    past = (C / C.shift(5) - 1).shift(1)
    rk2 = past.rank(axis=1, pct=True)
    n2 = past.notna().sum(axis=1)
    lw2 = (rk2 < 0.20).astype(float); sw2 = (rk2 > 0.80).astype(float)
    lw2 = lw2.div(lw2.sum(axis=1).replace(0, np.nan), axis=0)
    sw2 = sw2.div(sw2.sum(axis=1).replace(0, np.nan), axis=0)
    w2 = (lw2.fillna(0) - sw2.fillna(0)).where(n2 >= 100, 0.0)
    wk = ~w2.index.to_period("W").duplicated()
    w2 = w2.where(pd.Series(wk, index=w2.index)).ffill().fillna(0.0)
    turn2 = w2.diff().abs().sum(axis=1).fillna(0.0)
    out["S9_STOCKREV"] = (w2 * R).sum(axis=1).fillna(0) - turn2 * COST_BPS / 10000
    return pd.DataFrame(out)
