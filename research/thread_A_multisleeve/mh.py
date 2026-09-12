"""Minute-level harness. Built and sanity-tested BEFORE any strategy logic."""
import numpy as np, pandas as pd

COST_TICKS = 0.01 / 5.0   # SPY $0.01 spread ~ 0.2 index points at 1:10 ETF ratio
SLIP_BPS = 0.5


# ------------------------------------------------------------------ session
def build_rth(pkl="/home/claude/work/m1_raw.pkl"):
    d = pd.read_pickle(pkl)
    t = d.time.dt.tz_localize("UTC").dt.tz_convert("America/New_York")
    d = d.assign(ny=t, date=t.dt.date, mins=t.dt.hour * 60 + t.dt.minute)
    d = d[(d.mins >= 570) & (d.mins < 960)].copy()          # 09:30 - 16:00
    d["bar"] = d.mins - 570                                  # 0..389
    # drop days with too few bars (half days, feed outages)
    good = d.groupby("date").bar.size()
    d = d[d.date.isin(good[good >= 300].index)].reset_index(drop=True)
    # session-anchored derived series
    g = d.groupby("date", sort=False)
    d["sess_open"] = g.open.transform("first")
    tp = (d.high + d.low + d.close) / 3
    d["cum_pv"] = (tp * d.volume).groupby(d.date).cumsum()
    d["cum_v"] = d.volume.groupby(d.date).cumsum()
    d["vwap"] = d.cum_pv / d.cum_v.replace(0, np.nan)
    dev = (d.close - d.vwap) ** 2 * d.volume
    d["vwap_sd"] = np.sqrt(dev.groupby(d.date).cumsum() / d.cum_v.replace(0, np.nan))
    d["run_hi"] = g.high.cummax()
    d["run_lo"] = g.low.cummin()
    # prior-session levels (shifted by one day, no lookahead)
    day = d.groupby("date").agg(dh=("high", "max"), dl=("low", "min"),
                                dc=("close", "last"), do=("open", "first"))
    day["atr20"] = (day.dh - day.dl).rolling(20).mean()
    prev = day.shift(1).add_prefix("p_")
    d = d.merge(prev, left_on="date", right_index=True, how="left")
    # opening range, first 30 minutes
    orb = d[d.bar < 30].groupby("date").agg(or_hi=("high", "max"), or_lo=("low", "min"))
    d = d.merge(orb, left_on="date", right_index=True, how="left")
    d["or_rng"] = d.or_hi - d.or_lo
    return d.reset_index(drop=True)


# ------------------------------------------------------------------ backtest
def backtest(d, entries, stop_pts, targ_pts, max_bars, direction=1,
             cost_pts=None, label="", eod_exit=True):
    """entries: bool array. Enter at the OPEN of the NEXT bar.
    Stop/target resolved inside each minute bar; if both are touched in the
    same minute, the STOP is booked. stop_pts/targ_pts are arrays (per-bar)."""
    o, h, l, c = (d.open.values, d.high.values, d.low.values, d.close.values)
    bar, date = d.bar.values, d.date.values
    e = np.asarray(entries, bool)
    sp, tp = np.asarray(stop_pts, float), np.asarray(targ_pts, float)
    n = len(d)
    cp = COST_TICKS * 2 if cost_pts is None else cost_pts
    out = []
    i = 0
    while i < n - 1:
        if not e[i] or not np.isfinite(sp[i]) or sp[i] <= 0:
            i += 1; continue
        j0 = i + 1
        if date[j0] != date[i]:                 # never carry a signal overnight
            i += 1; continue
        entry = o[j0]
        risk = sp[i]
        stop = entry - direction * risk
        targ = entry + direction * tp[i]
        px = rsn = None
        j = j0
        while j < n and date[j] == date[i] and (j - j0) < max_bars:
            if direction == 1:
                if l[j] <= stop: px, rsn = stop, "stop"
                elif h[j] >= targ: px, rsn = targ, "target"
            else:
                if h[j] >= stop: px, rsn = stop, "stop"
                elif l[j] <= targ: px, rsn = targ, "target"
            if px is not None: break
            j += 1
        if px is None:
            j = min(j, n - 1)
            while j > j0 and (date[j] != date[i]): j -= 1
            px, rsn = c[j], ("eod" if bar[j] >= 388 else "time")
        gross = direction * (px - entry)
        slip = entry * SLIP_BPS / 10000.0 * 2
        pnl = gross - cp - slip
        out.append((label, date[i], bar[i], entry, px, rsn, j - j0 + 1,
                    pnl, pnl / risk, risk, direction))
        i = j + 1
    return pd.DataFrame(out, columns=["setup", "date", "bar", "entry", "exit", "reason",
                                      "held", "pnl_pts", "r", "risk_pts", "dir"])


