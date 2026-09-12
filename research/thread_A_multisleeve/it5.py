"""Iteration 5 — does DIVERSIFICATION restore the edge?

ASSESSMENT_iteration4 §5 left one question open: is the SPY edge index-specific,
or was it luck? No index-ETF data is reachable here, so instead of proxying an
index I test the mechanism that would make an index different from a stock —
diversification away of idiosyncratic risk.

Construction: sample k names, equal-weight their daily returns, chain to a level
series. High/low come from the equal-weighted average of each member's
high/prev_close and low/prev_close, which slightly UNDERSTATES the basket's true
intraday range (members' extremes do not occur simultaneously) and therefore
makes stops slightly harder to hit and targets slightly harder to reach — a
known, stated, and roughly symmetric approximation.

If the excess-over-control rises monotonically with k and survives a held-out
period, the index-specific hypothesis is supported. If it stays flat at zero,
the SPY result was one instrument's luck.
"""
import numpy as np, pandas as pd, glob, os, warnings
warnings.filterwarnings("ignore")

COST_BPS_PER_SIDE = 1.0     # index-level: back to SPY-like friction


def load_panel(src="/home/claude/xs/big_movers-main/collected_stocks/*.csv"):
    o = {}; h = {}; l = {}; c = {}
    for p in glob.glob(src):
        sym = os.path.basename(p)[:-4]
        try:
            df = pd.read_csv(p)
            df.columns = [x.strip().lower() for x in df.columns]
            if "datetime" not in df.columns: continue
            df["date"] = pd.to_datetime(df["datetime"], errors="coerce")
            df = df.dropna(subset=["date", "open", "high", "low", "close"])
            df = df.sort_values("date").drop_duplicates("date").set_index("date")
            if len(df) < 1200 or df.close.median() < 5: continue
            if (df.close * df.volume).median() < 5e6: continue
            o[sym], h[sym], l[sym], c[sym] = df.open, df.high, df.low, df.close
        except Exception:
            continue
    C = pd.DataFrame(c).sort_index()
    return (pd.DataFrame(o).reindex(C.index), pd.DataFrame(h).reindex(C.index),
            pd.DataFrame(l).reindex(C.index), C)


def make_index(O, H, L, C, cols):
    """Equal-weight basket -> chained OHLC level series."""
    pc = C[cols].shift(1)
    r_c = (C[cols] / pc - 1)
    r_o = (O[cols] / pc - 1)
    r_h = (H[cols] / pc - 1)
    r_l = (L[cols] / pc - 1)
    valid = r_c.notna().sum(axis=1)
    m_c = r_c.mean(axis=1); m_o = r_o.mean(axis=1)
    m_h = r_h.mean(axis=1); m_l = r_l.mean(axis=1)
    keep = valid >= max(3, int(0.6 * len(cols)))
    m_c = m_c[keep]; m_o = m_o[keep]; m_h = m_h[keep]; m_l = m_l[keep]
    lvl = 100 * (1 + m_c).cumprod()
    prev = lvl.shift(1).fillna(100)
    df = pd.DataFrame({"date": lvl.index,
                       "open": prev * (1 + m_o), "high": prev * (1 + m_h),
                       "low": prev * (1 + m_l), "close": lvl.values}).reset_index(drop=True)
    df["high"] = df[["open", "high", "close"]].max(axis=1)
    df["low"] = df[["open", "low", "close"]].min(axis=1)
    return df.dropna().reset_index(drop=True)


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


def run(df, sig, sm, tm, mh):
    o, h, l, c = df.open.values, df.high.values, df.low.values, df.close.values
    atr = df.atr14.values; dt = df.date.values; n = len(df)
    cost = COST_BPS_PER_SIDE*2/10000.0
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
        if px is None:
            j = min(e+mh, n-1); px = c[j]
        pnl = (px/entry - 1) - cost
        out.append((dt[e], pnl, pnl*entry/risk)); i = j+1
    return pd.DataFrame(out, columns=["date", "pnl", "r"])
