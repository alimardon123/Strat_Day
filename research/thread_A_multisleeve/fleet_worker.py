"""Iteration 4 — cross-sectional fan-out (BLOCKED.md option 2).

Each symbol is an INDEPENDENT concern under the ownership map, so this is the
one part of the study that is safe to parallelise. One process per symbol; no
shared state; the runner only pools the returned rows.

The rule set is FROZEN from the SPY study. Nothing is tuned per symbol. This is
a replication test at scale, not a search.
"""
import numpy as np, pandas as pd, os, warnings
warnings.filterwarnings("ignore")

COST_BPS_PER_SIDE = 2.5          # single stocks, wider than SPY's 1 bp
MIN_BARS = 1200
MIN_PRICE = 5.0
MIN_DOLLAR_VOL = 5e6

GEOMETRIES = [("wide_stop", 2.0, 1.0, 5),
              ("one_to_two", 1.0, 2.0, 10),
              ("tight_1p5", 0.75, 1.5, 10)]


def features(df):
    c, h, l, o = df.close, df.high, df.low, df.open
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    df["atr14"] = tr.ewm(alpha=1/14, adjust=False).mean()
    df["sma50"] = c.rolling(50).mean()
    df["sma200"] = c.rolling(200).mean()
    up = (c > df.sma200) & (df.sma200.diff(20) > 0)
    d_ = c.diff()
    u = d_.clip(lower=0).ewm(alpha=.5, adjust=False).mean()
    dn = (-d_.clip(upper=0)).ewm(alpha=.5, adjust=False).mean()
    rsi2 = 100 - 100 / (1 + u / dn.replace(0, np.nan))
    ibs = (c - l) / (h - l).replace(0, np.nan)
    ll10 = l.rolling(10).min()
    ret = c.pct_change()
    ds = (ret < 0).astype(int).groupby((ret >= 0).cumsum()).cumsum()
    rv = ret.rolling(20).std() * np.sqrt(252)
    vp = rv.rolling(504).rank(pct=True)
    s = pd.Series(0.0, index=df.index)
    s += np.where(rsi2 < 10, .25, 0) + np.where(rsi2 < 5, .10, 0)
    s += np.where(ibs < .20, .20, 0) + np.where(c <= ll10.shift(1), .20, 0)
    s += np.where(ds >= 3, .15, 0) + np.where(c < df.sma50, .10, 0)
    s += np.where(vp < .80, .10, 0) + np.where(vp > .90, -.15, 0)
    df["score"] = s.where(up, 0.0)
    return df


def run_geo(df, sig, stop_m, targ_m, max_hold):
    o, h, l, c = df.open.values, df.high.values, df.low.values, df.close.values
    atr = df.atr14.values
    dates = df.date.values
    n = len(df); cost = COST_BPS_PER_SIDE * 2 / 10000.0
    out = []; i = 0
    sig = np.asarray(sig, bool)
    while i < n - 1:
        if not sig[i] or not np.isfinite(atr[i]) or atr[i] <= 0:
            i += 1; continue
        e = i + 1; entry = o[e]
        if not np.isfinite(entry) or entry <= 0: i += 1; continue
        risk = stop_m * atr[i]
        stop, targ = entry - risk, entry + targ_m * atr[i]
        px = rsn = None
        for j in range(e, min(e + max_hold + 1, n)):
            if j == e and o[j] <= stop: px, rsn = o[j], "gap"
            elif l[j] <= stop: px, rsn = stop, "stop"
            elif h[j] >= targ: px, rsn = targ, "target"
            if px is not None: break
        if px is None:
            j = min(e + max_hold, n - 1); px, rsn = c[j], "time"
        pnl = (px / entry - 1) - cost
        out.append((dates[e], pnl, pnl * entry / risk))
        i = j + 1
    return pd.DataFrame(out, columns=["date", "pnl", "r"])


def worker(path):
    sym = os.path.basename(path).replace(".csv", "")
    try:
        df = pd.read_csv(path)
        df.columns = [x.strip().lower() for x in df.columns]
        if "datetime" not in df.columns: return []
        df["date"] = pd.to_datetime(df["datetime"], errors="coerce")
        df = df.dropna(subset=["date", "open", "high", "low", "close"])
        df = df[["date", "open", "high", "low", "close", "volume"]]
        df = df.sort_values("date").drop_duplicates("date").reset_index(drop=True)
        if len(df) < MIN_BARS: return []
        if df.close.median() < MIN_PRICE: return []
        if (df.close * df.volume).median() < MIN_DOLLAR_VOL: return []
        df["high"] = df[["open", "high", "close"]].max(axis=1)
        df["low"] = df[["open", "low", "close"]].min(axis=1)
        df = features(df)
        rows = []; trades = []
        rng = np.random.default_rng(abs(hash(sym)) % 2**31)
        up = (df.close > df.sma200) & (df.sma200.diff(20) > 0)
        for gname, sm, tm, mh in GEOMETRIES:
            for tier, thr in [("B", 0.35)]:
                t = run_geo(df, (df.score >= thr).values, sm, tm, mh)
                ctrl = run_geo(df, (up & (rng.random(len(df)) < 0.03)).values, sm, tm, mh)
                if len(t) < 5: continue
                rows.append(dict(sym=sym, geo=gname, tier=tier, n=len(t),
                                 bars=len(df),
                                 start=str(df.date.min().date()),
                                 end=str(df.date.max().date()),
                                 meanR=t.r.mean(), sdR=t.r.std(),
                                 win=(t.r > 0).mean(),
                                 ctrl_n=len(ctrl),
                                 ctrl_meanR=ctrl.r.mean() if len(ctrl) > 5 else np.nan,
                                 sumR=t.r.sum(),
                                 first_half=t[t.date < pd.Timestamp("2015-01-01")].r.mean(),
                                 second_half=t[t.date >= pd.Timestamp("2015-01-01")].r.mean(),
                                 n_first=(t.date < pd.Timestamp("2015-01-01")).sum(),
                                 n_second=(t.date >= pd.Timestamp("2015-01-01")).sum()))
                t2 = t.assign(sym=sym, geo=gname); trades.append(t2)
                c2 = ctrl.assign(sym=sym, geo=gname+"_CTRL"); trades.append(c2)
        if trades:
            pd.concat(trades).to_pickle(f"/home/claude/work/tr/{sym}.pkl")
        return rows
    except Exception:
        return []