def stats(t, n_days):
    if len(t) == 0: return dict(n=0)
    w, lo = t[t.r > 0], t[t.r <= 0]
    aw = w.r.mean() if len(w) else 0.0
    al = abs(lo.r.mean()) if len(lo) else 0.0
    pf = w.r.sum() / abs(lo.r.sum()) if len(lo) and lo.r.sum() != 0 else np.inf
    eq = t.r.cumsum(); dd = (eq - eq.cummax()).min()
    se = t.r.std() / np.sqrt(len(t))
    return dict(n=len(t), per_day=round(len(t) / n_days, 3),
                win=round((t.r > 0).mean() * 100, 1),
                rr=round(aw / al, 2) if al else np.inf,
                meanR=round(t.r.mean(), 4), pf=round(pf, 2),
                sumR=round(t.r.sum(), 1), ddR=round(dd, 1),
                t=round(t.r.mean() / se, 2) if se > 0 else 0.0,
                held=round(t.held.mean(), 1))


def fmt(name, s):
    if s.get("n", 0) == 0: return f"{name:<40} no trades"
    return (f"{name:<40} n={s['n']:>5} ({s['per_day']:>5}/day) win={s['win']:>5}% "
            f"R:R=1:{s['rr']:<5} meanR={s['meanR']:>+7} PF={s['pf']:<5} "
            f"t={s['t']:>5} sumR={s['sumR']:>7} ddR={s['ddR']}")


# ------------------------------------------------------------------ controls
def random_entries(d, per_day, seed, window=(10, 330)):
    rng = np.random.default_rng(seed)
    ok = (d.bar.values >= window[0]) & (d.bar.values <= window[1])
    p = per_day / (window[1] - window[0])
    return ok & (rng.random(len(d)) < p)


# ------------------------------------------------------------------ sanity
def sanity(build_fn=None):
    """A pure random walk must show ZERO edge through this harness."""
    rng = np.random.default_rng(0)
    days, bpd = 400, 390
    px = 2000 + np.cumsum(rng.normal(0, 0.3, days * bpd))
    hi = px + np.abs(rng.normal(0, 0.15, days * bpd))
    lo = px - np.abs(rng.normal(0, 0.15, days * bpd))
    d = pd.DataFrame(dict(open=px, high=np.maximum(hi, px), low=np.minimum(lo, px),
                          close=px, volume=1,
                          bar=np.tile(np.arange(bpd), days),
                          date=np.repeat(np.arange(days), bpd)))
    res = {}
    for st, tg in [(3.0, 6.0), (6.0, 3.0), (4.0, 4.0)]:
        ent = random_entries(d, 2.0, 42)
        t = backtest(d, ent, np.full(len(d), st), np.full(len(d), tg), 120,
                     cost_pts=0.0)
        s = stats(t, days)
        res[(st, tg)] = s
        exp_win = st / (st + tg) * 100
        print(f"  randomwalk stop={st} targ={tg}: win={s['win']}% "
              f"(theory {exp_win:.1f}%)  meanR={s['meanR']:+.4f}  t={s['t']}")
    return res


if __name__ == "__main__":
    print("SANITY: zero-drift random walk, zero costs. meanR must be ~0 and "
          "win% must match the geometric prior stop/(stop+target).")
    sanity()
