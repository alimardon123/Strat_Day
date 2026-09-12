"""Iteration 7 — a genuinely better SYSTEM, not a better rule.

Six iterations established that the per-trade edge is capped at roughly +0.08 to
+0.13R and cannot be improved by changing rules, resolution, or geometry. What
iteration 6 also established is that the binding constraint is the number of
INDEPENDENT BETS, which was 1.28 across 26 index ETFs.

That points at the one improvement the evidence supports: hold the rule fixed and
raise n_eff by trading decorrelated asset classes simultaneously. Per-trade edge
stays the same; portfolio Sharpe rises with the square root of the number of
independent bets. That is a better trading system by the only lever left.

Universe spans equity (US / developed / EM / single-country), duration, credit,
inflation, precious metals, broad commodities, energy, agriculture, currencies
and real estate.
"""
import numpy as np, pandas as pd, os, warnings
warnings.filterwarnings("ignore")

D = "/home/claude/etfs/CMSC320_Final_Tutorial_Huge_Stock_Market_Dataset-main/ETFs"
COST_BPS = 2.0

SLEEVES = {
    "US equity":      ["spy"],
    "Dev ex-US":      ["efa", "ewj"],
    "EM equity":      ["eem", "ewz"],
    "Duration":       ["tlt", "ief"],
    "Credit":         ["lqd", "hyg"],
    "Inflation":      ["tip"],
    "Precious":       ["gld", "slv", "gdx"],
    "Commodities":    ["dbc", "dba"],
    "Energy":         ["uso", "xop"],
    "FX":             ["uup", "fxe", "fxy", "fxb"],
    "Real estate":    ["vnq", "rwx"],
}
ALL = [s for v in SLEEVES.values() for s in v]


def load(sym):
    p = f"{D}/{sym}.us.txt"
    if not os.path.exists(p): return None
    d = pd.read_csv(p); d.columns = [c.strip().lower() for c in d.columns]
    d["date"] = pd.to_datetime(d.date, errors="coerce")
    d = d.dropna(subset=["date", "open", "high", "low", "close"]).sort_values("date")
    d = d.drop_duplicates("date").reset_index(drop=True)
    if len(d) < 1200: return None
    d["high"] = d[["open", "high", "close"]].max(axis=1)
    d["low"] = d[["open", "low", "close"]].min(axis=1)
    return d[["date", "open", "high", "low", "close", "volume"]]


def dipscore(df):
    c, h, l = df.close, df.high, df.low
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    df["atr14"] = tr.ewm(alpha=1/14, adjust=False).mean()
    df["sma50"] = c.rolling(50).mean(); df["sma200"] = c.rolling(200).mean()
    up = (c > df.sma200) & (df.sma200.diff(20) > 0)
    d_ = c.diff()
    u = d_.clip(lower=0).ewm(alpha=.5, adjust=False).mean()
    dn = (-d_.clip(upper=0)).ewm(alpha=.5, adjust=False).mean()
    rsi2 = 100 - 100/(1 + u/dn.replace(0, np.nan))
    ibs = (c - l)/(h - l).replace(0, np.nan)
    ll10 = l.rolling(10).min(); ret = c.pct_change()
    ds = (ret < 0).astype(int).groupby((ret >= 0).cumsum()).cumsum()
    vp = (ret.rolling(20).std()*np.sqrt(252)).rolling(504).rank(pct=True)
    s = pd.Series(0.0, index=df.index)
    s += np.where(rsi2 < 10, .25, 0) + np.where(rsi2 < 5, .10, 0)
    s += np.where(ibs < .20, .20, 0) + np.where(c <= ll10.shift(1), .20, 0)
    s += np.where(ds >= 3, .15, 0) + np.where(c < df.sma50, .10, 0)
    s += np.where(vp < .80, .10, 0) + np.where(vp > .90, -.15, 0)
    df["score"] = s.where(up, 0.0); df["up"] = up
    return df


def trades(df, sig, sm=2.0, tm=1.0, mh=5, cost_bps=COST_BPS):
    """Returns one row per trade with the DAILY R path, so trades can be
    aggregated into a portfolio equity curve rather than just averaged."""
    o, h, l, c = df.open.values, df.high.values, df.low.values, df.close.values
    atr = df.atr14.values; dt = df.date.values; n = len(df)
    cost = cost_bps*2/10000
    out = []; i = 0; sig = np.asarray(sig, bool)
    while i < n-1:
        if not sig[i] or not np.isfinite(atr[i]) or atr[i] <= 0: i += 1; continue
        e = i+1; entry = o[e]; risk = sm*atr[i]
        stop, targ = entry-risk, entry+tm*atr[i]; px = None
        for j in range(e, min(e+mh+1, n)):
            if j == e and o[j] <= stop: px = o[j]
            elif l[j] <= stop: px = stop
            elif h[j] >= targ: px = targ
            if px is not None: break
        if px is None: j = min(e+mh, n-1); px = c[j]
        p = (px/entry-1) - cost
        out.append((dt[e], dt[j], p, p*entry/risk)); i = j+1
    return pd.DataFrame(out, columns=["entry_date", "exit_date", "pnl", "r"])
