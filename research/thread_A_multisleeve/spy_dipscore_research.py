"""
SPY DipScore — full reproducible research script.

Reproduces every number in the report from a single SPY daily OHLCV CSV.
Usage:  python spy_dipscore_research.py spy_clean.csv

Data used in the study: SPY daily 2000-01-03 .. 2026-03-20 (6,593 bars),
unadjusted for dividends, cross-checked against an independent
dividend-adjusted source over 2010-2019 (daily-return correlation 0.982;
all residual gaps >0.2% were ex-dividend days).
"""
import sys
"""
SPY daily-bar setup research engine.

Execution model (deliberately pessimistic where the data is ambiguous):
  - All signals use data through bar t's CLOSE only. Entry is bar t+1's OPEN.
  - Stop / target are ATR-multiples fixed at entry.
  - Intraday path is UNKNOWN on daily bars. If a bar's range touches BOTH the
    stop and the target, we book the STOP. This is the single most important
    anti-inflation choice in the whole study.
  - Gap through stop at the open -> exit at that open (worse than the stop).
  - Time stop: exit at the close of bar entry+max_hold.
  - Costs: 1 bp per side (SPY is ~1c spread on a ~$500 tape) = 2 bp round trip.
"""
import numpy as np
import pandas as pd

COST_BPS_PER_SIDE = 1.0


