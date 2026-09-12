"""Iteration 8 — diversify the RULE.

Iteration 7 proved that spreading one long-only dip-buying rule across 23 asset
classes does not diversify the bet: realised strategy-return correlation was
0.529 against underlying price correlation of 0.198. The rule manufactures its
own common factor.

So this iteration builds four strategies with structurally DIFFERENT return
profiles and combines them. Each is a documented, mechanism-backed regularity,
not a mined pattern:

  S1 MEANREV   DipScore dip-buying in confirmed uptrends. Long-only. Makes money
               in grinding bull markets, loses in sustained declines.
  S2 TSMOM     Time-series momentum: hold each asset only while its own 12-month
               return is positive, else hold cash. The classic crisis-alpha
               profile — it exits falling markets by construction, which is the
               direct answer to "works in any market condition".
  S3 XSMOM     Cross-sectional momentum: long the strongest third of the
               universe, short the weakest third, market-neutral by construction.
               Its return does not depend on market direction at all.
  S4 TURNMONTH Turn-of-the-month effect: hold equity from the last trading day
               of a month through the third of the next. Driven by payroll and
               pension inflows — a flow mechanism, not a price pattern. This is
               the closest thing to the "human-behaviour rule" hypothesis, and
               it is testable.

Everything is expressed as a daily return on capital so the four can be
volatility-targeted and combined. Vol targeting uses a trailing 60-day estimate
lagged one day; no lookahead anywhere.
"""
import numpy as np, pandas as pd, os, warnings
warnings.filterwarnings("ignore")

D = "/home/claude/etfs/CMSC320_Final_Tutorial_Huge_Stock_Market_Dataset-main/ETFs"
UNIVERSE = ["spy", "efa", "eem", "ewj", "ewz", "ewa", "tlt", "ief", "lqd", "hyg",
            "tip", "gld", "slv", "gdx", "dbc", "dba", "uso", "xop", "uup", "fxe",
            "fxy", "fxb", "vnq", "rwx", "iyr"]
COST_BPS = 2.0
TARGET_VOL = 0.10


def load_prices():
    out = {}
    for s in UNIVERSE:
        p = f"{D}/{s}.us.txt"
        if not os.path.exists(p): continue
        d = pd.read_csv(p); d.columns = [c.strip().lower() for c in d.columns]
        d["date"] = pd.to_datetime(d.date, errors="coerce")
        d = d.dropna(subset=["date", "close"]).sort_values("date").drop_duplicates("date")
        if len(d) < 1200: continue
        out[s] = d.set_index("date")[["open", "high", "low", "close"]]
    C = pd.concat({k: v.close for k, v in out.items()}, axis=1).sort_index()
    return out, C


def vol_target(r, target=TARGET_VOL, lb=60, cap=3.0):
    """Scale a daily return stream to a constant target vol using only past data."""
    v = r.rolling(lb).std().shift(1) * np.sqrt(252)
    lev = (target / v).clip(upper=cap).fillna(0.0)
    return r * lev


def s2_tsmom(C, lookback=252):
    """Long each asset while its own trailing 12m return is positive, else flat."""
    r = C.pct_change()
    sig = (C / C.shift(lookback) - 1 > 0).shift(1).astype(float)
    sig = sig.where(C.shift(lookback).notna())
    w = sig.div(sig.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    turn = w.diff().abs().sum(axis=1).fillna(0.0)
    return (w * r).sum(axis=1) - turn * COST_BPS / 10000.0


def s3_xsmom(C, lookback=252, frac=3):
    """Long top third / short bottom third by trailing return. Market-neutral."""
    r = C.pct_change()
    mom = (C / C.shift(lookback) - 1).shift(1)
    rk = mom.rank(axis=1, pct=True)
    n = mom.notna().sum(axis=1)
    lw = (rk > 1 - 1/frac).astype(float); sw = (rk < 1/frac).astype(float)
    lw = lw.div(lw.sum(axis=1).replace(0, np.nan), axis=0)
    sw = sw.div(sw.sum(axis=1).replace(0, np.nan), axis=0)
    w = (lw.fillna(0) - sw.fillna(0)).where(n >= 8, 0.0)
    turn = w.diff().abs().sum(axis=1).fillna(0.0)
    return (w * r).sum(axis=1) - turn * COST_BPS / 10000.0


def s4_turn_of_month(C, sym="spy", days_before=1, days_after=3):
    """Hold equity across the month boundary only. A flow effect, not a pattern."""
    px = C[sym].dropna()
    r = px.pct_change()
    idx = pd.Series(np.arange(len(px)), index=px.index)
    month = px.index.to_period("M")
    last_of_month = idx.groupby(month).max()
    hold = pd.Series(False, index=px.index)
    for pos in last_of_month.values:
        lo = max(0, pos - days_before + 1); hi = min(len(px) - 1, pos + days_after)
        hold.iloc[lo:hi + 1] = True
    w = hold.shift(1).fillna(False).astype(float)
    turn = w.diff().abs().fillna(0.0)
    return (w * r).fillna(0.0) - turn * COST_BPS / 10000.0


def perf(r, label, ann=252):
    r = r.dropna()
    if len(r) < 100 or r.std() == 0:
        return None
    yrs = len(r) / ann
    cum = (1 + r).cumprod()
    cagr = cum.iloc[-1] ** (1 / yrs) - 1
    vol = r.std() * np.sqrt(ann)
    sh = r.mean() / r.std() * np.sqrt(ann)
    dd = (cum / cum.cummax() - 1).min()
    dn = r[r < 0].std() * np.sqrt(ann)
    sor = r.mean() * ann / dn if dn > 0 else np.nan
    return dict(label=label, cagr=cagr, vol=vol, sharpe=sh, sortino=sor,
                maxdd=dd, calmar=cagr / abs(dd) if dd < 0 else np.nan,
                exposure=(r != 0).mean())


def show(p):
    if p is None: return
    print(f"  {p['label']:<30} CAGR={p['cagr']*100:>6.2f}%  vol={p['vol']*100:>5.2f}%  "
          f"Sharpe={p['sharpe']:>5.2f}  Sortino={p['sortino']:>5.2f}  "
          f"maxDD={p['maxdd']*100:>7.2f}%  Calmar={p['calmar']:>5.2f}  "
          f"exposure={p['exposure']*100:>4.0f}%")