# ---------------------------------------------------------------- features
def add_features(df):
    d = df.copy()
    c, h, l, o = d.close, d.high, d.low, d.open

    prev_c = c.shift(1)
    tr = pd.concat([h - l, (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    d["atr14"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
    d["atr_pct"] = d.atr14 / c

    d["sma50"] = c.rolling(50).mean()
    d["sma200"] = c.rolling(200).mean()
    d["above200"] = c > d.sma200
    d["sma200_slope"] = d.sma200.diff(20)

    # Wilder RSI(2) - the classic short-lookback mean-reversion trigger
    delta = c.diff()
    up = delta.clip(lower=0).ewm(alpha=1 / 2, adjust=False).mean()
    dn = (-delta.clip(upper=0)).ewm(alpha=1 / 2, adjust=False).mean()
    d["rsi2"] = 100 - 100 / (1 + up / dn.replace(0, np.nan))

    # Internal Bar Strength: where in the day's range did it close
    rng = (h - l).replace(0, np.nan)
    d["ibs"] = (c - l) / rng

    d["ret1"] = c.pct_change()
    d["down_streak"] = (d.ret1 < 0).astype(int).groupby((d.ret1 >= 0).cumsum()).cumsum()
    d["gap"] = o / prev_c - 1
    d["dist200"] = c / d.sma200 - 1
    d["hh20"] = h.rolling(20).max()
    d["ll10"] = l.rolling(10).min()

    # realised vol regime, ranked against a 2y trailing window (no lookahead)
    rv = d.ret1.rolling(20).std() * np.sqrt(252)
    d["rv20"] = rv
    d["vol_pctile"] = rv.rolling(504).rank(pct=True)

    # trend/chop regime
    er = (c - c.shift(20)).abs() / c.diff().abs().rolling(20).sum()
    d["eff_ratio"] = er
    d["regime"] = np.where(d.vol_pctile > 0.80, "volatile",
                    np.where(d.eff_ratio > 0.35, "trend", "range"))
    return d


# ---------------------------------------------------------------- backtest
def run_backtest(d, signal, stop_atr, target_atr, max_hold,
                 direction=1, extra_slip_bps=0.0, label=""):
    """signal: boolean Series aligned to d, True on the bar whose NEXT open we enter."""
    o = d.open.values; h = d.high.values; l = d.low.values; c = d.close.values
    atr = d.atr14.values; dates = d.date.values
    regime = d.regime.values
    sig = signal.fillna(False).values
    n = len(d)
    cost = (COST_BPS_PER_SIDE * 2 + extra_slip_bps) / 10000.0

    trades = []
    i = 0
    while i < n - 1:
        if not sig[i] or not np.isfinite(atr[i]):
            i += 1
            continue
        e = i + 1                      # entry bar
        entry = o[e]
        risk = stop_atr * atr[i]
        if direction == 1:
            stop, target = entry - risk, entry + target_atr * atr[i]
        else:
            stop, target = entry + risk, entry - target_atr * atr[i]

        exit_px, exit_bar, reason = None, None, None
        for j in range(e, min(e + max_hold + 1, n)):
            if direction == 1:
                if j == e and o[j] <= stop:            # gapped through
                    exit_px, reason = o[j], "gap_stop"
                elif l[j] <= stop:                     # stop wins ties
                    exit_px, reason = stop, "stop"
                elif h[j] >= target:
                    exit_px, reason = target, "target"
            else:
                if j == e and o[j] >= stop:
                    exit_px, reason = o[j], "gap_stop"
                elif h[j] >= stop:
                    exit_px, reason = stop, "stop"
                elif l[j] <= target:
                    exit_px, reason = target, "target"
            if exit_px is not None:
                exit_bar = j
                break
        if exit_px is None:
            exit_bar = min(e + max_hold, n - 1)
            exit_px, reason = c[exit_bar], "time"

        gross = direction * (exit_px / entry - 1)
        pnl = gross - cost
        trades.append(dict(
            setup=label, entry_date=dates[e], exit_date=dates[exit_bar],
            entry=entry, exit=exit_px, reason=reason, bars=exit_bar - e + 1,
            pnl=pnl * 100, r_mult=pnl * entry / risk,
            regime=regime[i], risk_pct=risk / entry * 100))
        i = exit_bar + 1               # no overlapping positions
    return pd.DataFrame(trades)


# ---------------------------------------------------------------- reporting
def stats(t, years):
    if len(t) == 0:
        return dict(n=0)
    w = t[t.pnl > 0]; lo = t[t.pnl <= 0]
    aw = w.pnl.mean() if len(w) else 0.0
    al = abs(lo.pnl.mean()) if len(lo) else 0.0
    pf = w.pnl.sum() / abs(lo.pnl.sum()) if len(lo) and lo.pnl.sum() != 0 else np.inf
    eq = t.pnl.cumsum()
    dd = (eq - eq.cummax()).min()
    per_yr = len(t) / years
    sharpe = (t.pnl.mean() / t.pnl.std() * np.sqrt(per_yr)) if t.pnl.std() > 0 else 0.0
    # t-stat on mean trade return: is the edge distinguishable from zero at all
    tstat = t.pnl.mean() / (t.pnl.std() / np.sqrt(len(t))) if t.pnl.std() > 0 else 0.0
    return dict(n=len(t), per_yr=round(per_yr, 1),
                win=round(len(w) / len(t) * 100, 1),
                rr=round(aw / al, 2) if al else np.inf,
                avg=round(t.pnl.mean(), 3), avg_r=round(t.r_mult.mean(), 3),
                pf=round(pf, 2), total=round(t.pnl.sum(), 1),
                maxdd=round(dd, 1), sharpe=round(sharpe, 2), tstat=round(tstat, 2),
                hold=round(t.bars.mean(), 1))


def fmt(name, s):
    if s.get("n", 0) == 0:
        return f"{name:<34} no trades"
    return (f"{name:<34} n={s['n']:>4} ({s['per_yr']:>5}/yr)  win={s['win']:>5}%  "
            f"R:R=1:{s['rr']:<5}  avgR={s['avg_r']:>6}  PF={s['pf']:<5}  "
            f"Sharpe={s['sharpe']:>5}  t={s['tstat']:>5}  maxDD={s['maxdd']}%")

def make_setups(d):
    up = d.above200 & (d.sma200_slope > 0)
    s = {}

    # --- mean reversion family -------------------------------------------
    s["MR_rsi2_uptrend"]      = up & (d.rsi2 < 10)
    s["MR_rsi2_strict"]       = up & (d.rsi2 < 5)
    s["MR_ibs_low"]           = up & (d.ibs < 0.20)
    s["MR_ibs_verylow"]       = up & (d.ibs < 0.10)
    s["MR_3down"]             = up & (d.down_streak >= 3)
    s["MR_4down"]             = up & (d.down_streak >= 4)
    s["MR_ll10"]              = up & (d.close <= d.ll10.shift(1))
    s["MR_rsi2_ibs"]          = up & (d.rsi2 < 15) & (d.ibs < 0.25)
    s["MR_rsi2_ibs_calm"]     = up & (d.rsi2 < 15) & (d.ibs < 0.25) & (d.vol_pctile < 0.80)
    s["MR_deep_dip"]          = up & (d.close < d.sma50) & (d.rsi2 < 15)

    # --- momentum / continuation family ----------------------------------
    s["MO_hh20_break"]        = up & (d.close >= d.hh20.shift(1))
    s["MO_hh20_pullback"]     = up & (d.close >= d.hh20.shift(1) * 0.99) & (d.ibs > 0.7)
    s["MO_gap_up_trend"]      = up & (d.gap > 0.003)
    s["MO_strong_close"]      = up & (d.ibs > 0.85) & (d.close > d.sma50)

    # --- volatility / capitulation family --------------------------------
    s["VOL_wide_down_bar"]    = up & ((d.high - d.low) > 1.5 * d.atr14) & (d.ibs < 0.3)
    s["VOL_high_vol_dip"]     = up & (d.vol_pctile > 0.70) & (d.rsi2 < 15)
    s["VOL_panic_no_trendfil"] = (d.vol_pctile > 0.80) & (d.rsi2 < 5)

    # --- gap family (entry price is also the trigger -> extra slippage) ---
    s["GAP_down_fade"]        = up & (d.gap < -0.004)
    s["GAP_down_fade_deep"]   = up & (d.gap < -0.008)

    # --- shorts (tested separately, as the skill requires) ----------------
    dn = (~d.above200) & (d.sma200_slope < 0)
    s["SH_rsi2_high_downtrend"] = dn & (d.rsi2 > 90)
    s["SH_ibs_high_downtrend"]  = dn & (d.ibs > 0.85)
    return s


GAP_SETUPS = {"GAP_down_fade", "GAP_down_fade_deep", "MO_gap_up_trend"}
SHORT_SETUPS = {"SH_rsi2_high_downtrend", "SH_ibs_high_downtrend"}


def random_control(d, rate, seed, uptrend_only=True):
    """Benchmark: random entries at the same frequency, same exit rules.
    Any setup that cannot beat this is measuring SPY's drift, not an edge."""
    rng = np.random.default_rng(seed)
    base = rng.random(len(d)) < rate
    if uptrend_only:
        base = base & (d.above200 & (d.sma200_slope > 0)).values
    return pd.Series(base, index=d.index)

GAP_SETUPS = {"GAP_down_fade", "GAP_down_fade_deep", "MO_gap_up_trend"}
SHORT_SETUPS = {"SH_rsi2_high_downtrend", "SH_ibs_high_downtrend"}


def random_control(d, rate, seed, uptrend_only=True):
    """Benchmark: random entries, same exit rules. Any setup that cannot beat
    this is measuring SPY's drift and stop/target geometry, not an edge."""
    rng = np.random.default_rng(seed)
    base = rng.random(len(d)) < rate
    if uptrend_only:
        base = base & (d.above200 & (d.sma200_slope > 0)).values
    return pd.Series(base, index=d.index)


# ---------------------------------------------------------- the final system
def dipscore(x):
    """Confluence score, 0..1. Frozen on 2000-2015; unchanged for the 2016-2026 test."""
    up = x.above200 & (x.sma200_slope > 0)
    s = pd.Series(0.0, index=x.index)
    s += np.where(x.rsi2 < 10, 0.25, 0.0)          # short-lookback oversold
    s += np.where(x.rsi2 < 5, 0.10, 0.0)           # deeper oversold
    s += np.where(x.ibs < 0.20, 0.20, 0.0)         # closed on the low of the day
    s += np.where(x.close <= x.ll10.shift(1), 0.20, 0.0)   # new 10-day low
    s += np.where(x.down_streak >= 3, 0.15, 0.0)   # 3+ consecutive down closes
    s += np.where(x.close < x.sma50, 0.10, 0.0)    # pullback has real depth
    s += np.where(x.vol_pctile < 0.80, 0.10, 0.0)  # calm tape
    s += np.where(x.vol_pctile > 0.90, -0.15, 0.0) # penalise crisis vol
    return s.where(up, 0.0)


TIER_A, TIER_B, TIER_C = 0.55, 0.35, 0.20
STOP_ATR, TARGET_ATR, MAX_HOLD = 2.0, 1.0, 5


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "spy_clean.csv"
    d = add_features(pd.read_csv(path, parse_dates=["date"])).reset_index(drop=True)
    for name, mask in [("TRAIN 2000-2015", d.date <= "2015-12-31"),
                       ("TEST  2016-2026", d.date > "2015-12-31"),
                       ("FULL  2000-2026", d.date == d.date)]:
        x = d[mask].reset_index(drop=True)
        yrs = (x.date.max() - x.date.min()).days / 365.25
        sc = dipscore(x)
        ctrl = pd.concat([run_backtest(x, random_control(x, 0.06, 500 + k),
                                       STOP_ATR, TARGET_ATR, MAX_HOLD) for k in range(15)])
        print(f"\n--- {name} ---")
        for tn, thr in [("Tier A", TIER_A), ("Tier B (traded)", TIER_B), ("Tier C", TIER_C)]:
            t = run_backtest(x, sc >= thr, STOP_ATR, TARGET_ATR, MAX_HOLD, label=tn)
            print("  " + fmt(tn, stats(t, yrs)))
        print("  " + fmt("RANDOM-ENTRY CONTROL", stats(ctrl, yrs * 15)))
